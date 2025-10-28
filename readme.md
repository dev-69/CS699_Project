Job Scraper Pro 🚀

Job Scraper Pro is a full-stack Flask application that aggregates job postings from top sites like LinkedIn and Indeed. It uses a hybrid model, combining a fast, pre-populated database with a "smart" on-demand scraper to ensure users always get the most relevant results. The app includes full user authentication, saved jobs, and a multi-threaded background scraper.

Key Features

Hybrid Data Model: Serves 90% of requests instantly from a local SQLite database, with a smart on-demand fallback scraper for queries not in the cache.

Multi-Threaded Background Scraper: An efficient, high-performance scraper.py (using ThreadPoolExecutor) runs on a schedule to keep the database rich and fresh.

Smart Search:

Uses geopy to auto-detect a search's country from its location string.

Searches for jobs within a 50-mile radius of the location.

Intelligently handles location aliases (e.g., "India" -> "IN").

User Authentication: Full user system with registration, login, and password hashing (flask-login + flask-bcrypt).

Saved Jobs: Logged-in users can save jobs, which appear on a dedicated "My Saved Jobs" page.

Dynamic Pagination: A "Load More" button fetches and appends the next page of results without a full page refresh.

Tech Stack

Backend: Python 3, Flask

Scraping: jobspy

Database: SQLite

Auth: flask-login, flask-bcrypt

Geocoding: geopy

Frontend: HTML5, JavaScript (ES6+), Bootstrap 5

How to Set Up and Run

Follow these steps to get the project running locally.

1. Clone & Setup

# Clone the repository (if it's in one)
# git clone ...
# cd job-scraper-pro

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate


2. Install Requirements

Install all necessary Python libraries:

pip install flask pandas jobspy flask-login flask-bcrypt geopy


3. Create the Database

You must run the database setup script one time to create all the necessary tables (jobs, users, saved_jobs).

python database_setup.py


Output:

'jobs' table is ready.
'users' table is ready.
'saved_jobs' table is ready.


4. Run the Background Scraper (First Time)

To make the app useful, you need to populate the database with jobs. Run the multi-threaded scraper manually. This may take several minutes.

python scraper.py


5. Set Up the Automatic Scraper (Cron Job)

To keep your database fresh, set up the cron job to run the scraper automatically.

Open your crontab: crontab -e

Add the following line (adjust paths to match your project location):

This example runs the job every 6 hours.

0 */6 * * * cd /full/path/to/your/project && ./venv/bin/python scraper.py >> /full/path/to/your/project/scraper.log 2>&1


Note: Use which python (inside your venv) and pwd to get the correct absolute paths.

6. Run the Flask App

You're all set! Run the main Flask application:

python app.py


Open your browser and go to http://127.0.0.1:5000. You will be redirected to the login page.

Future Roadmap

This is the plan to evolve the project from a "tool" into a true "platform."

Phase 1: Recruiter Platform (The Big One)

Goal: Allow companies to post their own jobs (which will be prioritized in search).

Users: Add an is_recruiter boolean to the users table.

Database: Create a posted_jobs table (similar to jobs but with a recruiter_id).

UI: Create a "Recruiter Dashboard" with a "Post New Job" form and a list of their active postings.

App Logic: Update /search to query both posted_jobs and jobs, showing the posted_jobs (paid) results first.

Phase 2: Advanced Search & UI

Advanced Filters: Add dropdown filters for "Job Type" (Full-time, Contract, etc.) and "Date Posted" (Last 24h, Last 3 days, etc.).

Two-Pane UI: Re-design the UI so clicking a job on the left loads the full description in a pane on the right, without leaving the page (similar to LinkedIn).

Phase 3: Professional Polish

Pro Logos: Replace the Google favicon trick with a professional API like Brandfetch to get high-quality company logos.

Email Alerts: Allow users to "subscribe" to a search, receiving a daily/weekly email with new jobs that match their criteria.