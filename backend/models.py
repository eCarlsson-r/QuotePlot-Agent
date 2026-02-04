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
    datetime = Column(DateTime, default=func.now(), index=True) 
    
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

    def __repr__(self):
        return f"<TokenMap(symbol='{self.symbol}', active={self.is_active})>"

class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True)
    predicted_sentiment = Column(String(20)) # "Bullish" or "Bearish"
    confidence = Column(Float)
    price_at_prediction = Column(Float)
    timestamp = Column(DateTime, default=func.now())
    was_correct = Column(Boolean, nullable=True) # To be updated after 1 hour
    was_evaluated = Column(Boolean, default=False)
    actual_price_later = Column(Float, nullable=True)

class InvestorBehavior(Base):
    __tablename__ = "investor_behavior"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), index=True)
    flow_type = Column(String(50))  # e.g., "Exchange Inflow" (Bearish) or "Cold Storage" (Bullish)
    volume = Column(Float)
    timestamp = Column(DateTime, default=func.now())