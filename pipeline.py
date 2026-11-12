"""Pipeline integrasi data lintas-DBMS (federasi di level aplikasi).

  MySQL      -> fact_wholesale                 (transaksi)
  PostgreSQL -> dim_variant, dim_period, ref_market_event (master/referensi)
                         |
                  pandas.merge()  <- penggabungan terjadi DI SINI, bukan di SQL
                         |
                   DataFrame siap-visual
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy.engine import Engine

SQL_FACT = "SELECT sale_id, period_id, variant_id, units, source_row FROM fact_wholesale"
SQL_VARIANT = """SELECT variant_id, model, fuel_type, transmission, trim_type, sub_type, variant_label
                 FROM dim_variant"""
SQL_PERIOD = "SELECT period_id, period_date, year, month_num, month_name, quarter FROM dim_period"
SQL_EVENT = """SELECT event_name, start_period, end_period, category, description, source_url
               FROM ref_market_event ORDER BY start_period"""


@dataclass
class IntegrationReport:
    rows_fact_mysql: int
    rows_dim_variant_pg: int
    rows_dim_period_pg: int
    rows_merged: int
    unmatched_variant: int
    unmatched_period: int
    units_before: int
    units_after: int

    @property
    def ok(self) -> bool:
        return (
            self.rows_fact_mysql == self.rows_merged
            and self.unmatched_variant == 0
            and self.unmatched_period == 0
            and self.units_before == self.units_after
        )


def extract(mysql_engine: Engine, pg_engine: Engine) -> dict[str, pd.DataFrame]:
    """EXTRACT: satu kueri per DBMS."""
    return {
        "fact": pd.read_sql(SQL_FACT, mysql_engine),
        "variant": pd.read_sql(SQL_VARIANT, pg_engine),
        "period": pd.read_sql(SQL_PERIOD, pg_engine),
        "event": pd.read_sql(SQL_EVENT, pg_engine),
    }


def integrate(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, IntegrationReport]:
    """TRANSFORM/JOIN: gabungkan fakta (MySQL) dengan dimensi (PostgreSQL)."""
    fact, variant, period = frames["fact"], frames["variant"], frames["period"].copy()
    period["period_date"] = pd.to_datetime(period["period_date"])

    # validate="m:1" -> pandas error bila dimensi punya kunci ganda (menjaga integritas join)
    m = fact.merge(variant, on="variant_id", how="left", validate="m:1", indicator="_v")
    unmatched_v = int((m["_v"] != "both").sum())
    m = m.drop(columns="_v").merge(period, on="period_id", how="left", validate="m:1", indicator="_p")
    unmatched_p = int((m["_p"] != "both").sum())
    m = m.drop(columns="_p")

    m["powertrain"] = m["fuel_type"] + " " + m["transmission"]
    m = m.sort_values(["period_date", "variant_id"]).reset_index(drop=True)

    report = IntegrationReport(
        rows_fact_mysql=len(fact),
        rows_dim_variant_pg=len(variant),
        rows_dim_period_pg=len(period),
        rows_merged=len(m),
        unmatched_variant=unmatched_v,
        unmatched_period=unmatched_p,
        units_before=int(fact["units"].sum()),
        units_after=int(m["units"].sum()),
    )
    return m, report


def prepare_events(events: pd.DataFrame) -> pd.DataFrame:
    ev = events.copy()
    ev["start_date"] = pd.to_datetime(ev["start_period"].astype(str) + "01", format="%Y%m%d")
    ev["end_date"] = pd.to_datetime(ev["end_period"].astype(str) + "01", format="%Y%m%d") + pd.offsets.MonthBegin(1)
    return ev
