"""
LearnLens - build the PostgreSQL database
=========================================
Runs sql/schema.sql, then bulk-loads the CSVs in data/clean (and the CT
benchmarks in data/external) with COPY.

Setup once:
  1. Install PostgreSQL and create an empty database called learnlens.
  2. Copy .env.example to .env and put your password in DATABASE_URL.
  3. pip install -r requirements.txt

Run:  python scripts/build_database.py
"""

import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "sql" / "schema.sql"

# Parents first, children after, so foreign keys are always satisfied.
LOAD_ORDER = [
    ("programs", "clean"), ("terms", "clean"), ("courses", "clean"), ("cohorts", "clean"),
    ("students", "clean"), ("enrollments", "clean"), ("attendance", "clean"),
    ("grades", "clean"), ("survey_responses", "clean"), ("ct_benchmarks", "external"),
]


def load_env():
    """Tiny .env reader so we don't need an extra package."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def main():
    load_env()
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/learnlens")
    with psycopg.connect(url) as con:
        con.execute(SCHEMA.read_text(encoding="utf-8"))

        print("Loading tables:")
        for name, folder in LOAD_ORDER:
            path = ROOT / "data" / folder / f"{name}.csv"
            with con.cursor() as cur, cur.copy(
                f"COPY sis.{name} FROM STDIN WITH (FORMAT csv, HEADER true)"
            ) as copy:
                with open(path, "rb") as f:
                    while chunk := f.read(1 << 16):
                        copy.write(chunk)
            n = con.execute(f"SELECT count(*) FROM sis.{name}").fetchone()[0]
            print(f"  sis.{name:18s} {n:>6,} rows")

        con.execute("ANALYZE")
        print("\nAll constraints passed (keys, checks, foreign keys).")
    print("Database ready.")


if __name__ == "__main__":
    main()
