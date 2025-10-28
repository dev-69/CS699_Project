# scheduler.py
import schedule
import time
import subprocess
import sys

def run_scraper_job():
    print("Scheduler: Running scraper.py job...")
    try:
        # Use the same Python interpreter that is running this script
        subprocess.run([sys.executable, 'scraper.py'], check=True)
        print("Scheduler: scraper.py job finished.")
    except subprocess.CalledProcessError as e:
        print(f"Scheduler: Error running scraper.py: {e}")

# Schedule the job
# You can change this to your liking
schedule.every(8).hours.do(run_scraper_job)
# schedule.every().day.at("10:30").do(run_scraper_job)
# schedule.every(1).minutes.do(run_scraper_job) # For testing

print("Scheduler started. Waiting to run scheduled jobs...")

# Run the job once immediately at the start
run_scraper_job() 

while True:
    schedule.run_pending()
    time.sleep(60) # Check every 60 seconds