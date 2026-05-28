"""
migrate.py — QuotePlot database migration tool
Mirrors Laravel's artisan migrate commands.

Usage:
    python migrate.py             # Run pending migrations (safe, additive only)
    python migrate.py --fresh     # DROP all tables and recreate from scratch (⚠️ destroys all data)
    python migrate.py --rollback  # Drop all tables only (no recreate)
    python migrate.py --status    # Show which tables and indexes exist
"""

import argparse
from sqlalchemy import inspect, text
from database import engine
from models import Base

# ---------------------------------------------------------------------------
# Index definitions — composite indexes not expressed in models.py
# These are the performance-critical indexes identified from slow query analysis.
# ---------------------------------------------------------------------------
INDEXES = [
    # stocks — window function + range queries filter by (symbol, datetime)
    {
        "name":  "idx_stocks_symbol_datetime_desc",
        "table": "stocks",
        "ddl":   "ALTER TABLE stocks ADD INDEX idx_stocks_symbol_datetime_desc (symbol, datetime DESC)",
    },
    {
        "name":  "idx_stocks_symbol_datetime_asc",
        "table": "stocks",
        "ddl":   "ALTER TABLE stocks ADD INDEX idx_stocks_symbol_datetime_asc (symbol, datetime ASC)",
    },
    # investor_behavior — analyze_divergence + mine_investor_behavior
    {
        "name":  "idx_ib_symbol_timestamp",
        "table": "investor_behavior",
        "ddl":   "ALTER TABLE investor_behavior ADD INDEX idx_ib_symbol_timestamp (symbol, timestamp DESC)",
    },
    {
        "name":  "idx_ib_symbol_flow_timestamp",
        "table": "investor_behavior",
        "ddl":   "ALTER TABLE investor_behavior ADD INDEX idx_ib_symbol_flow_timestamp (symbol, flow_type, timestamp DESC)",
    },
    # prediction_logs — evaluate_predictions_task filters was_correct IS NULL + timestamp
    {
        "name":  "idx_pl_was_correct_timestamp",
        "table": "prediction_logs",
        "ddl":   "ALTER TABLE prediction_logs ADD INDEX idx_pl_was_correct_timestamp (was_correct, timestamp DESC)",
    },
    {
        "name":  "idx_pl_symbol",
        "table": "prediction_logs",
        "ddl":   "ALTER TABLE prediction_logs ADD INDEX idx_pl_symbol (symbol)",
    },
    # alternative_data — queried by symbol ORDER BY timestamp DESC
    {
        "name":  "idx_ad_symbol_timestamp",
        "table": "alternative_data",
        "ddl":   "ALTER TABLE alternative_data ADD INDEX idx_ad_symbol_timestamp (symbol, timestamp DESC)",
    },
]

CHECK_INDEX_SQL = text("""
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE()
    AND table_name   = :tbl
    AND index_name   = :idx
""")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _separator(char="─", width=60):
    print(char * width)


def _tables_exist(conn) -> list[str]:
    inspector = inspect(conn)
    return inspector.get_table_names()


def _drop_all(conn):
    """Drop all application tables in reverse dependency order."""
    tables = _tables_exist(conn)
    if not tables:
        print("  No tables found — nothing to drop.")
        return

    # Disable FK checks so we can drop in any order
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    for table in tables:
        conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
        print(f"  🗑️  Dropped table: {table}")
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    conn.commit()


def _create_all():
    """Create all tables from SQLAlchemy models."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    for table in inspector.get_table_names():
        print(f"  ✅ Table ready: {table}")


def _apply_indexes(conn):
    """Add composite indexes — skips any that already exist."""
    for idx in INDEXES:
        count = conn.execute(CHECK_INDEX_SQL, {"tbl": idx["table"], "idx": idx["name"]}).scalar()
        if count:
            print(f"  ⏭️  Index exists:  {idx['name']}")
        else:
            try:
                conn.execute(text(idx["ddl"]))
                conn.commit()
                print(f"  ✅ Index created: {idx['name']} on {idx['table']}")
            except Exception as e:
                print(f"  ❌ Index failed:  {idx['name']} → {e}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status():
    _separator()
    print("  migrate --status")
    _separator()
    with engine.connect() as conn:
        tables = _tables_exist(conn)
        print(f"\n  Tables ({len(tables)}):")
        for t in sorted(tables):
            print(f"    • {t}")

        print(f"\n  Composite indexes:")
        for idx in INDEXES:
            count = conn.execute(CHECK_INDEX_SQL, {"tbl": idx["table"], "idx": idx["name"]}).scalar()
            status = "✅ exists" if count else "❌ missing"
            print(f"    {status}  {idx['name']}")
    _separator()


def cmd_migrate():
    """Additive only — creates missing tables and indexes, touches nothing existing."""
    _separator()
    print("  migrate")
    _separator()
    print("\n  Creating missing tables...")
    _create_all()
    print("\n  Applying missing indexes...")
    with engine.connect() as conn:
        _apply_indexes(conn)
    print()
    _separator()
    print("  ✅ Migration complete.")
    _separator()


def cmd_fresh():
    """Drop everything and rebuild from scratch — mirrors migrate:fresh."""
    _separator("━")
    print("  migrate --fresh   ⚠️  ALL DATA WILL BE DESTROYED")
    _separator("━")

    confirm = input("\n  Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("  Aborted.")
        return

    print("\n  Dropping all tables...")
    with engine.connect() as conn:
        _drop_all(conn)

    print("\n  Creating tables from models...")
    _create_all()

    print("\n  Applying indexes...")
    with engine.connect() as conn:
        _apply_indexes(conn)

    print()
    _separator("━")
    print("  ✅ Fresh migration complete. Database is clean.")
    _separator("━")


def cmd_rollback():
    """Drop all tables only — no recreate."""
    _separator("━")
    print("  migrate --rollback   ⚠️  ALL DATA WILL BE DESTROYED")
    _separator("━")

    confirm = input("\n  Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("  Aborted.")
        return

    print("\n  Dropping all tables...")
    with engine.connect() as conn:
        _drop_all(conn)

    print()
    _separator("━")
    print("  ✅ Rollback complete. All tables dropped.")
    _separator("━")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="QuotePlot migration tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  (none)       Create missing tables and indexes — safe, additive
  --fresh      DROP all tables then recreate (⚠️  destroys all data)
  --rollback   DROP all tables only, no recreate
  --status     Show existing tables and index health
        """
    )
    parser.add_argument("--fresh",    action="store_true", help="Drop all tables and recreate")
    parser.add_argument("--rollback", action="store_true", help="Drop all tables only")
    parser.add_argument("--status",   action="store_true", help="Show table and index status")
    args = parser.parse_args()

    if args.fresh:
        cmd_fresh()
    elif args.rollback:
        cmd_rollback()
    elif args.status:
        cmd_status()
    else:
        cmd_migrate()