-- =====================================================================
-- DBMS 1 : MySQL  (database: innova_sales)
-- Peran  : sistem TRANSAKSI - menyimpan fakta penjualan wholesale bulanan
-- Catatan: variant_id & period_id adalah "foreign key logis" ke tabel di
--          PostgreSQL. Antar-DBMS tidak bisa FK fisik, jadi penggabungan
--          dilakukan di level aplikasi (pandas.merge) - lihat pipeline.py
-- =====================================================================

DROP TABLE IF EXISTS fact_wholesale;

CREATE TABLE fact_wholesale (
    sale_id     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    period_id   INT          NOT NULL COMMENT 'YYYYMM, kunci logis ke dim_period (PostgreSQL)',
    variant_id  INT          NOT NULL COMMENT 'kunci logis ke dim_variant (PostgreSQL)',
    units       INT          NOT NULL COMMENT 'jumlah unit wholesale (distribusi pabrik ke dealer)',
    source_row  INT          NOT NULL COMMENT 'nomor baris di CSV asli (keterlacakan)',
    PRIMARY KEY (sale_id),
    KEY idx_fact_period  (period_id),
    KEY idx_fact_variant (variant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
