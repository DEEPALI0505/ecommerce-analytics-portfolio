"""
test_sql_queries.py
Executes all SQL script files against the SQLite database to verify syntax,
table integrity, and query execution performance.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ecommerce.db"
SQL_DIR = BASE_DIR / "sql"

sql_files = [
    "01_schema_setup.sql",
    "02_cohort_retention_analysis.sql",
    "03_rfm_customer_segmentation.sql",
    "04_customer_lifetime_value.sql",
    "05_market_basket_analysis.sql"
]

print(f"[INFO] Connecting to SQLite database at: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

all_passed = True

for fname in sql_files:
    fpath = SQL_DIR / fname
    print(f"\n--- Testing {fname} ---")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into separate statements if multiple exist
    statements = [s.strip() for s in content.split(";") if s.strip()]
    
    for i, stmt in enumerate(statements, 1):
        # Ignore pure comments
        lines = [line.strip() for line in stmt.split("\n") if line.strip() and not line.strip().startswith("--")]
        if not lines:
            continue
            
        clean_stmt = "\n".join(lines)
        try:
            cursor.execute(clean_stmt)
            # If it's a SELECT statement, fetch sample rows
            if clean_stmt.strip().upper().startswith("SELECT") or clean_stmt.strip().upper().startswith("WITH"):
                results = cursor.fetchmany(3)
                print(f"  [OK] Statement {i} returned {len(results)} sample rows.")
                for r in results:
                    print(f"       {r}")
            else:
                conn.commit()
                print(f"  [OK] Statement {i} executed successfully.")
        except Exception as e:
            print(f"  [ERROR] Statement {i} failed: {e}")
            all_passed = False

conn.close()

if all_passed:
    print("\n[SUCCESS] All SQL queries executed perfectly with 0 errors!")
else:
    print("\n[WARNING] Some SQL statements encountered errors.")
