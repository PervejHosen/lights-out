"""Run the Lights Out pipeline: bronze -> silver -> gold, in DuckDB.

    cd "F:\\Study Resources\\Load Shedding Project"
    python 02_pipeline\\run.py

Needs: pip install duckdb
Writes 01_data/processed/lights_out.duckdb and one CSV per gold table in 01_data/processed/gold/.
"""
import glob
import os
import time

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
RAW = os.path.join(ROOT, "01_data", "raw").replace("\\", "/")
REF = os.path.join(ROOT, "01_data", "reference").replace("\\", "/")
OUT = os.path.join(ROOT, "01_data", "processed")
os.makedirs(os.path.join(OUT, "gold"), exist_ok=True)

db_path = os.path.join(OUT, "lights_out.duckdb")
con = duckdb.connect(db_path)
for path in sorted(glob.glob(os.path.join(HERE, "sql", "*.sql"))):
    sql = open(path, encoding="utf-8").read().replace("${RAW}", RAW).replace("${REF}", REF)
    t = time.time()
    con.execute(sql)
    print(f"{os.path.basename(path):28s} {time.time() - t:5.1f}s")

for (name,) in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'gold' ORDER BY 1").fetchall():
    con.execute(f"COPY gold.{name} TO '{os.path.join(OUT, 'gold', name + '.csv').replace(chr(92), '/')}' (HEADER)")
    n = con.execute(f"SELECT count(*) FROM gold.{name}").fetchone()[0]
    print(f"  gold.{name:30s} {n:>7,} rows")
con.close()
print(f"\nDone: {db_path}")
