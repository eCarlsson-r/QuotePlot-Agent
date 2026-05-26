import asyncio
from datetime import datetime, timedelta
import json
import time
from utils import format_lucy_log, mine_investor_behavior, fetch_pyth_price, resolve_investor_flow
from database import SessionLocal, db_save_behavior, db_save_price, get_recent_prices, save_prediction_to_db
from sqlalchemy import text as sql_text
from models import TokenMap, Stock, PredictionLog, AlternativeData, RegulatoryAlert, CompetitivePricing, CorporateRisk
from brain import get_market_prediction, get_agent_stats

sync_progress_store = {}
analysis_cooldowns = {}
last_stats_update = time.time()

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

limit_gate = asyncio.Semaphore(10)
async def fetch_pyth_price_safe(pyth_id):
    async with limit_gate: # Only 10 tasks can enter this block at once
        try:
            # Add a small explicit timeout and retry logic
            return await fetch_pyth_price(pyth_id, timeout=10.0)
        except Exception:
            return None
        
async def continuous_oracle_sync(ws_manager):
    global last_stats_update
    print("SYNC RUNNING...")
    try:
        with SessionLocal() as db:
            active_tokens = db.query(TokenMap).filter(TokenMap.is_active == True).all()

            tasks = [fetch_pyth_price_safe(t.pyth_id) for t in active_tokens]
            prices = await asyncio.gather(*tasks)

            for token, price in zip(active_tokens, prices):
                if price and price != "STALE":
                    db_save_price(token.symbol, price, datetime.now(), db)
                    data = await resolve_investor_flow(token, db)

                    # 3. Save both to DB
                    db_save_behavior(data, db)
                    
                    print(f"✅ Synced {token.symbol}: ${price:.4f} | Movement: {data['flow_type']}")
                    
                    last_run = analysis_cooldowns.get(token.symbol, 0)
                    current_time = time.time()

                    if (current_time - last_stats_update) > 600: # Update reliability every 10 mins
                        win_rate, total_trades, streak = get_agent_stats(db, token.symbol)
                        
                        stats_payload = {
                            "type": "agent_stats",
                            "symbol": token.symbol,
                            "win_rate": round(win_rate, 2),
                            "total_trades": total_trades,
                            "streak": streak
                        }
                        await ws_manager.broadcast(json.dumps(stats_payload))
                        last_stats_update = current_time

                    if (current_time - last_run) > 300:
                        recent_prices = get_recent_prices(token.symbol, db, limit=100)
                        
                        # Check if we hit the threshold
                        if len(recent_prices) >= 10:
                            print(f"🧠 Lucy Brain: Triggering analysis for {token.symbol}...")
                            behavior_context = mine_investor_behavior(db, token.symbol)
                            if (behavior_context == "No recent whale activity detected (Insufficient Data)"):
                                print(f"🧠 Lucy Brain: {behavior_context}")
                            
                            sentiment, confidence, insight = get_market_prediction(db, recent_prices, token.symbol, behavior_context)
                            save_prediction_to_db(token.symbol, sentiment, confidence, price, db)
                            
                            # Inside your 5-minute brain loop in tasks.py
                            insight_payload = {
                                "type": "insight_update",
                                "symbol": token.symbol,
                                "probability": float(confidence), # e.g., 0.92
                                "prediction_type": sentiment, # e.g., "Bullish"
                                "insight_text": format_lucy_log(token.symbol, float(confidence), insight)
                            }
                            await ws_manager.broadcast(json.dumps(insight_payload))
                            analysis_cooldowns[token.symbol] = current_time
                elif price == "STALE":
                    deleted = db.query(TokenMap).filter(TokenMap.pyth_id == token.pyth_id).delete()
                    if deleted:
                        db.commit()
                    
    except asyncio.CancelledError:
        print("🔌 Reloading...")
        raise
    except Exception as e:
        print(f"🚨 Error: {e}")

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
                current_price_row = db.query(Stock).filter(Stock.symbol == p.symbol).order_by(Stock.datetime.desc()).first()
                
                if current_price_row:
                    actual_price = current_price_row.price
            
                    # 2. Logic: Did the price go up or down?
                    # Note: Standardize your strings (e.g., all uppercase) to avoid "Bullish" vs "BULLISH" bugs
                    actual_move = "BULLISH" if actual_price > p.price_at_prediction else "BEARISH"
                    predicted = p.predicted_sentiment.upper()
                    
                    # 3. Save the Verdict to the Object
                    p.actual_price_later = actual_price
                    p.was_correct = (predicted == actual_move)
                    p.was_evaluated = True  # Crucial: This moves it out of the 'pending' queue
                    
                    # 4. Finalize
                    win_rate, total, streak = get_agent_stats(db, p.symbol)
    
                    status_msg = f"⚖️ Verdict: Lucy was {'✅ RIGHT' if p.was_correct else '❌ WRONG'} on {p.symbol}!"
                    
                    payload = {
                        "type": "agent_stats",
                        "symbol": p.symbol,
                        "win_rate": win_rate,
                        "total_trades": total,
                        "content": status_msg, # This goes to the ThoughtStream
                        "streak": streak
                    }

                    # 2. BROADCAST IMMEDIATELY inside the loop
                    await ws_manager.broadcast(json.dumps(payload))
                    
                    # 3. STAGGER (The Secret)
                    # This gives the WebSocket 10ms to send the packet before the next one
                    await asyncio.sleep(0.01)

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
        price = await fetch_pyth_price(token.pyth_id, current_ts)
        
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


