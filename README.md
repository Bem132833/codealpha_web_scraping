# 📚 Book Store Data Extraction & Price/Rating Analysis

**CodeAlpha Data Analytics Internship — Task 1: Web Scraping**

A Python web scraper that crawls an entire e-commerce book catalogue, stores the
data both raw and cleaned, and runs a light exploratory analysis on pricing and ratings.

## 🎯 Objective

Build a complete, production-style data extraction pipeline — not just a script
that prints values to the console — covering: crawling, error handling, structured
storage, data cleaning, logging, and a first pass at analysis.

## 🔍 Source

[books.toscrape.com](https://books.toscrape.com/) — a site purpose-built for
scraping practice, explicitly intended to be crawled, with no login or paywall.

## ⚙️ Approach

1. **Crawl** all catalogue pages (~1000 books) to collect every book's detail-page URL.
2. **Extract**, per book: title, price, star rating, stock availability & quantity,
   category, UPC, product type, price excl./incl. tax, tax amount, number of
   reviews, and full description.
3. **Store** the results multiple ways:
   - `data/books_raw.csv` — exactly what was scraped, untouched
   - `data/books_clean.csv` — analysis-ready version (deduplicated, validated, standardized)
   - `data/books.db` — a SQLite table (raw data), queryable with SQL
   - `logs/scraper.log` — full run log, also printed to console
4. **Analyze**: run SQL queries directly against the raw database, and build charts
   from the cleaned dataset with Seaborn/Matplotlib.
5. **Explore**: `notebooks/exploration.ipynb` for open-ended, first-look analysis
   separate from the polished scripted version.

## 🧰 Tech Stack

`Python` · `requests` · `BeautifulSoup4` · `SQLite3` · `pandas` · `matplotlib` · `seaborn` · `Jupyter`

## 🛡️ Scraping Etiquette

- Site's `robots.txt` is respected — this domain exists specifically to be scraped.
- Requests are throttled (~0.6s delay) to avoid hammering the server.
- Failed requests are retried with backoff instead of silently failing.
- A descriptive `User-Agent` identifies the scraper as an educational project.

## 🧹 Why Raw *and* Clean Data?

`books_raw.csv` is left exactly as scraped — untouched, including any duplicates
or missing fields. `books_clean.csv` is produced by `utils.clean_books_dataframe()`,
which:
- Drops duplicate books (same UPC scraped twice)
- Drops rows missing a title or price (unusable for analysis)
- Fills missing descriptions instead of leaving `NaN`
- Standardizes category text and strips stray whitespace
- Coerces numeric columns properly, dropping rows that fail

Keeping both versions is a deliberate, common data-engineering practice: you never
overwrite your original extraction, and every cleaning decision is traceable and
reproducible from the raw data if requirements change later.

## 🚧 Challenges & How They Were Solved

| Challenge | Solution |
|---|---|
| Star ratings are stored as CSS classes (`"star-rating Three"`), not numbers | Parsed the class list and mapped word → integer (`utils.rating_word_to_num`) |
| Availability text varies (`"In stock (22 available)"` vs `"In stock"`) | Regex extraction of quantity, with graceful fallback to `None` |
| Relative URLs (`../../../category/...`) differ in depth depending on page | Normalized every link to an absolute URL before requesting it |
| Network hiccups mid-crawl | Retry loop (3 attempts, exponential backoff) per request, shared via `utils.fetch()` |
| Reusing parsing logic across scraping, cleaning, and analysis | Extracted into `utils.py` instead of duplicating code in each script |

## 📊 Sample Findings

*(Fill in with your actual numbers after running the scripts — this section is
what turns the project from "I ran a script" into "I found something".)*

- Most expensive / cheapest categories on average
- How price relates to star rating (higher-rated ≠ necessarily pricier)
- Overall rating distribution across the full catalogue

Charts are saved to `charts/` after running `analysis.py`:
- `price_distribution.png`
- `avg_price_by_category.png`
- `rating_distribution.png`
- `price_vs_rating.png`

## ▶️ How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the scraper (takes a few minutes - ~1000 pages, politely throttled)
#    Produces: data/books_raw.csv, data/books_clean.csv, data/books.db, logs/scraper.log
python scraper.py

# 3. Run the analysis (SQL queries + charts)
python analysis.py

# 4. (Optional) Open the exploration notebook for freeform analysis
jupyter notebook notebooks/exploration.ipynb
```

## 📁 Project Structure

```
codealpha_web_scraping
├── scraper.py              # crawls the site, extracts data, saves raw + clean + SQLite
├── analysis.py              # SQL queries + chart generation
├── utils.py                 # shared helpers: logging, fetch/retry, parsing, cleaning
├── requirements.txt
├── README.md
├── .gitignore
├── notebooks/
│   └── exploration.ipynb    # freeform first-look analysis
├── data/                     # generated after running scraper.py
│   ├── books_raw.csv
│   ├── books_clean.csv
│   └── books.db
├── charts/                   # generated after running analysis.py
│   ├── price_distribution.png
│   ├── avg_price_by_category.png
│   ├── rating_distribution.png
│   └── price_vs_rating.png
└── logs/
    └── scraper.log           # generated after running scraper.py or analysis.py
```

## 📌 Part of the CodeAlpha Data Analytics Internship
This project was completed as Task 1 of the CodeAlpha Data Analytics internship.