from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.orm import Session, sessionmaker

from models import InvestorBehavior, PredictionLog, Stock

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