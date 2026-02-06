import asyncio
import requests
import time
import httpx
import re
from sqlalchemy import func
from datetime import datetime, timedelta
from models import InvestorBehavior, TokenMap

user_sessions = {}
http_client: httpx.AsyncClient = None  # Global client initialized in lifespan
async def get_client():
    global http_client
    if http_client is None or http_client.is_closed:
        http_client = httpx.AsyncClient(timeout=10.0)
    return http_client

# utils.py
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

def format_lucy_log(symbol, confidence, insight):
    prefix = "[INFO] "

    if "DIVERGENCE" in insight:
        prefix = "[ERROR] "
    elif "CONFIRMATION" in insight:
        prefix = "[SUCCESS] "
    elif confidence > 0.80:
        prefix = "[WARN] "

    return f"{prefix} {symbol.ljust(8)} @ {int(confidence*100)}% : {insight}"

async def get_tokens():
    """
    1. Fetches all Pyth feeds.
    2. Fetches CoinGecko's ID map (including addresses).
    3. Matches them to create a perfect TokenMap entry.
    """
    # 1. Get Pyth Feeds (Your existing logic)
    pyth_url = "https://hermes.pyth.network/v2/price_feeds?asset_type=crypto"
    # 2. Get CoinGecko ID Map with Addresses
    cg_url = "https://api.coingecko.com/api/v3/coins/list?include_platform=true"

    async with httpx.AsyncClient() as client:
        pyth_res, cg_res = await asyncio.gather(
            client.get(pyth_url),
            client.get(cg_url)
        )

        if pyth_res.status_code != 200 or cg_res.status_code != 200:
            return None

        pyth_feeds = pyth_res.json()
        cg_map = cg_res.json() # List of {id, symbol, platforms: {chain: address}}

        # Create a lookup for CG by symbol (uppercase)
        cg_lookup = {item['symbol'].upper(): item for item in cg_map}

        token_list = []
        for feed in pyth_feeds:
            attr = feed.get("attributes", {})
            symbol = attr.get("base", "").upper()
            
            # Match with CoinGecko
            cg_data = cg_lookup.get(symbol)
            
            # Extract the first available contract address
            address = None
            if cg_data and cg_data.get('platforms'):
                # We prioritize Ethereum or Solana, or just take the first one
                platforms = cg_data['platforms']
                address = next(iter(platforms.values())) if platforms else None

                token_list.append({
                    "symbol": symbol,
                    "coingecko_id": cg_data['id'] if cg_data else f"pyth-auto-{symbol.lower()}",
                    "pyth_id": feed["id"],
                    "address": address
                })

        return token_list

def get_fear_and_greed():
    """Fetches current crypto market sentiment."""
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url).json()
        data = response['data'][0]
        
        return {
            "value": data['value'],
            "sentiment": data['value_classification'], # e.g., "Greed"
            "timestamp": data['timestamp']
        }
    except Exception as e:
        print(f"Sentiment Error: {e}")
        return {"value": "50", "sentiment": "Neutral"}
        
def get_global_movers():
    """Fetches top 3 gainers and losers from CoinGecko."""
    try:
        # Free Demo API endpoint for market data
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "price_change_percentage_24h_desc",
            "per_page": 5,
            "page": 1
        }
        data = requests.get(url, params=params).json()
        
        gainers = [f"{c['symbol'].upper()} (+{round(c['price_change_percentage_24h'], 1)}%)" for c in data[:3]]
        return {"top_gainers": gainers}
    except Exception as e:
        return {"top_gainers": []}
    
def extract_symbol(db, text: str, session_id: str = "default_user"):
    """
    Scans text for crypto symbols. 
    Priority: 1. Uppercase symbols (BTC) 2. Known lowercase keywords.
    """
    # Look for 3-5 consecutive uppercase letters (e.g., "Tell me about SOL")
    found = re.findall(r'\b[A-Z]{3,5}\b', text)
    if found:
        symbol_obj = db.query(TokenMap).filter(TokenMap.symbol == found[0]).first()
        if symbol_obj:
            user_sessions[session_id] = symbol_obj.symbol
            return symbol_obj.symbol

    # Fallback: check for common lowercase mentions
    text_lower = text.lower()
    common_map = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "doge": "DOGE"}
    for name, sym in common_map.items():
        if name in text_lower:
            return sym
    
    return user_sessions.get(session_id, "BTC")  # Default to BTC if nothing is found


