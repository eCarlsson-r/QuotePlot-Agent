import asyncio
from datetime import datetime, timedelta
from database import SessionLocal, db_save_price, get_recent_prices, save_prediction_to_db
from sqlalchemy import text as sql_text
from models import TokenMap, Stock, PredictionLog
from brain import get_market_prediction
import routers.market as market_utils

sync_progress_store = {}

async def check_for_data_gaps(symbol: str, threshold_hours: int = 2):
    """Detects if a token is missing data and returns the start date for backfilling."""
    with SessionLocal() as db:
        last_entry = db.execute(
            sql_text("SELECT datetime FROM stocks WHERE symbol = :s ORDER BY datetime DESC LIMIT 1"),
            {"s": symbol}
        ).fetchone()

    if last_entry:
        last_dt = last_entry[0]
        # If the gap is larger than our threshold, return the last known timestamp
        if datetime.now() - last_dt > timedelta(hours=threshold_hours):
            print(f"🔍 Gap detected for {symbol}. Last data: {last_dt}. Triggering backfill...")
            return last_dt
    return None

async def continuous_oracle_sync(ws_manager):
    """The heartbeat loop."""
    while True:
        with SessionLocal() as db:
            active_tokens = db.query(TokenMap).filter(TokenMap.is_active == True).all()

            for token in active_tokens:
                # 1. FETCH
                price = await market_utils.fetch_pyth_price(token.pyth_id)
                
                if price:
                    # 2. STORE (Memory first)
                    db_save_price(token.symbol, price, datetime.now(), db)
                    
                    # 3. REASON (Brain second)
                    # We fetch the fresh window including the price we just added
                    recent_prices = get_recent_prices(token.symbol, db, limit=10)
                    
                    if len(recent_prices) >= 10:
                        description = f"Price is moving from {recent_prices[0]} to {recent_prices[-1]}"
                        sentiment, confidence = get_market_prediction(description)
                        try:
                            await ws_manager.broadcast(f"[BRAIN] 🧠 {token.symbol}: {sentiment} ({confidence*100:.1f}%)")
                        except: pass
                        save_prediction_to_db(token.symbol, sentiment, confidence, price, db)
        
        await asyncio.sleep(30)


async def evaluate_predictions_task(ws_manager):
    """The Judge: Compares old predictions with current prices."""
    while True:
        with SessionLocal() as db:
            # Look for unresolved predictions older than 1 hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            pending = db.query(PredictionLog).filter(
                PredictionLog.was_correct == None,
                PredictionLog.timestamp <= one_hour_ago
            ).all()

            for p in pending:
                # 2. Get the 'Current' price from our history
                current_price_row = db.query(Stock).filter(Stock.symbol == p.symbol).order_id(Stock.datetime.desc()).first()
                
                if current_price_row:
                    actual_move = "BULLISH" if current_price_row.price > p.price_at_prediction else "BEARISH"
                    p.was_correct = (p.predicted_sentiment == actual_move)
                    p.is_evaluated = True
                    p.actual_price_later = current_price_row.price
                
                    # 4. BROADCAST THE VERDICT
                    status = "✅ RIGHT" if p.was_correct else "❌ WRONG"
                    await ws_manager.broadcast(f"[JUDGE] ⚖️ Verdict: Lucy was {status} on {p.symbol}!")

            db.commit()
        await asyncio.sleep(3600) # Run every hour

async def backfill_history_task(symbol: str, start_dt: datetime):
    """Refactored backfiller: Uses TokenMap to find the correct Pyth ID."""
    now = datetime.now()
    total_steps = int((now - start_dt).total_seconds() / 3600)
    
    # 1. Get the Pyth ID from the database for this symbol
    with SessionLocal() as db:
        token = db.query(TokenMap).filter(TokenMap.symbol == symbol).first()
        if not token or not token.pyth_id:
            print(f"❌ Cannot backfill {symbol}: No Pyth ID found in TokenMap.")
            return

    # 2. Loop through the hours
    for i in range(total_steps):
        current_ts = int((start_dt + timedelta(hours=i)).timestamp())
        
        # Call the new universal fetcher with the ID
        price = await market_utils.fetch_pyth_price(token.pyth_id, current_ts)
        
        if price:
            with SessionLocal() as db:
                dt_str = datetime.fromtimestamp(current_ts).strftime('%Y-%m-%d %H:%M:%S')
                db_save_price(symbol, price, dt_str, db)
        
        # Update Lucy's progress bar on the frontend
        sync_progress_store[symbol] = int(((i + 1) / total_steps) * 100)
        
        # Short sleep to prevent hitting Pyth's rate limits (403 errors)
        await asyncio.sleep(0.1) 
        
    sync_progress_store[symbol] = 100
    print(f"✅ History sync finalized for {symbol}")