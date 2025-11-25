import time
import random
import shutil
import asyncio
import re
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

def bucket_exp(x):
    x = x.lower().strip()

    if x in ["n/a", "", "not disclosed", "unknown"]:
        return "Unknown"

    if "fresher" in x:
        return "0-1 years"

    nums = re.findall(r'\d+', x)

    if len(nums) == 0:
        return "Unknown"

    nums = [int(n) for n in nums]
    low = nums[0]
    high = nums[1] if len(nums) > 1 else nums[0]

    if high <= 1:
        return "0-1 years"
    elif high <= 3:
        return "1-3 years"
    elif high <= 5:
        return "3-5 years"
    elif high <= 10:
        return "5-10 years"
    else:
        return "10+ years"

def normalize_private_exp(x):

    x = x.lower().strip()

    if x in ["n/a", "", "not disclosed"]:
        return "Unknown"

    if "fresher" in x:
        return "0 years"

    nums = re.findall(r'\d+', x)

    if len(nums) == 0:
        return "Unknown"

    elif len(nums) == 1:
        return f"{nums[0]} years"
    
    else:
        return f"{nums[0]}-{nums[1]} years"


def parse_relative_date(text):
    if not text:
        return datetime.now().strftime("%Y-%m-%d")
    
    text = text.lower()
    today = datetime.now()

    if "just" in text or "today" in text or "hour" in text:
        return today.strftime("%Y-%m-%d")

    match = re.search(r"(\d+)", text)

    if not match:
        return today.strftime("%Y-%m-%d")
    num = int(match.group(1))

    if "day" in text or "d" in text:
        date_obj = today - timedelta(days=num)

    elif "week" in text or "w" in text:
        date_obj = today - timedelta(weeks=num)

    elif "month" in text or "m" in text:
        date_obj = today - timedelta(days=num * 30)

    else:
        date_obj = today

    return date_obj.strftime("%Y-%m-%d")


LINKEDIN_FILTERS = {
    "time": {
        "Any Time": "",
        "Past 24 Hours": "&f_TPR=r86400",
        "Past Week": "&f_TPR=r604800",
        "Past Month": "&f_TPR=r2592000",
    },
    "type": {"Any": "", "On-site": "&f_WT=1", "Remote": "&f_WT=2", "Hybrid": "&f_WT=3"},
    "level": {
        "Any": "",
        "Internship": "&f_E=1",
        "Entry Level": "&f_E=2",
        "Associate": "&f_E=3",
        "Mid-Senior": "&f_E=4",
    },
}

INDEED_FILTERS = {
    "Any Time": "",
    "Past 24 Hours": "&fromage=1",
    "Past Week": "&fromage=7",
    "Past Month": "&fromage=30",
}


