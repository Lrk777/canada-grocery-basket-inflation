"""Checks that the numbers in the README are computed the way the README says.

Run after `python src/build_db.py && python src/analysis.py`.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import BASKET, DB, OUT, SQL, SWAPS, category

needs_db = pytest.mark.skipif(not DB.exists(), reason="run src/build_db.py first")


def test_category_rules_cover_tricky_names():
    assert category("Peanut butter, 1 kilogram") == "Pantry"
    assert category("Canned tomatoes, 796 millilitres") == "Pantry"
    assert category("Pasta sauce, 650 millilitres") == "Pantry"
    assert category("Frozen strawberries, 600 grams") == "Frozen"
    assert category("Chicken thigh, per kilogram") == "Meat & seafood"


def test_swaps_keep_the_same_quantity():
    grams = {"Strawberries, 454 grams": 454 * 0.5, "Butter, 454 grams": 454 * 0.5}
    sub = {o: (s, q) for o, s, q, _ in SWAPS}
    assert sub["Strawberries, 454 grams"][1] * 600 == pytest.approx(grams["Strawberries, 454 grams"], abs=1)
    assert sub["Butter, 454 grams"][1] * 907 == pytest.approx(grams["Butter, 454 grams"], abs=1)
    assert sub["Milk, 2 litres"][1] * 4 == BASKET["Milk, 2 litres"] * 2


@needs_db
def test_hard_dq_checks_pass():
    con = sqlite3.connect(DB)
    dq = pd.read_sql((SQL / "02_dq_checks.sql").read_text(), con).set_index("check_name").n
    assert dq["orphan_dates"] == dq["orphan_products"] == dq["non_positive_prices"] == 0


@needs_db
def test_sql_basket_cost_matches_pandas():
    con = sqlite3.connect(DB)
    sql = pd.read_sql(
        "SELECT weekly_cost FROM v_basket_cost WHERE scenario='standard' AND geo_name='Ontario' AND date_key='2024-08'",
        con,
    ).weekly_cost.iloc[0]
    prices = pd.read_sql(
        "SELECT p.product, f.price FROM fact_price f JOIN dim_product p USING (product_key) "
        "JOIN dim_geo g USING (geo_key) WHERE g.geo_name='Ontario' AND f.date_key='2024-08'",
        con,
    ).set_index("product").price
    assert sql == pytest.approx(sum(prices[p] * q for p, q in BASKET.items()), abs=0.01)


@needs_db
def test_findings_are_internally_consistent():
    f = json.loads((OUT / "findings.json").read_text())
    drivers = pd.read_csv(OUT / "ontario_drivers.csv")
    assert drivers.share_of_increase_pct.sum() == pytest.approx(100, abs=0.01)
    ranks = [r["rank_most_expensive"] for r in f["province_ranking"] if r["geo_name"] != "Canada"]
    assert next(r for r in f["province_ranking"] if r["geo_name"] == "Canada")["rank_most_expensive"] is None
    assert sorted(ranks) == list(range(1, 11))
    assert f["ontario_annual_saving_smart"] >= f["ontario_annual_saving"]
