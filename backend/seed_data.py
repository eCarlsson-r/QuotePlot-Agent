import asyncio
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base  
from models import TokenMap # Ensure TokenMap is defined in models.py

# The "Rosetta Stone" mapping
WEB3_TOKENS = [
    {"symbol": "BTC", "cg_id": "bitcoin", "pyth_id": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"},
    {"symbol": "ETH", "cg_id": "ethereum", "pyth_id": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace"},
    {"symbol": "SOL", "cg_id": "solana",   "pyth_id": "0xef0d8b6fda2ce353c7d576f13303d840a3a29f31a69078ed3383a1523f6e5944"},
    {"symbol": "LINK", "cg_id": "chainlink", "pyth_id": "0x86e660506085f1c911850125585097486e921d743a6d71b312be0e80678d9101"},
    {"symbol": "ARB", "cg_id": "arbitrum", "pyth_id": "0x3fa42523f204ca433433583da89c7484d4127027387e35b0b2e3a15e011438a0"}
]

def seed_tokens():
    db = SessionLocal()
    tokens = db.query(TokenMap).filter(TokenMap.is_active == True).all()
    
    for t_data in tokens:
        print(t_data);
        # Avoid duplicates
        exists = db.query(TokenMap).filter(TokenMap.symbol == t_data["symbol"]).first()
        if not exists:
            new_token = TokenMap(**t_data)
            db.add(new_token)
    
    db.commit()
    db.close()
    print("✅ BTC and SOL added to TokenMap.")

def seed_database():
    print("🌱 Starting token mapping seed...")
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        for token in WEB3_TOKENS:
            # Check for existing record
            existing = db.query(TokenMap).filter(TokenMap.symbol == token["symbol"]).first()
            if not existing:
                new_entry = TokenMap(
                    symbol=token["symbol"],
                    coingecko_id=token["cg_id"],
                    pyth_id=token["pyth_id"],
                    is_active=True
                )
                db.add(new_entry)
                print(f"✅ Added {token['symbol']}")
            else:
                print(f"⏩ {token['symbol']} already exists, skipping.")
        
        db.commit()
        print("✨ Seeding complete!")
    except Exception as e:
        print(f"❌ Error seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
    seed_tokens()