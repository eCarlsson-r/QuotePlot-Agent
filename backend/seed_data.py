from utils import get_tokens
from database import SessionLocal, engine
from sqlalchemy import func
from models import Base, InvestorBehavior, TokenMap   # Ensure TokenMap is defined in models.py
import random
from datetime import datetime
import asyncio

async def seed_web3_tokens():
    db = SessionLocal()
    raw_token_data = await get_tokens();
    
    if not raw_token_data:
        print("⚠️ Warning: Token list is empty. Check your API/Utility.")
        return
    for data in raw_token_data:
        # 1. Normalize Symbol (Crucial for MySQL/Foreign Keys)
        sym = data.get("symbol")
        cg_id = data.get("cg_id")
        
        existing = db.query(TokenMap).filter(TokenMap.symbol == sym).first()
        
        if not existing:
            new_entry = TokenMap(
                symbol=sym,
                coingecko_id=cg_id, # Use .get() to prevent KeyErrors
                pyth_id=data.get("pyth_id"),
                is_active=True
            )
            db.add(new_entry)
            # Flush tells MySQL about the change without finishing the transaction
            db.flush() 
            print(f"✅ Added {sym} (CG: {cg_id})")
        else:
            print(f"⏩ {existing.symbol} already exists.")
    
    db.commit() # Save everything once loop is safe
    print("🏁 Token seeding successful.")

def seed_whale_data():
    db = SessionLocal()
    # We'll pull symbols directly from the tokens we just seeded
    active_symbols = [t.symbol for t in db.query(TokenMap).all()]
    
    for symbol in active_symbols:
        # Create a "Whale Accumulation" pattern for testing
        for _ in range(5):
            move = InvestorBehavior(
                symbol=symbol,
                flow_type="Cold Storage", # Bullish signal
                volume=random.uniform(100, 500),
                timestamp=func.now()
            )
            db.add(move)
    db.commit()
    db.close()
    print("🐋 Whale flows seeded. Lucy can now detect 'Strong Accumulation'.")

async def run_all_seeds():
    # 1. Initialize MySQL Tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed the Token Map
    await seed_web3_tokens()
    
    # 3. Seed the Whale Data (if this is async, use await)
    # If seed_whale_data is sync, just call it normally
    seed_whale_data() 
    
    print("🚀 All systems seeded and ready for Lucy!")

if __name__ == "__main__":
    asyncio.run(run_all_seeds())