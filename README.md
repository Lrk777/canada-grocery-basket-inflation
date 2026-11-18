# What a weekly grocery basket costs across Canada

**Live dashboard: [lrk777.github.io/canada-grocery-basket-inflation](https://lrk777.github.io/canada-grocery-basket-inflation/)**. Pick a province to see its basket cost over time, what drove the increase, and which swaps pay off there.

## The question

How much more does the same weekly basket of 24 grocery staples cost in each province than it did before the 2022 food-price surge? Which items drove Ontario's increase, and how much could a household save a year by switching to cheaper forms of the same food?

## Key findings

All figures compare June–August 2021 with June–August 2024, using the same three summer months so seasonal produce is compared like for like.

1. **The basket rose 11–23% depending on the province.** British Columbia rose the most (+22.5%, $80.55 → $98.67 a week) and Quebec the least (+10.8%). Ontario was second-cheapest and second-slowest: +16.4%, from $74.58 to $86.80 a week, or about $4,514 a year.
2. **Ground beef alone drove 18% of Ontario's increase.** Its price rose 52% in Ontario against 38% nationally, the widest Ontario-vs-Canada gap of all 110 products. Romaine lettuce (+53%) and orange juice (+52%) came next. Chicken breasts (−4%) and white rice (−15%) got cheaper.
3. **Five swaps save an Ontario household about $501 a year (11% of the basket),** with the same amount of food: 4 L milk instead of two 2 L cartons, chicken thighs instead of breasts, canned instead of fresh salmon, margarine instead of butter, and onions by the bag. Across the last 12 months that saving ranged from $285 to $561. Two "obvious" swaps cost more in Ontario: frozen broccoli (−$58 a year) and frozen strawberries (−$4).

| Province | Weekly basket, summer 2021 | Summer 2024 | Change | Smart-swap saving a year |
|---|---:|---:|---:|---:|
| British Columbia | $80.55 | $98.67 | +22.5% | $551 |
| Newfoundland and Labrador | $80.70 | $98.58 | +22.2% | $608 |
| Alberta | $78.69 | $95.67 | +21.6% | $512 |
| Prince Edward Island | $79.06 | $95.36 | +20.6% | $480 |
| Nova Scotia | $78.32 | $94.62 | +20.8% | $524 |
| New Brunswick | $79.00 | $94.40 | +19.5% | $514 |
| Saskatchewan | $76.35 | $92.30 | +20.9% | $487 |
| Manitoba | $74.89 | $91.69 | +22.4% | $444 |
| **Ontario** | **$74.58** | **$86.80** | **+16.4%** | **$501** |
| Quebec | $77.64 | $86.04 | +10.8% | $247 |
| Canada (average) | $76.44 | $88.50 | +15.8% | $423 |

## Recommendation

For a household or a budgeting app: **make a swap only where it saves money in your province, and recheck every few months.** A fixed list of "cheap swaps" is wrong in places. In Quebec, chicken thighs cost more than breasts, which turns a $151 Ontario saving into a $90 loss. Frozen broccoli costs more than fresh everywhere east of Manitoba. Province-specific swaps save $247–$608 a year depending on the province.

For a retailer or a food-insecurity program in Ontario: **watch ground beef first.** It is the largest single driver of the basket increase, and it rose 14 percentage points faster in Ontario than nationally. A promotion or subsidy there moves the basket more than one on any other staple.

| Option | Saves (Ontario, a year) | Trade-off |
|---|---:|---|
| All five money-saving swaps | ~$501 | Taste and preference (thighs, margarine, canned salmon); 4 L milk needs fridge space |
| Only milk and chicken | ~$279 | Simplest change; keeps fresh salmon and butter |
| Every swap on a generic list (7) | ~$439 | Includes 2 swaps that lose money here |

## Data

| | |
|---|---|
| Source | Statistics Canada, [Table 18-10-0245-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810024501), *Monthly average retail prices for selected products* (DOI [10.25318/1810024501-eng](https://doi.org/10.25318/1810024501-eng)) |
| Coverage | 110 products × 10 provinces + Canada × 92 months (Jan 2017 – Aug 2024); 111,228 prices |
| Licence | [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/reference/licence) |
| How it is fetched | `src/build_db.py` downloads an unmodified public copy of the StatCan export ([mgfoo/canadianGroceryTrends](https://github.com/mgfoo/canadianGroceryTrends), pinned to a commit and checked by SHA-256), so anyone gets the same numbers as this README. `GROCERY_SOURCE=latest` pulls the newest release from StatCan instead |

Raw data, the SQLite database, outputs and the dashboard are not committed. A GitHub Actions workflow rebuilds them on every push, runs the tests, and publishes the dashboard to GitHub Pages.

## Method

1. **Ingest and validate.** Load the CSV, check that the unit is dollars and that there are no duplicate (month, province, product) keys or missing prices. There were none.
2. **SQL star schema** (`sql/01_schema.sql`): `fact_price` (product × geography × month, with the StatCan series ID kept for traceability), `dim_product` (item, pack size, category), `dim_geo`, `dim_date`, and a `basket` table holding the standard and swap scenarios.
3. **Data-quality checks** (`sql/02_dq_checks.sql`): hard checks (orphan keys, non-positive prices) stop the build. Soft checks are reported: 315 month-over-month jumps above 50% (191 in meat, 95 in produce; consistent with promotions, so kept), and 4 L milk not being published for Newfoundland and Labrador (that swap is skipped there).
4. **Basket cost** (`sql/10_basket_cost.sql`): a view that prices the weekly basket for every province and month, and marks a month complete only if every item has a price.
5. **Analysis** (`src/analysis.py`): province ranking (`sql/12`), each item's contribution to the change in weekly cost, Ontario vs Canada for all 110 products, and swap savings per province, with a 12-month range as a sensitivity check.
6. **Dashboard** (`src/dashboard.py`): one self-contained HTML page with no libraries, served by GitHub Pages.

**A mistake caught along the way:** the first draft compared Nov 2021–Jan 2022 with Jun–Aug 2024. Summer strawberries then looked 37% cheaper, and fresh produce looked like it was falling. Comparing the same summer months removed that seasonal artefact; strawberries are actually up 8% in Ontario.

## Dashboard

[Open the live dashboard](https://lrk777.github.io/canada-grocery-basket-inflation/). It has four views, all driven by a province selector: weekly basket cost by month against the Canada average, the increase by province, which items drove it, and the swap savings. Every chart has a table view.

## How to run

```bash
pip install -r requirements.txt
python src/build_db.py     # download, load the star schema, run data-quality checks
python src/analysis.py     # findings -> data/processed/
python src/dashboard.py    # dashboard/index.html
pytest -q
```

## Limitations and next steps

- **Average prices are not a price index.** StatCan recommends the Consumer Price Index (table 18-10-0004-01) for measuring inflation. Average prices can shift when the mix of brands and stores changes. The basket here is a household cost estimate, not an inflation rate.
- **The basket is illustrative.** The 24 items and quantities resemble a two-adult staples list. They are not CPI weights and not a nutritious-food basket (such as Ontario's Nutritious Food Basket).
- **Swaps assume equal value per kilogram or litre.** One broccoli head is assumed to weigh about 500 g. Taste, waste and nutrition differences are not priced.
- **The data ends in August 2024.** The next step is to rerun on the latest StatCan release, add the CPI food index as a cross-check, and add income (average weekly earnings, table 14-10-0223-01) to show the basket as a share of pay.
- A Tableau Public version of the dashboard is planned.

## Author

Lavanya Kumar · Bachelor of Data Science (Honours), York University, graduating April 2027 · [GitHub](https://github.com/Lrk777) · [LinkedIn](https://www.linkedin.com/in/lavanya-kumar-610a07214)
