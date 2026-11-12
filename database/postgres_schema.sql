-- =====================================================================
-- DBMS 2 : PostgreSQL  (database: innova_catalog)
-- Peran  : katalog MASTER & REFERENSI - dimensi varian, kalender, anotasi
--          peristiwa pasar. Dipakai untuk "memperkaya" fakta dari MySQL.
-- =====================================================================

DROP TABLE IF EXISTS ref_market_event;
DROP TABLE IF EXISTS dim_variant;
DROP TABLE IF EXISTS dim_period;

CREATE TABLE dim_variant (
    variant_id    INTEGER      PRIMARY KEY,
    model         VARCHAR(20)  NOT NULL,
    fuel_type     VARCHAR(20)  NOT NULL,
    transmission  VARCHAR(20)  NOT NULL,
    trim_type     VARCHAR(20)  NOT NULL,
    sub_type      VARCHAR(40)  NOT NULL,
    variant_label VARCHAR(120) NOT NULL,
    CONSTRAINT uq_variant UNIQUE (model, fuel_type, transmission, trim_type, sub_type)
);

CREATE TABLE dim_period (
    period_id   INTEGER     PRIMARY KEY,
    period_date DATE        NOT NULL,
    year        SMALLINT    NOT NULL,
    month_num   SMALLINT    NOT NULL CHECK (month_num BETWEEN 1 AND 12),
    month_name  VARCHAR(3)  NOT NULL,
    quarter     SMALLINT    NOT NULL CHECK (quarter BETWEEN 1 AND 4)
);

CREATE TABLE ref_market_event (
    event_id     SERIAL       PRIMARY KEY,
    event_name   VARCHAR(120) NOT NULL,
    start_period INTEGER      NOT NULL REFERENCES dim_period(period_id),
    end_period   INTEGER      NOT NULL REFERENCES dim_period(period_id),
    category     VARCHAR(40)  NOT NULL,
    description  TEXT,
    source_url   TEXT
);

CREATE INDEX idx_variant_model ON dim_variant (model);
CREATE INDEX idx_period_year   ON dim_period (year);
