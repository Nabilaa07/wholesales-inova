"""Seed script: CSV Kaggle -> MySQL (fakta) + PostgreSQL (dimensi/referensi).

Pemakaian (dari root repo):
    python database/seed_data.py              # seed kedua database
    python database/seed_data.py --only mysql
    python database/seed_data.py --only postgres
    python database/seed_data.py --dry-run    # hanya validasi & tampilkan ringkasan

Skema dibuat ulang (DROP + CREATE) setiap dijalankan -> aman diulang (idempotent).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from db import get_mysql_engine, get_postgres_engine  # noqa: E402

CSV_PATH = ROOT / "data" / "Innova_Wholesales_Data_2017_2026.csv"
EVENTS_PATH = ROOT / "database" / "seed" / "market_events.csv"
NO_SUB = "Tanpa Sub-Tipe"
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def load_and_clean(path: Path = CSV_PATH):
    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]
    df = raw.rename(columns={
        "Year": "year", "Month": "month", "Model": "model", "Fuel_Type": "fuel_type",
        "Transmission": "transmission", "Type": "trim_type", "Wholesale": "units",
        "Sub-Type": "sub_type",
    }).copy()
    df["source_row"] = df.index + 2  # +1 header, +1 karena indeks mulai 0 -> nomor baris file
    for col in ["model", "fuel_type", "transmission", "trim_type", "month"]:
        df[col] = df[col].astype(str).str.strip()
    df["sub_type"] = df["sub_type"].fillna(NO_SUB).astype(str).str.strip()
    df["month_num"] = df["month"].str[:3].map(MONTHS)  # 'Sept' -> 'Sep'
    if df["month_num"].isna().any():
        raise ValueError("Ada nama bulan yang tidak dikenali")
    df["period_id"] = df["year"] * 100 + df["month_num"]

    # ---- dim_variant ----
    key = ["model", "fuel_type", "transmission", "trim_type", "sub_type"]
    dim_variant = df[key].drop_duplicates().sort_values(key).reset_index(drop=True)
    dim_variant["variant_id"] = dim_variant.index + 1

    def label(r):
        sub = "" if r.sub_type == NO_SUB else f" {r.sub_type}"
        return f"{r.model} {r.trim_type}{sub} - {r.fuel_type} {r.transmission}"

    dim_variant["variant_label"] = dim_variant.apply(label, axis=1)
    dim_variant = dim_variant[["variant_id", *key, "variant_label"]]

    # ---- dim_period ----
    dim_period = df[["period_id", "year", "month_num"]].drop_duplicates().sort_values("period_id")
    dim_period["period_date"] = pd.to_datetime(
        dict(year=dim_period["year"], month=dim_period["month_num"], day=1)).dt.date
    dim_period["month_name"] = dim_period["month_num"].map({v: k for k, v in MONTHS.items()})
    dim_period["quarter"] = (dim_period["month_num"] - 1) // 3 + 1
    dim_period = dim_period[["period_id", "period_date", "year", "month_num", "month_name", "quarter"]]

    # ---- fact_wholesale ----
    fact = df.merge(dim_variant[["variant_id", *key]], on=key, how="left", validate="m:1")
    fact = fact[["period_id", "variant_id", "units", "source_row"]].sort_values("source_row")

    events = pd.read_csv(EVENTS_PATH)
    events["source_url"] = events["source_url"].where(events["source_url"].notna(), None)
    return fact, dim_variant, dim_period, events


def run_sql_file(engine, path: Path) -> None:
    statements = []
    for chunk in path.read_text(encoding="utf-8").split(";"):
        lines = [ln for ln in chunk.splitlines() if not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def seed_mysql(fact: pd.DataFrame) -> None:
    eng = get_mysql_engine()
    run_sql_file(eng, ROOT / "database" / "mysql_schema.sql")
    fact.to_sql("fact_wholesale", eng, if_exists="append", index=False, chunksize=500, method="multi")
    print(f"[MySQL]      fact_wholesale     : {len(fact):>5} baris")


def seed_postgres(dim_variant, dim_period, events) -> None:
    eng = get_postgres_engine()
    run_sql_file(eng, ROOT / "database" / "postgres_schema.sql")
    dim_period.to_sql("dim_period", eng, if_exists="append", index=False, chunksize=500, method="multi")
    dim_variant.to_sql("dim_variant", eng, if_exists="append", index=False, chunksize=500, method="multi")
    events.to_sql("ref_market_event", eng, if_exists="append", index=False)
    print(f"[PostgreSQL] dim_period         : {len(dim_period):>5} baris")
    print(f"[PostgreSQL] dim_variant        : {len(dim_variant):>5} baris")
    print(f"[PostgreSQL] ref_market_event   : {len(events):>5} baris")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["mysql", "postgres"], help="seed salah satu DBMS saja")
    ap.add_argument("--dry-run", action="store_true", help="validasi CSV tanpa menyentuh database")
    args = ap.parse_args()

    fact, dim_variant, dim_period, events = load_and_clean()
    print(f"CSV dibaca: {len(fact)} baris fakta | {len(dim_variant)} varian | "
          f"{len(dim_period)} periode | total unit = {int(fact['units'].sum()):,}")
    if args.dry_run:
        return
    if args.only in (None, "postgres"):
        seed_postgres(dim_variant, dim_period, events)
    if args.only in (None, "mysql"):
        seed_mysql(fact)
    print("Selesai.")


if __name__ == "__main__":
    main()
