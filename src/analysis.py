"""Answer the project questions from the star schema. Writes CSVs + findings.json to data/processed/.

Usage: python src/analysis.py   (after build_db.py)
"""

from __future__ import annotations

import json
import sqlite3

import pandas as pd

from config import BASE, BASKET, DB, LATEST, OUT, PRE, SQL, SWAPS, WEEKS_PER_YEAR


def q(con, name: str, **params) -> pd.DataFrame:
    return pd.read_sql((SQL / name).read_text(), con, params=params)


def window(con, w) -> pd.DataFrame:
    return q(con, "11_window_prices.sql", start=w[0], end=w[1])


def main() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    f: dict = {"windows": {"pre": PRE, "base": BASE, "latest": LATEST}}

    # 1. Basket cost by province, base vs latest
    rank = q(con, "12_province_ranking.sql", b0=BASE[0], b1=BASE[1], l0=LATEST[0], l1=LATEST[1])
    rank.to_csv(OUT / "province_ranking.csv", index=False)
    f["province_ranking"] = rank.to_dict(orient="records")

    # Monthly basket series for the dashboard
    series = pd.read_sql("SELECT * FROM v_basket_cost WHERE complete = 1 ORDER BY date_key", con)
    series.to_csv(OUT / "basket_monthly.csv", index=False)

    # 2. Which items drove Ontario's increase (contribution to the change in weekly basket cost)
    b, l, p = window(con, BASE), window(con, LATEST), window(con, PRE)
    key = ["geo_name", "product", "category"]
    m = b.merge(l, on=key, suffixes=("_base", "_latest")).merge(
        p.rename(columns={"avg_price": "avg_price_pre", "n_months": "n_months_pre"}), on=key, how="left"
    )
    m["pct_chg"] = 100 * (m.avg_price_latest / m.avg_price_base - 1)
    m["pct_change_since_2017"] = 100 * (m.avg_price_latest / m.avg_price_pre - 1)
    m.to_csv(OUT / "item_changes.csv", index=False)

    on = m[(m.geo_name == "Ontario") & m["product"].isin(BASKET)].copy()
    on["qty"] = on["product"].map(BASKET)
    on["weekly_change"] = (on.avg_price_latest - on.avg_price_base) * on.qty
    total = on.weekly_change.sum()
    on["share_of_increase_pct"] = 100 * on.weekly_change / total
    on = on.sort_values("weekly_change", ascending=False)
    on[["product", "category", "avg_price_base", "avg_price_latest", "pct_chg", "qty", "weekly_change",
        "share_of_increase_pct"]].to_csv(OUT / "ontario_drivers.csv", index=False)
    f["ontario_weekly_change"] = round(total, 2)
    f["ontario_top_drivers"] = on.head(5)[["product", "pct_chg", "weekly_change", "share_of_increase_pct"]].round(2).to_dict(orient="records")
    f["ontario_items_falling"] = on[on.weekly_change < 0][["product", "pct_chg"]].round(1).to_dict(orient="records")

    # 3. Ontario vs Canada, all 110 products: where did Ontario rise faster than the country?
    can = m[m.geo_name == "Canada"].set_index("product").pct_chg
    ont = m[m.geo_name == "Ontario"].set_index("product")
    gap = pd.DataFrame({"category": ont.category, "ontario_pct": ont.pct_chg, "canada_pct": can})
    gap["gap_pts"] = gap.ontario_pct - gap.canada_pct
    gap = gap.sort_values("gap_pts", ascending=False)
    gap.round(2).to_csv(OUT / "ontario_vs_canada_items.csv")
    f["ontario_vs_canada_top"] = gap.head(5).round(1).reset_index().to_dict(orient="records")
    f["ontario_vs_canada_bottom"] = gap.tail(3).round(1).reset_index().to_dict(orient="records")
    cat = m[m.geo_name.isin(["Ontario", "Canada"])].groupby(["category", "geo_name"]).pct_chg.median().unstack()
    cat.round(1).to_csv(OUT / "category_median_change.csv")
    f["category_median_change"] = cat.round(1).reset_index().to_dict(orient="records")

    # 4. Swap savings in every province, latest window, plus a 12-month range for Ontario
    rows = []
    for orig, sub, qty, note in SWAPS:
        for geo in l.geo_name.unique():
            a = l[(l.geo_name == geo) & (l["product"] == orig)].avg_price
            s = l[(l.geo_name == geo) & (l["product"] == sub)].avg_price
            if a.empty or s.empty:
                continue
            weekly = a.iloc[0] * BASKET[orig] - s.iloc[0] * qty
            rows.append({"geo_name": geo, "original": orig, "substitute": sub, "note": note,
                         "weekly_saving": weekly, "annual_saving": weekly * WEEKS_PER_YEAR})
    sw = pd.DataFrame(rows)
    sw.round(2).to_csv(OUT / "swap_savings.csv", index=False)
    by_geo = sw.groupby("geo_name").annual_saving.agg(["sum", "count"]).rename(columns={"sum": "annual_saving", "count": "n_swaps"})
    # The recommendation: only make the swaps that save money in that province right now.
    pos = sw[sw.annual_saving > 0].groupby("geo_name").annual_saving.agg(["sum", "count"])
    by_geo["annual_saving_smart"] = pos["sum"]
    by_geo["n_swaps_smart"] = pos["count"]
    by_geo.round(0).to_csv(OUT / "swap_savings_by_geo.csv")
    f["smart_swap_saving_by_geo"] = by_geo.annual_saving_smart.round(0).to_dict()
    f["swaps_that_cost_more"] = sw[sw.annual_saving <= 0][["geo_name", "original", "substitute", "annual_saving"]].round(0).to_dict(orient="records")
    on_sw = sw[sw.geo_name == "Ontario"].sort_values("annual_saving", ascending=False)
    f["ontario_swaps"] = on_sw[["original", "substitute", "annual_saving"]].round(0).to_dict(orient="records")
    f["ontario_annual_saving"] = round(on_sw.annual_saving.sum(), 0)
    f["ontario_annual_saving_smart"] = round(on_sw[on_sw.annual_saving > 0].annual_saving.sum(), 0)
    std = rank.set_index("geo_name").latest_weekly_cost
    f["ontario_saving_share_of_basket_pct"] = round(100 * on_sw.weekly_saving.sum() / std["Ontario"], 1)
    f["swap_annual_saving_by_geo"] = by_geo.annual_saving.round(0).to_dict()

    # Sensitivity: the same Ontario swap total computed month by month over the last 12 months
    s12 = series[(series.geo_name == "Ontario")].pivot(index="date_key", columns="scenario", values="weekly_cost").tail(12)
    s12["annual_saving"] = (s12.standard - s12.swap) * WEEKS_PER_YEAR
    f["ontario_saving_12m_range"] = [round(s12.annual_saving.min(), 0), round(s12.annual_saving.max(), 0)]
    f["ontario_saving_12m_months"] = [s12.index.min(), s12.index.max()]

    # Same check for the recommended "smart" swaps (only those that save money in Ontario now)
    smart = on_sw[on_sw.annual_saving > 0]
    monthly = pd.read_sql(
        "SELECT p.product, f.date_key, f.price FROM fact_price f JOIN dim_product p USING (product_key) "
        "JOIN dim_geo g USING (geo_key) WHERE g.geo_name = 'Ontario'", con
    ).pivot(index="date_key", columns="product", values="price").tail(12)
    qty = {s: q_ for _, s, q_, _ in SWAPS}
    smart_monthly = sum(
        (monthly[o] * BASKET[o] - monthly[s] * qty[s]) for o, s in zip(smart.original, smart.substitute)
    ) * WEEKS_PER_YEAR
    f["ontario_smart_saving_12m_range"] = [round(smart_monthly.min(), 0), round(smart_monthly.max(), 0)]
    f["ontario_smart_saving_share_of_basket_pct"] = round(100 * smart.weekly_saving.sum() / std["Ontario"], 1)

    # Affordability context: standard basket per year
    f["ontario_annual_basket_latest"] = round(std["Ontario"] * WEEKS_PER_YEAR, 0)

    # 5. Data-quality: largest month-over-month jumps (flagged, not removed)
    jumps = pd.read_sql(
        """SELECT * FROM (
             SELECT g.geo_name, p.product, f.date_key, f.price,
                    f.price / LAG(f.price) OVER (PARTITION BY f.geo_key, f.product_key ORDER BY f.date_key) - 1 AS mom
             FROM fact_price f JOIN dim_geo g USING (geo_key) JOIN dim_product p USING (product_key))
           WHERE ABS(mom) > 0.5 ORDER BY ABS(mom) DESC""", con)
    jumps.to_csv(OUT / "dq_mom_jumps.csv", index=False)
    f["dq_mom_jumps"] = {"n": len(jumps), "by_category": jumps.merge(
        pd.read_sql("SELECT product, category FROM dim_product", con), on="product").category.value_counts().to_dict(),
        "in_basket_ontario": int(jumps[(jumps.geo_name == "Ontario") & jumps["product"].isin(BASKET)].shape[0])}

    con.close()
    (OUT / "findings.json").write_text(json.dumps(f, indent=2, default=float))
    return f


if __name__ == "__main__":
    out = main()
    print(json.dumps(out, indent=1, default=float)[:6000])
