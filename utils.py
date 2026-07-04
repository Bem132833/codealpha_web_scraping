"""
utils.py
---------
CodeAlpha Task 1: Web Scraping — shared helper functions.

Pulling these out of scraper.py keeps the main script focused on the crawl
flow, and lets analysis/cleaning steps reuse the same parsing logic instead
of duplicating it.

Contains:
    - setup_logging()          -> configures console + file logging
    - fetch()                  -> GET with retries/backoff, polite delay
    - rating_word_to_num()     -> "Three" -> 3
    - parse_stock_quantity()   -> "In stock (22 available)" -> 22
    - parse_money()            -> "£51.77" -> 51.77
    - clean_books_dataframe()  -> raw scraped df -> analysis-ready df
"""

import logging
import re
import time
import random
from pathlib import Path

import pandas as pd
import requests

RATING_WORD_TO_NUM = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

DEFAULT_HEADERS = {
    "User-Agent": "CodeAlpha-Internship-Scraper/1.0 (educational project; contact: student)"
}


def setup_logging(log_file: Path, logger_name: str = "scraper") -> logging.Logger:
    """Configure a logger that writes to both the console and a log file."""
    log_file.parent.mkdir(exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # avoid duplicate handlers on repeated runs/imports

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


def fetch(url: str, log: logging.Logger, max_retries: int = 3,
          delay_seconds: float = 1.5) -> requests.Response | None:
    """GET a URL with retries + backoff. Returns None if all retries fail."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
            resp.raise_for_status()
            time.sleep(delay_seconds + random.uniform(0, 0.5))
            return resp
        except requests.RequestException as e:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, max_retries, url, e)
            time.sleep(1.5 * attempt)
    log.error("Giving up on %s after %d attempts", url, max_retries)
    return None


def rating_word_to_num(word: str) -> int | None:
    """Convert a CSS-class rating word ('Three') into an integer (3)."""
    return RATING_WORD_TO_NUM.get(word)


def parse_stock_quantity(availability_text: str) -> int | None:
    """Extract stock quantity from strings like 'In stock (22 available)'."""
    match = re.search(r"\((\d+)\s+available\)", availability_text)
    return int(match.group(1)) if match else None


def parse_money(value: str) -> float | None:
    """Convert a price/tax string like '£51.77' into a float."""
    if not value:
        return None
    cleaned = re.sub(r"[^\d.]", "", value)
    return float(cleaned) if cleaned else None


def clean_books_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Turn the raw scraped data into an analysis-ready dataset.

    Steps:
        - Drop exact duplicate rows (same UPC scraped twice)
        - Drop rows missing a title or price (unusable for analysis)
        - Fill missing descriptions with a placeholder instead of NaN
        - Strip stray whitespace from text fields
        - Standardize category text (title case)
        - Ensure numeric columns are actually numeric, drop rows that fail
    """
    clean = df.copy()

    text_cols = ["title", "category", "upc", "product_type", "description"]
    for col in text_cols:
        if col in clean.columns:
            clean[col] = clean[col].astype(str).str.strip()

    if "category" in clean.columns:
        clean["category"] = clean["category"].str.title()

    if "description" in clean.columns:
        clean["description"] = clean["description"].replace(
            {"": "No description available.", "nan": "No description available."}
        )

    if "upc" in clean.columns:
        clean = clean.drop_duplicates(subset="upc")

    numeric_cols = ["price", "price_excl_tax", "price_incl_tax", "tax", "rating",
                     "stock_qty", "num_reviews"]
    for col in numeric_cols:
        if col in clean.columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce")

    required_cols = [c for c in ["title", "price"] if c in clean.columns]
    clean = clean.dropna(subset=required_cols)

    clean = clean.reset_index(drop=True)
    return clean