async def fetch_pyth_price(price_id: str, timeout: float = 10.0):
    # Pyth Hermes V2 endpoint
    url = "https://hermes.pyth.network/v2/updates/price/latest"
    # Pass params as a dict to let the library handle the [] encoding
    params = {"ids[]": [price_id]}

    try:
        client = await get_client()
        response = await client.get(url, params=params, timeout=timeout)
        if response.status_code != 200:
            print(f"❌ Pyth Error {response.status_code}: {response.text}")
            return None
        data = response.json()
        
        # Safe traversal of the Pyth JSON structure
        if "parsed" in data and len(data["parsed"]) > 0:
            p = data["parsed"][0].get("price", {})
            publish_time = p.get("publish_time")

            # Check if stale (e.g., older than 24 hours)
            if (int(time.time()) - publish_time) > 86400:
                print(f"⚠️ Feed {price_id} is stale.")
                return "STALE" # Return a unique string to signal deletion

            raw_price = float(p.get("price", 0))
            expo = int(p.get("expo", 0))

            if raw_price != 0:
                return raw_price * (10 ** expo)
        
        return None # Explicitly return None if data is missing
    except httpx.ConnectError:
        print("❌ Connection Error: Could not reach Pyth servers.")
    except httpx.TimeoutException:
        print("❌ Timeout Error: Pyth took too long to respond.")
    except Exception as e:
        print(f"❌ Unexpected Error during fetch: {type(e).__name__} - {e}")
    return None

api_semaphore = asyncio.Semaphore(2)
async def fetch_dex_whales(address: str):
    """
    Queries DexScreener for the specific contract address.
    Filters for the highest liquidity pair to detect whale volume.
    """
    if not address:
        return None
        
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    
    async with api_semaphore: # Ensuring we stay within the 300 req/min limit
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None
                    
                data = response.json()
                pairs = data.get('pairs', [])
                
                if not pairs:
                    return None
                
                # We want the 'Main' pair (usually the one with the most liquidity)
                # This helps us avoid 'dust' pools or fake liquidity.
                main_pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
                
                # Extract 24h volume and transaction counts
                volume_24h = float(main_pair.get('volume', {}).get('h24', 0))
                txns_24h = main_pair.get('txns', {}).get('h24', {})
                buys = txns_24h.get('buys', 0)
                sells = txns_24h.get('sells', 0)

                # Determine flow type based on buy/sell pressure
                flow_type = "Whale Swap"
                if buys > (sells * 1.5):
                    flow_type = "Cold Storage"    # Strong buying = Accumulation
                elif sells > (buys * 1.5):
                    flow_type = "Exchange Inflow" # Strong selling = Distribution

                return {
                    "type": flow_type,
                    "amount": volume_24h / 100 # Normalized volume "score"
                }
        except Exception as e:
            print(f"⚠️ DexScreener Error for {address}: {e}")
    return None

def infer_whale_activity(price_history):
    """
    Detects 'Ghost Whales' by analyzing price volatility spikes.
    If price moves > 2% between syncs, a whale likely caused it.
    """
    if len(price_history) < 2:
        return "Whale Swap" # Neutral/Unknown

    current_p = float(price_history[0].price)
    last_p = float(price_history[1].price)
    diff_pct = ((current_p - last_p) / last_p) * 100

    if diff_pct > 2.0:
        return "Cold Storage"    # Price spike = Accumulation
    elif diff_pct < -2.0:
        return "Exchange Inflow" # Price dump = Distribution
    
    return "Whale Swap" # Sideways/Retail noise

def map_to_investor_behavior(symbol, flow_type, volume):
    """
    A unified mapper that works regardless of where the data comes from.
    Lucy doesn't care who the API is; she just wants the facts.
    """
    # Standardize the flow type so Lucy's brain understands it
    valid_flows = ["Exchange Inflow", "Cold Storage", "Whale Swap"]
    if flow_type not in valid_flows:
        flow_type = "Whale Swap"

    return {
        "symbol": symbol.upper(),
        "flow_type": flow_type,
        "volume": float(volume),
        "timestamp": datetime.now()
    }

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
    if avg_vol == 0:
        return "No recent whale activity detected (Insufficient Data)"
    elif net_flow > dynamic_threshold: # Threshold depends on the asset
        return "Heavy Distribution (Whales Selling)"
    elif net_flow < -dynamic_threshold:
        return "Strong Accumulation (Whales Buying)"
    else:
        return "Neutral Sideways Movement"