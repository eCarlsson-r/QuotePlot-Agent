import asyncio
import random
from datetime import datetime
 
from sqlalchemy import func
 
from database import SessionLocal
from models import InvestorBehavior, TokenMap
from utils import get_client, get_tokens
 
# ---------------------------------------------------------------------------
# Curated token allowlist — only these symbols are seeded from the full
# Pyth/CoinGecko feed. Add or remove symbols here as needed.
# ---------------------------------------------------------------------------
SEED_SYMBOLS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX",
    "LINK", "DOT", "MATIC", "UNI", "ATOM", "LTC", "BCH", "APT",
    "ARB", "OP", "INJ", "SUI",
}
 
 
# ---------------------------------------------------------------------------
# Token seeder
# ---------------------------------------------------------------------------
 
async def seed_web3_tokens():
    print("🌐 Fetching token list from Pyth + CoinGecko...")
 
    # Retry with backoff — the post-deploy shell fires while the container
    # network stack is still initialising. DNS ([Errno -2]) resolves within
    # a few seconds once the runtime network is fully up.
    raw_token_data = None
    for attempt in range(1, 6):
        raw_token_data = await get_tokens()
        if raw_token_data:
            break
        wait = attempt * 5          # 5s, 10s, 15s, 20s, 25s
        print(f"  ⏳ Attempt {attempt}/5 failed — retrying in {wait}s...")
        await asyncio.sleep(wait)
 
    if not raw_token_data:
        print("⚠️  Warning: Token list is empty after 5 attempts. Check network / API keys.")
        return
 
    # Filter to curated allowlist
    filtered = [
        t for t in raw_token_data
        if t.get("symbol", "").upper() in SEED_SYMBOLS
    ]
    print(f"   Found {len(raw_token_data)} total feeds → seeding {len(filtered)} curated tokens.")
 
    added = updated = skipped = 0
 
    with SessionLocal() as db:
        for data in filtered:
            sym   = data["symbol"].upper()
            cg_id = data.get("coingecko_id")
 
            existing = db.query(TokenMap).filter(TokenMap.symbol == sym).first()
 
            if not existing:
                db.add(TokenMap(
                    symbol      = sym,
                    coingecko_id= cg_id,
                    pyth_id     = data.get("pyth_id"),
                    address     = data.get("address"),
                    chain       = data.get("chain"),
                    is_active   = True,
                ))
                added += 1
                print(f"  ✅ Added   {sym:<8} chain={data.get('chain') or 'n/a'}")
            else:
                changed = False
                for field in ("coingecko_id", "pyth_id", "address", "chain"):
                    new_val = data.get(field) if field != "coingecko_id" else cg_id
                    if new_val and getattr(existing, field) != new_val:
                        setattr(existing, field, new_val)
                        changed = True
                if changed:
                    updated += 1
                    print(f"  🔄 Updated {sym:<8} chain={existing.chain or 'n/a'}")
                else:
                    skipped += 1
 
        db.commit()
 
    print(f"\n  🏁 Token seeding: {added} added, {updated} updated, {skipped} unchanged.")
 
 
# ---------------------------------------------------------------------------
# Whale data seeder
# ---------------------------------------------------------------------------
 
def seed_whale_data():
    """
    Seeds 5 InvestorBehavior rows per active token so analyze_divergence()
    and mine_investor_behavior() have data to work with immediately after deploy.
 
    Uses a fresh SessionLocal() so it sees the tokens committed by
    seed_web3_tokens() rather than a stale transaction snapshot.
    """
    with SessionLocal() as db:
        active_symbols = [
            t.symbol for t in
            db.query(TokenMap).filter(TokenMap.is_active == True).all()
        ]
 
        if not active_symbols:
            print("⚠️  No active tokens found — skipping whale seed.")
            return
 
        flow_types = ["Cold Storage", "Exchange Inflow", "Whale Swap"]
        now = datetime.now()
 
        for symbol in active_symbols:
            for _ in range(5):
                db.add(InvestorBehavior(
                    symbol    = symbol,
                    flow_type = random.choice(flow_types),
                    volume    = random.uniform(100, 500),
                    timestamp = now,
                ))
 
        db.commit()
 
    print(f"  🐋 Whale flows seeded for {len(active_symbols)} tokens.")
 
 
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
 
async def run_all_seeds():
    try:
        await seed_web3_tokens()
        seed_whale_data()
        print("\n🚀 All systems seeded and ready for Lucy!")
    finally:
        # Close the shared BD-proxied httpx client cleanly so the script exits
        # without ResourceWarning: "Unclosed client session"
        client = await get_client()
        if not client.is_closed:
            await client.aclose()
 
 
if __name__ == "__main__":
    asyncio.run(run_all_seeds())
 