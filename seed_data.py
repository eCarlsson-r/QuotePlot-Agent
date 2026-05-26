from utils import get_tokens
from database import SessionLocal, engine
from sqlalchemy import func
from models import Base, InvestorBehavior, TokenMap
import random
from datetime import datetime
import asyncio

from migrate_db import migrate


async def seed_web3_tokens():
    db = SessionLocal()
    raw_token_data = await get_tokens()

    if not raw_token_data:
        print("⚠️ Warning: Token list is empty. Check your API/Utility.")
        db.close()
        return

    added = updated = skipped = 0
    for data in raw_token_data:
        sym = data.get("symbol")
        if not sym:
            continue

        cg_id = data.get("coingecko_id")
        existing = db.query(TokenMap).filter(TokenMap.symbol == sym).first()

        if not existing:
            db.add(
                TokenMap(
                    symbol=sym,
                    coingecko_id=cg_id,
                    pyth_id=data.get("pyth_id"),
                    address=data.get("address"),
                    chain=data.get("chain"),
                    is_active=True,
                )
            )
            added += 1
            print(f"✅ Added {sym} (chain={data.get('chain')})")
        else:
            changed = False
            if cg_id and existing.coingecko_id != cg_id:
                existing.coingecko_id = cg_id
                changed = True
            if data.get("pyth_id") and existing.pyth_id != data.get("pyth_id"):
                existing.pyth_id = data.get("pyth_id")
                changed = True
            if data.get("address") and existing.address != data.get("address"):
                existing.address = data.get("address")
                changed = True
            if data.get("chain") and existing.chain != data.get("chain"):
                existing.chain = data.get("chain")
                changed = True
            if changed:
                updated += 1
                print(f"🔄 Updated {sym} (chain={existing.chain})")
            else:
                skipped += 1

    db.commit()
    db.close()
    print(f"🏁 Token seeding done: {added} added, {updated} updated, {skipped} unchanged.")


def seed_whale_data():
    db = SessionLocal()
    active_symbols = [t.symbol for t in db.query(TokenMap).filter(TokenMap.is_active == True).all()]

    for symbol in active_symbols:
        for _ in range(5):
            move = InvestorBehavior(
                symbol=symbol,
                flow_type="Cold Storage",
                volume=random.uniform(100, 500),
                timestamp=func.now(),
            )
            db.add(move)
    db.commit()
    db.close()
    print("🐋 Whale flows seeded. Lucy can now detect 'Strong Accumulation'.")


async def run_all_seeds():
    migrate()
    await seed_web3_tokens()
    seed_whale_data()
    print("🚀 All systems seeded and ready for Lucy!")


if __name__ == "__main__":
    asyncio.run(run_all_seeds())
