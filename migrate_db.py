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


def migrate() -> None:
    Base.metadata.create_all(bind=engine)

    if not column_exists("token_map", "chain"):
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE token_map ADD COLUMN chain VARCHAR(32) NULL")
            )
        print("✅ Added token_map.chain")
    else:
        print("⏩ token_map.chain already exists")

    print("🏁 Migration complete.")


if __name__ == "__main__":
    migrate()
