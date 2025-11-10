import os
import time
import random
import sqlite3
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
DB_PATH = "jobs.db"
OUTPUT_CSV = "output/jobs.csv"
os.makedirs("output", exist_ok=True)

# ---------------------------------------------------------------------------
# DATABASE SETUP
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            job_url TEXT,
            site TEXT,
            job_type TEXT,
            date_posted TEXT,
            num_applicants TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    return conn


def insert_job(conn, job):
    with conn:
        try:
            conn.execute("""
                INSERT INTO jobs (title, company, location, description, job_url, site, job_type, date_posted, num_applicants)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get("title"), job.get("company"), job.get("location"),
                job.get("description"), job.get("job_url"), job.get("site"),
                job.get("job_type"), job.get("date_posted"), job.get("num_applicants")
            ))
        except sqlite3.IntegrityError:
            pass


# ---------------------------------------------------------------------------
# SELENIUM CONFIGURATION
# ---------------------------------------------------------------------------
def get_driver(headless=False):
    import undetected_chromedriver as uc
    from selenium.webdriver.chrome.service import Service

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")

    # ✅ Realistic user-agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.7444.134 Safari/537.36"
    )

    # ✅ Force uc to use your already installed chromedriver (skip SSL handshake)
    driver = uc.Chrome(
        driver_executable_path="/usr/local/bin/chromedriver",
        options=options,
        use_subprocess=True,
        version_main=142
    )

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


# ---------------------------------------------------------------------------
# INDEED SCRAPER
# ---------------------------------------------------------------------------
def scrape_indeed(keyword="software engineer", pages=3, headless=True):
    print(f"\n🌐 Scraping Indeed for '{keyword}' ...")
    driver = get_driver(headless)
    jobs = []

    base_url = f"https://in.indeed.com/jobs?q={keyword.replace(' ', '+')}&l=India"
    driver.get(base_url)
    time.sleep(random.uniform(6, 9))

    for page in range(1, pages + 1):
        print(f"🌀 Page {page} ...")

        # Scroll to load lazy content
        for scroll_y in range(0, 6):
            driver.execute_script(f"window.scrollTo(0, {scroll_y * 800});")
            time.sleep(random.uniform(1.5, 2.5))
        time.sleep(random.uniform(5, 8))

        cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon, div.slider_container")
        print(f"Page {page}: {len(cards)} job cards found")

        for c in cards:
            try:
                title = c.find_element(By.CSS_SELECTOR, "h2 span").text
                company = c.find_element(By.CSS_SELECTOR, "span[data-testid='company-name']").text
                location = c.find_element(By.CSS_SELECTOR, "div[data-testid='text-location']").text
                try:
                    desc = c.find_element(By.CSS_SELECTOR, "div[data-testid='attribute_snippet_testid']").text
                except:
                    desc = "N/A"
                try:
                    link = c.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                except:
                    link = "N/A"

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": desc,
                    "job_url": link,
                    "site": "Indeed",
                    "job_type": "N/A",
                    "date_posted": datetime.now().strftime("%Y-%m-%d"),
                    "num_applicants": "N/A"
                })
            except Exception:
                continue

        # Try pagination first
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "a[data-testid='pagination-page-next']")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(random.uniform(2, 4))
            next_btn.click()
            time.sleep(random.uniform(8, 12))
            continue
        except Exception:
            print("⚠️ No next button found — trying manual URL fallback...")

        # Manual URL fallback if no button exists
        try:
            next_url = f"{base_url}&start={(page) * 10}"
            driver.get(next_url)
            time.sleep(random.uniform(7, 10))
        except Exception as e:
            print(f"❌ Fallback failed: {e}")
            break

    driver.quit()
    print(f"✅ {len(jobs)} jobs scraped from Indeed.")
    return jobs


# ---------------------------------------------------------------------------
# NAUKRI SCRAPER
# ---------------------------------------------------------------------------
def scrape_naukri(keyword="software engineer", pages=2, headless=False):
    print(f"\n🌐 Scraping Naukri for '{keyword}' ...")
    driver = get_driver(headless)
    jobs = []

    for p in range(1, pages + 1):
        url = f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs-{p}?k={keyword}"
        print(f"Visiting: {url}")
        driver.get(url)
        time.sleep(random.uniform(7, 10))

        cards = driver.find_elements(By.CSS_SELECTOR, ".cust-job-tuple")
        print(f"Page {p}: {len(cards)} job cards found")

        for c in cards:
            try:
                title = c.find_element(By.CSS_SELECTOR, ".title").text
                company = c.find_element(By.CSS_SELECTOR, ".comp-name").text
                location = c.find_element(By.CSS_SELECTOR, ".locWdth").text
                try:
                    desc = c.find_element(By.CSS_SELECTOR, ".job-description").text
                except:
                    desc = "N/A"
                try:
                    link = c.find_element(By.CSS_SELECTOR, ".title").get_attribute("href")
                except:
                    link = "N/A"

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": desc,
                    "job_url": link,
                    "site": "Naukri",
                    "job_type": "N/A",
                    "date_posted": datetime.now().strftime("%Y-%m-%d"),
                    "num_applicants": "N/A"
                })
            except Exception:
                continue
        time.sleep(random.uniform(5, 8))

    driver.quit()
    print(f"✅ {len(jobs)} jobs scraped from Naukri.")
    return jobs


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------
def main():
    conn = init_db()
    all_jobs = []

    job_roles = [
        "software engineer",
        "data scientist",
        "machine learning engineer",
        "backend developer",
        "frontend developer",
        "full stack developer",
        "devops engineer",
        "ai engineer",
        "data analyst",
        "android developer"
    ]

    for role in job_roles:
        print("\n" + "=" * 80)
        print(f"🔍 Starting scraping for role: {role.upper()}")
        print("=" * 80)

        indeed_jobs = scrape_indeed(role, pages=3, headless=False)
        naukri_jobs = scrape_naukri(role, pages=2, headless=False)

        for job in (indeed_jobs + naukri_jobs):
            insert_job(conn, job)

        all_jobs.extend(indeed_jobs + naukri_jobs)
        print(f"💾 Saved {len(indeed_jobs) + len(naukri_jobs)} jobs for role '{role}'.")
        time.sleep(random.randint(10, 15))

    df = pd.DataFrame(all_jobs)
    df.to_csv(OUTPUT_CSV, index=False)
    print("\n🎯 All jobs saved successfully.")
    print(f"📁 CSV: {OUTPUT_CSV}")
    print(f"🗄️  DB: {DB_PATH}")
    print(f"Total: {len(df)} job records scraped.")

    conn.close()


if __name__ == "__main__":
    main()
