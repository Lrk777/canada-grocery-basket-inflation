"""Project settings: sources, the weekly basket, and the swap scenario.

Every assumption a reviewer might question lives here, in one place.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "18100245.csv"
DB = ROOT / "data" / "grocery.sqlite"
OUT = ROOT / "data" / "processed"
SQL = ROOT / "sql"

# Statistics Canada, Table 18-10-0245-01 (Monthly average retail prices for selected products).
STATCAN_URL = "https://www150.statcan.gc.ca/n1/tbl/csv/18100245-eng.zip"
# Unmodified copy of the same table (Jan 2017 - Aug 2024), pinned to a commit so results are reproducible.
MIRROR_URL = "https://github.com/mgfoo/canadianGroceryTrends/raw/183a13ecc47859430fb4ca5660059b70ffa19ad7/data/food_prices.csv"
# GROCERY_SOURCE=pinned (default) reproduces the README; =latest pulls the newest StatCan release.
SOURCES = [MIRROR_URL] if os.environ.get("GROCERY_SOURCE", "pinned") == "pinned" else [STATCAN_URL, MIRROR_URL]
RAW_SHA256 = "5e0acba01465821d695f29c38fc79bb06b7b652be45a7e1dcba6ff8ef3c5a718"

PROVINCES = [
    "Newfoundland and Labrador", "Prince Edward Island", "Nova Scotia", "New Brunswick", "Quebec",
    "Ontario", "Manitoba", "Saskatchewan", "Alberta", "British Columbia",
]

# Comparison windows: the same three summer months in each year, so seasonal produce prices
# (strawberries, tomatoes, lettuce) are compared like for like. An earlier draft compared
# Nov-Jan with Jun-Aug and made summer strawberries look 37% cheaper; that was seasonality.
BASE = ("2021-06", "2021-08")    # the summer before the 2022 food-price surge
LATEST = ("2024-06", "2024-08")  # last three months in the table
PRE = ("2017-06", "2017-08")     # first full summer in the series

# A weekly basket for a two-adult household. Quantities are in each product's own unit
# (e.g. 0.5 of "Butter, 454 grams" = 227 g). Chosen to resemble a common staples list,
# not a CPI weight; see README "Limitations".
BASKET = {
    "Milk, 2 litres": 1,
    "Eggs, 1 dozen": 1,
    "White bread, 675 grams": 1,
    "Butter, 454 grams": 0.5,
    "Block cheese, 500 grams": 0.5,
    "Yogurt, 500 grams": 1,
    "Chicken breasts, per kilogram": 1,
    "Ground beef, per kilogram": 0.5,
    "Salmon, per kilogram": 0.25,
    "Bananas, per kilogram": 1,
    "Apples, per kilogram": 1,
    "Strawberries, 454 grams": 0.5,
    "Potatoes, 4.54 kilograms": 0.25,
    "Carrots, 1.36 kilograms": 0.5,
    "Onions, per kilogram": 0.5,
    "Tomatoes, per kilogram": 0.5,
    "Romaine lettuce, unit": 1,
    "Broccoli, unit": 1,
    "Dry or fresh pasta, 500 grams": 1,
    "White rice, 2 kilograms": 0.25,
    "Cereal, 400 grams": 0.5,
    "Roasted or ground coffee, 340 grams": 0.5,
    "Canned tomatoes, 796 millilitres": 1,
    "Orange juice, 2 litres": 0.5,
}

# Swaps to a cheaper form of the same food, matched on quantity.
# (original, substitute, substitute quantity per week, note)
SWAPS = [
    ("Milk, 2 litres", "Milk, 4 litres", 0.5, "same 2 L, bought as one 4 L jug"),
    ("Chicken breasts, per kilogram", "Chicken thigh, per kilogram", 1, "same 1 kg, thighs instead of breasts"),
    ("Butter, 454 grams", "Margarine, 907 grams", 0.25, "same 227 g"),
    ("Strawberries, 454 grams", "Frozen strawberries, 600 grams", 227 / 600, "same 227 g, frozen"),
    ("Salmon, per kilogram", "Canned salmon, 213 grams", 250 / 213, "same 250 g, canned"),
    ("Broccoli, unit", "Frozen broccoli, 500 grams", 1, "one head (~500 g assumed) vs a 500 g frozen bag"),
    ("Onions, per kilogram", "Onions, 1.36 kilograms", 0.5 / 1.36, "same 500 g, bought by the bag"),
]

WEEKS_PER_YEAR = 52


def category(product: str) -> str:
    p = product.lower()
    if p.startswith("frozen"):
        return "Frozen"
    if p.startswith("canned") or any(w in p for w in ("peanut butter", "juice", "sauce")):
        return "Pantry"
    rules = [
        ("Meat & seafood", ["beef", "pork", "chicken", "bacon", "wieners", "salmon", "shrimp", "tuna"]),
        ("Dairy & eggs", ["milk", "cream", "butter", "margarine", "cheese", "yogurt", "eggs"]),
        ("Frozen", ["frozen"]),
        ("Fresh produce", ["apples", "oranges", "bananas", "pears", "lemons", "limes", "grapes", "cantaloupe",
                           "strawberries", "avocado", "potatoes", "tomatoes", "cabbage", "carrots", "onions",
                           "celery", "cucumber", "mushrooms", "lettuce", "broccoli", "peppers", "squash",
                           "salad greens"]),
        ("Bakery & grains", ["bread", "flatbread", "crackers", "cookies", "pasta", "rice", "cereal", "flour"]),
        ("Pantry", ["sugar", "juice", "coffee", "tea", "ketchup", "oil", "peanut butter", "mayonnaise", "canned",
                    "lentils", "beans", "tofu", "hummus", "salsa", "sauce", "dressing", "almonds", "peanuts",
                    "sunflower", "meatless", "baby food", "infant"]),
        ("Household & personal care", ["deodorant", "toothpaste", "shampoo", "detergent"]),
    ]
    for name, words in rules:
        if any(w in p for w in words):
            return name
    return "Other"
