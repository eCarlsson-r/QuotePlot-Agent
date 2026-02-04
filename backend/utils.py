import asyncio
import httpx
import re
from sqlalchemy import func
from datetime import datetime, timedelta
from models import InvestorBehavior, TokenMap

async def get_tokens():
    url = "https://hermes.pyth.network/v2/price_feeds"
    params = {"asset_type": "crypto"}

    for attempt in range(3):
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                feeds = response.json()
                token_list = []
                for feed in feeds:
                    attr = feed.get("attributes", {})
                    if attr.get("quote_currency") != "USD":
                        continue
                    symbol = attr.get("base", "").upper()

                    # 3. Avoid obscure testnet or 'wrapped' tokens if desired
                    # Many 'wrapped' tokens have 'W' or 'test' in the description
                    description = attr.get("description", "").upper()
                    if "TEST" in description or "MOCK" in description:
                        continue
                     
                    token_list.append({
                        "symbol": symbol,
                        "cg_id": f"pyth-auto-{symbol.lower()}", # Placeholder for CoinGecko ID
                        "pyth_id": feed["id"] # This is the REAL hex ID
                    })
                
                unique_tokens = {t['symbol']: t for t in token_list}.values()
                print(f"✅ Found {len(list(unique_tokens))} crypto feeds on Hermes.")
                return list(unique_tokens)
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 10 # Wait 10, then 20 seconds
                print(f"⏳ Rate limited (429). Lucy is waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return None
            
    print("🚫 Max retries reached. Seeding aborted.")
    return None

def extract_symbol(db, text: str):
    """
    Scans text for crypto symbols. 
    Priority: 1. Uppercase symbols (BTC) 2. Known lowercase keywords.
    """
    # Look for 3-5 consecutive uppercase letters (e.g., "Tell me about SOL")
    found = re.findall(r'\b[A-Z]{3,5}\b', text)
    if found:
        symbol = db.query(TokenMap).filter(TokenMap.symbol == found[0]).first()
        if symbol:
            return symbol.symbol

    # Fallback: check for common lowercase mentions
    text_lower = text.lower()
    common_map = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "doge": "DOGE"}
    for name, sym in common_map.items():
        if name in text_lower:
            return sym
            
    return "BTC"  # Default to BTC if nothing is found

def mine_investor_behavior(db, symbol: str):
    """
    Mines the database for whale activity in the last 24 hours.
    Returns a behavioral context string for Lucy's brain.
    """
    one_day_ago = func.now() - timedelta(hours=24)

    avg_vol = db.query(func.avg(InvestorBehavior.volume)).filter(
        InvestorBehavior.symbol == symbol,
        InvestorBehavior.timestamp >= one_day_ago
    ).scalar() or 0

    dynamic_threshold = max(avg_vol * 2.0, 100)
    
    # Query for Net Flow (Inflows - Outflows)
    inflows = db.query(func.sum(InvestorBehavior.volume)).filter(
        InvestorBehavior.symbol == symbol,
        InvestorBehavior.flow_type == "Exchange Inflow",
        InvestorBehavior.timestamp >= one_day_ago
    ).scalar() or 0

    outflows = db.query(func.sum(InvestorBehavior.volume)).filter(
        InvestorBehavior.symbol == symbol,
        InvestorBehavior.flow_type == "Cold Storage",
        InvestorBehavior.timestamp >= one_day_ago
    ).scalar() or 0

    net_flow = inflows - outflows

    # Classify the behavior
    if net_flow > dynamic_threshold: # Threshold depends on the asset
        return "Heavy Distribution (Whales Selling)"
    elif net_flow < -dynamic_threshold:
        return "Strong Accumulation (Whales Buying)"
    else:
        return "Neutral Sideways Movement"