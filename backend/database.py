from sqlalchemy import create_engine
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