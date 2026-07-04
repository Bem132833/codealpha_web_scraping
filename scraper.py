"""
scraper.py
-----------
CodeAlpha Data Analytics Internship - Task 1: Web Scraping

Scrapes the full book catalogue from https://books.toscrape.com/
(a website purpose-built for scraping practice - safe, ToS-friendly, no login).

What it collects, per book:
    title, price, rating, availability, stock_qty, category, upc,
    product_type, price_excl_tax, price_incl_tax, tax, num_reviews,
    description, detail_url

Output:
    - data/books_raw.csv     -> exactly what was scraped, untouched
    - data/books_clean.csv   -> analysis-ready version (see utils.clean_books_dataframe)
    - data/books.db          -> SQLite table "books" (raw data), queryable with SQL
    - logs/scraper.log       -> full run log (also printed to console)

Etiquette:
    - Respects robots.txt (this site explicitly allows scraping - it exists for that purpose)
    - Adds a short delay between requests to avoid hammering the server
    - Uses a descriptive User-Agent
    - Retries failed requests a few times before giving up

Shared parsing/logging helpers live in utils.py.
"""

import csv
import re
import sqlite3
from pathlib import Path

from bs4 import BeautifulSoup

from utils import fetch, parse_money, parse_stock_quantity, rating_word_to_num, \
    clean_books_dataframe, setup_logging

BASE_URL = "https://books.toscrape.com/"
CATALOGUE_URL = BASE_URL + "catalogue/page-{}.html"

DATA_DIR = Path(__file__).parent / "data"
RAW_CSV_PATH = DATA_DIR / "books_raw.csv"
CLEAN_CSV_PATH = DATA_DIR / "books_clean.csv"
DB_PATH = DATA_DIR / "books.db"
LOG_PATH = Path(__file__).parent / "logs" / "scraper.log"

log = setup_logging(LOG_PATH, logger_name="scraper")


def get_total_pages() -> int:
    """Read page 1 to find how many catalogue pages exist."""
    resp = fetch(CATALOGUE_URL.format(1), log)
    if resp is None:
        raise RuntimeError("Could not reach the site to determine page count.")
    soup = BeautifulSoup(resp.text, "html.parser")
    current = soup.select_one("li.current")
    if current:
        # text looks like "Page 1 of 50"
        match = re.search(r"of\s+(\d+)", current.get_text())
        if match:
            return int(match.group(1))
    return 1


def get_book_links_from_catalogue(page_num: int) -> list[str]:
    """Return absolute detail-page URLs for every book listed on a catalogue page."""
    resp = fetch(CATALOGUE_URL.format(page_num), log)
    if resp is None:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for h3 in soup.select("h3 a"):
        href = h3.get("href")
        # links are relative to /catalogue/, normalize to absolute
        detail_url = BASE_URL + "catalogue/" + href.replace("../../../", "")
        links.append(detail_url)
    return links


def parse_book_detail(url: str) -> dict | None:
    """Scrape a single book detail page into a dict of fields."""
    resp = fetch(url, log)
    if resp is None:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.select_one("div.product_main h1").get_text(strip=True)

    price_str = soup.select_one("p.price_color").get_text(strip=True)
    price = parse_money(price_str)

    rating_class = soup.select_one("p.star-rating")["class"]
    rating_word = [c for c in rating_class if c != "star-rating"][0]
    rating = rating_word_to_num(rating_word)

    availability_text = soup.select_one("p.availability").get_text(strip=True)
    stock_qty = parse_stock_quantity(availability_text)

    breadcrumb = soup.select("ul.breadcrumb li a")
    category = breadcrumb[-1].get_text(strip=True) if len(breadcrumb) >= 2 else None

    desc_tag = soup.select_one("#product_description")
    description = (
        desc_tag.find_next_sibling("p").get_text(strip=True) if desc_tag else ""
    )

    # product info table: UPC, product type, price excl/incl tax, tax, num reviews
    table = {}
    for row in soup.select("table.table.table-striped tr"):
        key = row.select_one("th").get_text(strip=True)
        val = row.select_one("td").get_text(strip=True)
        table[key] = val

    return {
        "title": title,
        "price": price,
        "rating": rating,
        "availability": availability_text,
        "stock_qty": stock_qty,
        "category": category,
        "upc": table.get("UPC"),
        "product_type": table.get("Product Type"),
        "price_excl_tax": parse_money(table.get("Price (excl. tax)", "")),
        "price_incl_tax": parse_money(table.get("Price (incl. tax)", "")),
        "tax": parse_money(table.get("Tax", "")),
        "num_reviews": int(table.get("Number of reviews", 0) or 0),
        "description": description,
        "detail_url": url,
    }


def save_raw_to_csv(books: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    fieldnames = list(books[0].keys())
    with open(RAW_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(books)
    log.info("Saved %d rows to %s", len(books), RAW_CSV_PATH)


def save_to_sqlite(books: list[dict]) -> None:
    """Save the RAW scraped data to SQLite. Kept intentionally unfiltered so the
    analysis step can demonstrate handling messiness (duplicates, nulls) with SQL."""
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            title TEXT,
            price REAL,
            rating INTEGER,
            availability TEXT,
            stock_qty INTEGER,
            category TEXT,
            upc TEXT PRIMARY KEY,
            product_type TEXT,
            price_excl_tax REAL,
            price_incl_tax REAL,
            tax REAL,
            num_reviews INTEGER,
            description TEXT,
            detail_url TEXT
        )
    """)
    cur.execute("DELETE FROM books")  # fresh run each time
    cur.executemany(
        """INSERT OR REPLACE INTO books VALUES
        (:title, :price, :rating, :availability, :stock_qty, :category, :upc,
         :product_type, :price_excl_tax, :price_incl_tax, :tax, :num_reviews,
         :description, :detail_url)""",
        books,
    )
    conn.commit()
    conn.close()
    log.info("Saved %d rows to %s", len(books), DB_PATH)


def save_clean_csv(books: list[dict]) -> None:
    """Run the raw scraped data through utils.clean_books_dataframe() and save it."""
    import pandas as pd
    raw_df = pd.DataFrame(books)
    clean_df = clean_books_dataframe(raw_df)
    clean_df.to_csv(CLEAN_CSV_PATH, index=False)
    dropped = len(raw_df) - len(clean_df)
    log.info("Saved %d cleaned rows to %s (%d rows dropped/deduplicated)",
              len(clean_df), CLEAN_CSV_PATH, dropped)


def main():
    log.info("Determining total number of catalogue pages...")
    total_pages = get_total_pages()
    log.info("Found %d catalogue pages to crawl.", total_pages)

    all_links = []
    for page in range(1, total_pages + 1):
        links = get_book_links_from_catalogue(page)
        all_links.extend(links)
        log.info("Page %d/%d: found %d books", page, total_pages, len(links))

    log.info("Total book links collected: %d", len(all_links))

    books = []
    for i, link in enumerate(all_links, start=1):
        book = parse_book_detail(link)
        if book:
            books.append(book)
        if i % 50 == 0 or i == len(all_links):
            log.info("Scraped %d/%d books", i, len(all_links))

    if not books:
        log.error("No books scraped - aborting save.")
        return

    save_raw_to_csv(books)
    save_to_sqlite(books)
    save_clean_csv(books)
    log.info("Done.")


if __name__ == "__main__":
    main()