from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, Float, String, Integer, Boolean, func, Text
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
    address = Column(Text, nullable=True)              # Contract / mint for DEX lookups
    chain = Column(String(32), nullable=True)          # DexScreener chain slug (ethereum, solana, bsc, ...)
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


class AlternativeData(Base):
    __tablename__ = "alternative_data"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), index=True)
    job_postings = Column(Integer, default=0)
    web_traffic_visits = Column(Integer, default=0)
    timestamp = Column(DateTime, default=func.now())


class RegulatoryAlert(Base):
    __tablename__ = "regulatory_alerts"
    id = Column(Integer, primary_key=True)
    authority = Column(String(50), index=True)  # e.g. "SEC", "FCA"
    title = Column(String(255))
    url = Column(Text)
    summary = Column(Text)
    severity = Column(String(20))  # "Low", "Medium", "High", "Critical"
    timestamp = Column(DateTime, default=func.now())


class CompetitivePricing(Base):
    __tablename__ = "competitive_pricing"
    id = Column(Integer, primary_key=True)
    item_name = Column(String(100), index=True)  # e.g., "Nvidia H100", "RTX 4090"
    price = Column(Float)
    source = Column(String(50))
    timestamp = Column(DateTime, default=func.now())


class CorporateRisk(Base):
    __tablename__ = "corporate_risk"
    id = Column(Integer, primary_key=True)
    company_name = Column(String(100), index=True)
    leadership_signals = Column(Text)
    financial_health = Column(Text)
    timestamp = Column(DateTime, default=func.now())


class SectorIntelligence(Base):
    __tablename__ = "sector_intelligence"
    id = Column(Integer, primary_key=True)
    sector_name = Column(String(50), index=True)
    synthesis_json = Column(Text)
    timestamp = Column(DateTime, default=func.now())

