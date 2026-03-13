#!/usr/bin/env python3
"""
migrate_sqlite_to_postgres.py
==============================
Migrates ALL data from a local SQLite database to a PostgreSQL database.
"""

import asyncio
import os
import sys
import sqlite3
from datetime import datetime

# -- CONFIG --------------------------------------------------------------------
# Path to your SQLite database file
SQLITE_PATH = r"c:\Users\MS-Fin-10\Documents\GitHub\Digital-Arena\bot_database.db"

# PostgreSQL connection URL
POSTGRES_URL = os.getenv("POSTGRES_URL", "")  # Set as env var or paste here

# Tables to migrate (in order - respects foreign keys)
TABLES_ORDER = [
    "users",
    "clubs",
    "computers",
    "club_zone_settings",
    "restaurant_tables",
    "admins",
    "bookings",
    "audit_logs",
    "reviews",
    "promo_codes",
    "app_auth_codes",
    "app_sessions",
    "payments",
    "bar_items",
    "bar_orders",
    "icafe_sessions",
    "audit_discrepancies",
]

# -----------------------------------------------------------------------------


def read_sqlite_table(sqlite_path: str, table: str):
    """Read all rows from a SQLite table. Returns (columns, rows)."""
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        conn.close()
        return columns, [dict(row) for row in rows]
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            return [], []  # Table doesn't exist yet - skip
        raise


async def migrate_table_to_postgres(pg_url: str, table: str, columns: list, rows: list) -> int:
    """Insert rows into PostgreSQL table. Returns number of inserted rows."""
    if not rows or not columns:
        return 0

    import asyncpg

    # Convert pg:// to asyncpg format
    url = pg_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    conn = await asyncpg.connect(url)
    inserted = 0
    skipped = 0

    try:
        for row in rows:
            # Build INSERT ... ON CONFLICT DO NOTHING (safe upsert)
            col_names = ", ".join(f'"{c}"' for c in columns)
            placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
            sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

            values = []
            for col in columns:
                val = row[col]
                # Convert SQLite datetime strings to Python datetime objects
                if val and isinstance(val, str):
                    for fmt in ("%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z",
                                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                                "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
                        try:
                            val = datetime.strptime(val, fmt)
                            break
                        except ValueError:
                            continue
                values.append(val)

            try:
                result = await conn.execute(sql, *values)
                if result == "INSERT 0 1":
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

    finally:
        await conn.close()

    return inserted


async def main():
    print("=" * 60)
    print("  Digital Arena - SQLite -> PostgreSQL Migration Tool")
    print("=" * 60)

    # -- Check SQLite file ----------------------------------------------------
    if not os.path.exists(SQLITE_PATH):
        print(f"\n[!] SQLite file not found: {SQLITE_PATH}")
        sys.exit(1)
    print(f"\n[OK] SQLite file found: {SQLITE_PATH}")

    # -- Check PostgreSQL URL -------------------------------------------------
    pg_url = POSTGRES_URL or os.getenv("POSTGRES_URL", "")
    if not pg_url:
        print("\n[!] PostgreSQL URL not set!")
        sys.exit(1)
    print(f"[OK] PostgreSQL URL: {pg_url[:30]}...")

    # -- Test PostgreSQL connection --------------------------------------------
    try:
        import asyncpg
        url = pg_url.replace("postgres://", "postgresql://", 1)
        test_conn = await asyncpg.connect(url)
        pg_version = await test_conn.fetchval("SELECT version()")
        await test_conn.close()
        print(f"[OK] PostgreSQL connected: {pg_version[:40]}...")
    except Exception as e:
        print(f"\n[!] Cannot connect to PostgreSQL: {e}")
        sys.exit(1)

    # -- Count total SQLite rows -----------------------------------------------
    print(f"\n[*] Reading from SQLite ({SQLITE_PATH})...\n")
    total_rows = 0
    table_data = {}

    for table in TABLES_ORDER:
        columns, rows = read_sqlite_table(SQLITE_PATH, table)
        table_data[table] = (columns, rows)
        count = len(rows)
        total_rows += count
        if count > 0:
            print(f"   [TAB] {table:<30} {count:>5} rows")

    if total_rows == 0:
        print("   [!] SQLite database is empty - nothing to migrate.")
        sys.exit(0)

    print(f"\n   Total: {total_rows} rows to migrate")

    # -- Ask for confirmation --------------------------------------------------
    print("\n" + "-" * 60)
    # Using non-interactive confirm if pipe is used
    if sys.stdin.isatty():
        confirm = input("[?] Start migration? (yes/no): ").strip().lower()
    else:
        confirm = "yes"
    
    if confirm not in ("yes", "y", "да"):
        print("Migration cancelled.")
        sys.exit(0)

    # -- Migrate ---------------------------------------------------------------
    print("\n[*] Migrating...\n")
    grand_total = 0

    for table in TABLES_ORDER:
        columns, rows = table_data[table]
        if not rows:
            continue
        print(f"   [UP] {table:<30}", end="", flush=True)
        inserted = await migrate_table_to_postgres(pg_url, table, columns, rows)
        grand_total += inserted
        print(f" -> {inserted}/{len(rows)} inserted OK")

    # -- Summary ---------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  [OK] Migration Complete!")
    print("=" * 60)
    print(f"\n  Total rows migrated: {grand_total} / {total_rows}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
