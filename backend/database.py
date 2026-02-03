from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime, timedelta

from models import PredictionLog

# Replace with your actual MySQL credentials from your PHP configuration
# Example from your search.php: server="127.0.0.1", user="root", database="stocksdata"
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@127.0.0.1:3306/stocksdata"

# pool_size and max_overflow help manage the connection pool for multiple routers
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_size=10, 
    max_overflow=20,
    pool_pre_ping=True
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
    """Retrieves the last X price points for a token."""
    query = sql_text("""
        SELECT price FROM stocks 
        WHERE symbol = :s 
        ORDER BY datetime DESC LIMIT :l
    """)
    rows = db.execute(query, {"s": symbol.upper(), "l": limit}).mappings().all()
    
    # We get them DESC (newest first), so we reverse to get chronological order
    return [float(r['price']) for r in rows][::-1]

def db_save_price(symbol: str, price: float, dt: str, db: Session):
    """Unified database saver with conflict resolution."""
    query = sql_text("""
        INSERT INTO stocks (symbol, price, datetime) 
        VALUES (:s, :p, :dt)
        ON DUPLICATE KEY UPDATE price = VALUES(price)
    """)
    db.execute(query, {"s": symbol, "p": price, "dt": dt})
    db.commit()

def save_prediction_to_db(symbol: str, sentiment: str, confidence: float, price: float, db: Session):
    """Persists Lucy's analytical thoughts for the Judge to evaluate later."""
    new_prediction = PredictionLog(
        symbol=symbol.upper(),
        predicted_sentiment=sentiment, # "BULLISH" or "BEARISH"
        confidence=confidence,           # e.g., 0.85
        price_at_prediction=price,
        is_evaluated=False
    )
    db.add(new_prediction)
    db.commit()
    db.refresh(new_prediction)
    return new_prediction