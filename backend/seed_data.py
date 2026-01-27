import sqlalchemy
from database import engine
from datetime import datetime, timedelta
import random

def seed_stocks():
    # We will use raw SQL to match your agent's query style
    symbols = ["BTC", "ETH", "SOL", "AAPL", "TSLA"]
    
    with engine.connect() as conn:
        print("🌱 Seeding stock data...")
        
        for sym in symbols:
            # Generate 15 rows for each symbol (agent asks for last 10)
            base_price = random.uniform(50, 50000)
            
            for i in range(15):
                # Create a slight trend
                price_variation = random.uniform(-0.02, 0.03) 
                current_price = base_price * (1 + price_variation)
                # Spread them out by 1 hour each
                dt = datetime.now() - timedelta(hours=i)
                
                query = sqlalchemy.text("""
                    INSERT INTO stocks (symbol, price, datetime) 
                    VALUES (:s, :p, :dt)
                """)
                conn.execute(query, {"s": sym, "p": current_price, "dt": dt})
        
        conn.commit()
        print("✅ Database populated!")

if __name__ == "__main__":
    seed_stocks()