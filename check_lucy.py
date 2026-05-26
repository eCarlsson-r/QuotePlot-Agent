import asyncio, time
from utils import fetch_pyth_price
from database import SessionLocal, engine
from models import TokenMap, Stock, PredictionLog
from routers import agent
import models

# This command tells SQLAlchemy to create any tables defined in models.py 
# that don't exist yet in the 'stocksdata' database.
models.Base.metadata.create_all(bind=engine)
print("✅ Database tables initialized.")

async def check_data_growth():
    db = SessionLocal()
    initial_count = db.query(Stock).count()
    print(f"📊 Initial Stock Rows: {initial_count}")
    
    print("⏳ Waiting 35 seconds for background sync...")
    await asyncio.sleep(35)
    
    new_count = db.query(Stock).count()
    db.close()
    
    if new_count > initial_count:
        print(f"✅ GROWTH: Found {new_count - initial_count} new price entries!")
    else:
        print("⚠️ STAGNANT: No new rows found. Ensure 'sync_task' is running in main.py.")


async def run_diagnostics():
    print("🔍 --- LUCY SYSTEM CHECK --- 🔍")
    db = SessionLocal()
    
    # 1. Check Database Schema
    try:
        token_count = db.query(TokenMap).count()
        print(f"✅ DB: TokenMap accessible. Total tokens: {token_count}")
        
        stock_count = db.query(Stock).count()
        print(f"✅ DB: Stock history accessible. Rows: {stock_count}")
    except Exception as e:
        print(f"❌ DB ERROR: Ensure tables are migrated. Details: {e}")

    # 2. Check Pyth Connectivity
    print("🌐 Testing Oracle connectivity...")
    btc_id = "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"
    price = await fetch_pyth_price(btc_id)
    if price is not None:
        print(f"✅ ORACLE: Pyth connection active. Live BTC: ${price:,.2f}")
    else:
        print("❌ ORACLE ERROR: Received 'None' from fetch_pyth_price. Check API URL or Price ID.")

    # 3. Check Prediction Engine
    print("🧠 Testing SVC Inference...")
    dummy_prices = [100.0, 101.0, 100.5, 102.0, 103.0, 102.5, 104.0, 105.0, 104.5, 106.0]
    pred, conf = agent.predict_market_sentiment(dummy_prices)
    if pred and conf:
        print(f"✅ BRAIN: SVC model active. Test prediction: {pred} ({conf*100:.1f}%)")
    else:
        print("❌ BRAIN ERROR: Inference engine failed.")

    print("\n🚀 LUCY IS READY FOR DEPLOYMENT")
    db.close()
    await check_data_growth() # Put the logic here

if __name__ == "__main__":
    asyncio.run(run_diagnostics())