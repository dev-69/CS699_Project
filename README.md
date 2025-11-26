# Job Market Intelligence

A Job Market Intelligence platform that bridges the gap between job discovery and skill acquisition. It automates the search process across fragmented sectors (Private & Government) and provides actionable career insights.

## Features
- Live scraping of private-sector job boards (LinkedIn, Indeed, Naukri) using Playwright / Selenium.
- Government job notifications scraping (JobKaka).
- Stores results in a local SQLite database (`data/jobs.db`) and appends to CSV (`data/all_jobs.csv`).
- Analytics: skill extraction (spaCy), visualisations with Plotly in Streamlit.
- Learning recommendations (YouTube, MIT OCW, Coursera/Udemy) using `youtube-search` and web search (DDGS).

## Requirements
- Python 3.8+ (project tested on 3.10)
- See `requirements.txt` for Python package dependencies. Key packages include:
  - streamlit, pandas, plotly
  - selenium, playwright, undetected-chromedriver
  - spacy, beautifulsoup4

Some components require additional system setup (browsers / drivers):
- Google Chrome / Chromium (for undetected-chromedriver / Selenium)
- Playwright browsers (run `playwright install` after installing Python packages)

## Installation
1. Clone the repo and change into the project folder:

```bash
git clone https://github.com/dev-69/CS699_Project
cd CS699_Project
```

2. Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# If you plan to use Playwright scraping, install browsers:
playwright install
```

3. (Optional) If spaCy model is missing, the app tries to download `en_core_web_sm` automatically. You can also run:

```bash
python -m spacy download en_core_web_sm
```

4. Ensure a Chromium/Chrome executable is available in PATH for undetected-chromedriver / Selenium. On Debian/Ubuntu you can install `chromium` or Google Chrome.

## Usage

- Start the Streamlit UI:

```bash
streamlit run app.py
```

The app exposes a sidebar to select scraping mode (Private / Government), filters and the number of items per site. Use the interface to start scraping. Results are saved into `data/jobs.db` and appended to `data/all_jobs.csv`.

## Project structure

- `app.py` — Streamlit app and main UI logic.
- `requirements.txt` — Python dependencies.
- `data/` — Storage for `jobs.db` (SQLite) and `all_jobs.csv`.
- `src/`
  - `scraper.py` — scrapers using Selenium (Indeed, Naukri, JobKaka) and Playwright (LinkedIn).
  - `database.py` — SQLite helpers and CSV saving/loading.
  - `analytics_engine.py` — skill extraction and location cleaning using spaCy.
  - `recommender.py` — fetches learning resources (YouTube, DDGS searches).
- `lib/` — frontend assets used by the UI.

## Notes 
- Scraping job sites can be fragile. Select appropriate delays and respect site terms of service and robots.txt. This project uses undetected-chromedriver and Playwright, which may still be blocked by some providers.
- For production or heavy scraping, consider using official APIs (if available) or rate-limited worker queues.
- The scrapers open browser instances which will require X display support if run headless=false; prefer headless mode for servers.

## Data
- SQLite DB: `data/jobs.db` (table: `jobs`)
- CSV: `data/all_jobs.csv` (appended rows for each scraped job)