class SeleniumScraper:
    def __init__(self):
        self.driver = None

    def get_driver(self, headless=False):
        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--allow-insecure-localhost")

        browser_path = (
            shutil.which("google-chrome")
            or shutil.which("google-chrome-stable")
            or shutil.which("chromium")
        )

        try:
            if browser_path:
                driver = uc.Chrome(
                    options=options,
                    browser_executable_path=browser_path,
                    use_subprocess=True,
                )

            else:
                driver = uc.Chrome(options=options, use_subprocess=True)

            return driver
        
        except Exception as e:
            print(f"Error creating driver: {e}")
            raise

    def scrape_indeed(self, keyword, limit=10, time_filter="Any Time"):
        print(f"[Indeed] Scraping '{keyword}' (limit={limit})")
        jobs = []
        time_param = INDEED_FILTERS.get(time_filter, "")
        page = 0

        try:
            self.driver = self.get_driver(headless=False)

            while len(jobs) < limit:
                url = f"https://in.indeed.com/jobs?q={keyword}&l=India{time_param}&start={page * 10}"
                print(f"[Indeed] Fetching page {page + 1}: {url}")

                try:
                    self.driver.get(url)
                    time.sleep(random.uniform(5, 8))
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.job_seen_beacon")
                        )
                    )

                except Exception as e:
                    print(f"[Indeed] Error loading page: {e}")
                    break

                cards = self.driver.find_elements(
                    By.CSS_SELECTOR, "div.job_seen_beacon"
                )

                if not cards:
                    print("[Indeed] No job cards found")
                    break

                print(f"[Indeed] Found {len(cards)} job cards")

                for card in cards:
                    if len(jobs) >= limit:
                        break

                    try:
                        title = card.find_element(By.CSS_SELECTOR, "h2 span").text

                        company = card.find_element(
                            By.CSS_SELECTOR, "span[data-testid='company-name']"
                        ).text

                        loc = card.find_element(
                            By.CSS_SELECTOR, "div[data-testid='text-location']"
                        ).text

                        salary = "Not Disclosed"
                        try:
                            meta_items = card.find_elements(
                                By.CSS_SELECTOR, ".metadata"
                            )

                            for m in meta_items:
                                txt = m.text
                                if "₹" in txt or "year" in txt or "month" in txt:
                                    salary = txt
                                    break

                        except:
                            pass

                        try:
                            date_text = card.find_element(
                                By.CSS_SELECTOR, "span.date"
                            ).text

                        except:
                            date_text = "Today"

                        try:
                            link = card.find_element(
                                By.CSS_SELECTOR, "a"
                            ).get_attribute("href")

                        except:
                            link = "#"

                        jobs.append(
                            {
                                "title": title,
                                "company": company,
                                "location": loc,
                                "salary": salary,
                                "experience": "N/A",
                                "description": f"{title} {company} {loc}",
                                "job_url": link,
                                "site": "Indeed",
                                "date_posted": parse_relative_date(date_text),
                            }
                        )

                        print(f"[Indeed] Scraped: {title} at {company}")

                    except Exception as e:
                        print(f"[Indeed] Error parsing job: {e}")

                if len(jobs) >= limit:
                    break

                page += 1
                time.sleep(random.uniform(3, 5))

        except Exception as e:
            print(f"[Indeed] Fatal error: {e}")

        finally:
            try:
                self.driver.quit()
            except:
                pass

        print(f"[Indeed] Total scraped: {len(jobs)}")
        return jobs

    def scrape_naukri(self, keyword, location, limit=10):
        print(f"[Naukri] Scraping '{keyword}' (limit={limit})")
        jobs = []
        page = 1

        try:
            self.driver = self.get_driver(headless=False)

            while len(jobs) < limit:
                url = (
                    f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs-{page}"
                )
                print(f"[Naukri] Fetching page {page}: {url}")

                try:
                    self.driver.get(url)
                    time.sleep(random.uniform(5, 8))
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".srp-jobtuple-wrapper")
                        )
                    )

                except Exception as e:
                    print(f"[Naukri] Error loading page: {e}")
                    break

                cards = self.driver.find_elements(
                    By.CSS_SELECTOR, ".srp-jobtuple-wrapper"
                )

                if not cards:
                    print("[Naukri] No job cards found")
                    break

                print(f"[Naukri] Found {len(cards)} job cards")

                for card in cards:
                    if len(jobs) >= limit:
                        break

                    try:
                        title = card.find_element(
                            By.CSS_SELECTOR, ".title"
                        ).text

                        company = card.find_element(
                            By.CSS_SELECTOR, ".comp-name"
                        ).text

                        loc = card.find_element(
                            By.CSS_SELECTOR, ".locWdth"
                        ).text

                        try:
                            exp = card.find_element(
                                By.CSS_SELECTOR, ".expwdth"
                            ).text

                        except:
                            exp = "N/A"


                        try:
                            sal = card.find_element(
                                By.CSS_SELECTOR, ".sal-wrap"
                            ).text

                        except:
                            sal = "Not Disclosed"


                        try:
                            date_text = card.find_element(
                                By.CSS_SELECTOR, ".job-post-day"
                            ).text

                        except:
                            date_text = "Today"


                        try:
                            link = card.find_element(
                                By.CSS_SELECTOR, ".title"
                            ).get_attribute("href")

                        except:
                            link = "#"


                        jobs.append(
                            {
                                "title": title,
                                "company": company,
                                "location": loc,
                                "salary": sal,
                                "experience": exp,
                                "description": f"{title} {company} {loc}",
                                "job_url": link,
                                "site": "Naukri",
                                "date_posted": parse_relative_date(date_text),
                            }
                        )

                        print(f"[Naukri] Scraped: {title} at {company}")

                    except Exception as e:
                        print(f"[Naukri] Error parsing job: {e}")

                if len(jobs) >= limit:
                    break

                page += 1
                time.sleep(random.uniform(3, 5))

        except Exception as e:
            print(f"[Naukri] Fatal error: {e}")

        finally:
            try:
                self.driver.quit()

            except:
                pass

        print(f"[Naukri] Total scraped: {len(jobs)}")
        return jobs

    def scrape_jobkaka(self, limit=30, query=None):
        if query:
            print(f"[JobKaka] Searching for '{query}' (Limit: {limit})")

        else:
            print(f"[JobKaka] Scraping Latest Jobs (Limit: {limit})")

        jobs = []
        current_page = 1

        try:
            self.driver = self.get_driver(headless=True)

            while len(jobs) < limit:
                if query:
                    url = (
                        f"https://www.jobkaka.com/page/{current_page}/?s={query}"
                    )

                else:
                    url = f"https://www.jobkaka.com/page/{current_page}/"

                print(f"[JobKaka] Page {current_page}: {url}")

                try:
                    self.driver.get(url)
                    time.sleep(random.uniform(3, 5))
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "a.content_link")
                        )
                    )

                except Exception as e:
                    print(f"[JobKaka] Error loading page: {e}")
                    break

                job_cards = self.driver.find_elements(
                    By.CSS_SELECTOR, "a.content_link"
                )

                if not job_cards:
                    print("[JobKaka] No more jobs found")
                    break

                print(
                    f"[JobKaka] Found {len(job_cards)} job cards on page {current_page}"
                )

                for job in job_cards:
                    if len(jobs) >= limit:
                        break

                    try:
                        title = job.find_element(
                            By.CSS_SELECTOR, ".entry-title"
                        ).text.strip()

                        details = job.find_elements(
                            By.CSS_SELECTOR, ".entry-job-date-details"
                        )

                        updated_on = (
                            details[0].text.strip() if len(details) > 0 else "N/A"
                        )

                        job_type = (
                            details[1].text.strip() if len(details) > 1 else "N/A"
                        )

                        qualification = (
                            details[2].text.strip() if len(details) > 2 else "N/A"
                        )

                        salary = (
                            details[3].text.strip()
                            if len(details) > 3
                            else "Not Disclosed"
                        )

                        link = job.get_attribute("href")

                        from src.analytics_engine import clean_location

                        state = clean_location(title)
                        if query and state == "Unknown":
                            state = query.capitalize()

                        jobs.append(
                            {
                                "title": title,
                                "company": job_type,
                                "location": state,
                                "salary": salary,
                                "experience": qualification,
                                "description": title,
                                "job_url": link,
                                "site": "JobKaka",
                                "date_posted": updated_on,
                            }
                        )

                        print(f"[JobKaka] Scraped: {title}")

                    except Exception as e:
                        print(f"[JobKaka] Error parsing job: {e}")

                if len(jobs) >= limit:
                    break

                current_page += 1
                time.sleep(random.uniform(2, 4))

        except Exception as e:
            print(f"[JobKaka] Fatal error: {e}")

        finally:
            try:
                self.driver.quit()
            except:
                pass

        print(f"[JobKaka] Total scraped: {len(jobs)}")
        return jobs


