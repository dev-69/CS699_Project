import time
import random
import shutil
import asyncio
import re
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


def parse_relative_date(text):
    if not text:
        return datetime.now().strftime("%Y-%m-%d")
    text = text.lower()
    today = datetime.now()
    
    if "just" in text or "today" in text or "hour" in text:
        return today.strftime("%Y-%m-%d")
    
    match = re.search(r'(\d+)', text)
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
        "Past Month": "&f_TPR=r2592000"
    },
    "type": {
        "Any": "",
        "On-site": "&f_WT=1",
        "Remote": "&f_WT=2",
        "Hybrid": "&f_WT=3"
    },
    "level": {
        "Any": "",
        "Internship": "&f_E=1",
        "Entry Level": "&f_E=2",
        "Associate": "&f_E=3",
        "Mid-Senior": "&f_E=4"
    }
}

INDEED_FILTERS = {
    "Any Time": "",
    "Past 24 Hours": "&fromage=1",
    "Past Week": "&fromage=7",
    "Past Month": "&fromage=30"
}


class SeleniumScraper:
    def get_driver(self, headless=False):
        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        
        browser_path = shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium")
        if browser_path:
            return uc.Chrome(options=options, browser_executable_path=browser_path, use_subprocess=True)
        return uc.Chrome(options=options, use_subprocess=True)

    def scrape_indeed(self, keyword, limit=10, time_filter="Any Time"):
        driver = self.get_driver(headless=False)
        jobs = []
        time_param = INDEED_FILTERS.get(time_filter, "")
        
        try:
            driver.get(f"https://in.indeed.com/jobs?q={keyword}&l=India{time_param}")
            time.sleep(random.uniform(5, 8))
            
            cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
            for card in cards[:limit]:
                try:
                    title = card.find_element(By.CSS_SELECTOR, "h2 span").text
                    company = card.find_element(By.CSS_SELECTOR, "span[data-testid='company-name']").text
                    loc = card.find_element(By.CSS_SELECTOR, "div[data-testid='text-location']").text
                    
                    try:
                        date_text = card.find_element(By.CSS_SELECTOR, "span.date").text
                    except:
                        date_text = "Today"
                    try:
                        link = card.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    except:
                        link = "N/A"

                    salary = "Not Disclosed"
                    try:
                        meta_items = card.find_elements(By.CSS_SELECTOR, ".metadata")
                        for m in meta_items:
                            txt = m.text
                            if "₹" in txt or "a year" in txt:
                                salary = txt
                                break
                    except:
                        pass

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "salary": salary,
                        "experience": "N/A",
                        "description": title,
                        "job_url": link,
                        "site": "Indeed",
                        "date_posted": parse_relative_date(date_text)
                    })
                except:
                    continue
        finally:
            driver.quit()
        return jobs

    def scrape_naukri(self, keyword, location, limit=10):
        driver = self.get_driver(headless=False)
        jobs = []
        try:
            driver.get(f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs")
            time.sleep(random.uniform(5, 8))
            
            cards = driver.find_elements(By.CSS_SELECTOR, ".srp-jobtuple-wrapper")
            for card in cards[:limit]:
                try:
                    title = card.find_element(By.CSS_SELECTOR, ".title").text
                    company = card.find_element(By.CSS_SELECTOR, ".comp-name").text
                    loc = card.find_element(By.CSS_SELECTOR, ".locWdth").text
                    
                    try:
                        exp = card.find_element(By.CSS_SELECTOR, ".expwdth").text
                    except:
                        exp = "N/A"
                    
                    try:
                        sal = card.find_element(By.CSS_SELECTOR, ".sal-wrap").text
                    except:
                        sal = "Not Disclosed"

                    try:
                        date_text = card.find_element(By.CSS_SELECTOR, ".job-post-day").text
                    except:
                        date_text = "Today"
                    
                    try:
                        link = card.find_element(By.CSS_SELECTOR, ".title").get_attribute("href")
                    except:
                        link = "N/A"

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "salary": sal,
                        "experience": exp,
                        "description": title,
                        "job_url": link,
                        "site": "Naukri",
                        "date_posted": parse_relative_date(date_text)
                    })
                except:
                    continue
        finally:
            driver.quit()
        return jobs
        
    def scrape_jobkaka(self, limit=30, query=None):
        driver = self.get_driver(headless=True)
        all_jobs = []
        current_page = 1

        try:
            while len(all_jobs) < limit:
                if query:
                    url = f"https://www.jobkaka.com/page/{current_page}/?s={query}"
                else:
                    url = f"https://www.jobkaka.com/page/{current_page}/"
                
                driver.get(url)
                time.sleep(2)

                jobs = driver.find_elements(By.CSS_SELECTOR, "a.content_link")
                if not jobs:
                    break

                for job in jobs:
                    if len(all_jobs) >= limit:
                        break

                    try:
                        title = job.find_element(By.CSS_SELECTOR, ".entry-title").text.strip()

                        details = job.find_elements(By.CSS_SELECTOR, ".entry-job-date-details")
                        updated_on = details[0].text.strip() if len(details) > 0 else ""
                        job_type = details[1].text.strip() if len(details) > 1 else ""
                        qualification = details[2].text.strip() if len(details) > 2 else ""
                        salary = details[3].text.strip() if len(details) > 3 else ""
                        link = job.get_attribute("href")
                        
                        state = clean_location(title)
                        if query and state == "Unknown":
                            state = query.capitalize()

                        all_jobs.append({
                            "title": title,
                            "company": job_type,
                            "location": state,
                            "salary": salary,
                            "experience": qualification,
                            "description": title,
                            "job_url": link,
                            "site": "JobKaka",
                            "date_posted": updated_on
                        })

                    except Exception as e:
                        print("Error parsing job:", e)

                current_page += 1
                time.sleep(1)

        finally:
            driver.quit()

        return all_jobs


