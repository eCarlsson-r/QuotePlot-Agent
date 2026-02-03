from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, Float, String, Integer, Boolean, func
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True)  # e.g., "BTC", "ETH"
    price = Column(Float, nullable=False)
    datetime = Column(DateTime, default=datetime.utcnow, index=True) 
    
    # Optional: If you want to support Candlestick charts later
    # open = Column(Float)
    # high = Column(Float)
    # low = Column(Float)
    # volume = Column(Float)

class TokenMap(Base):
    __tablename__ = "token_map"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True) # e.g., "BTC"
    coingecko_id = Column(String(50))                   # e.g., "bitcoin"
    pyth_id = Column(String(100), nullable=True)        # The 0x... hex string
    is_active = Column(Boolean, default=True)

class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True)
    predicted_sentiment = Column(String(20)) # "Bullish" or "Bearish"
    confidence = Column(Float)
    price_at_prediction = Column(Float)
    timestamp = Column(DateTime, default=func.now())
    was_correct = Column(Boolean, nullable=True) # To be updated after 1 hour