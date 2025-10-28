import sqlite3
import pandas as pd
from jobspy import scrape_jobs
import concurrent.futures

# --- Configuration ---
DB_NAME = 'jobs.db'
HOURS_TO_SCRAPE = 6
RESULTS_PER_SEARCH = 30 
MAX_WORKERS = 5 

# --- Location Alias Map (Copied from app.py) ---
# Translates user-friendly names to the short-codes jobspy prefers
LOCATION_ALIAS_MAP = {
    "india": "IN",
    "united states": "US",
    "usa": "US",
    "united kingdom": "UK",
    "uk": "UK",
    "remote": "Remote" # Keep 'Remote' as-is
    # Add more as you find them
}

# --- Added 'country' key and updated locations ---
PREDEFINED_SEARCHES = [
    {"search_term": "Software Engineer", "location": "Remote", "country": "usa"},
    {"search_term": "Data Analyst", "location": "New York, NY", "country": "usa"},
    {"search_term": "Python Developer", "location": "San Francisco, CA", "country": "usa"},
    
    # Use the alias-friendly location "IN" instead of "India"
    {"search_term": "Software Engineer", "location": "IN", "country": "india"},
    {"search_term": "Python Developer", "location": "IN", "country": "india"},
    {"search_term": "Data Analyst", "location": "IN", "country": "india"},
    {"search_term": "Data Scientist", "location": "IN", "country": "india"},
    {"search_term": "Frontend Developer", "location": "IN", "country": "india"},
    {"search_term": "Backend Developer", "location": "IN", "country": "india"},
    {"search_term": "Full Stack Developer", "location": "IN", "country": "india"},
    {"search_term": "DevOps Engineer", "location": "IN", "country": "india"},
    {"search_term": "Product Manager", "location": "IN", "country": "india"},

    {"search_term": "Software Engineer", "location": "Bangalore", "country": "india"},
    {"search_term": "Data Analyst", "location": "Pune", "country": "india"},
    {"search_term": "Software Engineer", "location": "Hyderabad", "country": "india"},

    {"search_term": "Microsoft", "location": "IN", "country": "india"},
    {"search_term": "Google", "location": "IN", "country": "india"},
    {"search_term": "Amazon", "location": "IN", "country": "india"},
    {"search_term": "Infosys", "location": "IN", "country": "india"},
    {"search_term": "TCS", "location": "IN", "country": "india"},
    {"search_term": "Salesforce", "location": "IN", "country": "india"}, # Added Salesforce
    {"search_term": "Red Hat", "location": "IN", "country": "india"},    # Added Red Hat
]
# ---------------------

def save_jobs_to_db(jobs_df):
    """Saves a DataFrame of jobs to the SQLite database, ignoring duplicates."""
    if jobs_df.empty:
        print("No new jobs found to save.")
        return 0

    conn = sqlite3.connect(DB_NAME)
    new_jobs_count = 0
    for _, row in jobs_df.iterrows():
        try:
            row.to_frame().T.to_sql('jobs', conn, if_exists='append', index=False)
            new_jobs_count += 1
        except sqlite3.IntegrityError:
            pass 
        except Exception as e:
            print(f"Error saving row to DB: {e}")
            
    conn.commit()
    conn.close()
    return new_jobs_count

def scrape_one_search(search):
    """
    Scrapes a single search combination. This function will be
    called by each thread.
    """
    
    # --- NEW: Use the alias map ---
    location_to_scrape = LOCATION_ALIAS_MAP.get(search['location'].lower(), search['location'])
    
    print(f"Scraping for: {search['search_term']} in {location_to_scrape} ({search['country']})")
    
    try:
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed"], 
            search_term=search['search_term'],
            location=location_to_scrape, # <-- Use the fixed location
            results_wanted=RESULTS_PER_SEARCH,
            hours_old=HOURS_TO_SCRAPE,
            country_indeed=search['country']
        )
        
        if not jobs.empty:
            # Add columns with default values if they don't exist
            if 'job_type' not in jobs.columns: jobs['job_type'] = 'N/A'
            if 'date_posted' not in jobs.columns: jobs['date_posted'] = 'N/A'
            if 'num_applicants' not in jobs.columns: jobs['num_applicants'] = 'N/A'
            
            db_columns = ['title', 'company', 'location', 'description', 
                          'job_url', 'site', 'job_type',
                          'date_posted', 'num_applicants']
            
            jobs_to_save = jobs[db_columns].fillna('N/A')
            
            print(f"Found {len(jobs_to_save)} jobs for: {search['search_term']}")
            return jobs_to_save
        
        print(f"Found 0 jobs for: {search['search_term']}")

    except Exception as e:
        print(f"Error scraping {search['search_term']}: {e}")
    
    return pd.DataFrame() 

def run_scrape():
    """
    Main function to scrape jobs for all predefined searches in parallel.
    """
    print(f"Starting scheduled scrape for {len(PREDEFINED_SEARCHES)} searches using up to {MAX_WORKERS} threads...")
    
    all_job_dfs = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(scrape_one_search, PREDEFINED_SEARCHES)
        all_job_dfs = [df for df in results if not df.empty]

    if not all_job_dfs:
        print("\nNo new jobs found in this scrape cycle.")
        return

    all_new_jobs_df = pd.concat(all_job_dfs, ignore_index=True)

    if not all_new_jobs_df.empty:
        all_new_jobs_df.drop_duplicates(subset=['job_url'], inplace=True)
        
        print(f"\nTotal new unique jobs found across all searches: {len(all_new_jobs_df)}")
        saved_count = save_jobs_to_db(all_new_jobs_df)
        print(f"Successfully saved {saved_count} new jobs to the database.")
    else:
        print("\nNo new jobs found in this scrape cycle (after deduplication).")

if __name__ == "__main__":
    run_scrape()