class LinkedInScraper:
    async def scrape(self, keyword, location="India", limit=10, time_filter="Any Time", work_type="Any", exp_level="Any"):
        data = []
        t_param = LINKEDIN_FILTERS["time"].get(time_filter, "")
        w_param = LINKEDIN_FILTERS["type"].get(work_type, "")
        e_param = LINKEDIN_FILTERS["level"].get(exp_level, "")
        base_url = f"https://www.linkedin.com/jobs/search?keywords={keyword}&location={location}{t_param}{w_param}{e_param}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
            await page.goto(base_url, timeout=60000)
            for _ in range(3):
                await page.keyboard.press("PageDown")
                await asyncio.sleep(1)

            cards = await page.query_selector_all(".base-search-card")
            for card in cards[:limit]:
                try:
                    title_el = await card.query_selector(".base-search-card__title")
                    company_el = await card.query_selector(".base-search-card__subtitle")
                    loc_el = await card.query_selector(".job-search-card__location")
                    link_el = await card.query_selector(".base-card__full-link")
                    
                    sal = "Not Disclosed"
                    
                    date_text = "Today"
                    date_el = await card.query_selector("time")
                    if date_el:
                        dt = await date_el.get_attribute("datetime")
                        date_text = dt if dt else await date_el.inner_text()

                    title = await title_el.inner_text() if title_el else "N/A"
                    company = await company_el.inner_text() if company_el else "N/A"
                    loc = await loc_el.inner_text() if loc_el else "N/A"
                    link = await link_el.get_attribute("href") if link_el else "#"
                    if "?" in link:
                        link = link.split("?")[0]

                    data.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": loc.strip(),
                        "salary": sal,
                        "experience": "N/A",
                        "description": title,
                        "job_url": link,
                        "site": "LinkedIn",
                        "date_posted": parse_relative_date(date_text.strip())
                    })
                except:
                    continue
            await browser.close()
        return data
