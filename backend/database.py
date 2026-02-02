from sqlalchemy import create_engine, Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

Base = declarative_base()

# Dependency to get a DB session across all routers
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class TokenMap(Base):
    __tablename__ = "token_map"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True) # e.g., "BTC"
    coingecko_id = Column(String(50))                   # e.g., "bitcoin"
    pyth_id = Column(String(100), nullable=True)        # The 0x... hex string
    is_active = Column(Boolean, default=True)