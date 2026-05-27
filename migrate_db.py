"""
Apply schema updates to an existing MySQL (or other) database without dropping data.

Usage:
    python migrate_db.py
"""

from sqlalchemy import inspect, text

from database import engine
from models import Base


def column_exists(table: str, column: str) -> bool:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


# 🌟 NEW: Helper function to check if the index already exists
def index_exists(table: str, index_name: str) -> bool:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return False
    return index_name in {idx["name"] for idx in insp.get_indexes(table)}


def migrate() -> None:
    Base.metadata.create_all(bind=engine)

    # 1. Check/Add Column migration
    if not column_exists("token_map", "chain"):
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE token_map ADD COLUMN chain VARCHAR(32) NULL")
            )
        print("✅ Added token_map.chain")
    else:
        print("⏩ token_map.chain already exists")

    # 2. 🌟 NEW: Check/Add Performance Index Migration
    # Note: Using 'stocks' table name as defined in database.py
    if not index_exists("stocks", "idx_stock_symbol_datetime"):
        with engine.begin() as conn:
            conn.execute(
                text("CREATE INDEX idx_stock_symbol_datetime ON stocks (symbol, datetime DESC)")
            )
        print("✅ Created index idx_stock_symbol_datetime on table 'stocks'")
    else:
        print("⏩ idx_stock_symbol_datetime index already exists")

    print("🏁 Migration complete.")


if __name__ == "__main__":
    migrate()