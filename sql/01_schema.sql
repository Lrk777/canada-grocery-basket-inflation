-- Star schema for monthly average retail prices (StatCan 18-10-0245-01).
-- Grain of fact_price: one product, in one province (or Canada), in one month.

DROP TABLE IF EXISTS fact_price;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_geo;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS basket;

CREATE TABLE dim_date (
    date_key   TEXT PRIMARY KEY,          -- 'YYYY-MM'
    year       INTEGER NOT NULL,
    month      INTEGER NOT NULL,
    quarter    INTEGER NOT NULL
);

CREATE TABLE dim_geo (
    geo_key    INTEGER PRIMARY KEY,
    geo_name   TEXT NOT NULL UNIQUE,
    is_province INTEGER NOT NULL           -- 0 for the Canada aggregate
);

CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY,
    product     TEXT NOT NULL UNIQUE,     -- as published, e.g. 'Butter, 454 grams'
    item        TEXT NOT NULL,            -- text before the first comma
    pack        TEXT NOT NULL,            -- size or unit, e.g. '454 grams', 'per kilogram'
    category    TEXT NOT NULL
);

CREATE TABLE fact_price (
    date_key    TEXT    NOT NULL REFERENCES dim_date(date_key),
    geo_key     INTEGER NOT NULL REFERENCES dim_geo(geo_key),
    product_key INTEGER NOT NULL REFERENCES dim_product(product_key),
    price       REAL    NOT NULL CHECK (price > 0),
    vector      TEXT    NOT NULL,         -- StatCan series ID, kept for traceability
    PRIMARY KEY (date_key, geo_key, product_key)
);

-- Weekly basket and its cheaper-swap version (scenario = 'standard' | 'swap').
CREATE TABLE basket (
    scenario    TEXT    NOT NULL,
    product_key INTEGER NOT NULL REFERENCES dim_product(product_key),
    qty_per_week REAL   NOT NULL CHECK (qty_per_week > 0),
    PRIMARY KEY (scenario, product_key)
);
