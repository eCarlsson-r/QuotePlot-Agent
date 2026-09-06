from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.orm import Session, sessionmaker
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from backend.models import InvestorBehavior, PredictionLog, Stock

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DB_URL")
if not SQLALCHEMY_DATABASE_URL:
    user = os.getenv("DB_USER", "root")
    password = quote_plus(os.getenv("DB_PASS", ""))
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "quoteplot")
    SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"

# pool_size and max_overflow help manage the connection pool for multiple routers
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,          # 5 persistent connections — enough for 1 uvicorn worker
    max_overflow=10,      # Up to 10 extra on burst (APScheduler + concurrent requests)
    pool_timeout=30,      # Wait max 30s for a connection before raising
    pool_recycle=1800,    # Recycle connections every 30 min — prevents MySQL 8h timeout drop
    pool_pre_ping=True,   # Verify connection alive before using (catches dropped connections)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get a DB session across all routers
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_recent_prices(symbol: str, db: Session, limit: int = 10):
    return db.query(Stock).filter(Stock.symbol == symbol).order_by(Stock.datetime.desc()).limit(limit).all()

def db_save_price(symbol: str, price: float, dt: str, db: Session):
    """Unified database saver with conflict resolution."""
    query = sql_text("""
        INSERT INTO stocks (symbol, price, datetime) 
        VALUES (:s, :p, :dt)
        ON DUPLICATE KEY UPDATE price = VALUES(price)
    """)
    db.execute(query, {"s": symbol, "p": price, "dt": dt})
    db.commit()

def db_save_behavior(data: InvestorBehavior, db: Session):
    """Unified database saver with conflict resolution."""
    query = sql_text("""
        INSERT INTO investor_behavior (symbol, flow_type, volume, timestamp) 
        VALUES (:s, :ft, :v, :ts)
        ON DUPLICATE KEY UPDATE volume = VALUES(volume)
    """)
    db.execute(query, {"s": data['symbol'], "ft": data['flow_type'], "v": data['volume'], "ts": data['timestamp']})
    db.commit()

def save_prediction_to_db(symbol: str, sentiment: str, confidence: float, price: float, db: Session):
    """Persists Lucy's analytical thoughts for the Judge to evaluate later."""
    new_prediction = PredictionLog(
        symbol=symbol.upper(),
        predicted_sentiment=sentiment, # "BULLISH" or "BEARISH"
        confidence=confidence,           # e.g., 0.85
        price_at_prediction=price,
        was_evaluated=False,
        was_correct=None # Explicitly Null until evaluated
    )
    db.add(new_prediction)
    db.commit()
    db.refresh(new_prediction)
    return new_prediction