class LinkedInScraper:
    async def scrape(
        self,
        keyword,
        location="India",
        limit=10,
        time_filter="Any Time",
        work_type="Any",
        exp_level="Any",
    ):
        print(f"[LinkedIn] Scraping '{keyword}'")
        data = []

        t_param = LINKEDIN_FILTERS["time"].get(time_filter, "")
        w_param = LINKEDIN_FILTERS["type"].get(work_type, "")
        e_param = LINKEDIN_FILTERS["level"].get(exp_level, "")

        base_url = (
            f"https://www.linkedin.com/jobs/search?"
            f"keywords={keyword}&location={location}{t_param}{w_param}{e_param}"
        )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/115.0.0.0 Safari/537.36"
                    )
                )

                print(f"[LinkedIn] Fetching URL: {base_url}")
                await page.goto(base_url, timeout=60000, wait_until="networkidle")

                for _ in range(3):
                    await page.keyboard.press("PageDown")
                    await asyncio.sleep(1)

                cards = await page.query_selector_all(".base-search-card")
                print(f"[LinkedIn] Found {len(cards)} job cards")

                for card in cards[:limit]:
                    try:
                        title_el = await card.query_selector(
                            ".base-search-card__title"
                        )

                        company_el = await card.query_selector(
                            ".base-search-card__subtitle"
                        )

                        loc_el = await card.query_selector(
                            ".job-search-card__location"
                        )

                        link_el = await card.query_selector(
                            ".base-card__full-link"
                        )

                        salary = "Not Disclosed"
                        date_text = "Today"

                        date_el = await card.query_selector("time")
                        if date_el:
                            dt = await date_el.get_attribute("datetime")
                            date_text = dt or await date_el.inner_text()

                        title = (
                            await title_el.inner_text() if title_el else "N/A"
                        )

                        company = (
                            await company_el.inner_text()
                            if company_el
                            else "N/A"
                        )

                        loc = (
                            await loc_el.inner_text() if loc_el else "N/A"
                        )

                        link = (
                            await link_el.get_attribute("href")
                            if link_el
                            else "#"
                        )

                        if "?" in link:
                            link = link.split("?")[0]

                        data.append(
                            {
                                "title": title.strip(),
                                "company": company.strip(),
                                "location": loc.strip(),
                                "salary": salary,
                                "experience": "N/A",
                                "description": title.strip(),
                                "job_url": link,
                                "site": "LinkedIn",
                                "date_posted": parse_relative_date(
                                    date_text.strip()
                                ),
                            }
                        )

                        print(f"[LinkedIn] Scraped: {title}")

                    except Exception as e:
                        print(f"[LinkedIn] Error parsing job: {e}")

                await browser.close()

        except Exception as e:
            print(f"[LinkedIn] Fatal error: {e}")

        print(f"[LinkedIn] Total scraped: {len(data)}")
        return data
