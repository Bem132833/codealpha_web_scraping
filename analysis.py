"""
analysis.py
------------
CodeAlpha Task 1 (Web Scraping) - bonus analysis layer.

Two data sources are used deliberately:
    - data/books.db (raw)        -> a few example SQL queries, run against the
                                     UNCLEANED data (proves SQL comfort with messy data)
    - data/books_clean.csv        -> used for chart-building (best practice: never
                                     visualize data you haven't validated/cleaned first)

Run this AFTER scraper.py has created data/books.db and data/books_clean.csv
"""

import sqlite3
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from utils import setup_logging

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "books.db"
CLEAN_CSV_PATH = DATA_DIR / "books_clean.csv"
CHARTS_DIR = Path(__file__).parent / "charts"
LOG_PATH = Path(__file__).parent / "logs" / "scraper.log"

log = setup_logging(LOG_PATH, logger_name="analysis")

sns.set_theme(style="whitegrid")


def load_clean_data() -> pd.DataFrame:
    return pd.read_csv(CLEAN_CSV_PATH)


def run_sql_examples():
    """A few example SQL queries against the RAW database - demonstrates SQL skill,
    including handling of duplicate/messy raw data at the query level."""
    conn = sqlite3.connect(DB_PATH)

    print("\n--- Average price per category (top 10) ---")
    q1 = """
        SELECT category, ROUND(AVG(price), 2) AS avg_price, COUNT(DISTINCT upc) AS num_books
        FROM books
        GROUP BY category
        ORDER BY avg_price DESC
        LIMIT 10
    """
    print(pd.read_sql_query(q1, conn).to_string(index=False))

    print("\n--- Top 10 highest-rated, in-stock categories (min 3 books) ---")
    q2 = """
        SELECT category, ROUND(AVG(rating), 2) AS avg_rating, COUNT(DISTINCT upc) AS num_books
        FROM books
        WHERE stock_qty > 0
        GROUP BY category
        HAVING num_books >= 3
        ORDER BY avg_rating DESC
        LIMIT 10
    """
    print(pd.read_sql_query(q2, conn).to_string(index=False))

    conn.close()


def make_charts(df: pd.DataFrame):
    CHARTS_DIR.mkdir(exist_ok=True)

    # 1. Price distribution
    plt.figure(figsize=(8, 5))
    sns.histplot(df["price"], bins=30, kde=True, color="#4C72B0")
    plt.title("Distribution of Book Prices")
    plt.xlabel("Price (£)")
    plt.ylabel("Number of Books")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "price_distribution.png", dpi=150)
    plt.close()

    # 2. Average price by top 10 categories (by book count)
    top_cats = df["category"].value_counts().head(10).index
    subset = df[df["category"].isin(top_cats)]
    avg_price = subset.groupby("category")["price"].mean().sort_values(ascending=False)

    plt.figure(figsize=(9, 5))
    sns.barplot(x=avg_price.values, y=avg_price.index, palette="viridis")
    plt.title("Average Price by Category (Top 10 Most-Stocked Categories)")
    plt.xlabel("Average Price (£)")
    plt.ylabel("Category")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "avg_price_by_category.png", dpi=150)
    plt.close()

    # 3. Rating distribution
    plt.figure(figsize=(6, 5))
    sns.countplot(x="rating", data=df, palette="mako")
    plt.title("Rating Distribution Across All Books")
    plt.xlabel("Star Rating")
    plt.ylabel("Number of Books")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "rating_distribution.png", dpi=150)
    plt.close()

    # 4. Price vs Rating relationship
    plt.figure(figsize=(7, 5))
    sns.boxplot(x="rating", y="price", data=df, palette="crest")
    plt.title("Price Spread by Rating")
    plt.xlabel("Star Rating")
    plt.ylabel("Price (£)")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "price_vs_rating.png", dpi=150)
    plt.close()

    log.info("Charts saved to %s/", CHARTS_DIR)


def main():
    if not DB_PATH.exists():
        print("data/books.db not found - run scraper.py first.")
        return
    if not CLEAN_CSV_PATH.exists():
        print("data/books_clean.csv not found - run scraper.py first.")
        return

    run_sql_examples()

    df = load_clean_data()
    log.info("Loaded %d cleaned books for charting.", len(df))
    make_charts(df)


if __name__ == "__main__":
    main()