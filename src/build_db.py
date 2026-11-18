"""Load the raw StatCan CSV into a SQLite star schema and run the data-quality checks.

Usage: python src/build_db.py
"""

from __future__ import annotations

import hashlib
import io
import sqlite3
import sys
import urllib.request
import zipfile

import pandas as pd

from config import BASKET, DB, RAW, RAW_SHA256, SOURCES, SQL, SWAPS, category

HARD_CHECKS = {"orphan_dates", "orphan_products", "non_positive_prices"}


def download() -> None:
    """Fetch the table if it isn't on disk, trying each URL in config.SOURCES in order."""
    if RAW.exists():
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    for url in SOURCES:
        try:
            data = urllib.request.urlopen(url, timeout=120).read()
        except OSError as exc:  # network blocked, 403 bot check, etc.
            print(f"[warn] {url}: {exc}")
            continue
        if url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                data = z.read("18100245.csv")
        RAW.write_bytes(data)
        print(f"downloaded {len(data):,} bytes from {url}")
        return
    sys.exit("could not download the source table; see README 'Data'")


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(RAW, usecols=["REF_DATE", "GEO", "Products", "VALUE", "VECTOR", "UOM"])
    n0 = len(df)
    df = df.dropna(subset=["VALUE"])
    assert (df.UOM == "Dollars").all(), "unexpected unit of measure"
    df["Products"] = df.Products.str.replace(r"\s+", " ", regex=True).str.strip()
    dupes = df.duplicated(["REF_DATE", "GEO", "Products"]).sum()
    assert dupes == 0, f"{dupes} duplicate (month, geo, product) keys"
    print(f"raw rows {n0:,}; kept {len(df):,} with a price")
    return df


def build(df: pd.DataFrame) -> None:
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript((SQL / "01_schema.sql").read_text())

    dates = pd.DataFrame({"date_key": sorted(df.REF_DATE.unique())})
    dates["year"] = dates.date_key.str[:4].astype(int)
    dates["month"] = dates.date_key.str[5:7].astype(int)
    dates["quarter"] = (dates.month - 1) // 3 + 1
    dates.to_sql("dim_date", con, if_exists="append", index=False)

    geos = pd.DataFrame({"geo_name": sorted(df.GEO.unique())})
    geos["geo_key"] = range(1, len(geos) + 1)
    geos["is_province"] = (geos.geo_name != "Canada").astype(int)
    geos.to_sql("dim_geo", con, if_exists="append", index=False)

    prods = pd.DataFrame({"product": sorted(df.Products.unique())})
    prods["product_key"] = range(1, len(prods) + 1)
    prods["item"] = prods["product"].str.split(",").str[0].str.strip()
    prods["pack"] = prods["product"].str.split(",", n=1).str[1].fillna("unit").str.strip()
    prods["category"] = prods["product"].map(category)
    prods.to_sql("dim_product", con, if_exists="append", index=False)

    fact = (
        df.merge(geos, left_on="GEO", right_on="geo_name")
        .merge(prods, left_on="Products", right_on="product")
        .rename(columns={"REF_DATE": "date_key", "VALUE": "price", "VECTOR": "vector"})
    )[["date_key", "geo_key", "product_key", "price", "vector"]]
    fact.to_sql("fact_price", con, if_exists="append", index=False)

    key = dict(zip(prods["product"], prods.product_key))
    rows = [("standard", key[p], q) for p, q in BASKET.items()]
    swap = dict(BASKET)
    for orig, sub, qty, _ in SWAPS:
        swap.pop(orig)
        swap[sub] = qty
    rows += [("swap", key[p], q) for p, q in swap.items()]
    con.executemany("INSERT INTO basket VALUES (?, ?, ?)", rows)
    con.commit()

    for f in sorted(SQL.glob("1*.sql")):
        if "CREATE VIEW" in f.read_text():
            con.executescript(f.read_text())

    dq = pd.read_sql((SQL / "02_dq_checks.sql").read_text(), con)
    print(dq.to_string(index=False))
    bad = dq[dq.check_name.isin(HARD_CHECKS) & (dq.n > 0)]
    con.close()
    if len(bad):
        sys.exit(f"hard data-quality checks failed:\n{bad}")
    print(f"built {DB.name}: {len(fact):,} facts, {len(prods)} products, {len(geos)} geographies, {len(dates)} months")


if __name__ == "__main__":
    download()
    digest = sha256(RAW)
    if digest != RAW_SHA256:
        print(f"[note] raw file differs from the pinned version ({digest[:12]}…); a newer StatCan release?")
    build(load_raw())