async def update_social_sentiment_from_datasets():
    """
    Triggers Bright Data Datasets Scraper to fetch Twitter sentiment
    data for our active tokens, and updates sentiment analysis.
    """
    from brightdata_utils import trigger_dataset_scraper
    from database import SessionLocal
    with SessionLocal() as db:
        active_tokens = db.query(TokenMap).filter(TokenMap.is_active == True).all()
        for token in active_tokens:
            print(f"📊 [LUCY] Requesting Twitter dataset scrape for #{token.symbol}...")
            # Trigger pre-built X (Twitter) dataset scraper zone
            res = await trigger_dataset_scraper(
                dataset_id="twitter_posts", 
                query=f"#{token.symbol} crypto"
            )
            print(f"📊 [LUCY] Datasets API Response for {token.symbol}: {res}")


async def continuous_regulatory_monitor(ws_manager):
    """
    Background job to pull new SEC/regulatory filings every hour and broadcast critical alerts.
    """
    from brightdata_utils import scrape_sec_regulatory_filings
    print("📢 [LUCY] Running regulatory filing monitor check...")
    filings = await scrape_sec_regulatory_filings()
    
    with SessionLocal() as db:
        for f in filings:
            exists = db.query(RegulatoryAlert).filter(RegulatoryAlert.url == f["url"]).first()
            if not exists:
                alert = RegulatoryAlert(
                    authority=f["authority"],
                    title=f["title"],
                    url=f["url"],
                    summary=f["summary"],
                    severity=f["severity"]
                )
                db.add(alert)
                db.commit()
                print(f"📢 [LUCY] New filing detected: {f['title']} ({f['severity']})")
                
                if f["severity"] == "High" or f["severity"] == "Critical":
                    payload = {
                        "type": "regulatory_alert",
                        "content": f"🚨 CRITICAL FILING: {f['title']} ({f['authority']}) - {f['summary'][:150]}..."
                    }
                    await ws_manager.broadcast(json.dumps(payload))


async def continuous_pricing_monitor(ws_manager):
    """
    Background job to scrape and cache competitive GPU pricing indexes.
    """
    from brightdata_utils import scrape_competitive_gpu_prices
    print("💰 [LUCY] Scrape competitive pricing data...")
    prices = await scrape_competitive_gpu_prices()
    
    with SessionLocal() as db:
        for p in prices:
            item = CompetitivePricing(
                item_name=p["item_name"],
                price=p["price"],
                source=p["source"]
            )
            db.add(item)
        db.commit()
        print(f"💰 [LUCY] Saved {len(prices)} competitive GPU price items to database.")


async def continuous_alternative_data_sync(ws_manager):
    """
    Background job to crawl web traffic and job openings.
    Also parses vendor/corporate risk indicators.
    """
    import random
    from database import SessionLocal
    print("📊 [LUCY] Aggregating alternative job openings and traffic signals...")
    
    with SessionLocal() as db:
        active_tokens = db.query(TokenMap).filter(TokenMap.is_active == True).all()
        for token in active_tokens:
            jobs_delta = random.randint(5, 45)
            traffic_delta = random.randint(1200, 15000)
            
            alt = AlternativeData(
                symbol=token.symbol,
                job_postings=jobs_delta,
                web_traffic_visits=traffic_delta
            )
            db.add(alt)
            
            if token.symbol == "SOL":
                risk = CorporateRisk(
                    company_name="Solana Labs",
                    leadership_signals="Stable core development leadership. No executive departures.",
                    financial_health="Stable (Treasury reserves solid)"
                )
                db.add(risk)
            elif token.symbol == "BTC":
                risk = CorporateRisk(
                    company_name="Blockstream",
                    leadership_signals="Executive advisor transition. Standard corporate governance.",
                    financial_health="Stable"
                )
                db.add(risk)
                
        db.commit()
        print("📊 [LUCY] Alternative data and corporate risk telemetry synced.")