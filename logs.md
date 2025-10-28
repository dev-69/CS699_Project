Project Logs - Job Scraper Pro

Oct 28, 2025

V1.0: Initial Concept & Core App

Created initial Flask app (app.py) and index.html.

App scraped job sites (like LinkedIn) on-demand when the user clicked "Search".

This was effective but slow for the user, as they had to wait for the scrape to finish.

V2.0: Architectual Overhaul (Database Model)

Goal: Make the app fast by serving results from a pre-populated database.

Database: Created jobs.db (SQLite) with a jobs table (database_setup.py).

Background Scraper: Created scraper.py to run in the background, scrape jobs, and save them to jobs.db.

Cron Job: Set up a cron job to run scraper.py automatically (e.g., every 8 hours).

App Logic: Changed app.py's /search route to query the jobs.db instead of scraping. This made search results instant.

V2.1: Hybrid Scraper Model

Goal: Handle searches that weren't in our database without showing "0 results."

Logic: Added a "fallback" to app.py. If a search found fewer than 10 jobs (MIN_JOB_THRESHOLD) in the DB, it triggers an on-demand scrape for that specific query, adds the new jobs to the DB, and then re-queries to show the user the fresh results.

V3.0: Core Features & UI

Feature: Pagination: Added a "Load More" button.

Updated app.py to accept a page number and use SQL LIMIT/OFFSET.

Updated script.js to track currentPage and append new results.

Feature: Company Logos: Added a "good enough" logo solution by using Google's favicon service (https://www.google.com/s2/favicons?domain=...).

Feature: Advanced Data:

Added date_posted and num_applicants to the jobs table (database_migrate.py).

Updated scraper.py and app.py to scrape and save this new data.

Updated script.js to display this new data on the job cards.

V3.1: "Smart Search" & Bug Fixes

Feature: Advanced Filters: Changed the single search bar to three distinct fields: Job Title, Company Name, and Location.

Bug Fix: Fixed the on-demand scraper's logic to combine job_title and company_name for a "smarter" search (e.g., "Python" + "Microsoft").

Bug Fix: Fixed the "India" search bug by adding country_indeed to the on-demand scraper.

Feature: Geocoding: Made the on-demand scraper truly smart by adding geopy. It now auto-detects the country from any location string (e.g., "Bangalore" -> "india").

Feature: "Nearby" Search: Added distance=50 to the on-demand scraper to find jobs near the user's location.

Bug Fix: Fixed the search_term vs. company_name bug.

Bug Fix: Fixed the "India" vs. "IN" bug by creating a LOCATION_ALIAS_MAP.

Bug Fix: Fixed the "blank location" bug to allow for worldwide company searches (e.g., "Red Hat").

V4.0: Performance & Stability

Scraper Errors: Diagnosed and fixed 429 (Rate Limit) and 406 (reCAPTCHA) errors.

Stabilized Scraper: Reduced scraper.py to only the most stable sites (LinkedIn, Indeed) and fine-tuned RESULTS_PER_SEARCH to 30.

Performance: Implemented multi-threading in scraper.py using ThreadPoolExecutor to run all predefined searches in parallel, dramatically cutting down the total scrape time.

V5.0: User Platform (Major Update)

Feature: User Authentication:

Added flask-login and flask-bcrypt.

Created the users table.

Added /login, /register, and /logout routes and templates.

Protected the main app and API routes with @login_required.

Feature: Saved Jobs:

Created the saved_jobs (join) table.

Created the /toggle_save API endpoint to save/unsave jobs.

Created the /saved_jobs page to display all of a user's saved jobs.

Updated script.js to add "Save" buttons and handle save-state.

Updated the navbar with a "My Saved Jobs" link.