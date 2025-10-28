# app.py
import sqlite3
import pandas as pd
from flask import (
    Flask, render_template, request, jsonify, 
    redirect, url_for, flash, session
)
from jobspy import scrape_jobs
import logging
import math
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, 
    logout_user, login_required, current_user
)
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable


app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_really_strong_secret_key_please_change_this' 
DB_NAME = 'jobs.db'
MIN_JOB_THRESHOLD = 10
JOBS_PER_PAGE = 20

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info'

# --- Geocoding Setup ---
geolocator = Nominatim(user_agent="job_scraper_app_v1")

# Map of geopy country name -> jobspy country code
COUNTRY_MAP = {
    "india": "india",
    "united states": "usa",
    "united kingdom": "uk",
    "canada": "canada",
    "australia": "australia",
    "germany": "germany",
    "france": "france",
}

def get_country_from_location(location_str):
    """
    Tries to find a valid jobspy country from a location string.
    Returns None for worldwide, or 'usa' as a fallback.
    """
    location_str = location_str.lower().strip()
    
    # Handle empty string for worldwide search
    if not location_str:
        print("Empty location, returning None for worldwide search.")
        return None
    
    # Handle "Remote"
    if "remote" in location_str:
        return "usa" 
        
    # Check for direct country names
    for key, value in COUNTRY_MAP.items():
        if key in location_str:
            return value

    # Try to geocode the location string
    try:
        location_data = geolocator.geocode(location_str, language="en", addressdetails=True, timeout=5)
        
        if location_data and 'address' in location_data.raw and 'country' in location_data.raw['address']:
            country_name = location_data.raw['address']['country'].lower()
            
            if country_name in COUNTRY_MAP:
                return COUNTRY_MAP[country_name]
            
    except (GeocoderTimedOut, GeocoderUnavailable):
        print(f"Geocoding service timed out for location: {location_str}")
    except Exception as e:
        print(f"Geocoding error: {e}")

    # Fallback for unknown locations
    print(f"Could not determine country for '{location_str}'. Defaulting to 'usa'.")
    return "usa"


# --- User Model & Loader ---
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()
    if user_row:
        return User(id=user_row['id'], username=user_row['username'], email=user_row['email'])
    return None

# --- Helper Function: Save to DB ---
def save_jobs_to_db(jobs_df):
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
            print(f"Error saving row: {e}")
    conn.commit()
    conn.close()
    return new_jobs_count

# --- Helper Function: On-Demand Scrape ---
def run_on_demand_scrape(search_term, company_name, location, country):
    """
    Performs a single, on-demand scrape for a user's query.
    """
    print(f"Running on-demand scrape for: title='{search_term}', company='{company_name}' in '{location}' (country: {country})")
    
    # Build params dynamically
    scrape_params = {
        "site_name": ["linkedin", "indeed"],
        "search_term": search_term,
        "company_name": company_name,
        "location": location,
        "results_wanted": 20,
        "hours_old": 48
    }
    
    # Only add distance/country if a location is specified
    if location and country:
        scrape_params["country_indeed"] = country
        scrape_params["distance"] = 50

    try:
        jobs_df = scrape_jobs(**scrape_params)

        if jobs_df.empty:
            print("On-demand scrape found 0 jobs.")
            return 0
        
        db_columns = ['title', 'company', 'location', 'description', 
                      'job_url', 'site', 'job_type',
                      'date_posted', 'num_applicants']
        
        for col in db_columns:
            if col not in jobs_df.columns:
                jobs_df[col] = 'N/A' 

        jobs_to_save = jobs_df[db_columns]
        saved_count = save_jobs_to_db(jobs_to_save)
        print(f"On-demand scrape saved {saved_count} new jobs.")
        return saved_count

    except Exception as e:
        print(f"Error during on-demand scrape: {e}")
        return 0

# --- Helper Function: Count DB Jobs ---
def count_db_jobs(job_title, company_name, location):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM jobs WHERE 1=1"
    params = []
    if job_title:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f'%{job_title}%', f'%{job_title}%'])
    if company_name:
        query += " AND company LIKE ?"
        params.append(f'%{company_name}%')
    if location:
        query += " AND location LIKE ?"
        params.append(f'%{location}%')
    cursor.execute(query, tuple(params))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- Helper Function: Query DB ---
def query_db_for_jobs(job_title, company_name, location, page=1):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    offset = (page - 1) * JOBS_PER_PAGE
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if job_title:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f'%{job_title}%', f'%{job_title}%'])
    if company_name:
        query += " AND company LIKE ?"
        params.append(f'%{company_name}%')
    if location:
        query += " AND location LIKE ?"
        params.append(f'%{location}%')
    query += " ORDER BY scraped_at DESC LIMIT ? OFFSET ?"
    params.extend([JOBS_PER_PAGE, offset])
    cursor.execute(query, tuple(params))
    results = cursor.fetchall()
    conn.close()
    jobs_list = [dict(row) for row in results]
    return jobs_list


# --- Auth Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
            )
            conn.commit()
            flash('Your account has been created! You are now able to log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists.', 'danger')
        finally:
            conn.close()
    return render_template('register.html', title='Register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user_row = cursor.fetchone()
        conn.close()
        if user_row and bcrypt.check_password_hash(user_row['password'], password):
            user_obj = User(id=user_row['id'], username=user_row['username'], email=user_row['email'])
            login_user(user_obj, remember=request.form.get('remember'))
            flash('Login Successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- NEW: Save Job Route ---

@app.route('/toggle_save', methods=['POST'])
@login_required
def toggle_save():
    """
    Saves or unsaves a job for the current user.
    """
    data = request.get_json()
    job_id = data.get('job_id')
    
    if not job_id:
        return jsonify({'error': 'Job ID is required'}), 400
        
    user_id = current_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    status = ""
    try:
        # Try to insert the saved job.
        cursor.execute(
            "INSERT INTO saved_jobs (user_id, job_id) VALUES (?, ?)",
            (user_id, job_id)
        )
        conn.commit()
        status = "saved"
    except sqlite3.IntegrityError:
        # If it fails (UNIQUE constraint), it's already saved. So we delete it.
        cursor.execute(
            "DELETE FROM saved_jobs WHERE user_id = ? AND job_id = ?",
            (user_id, job_id)
        )
        conn.commit()
        status = "unsaved"
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({'status': status, 'job_id': job_id})

# --- Main App Routes ---
@app.route('/')
@login_required 
def index():
    return render_template('index.html')

# --- NEW: Saved Jobs Page Route ---

@app.route('/saved_jobs')
@login_required
def saved_jobs():
    user_id = current_user.id
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # SQL query to get all jobs from the 'jobs' table
    # that have a matching 'job_id' in the 'saved_jobs' table
    # for the current 'user_id'.
    query = """
    SELECT j.* FROM jobs j
    JOIN saved_jobs sj ON j.id = sj.job_id
    WHERE sj.user_id = ?
    ORDER BY sj.id DESC
    """
    
    cursor.execute(query, (user_id,))
    jobs = cursor.fetchall() # This will be a list of job rows
    conn.close()
    
    # Convert list of sqlite3.Row objects to a list of dicts
    saved_jobs_list = [dict(job) for job in jobs]
    
    # We also pass the list of IDs so the save buttons are "on"
    saved_job_ids = [job['id'] for job in saved_jobs_list]
    
    return render_template(
        'saved_jobs.html', 
        title='My Saved Jobs', 
        jobs=saved_jobs_list, 
        saved_job_ids=saved_job_ids
    )


@app.route('/search', methods=['POST'])
@login_required
def search():
    data = request.get_json()
    job_title = data.get('job_title')
    company_name = data.get('company_name')
    location = data.get('location')
    page = data.get('page', 1)

    if not job_title and not company_name and not location:
        return jsonify({'error': 'At least one search filter is required'}), 400

    try:
        total_jobs_count = count_db_jobs(job_title, company_name, location)
        
        if total_jobs_count < MIN_JOB_THRESHOLD and page == 1 and (job_title or company_name or location):
            print(f"Found only {total_jobs_count} jobs. Triggering live scrape...")

            # --- Location Alias Fix (for "India" -> "IN") ---
            LOCATION_ALIAS_MAP = {
                "india": "IN",
                "united states": "US",
                "usa": "US",
                "united kingdom": "UK",
                "uk": "UK"
            }
            location_to_scrape = LOCATION_ALIAS_MAP.get(location.lower().strip(), location)
            
            # Get country dynamically
            country_to_use = get_country_from_location(location)
    
            if job_title or company_name or location:
                print(f"Running on-demand scrape for: title='{job_title}', company='{company_name}' in '{location_to_scrape}' (Country: {country_to_use})")
                
                # Pass the fixed location and country
                run_on_demand_scrape(job_title, company_name, location_to_scrape, country_to_use) 
    
                # Get the count AGAIN
                total_jobs_count = count_db_jobs(job_title, company_name, location)
                print(f"Total jobs after scrape: {total_jobs_count}")

        total_pages = math.ceil(total_jobs_count / JOBS_PER_PAGE)
        jobs = query_db_for_jobs(job_title, company_name, location, page)

        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = lambda cursor, row: row[0] # Makes cursor return just the first column
        cursor = conn.cursor()
        cursor.execute("SELECT job_id FROM saved_jobs WHERE user_id = ?", (current_user.id,))
        saved_job_ids = cursor.fetchall()
        conn.close()



        return jsonify({
            "jobs": jobs,
            "total_pages": total_pages,
            "current_page": page
        })
        
    except Exception as e:
        print(f"Error in /search endpoint: {e}")
        return jsonify({'error': 'An error occurred while fetching jobs.'}), 500
    
if __name__ == '__main__':
    app.run(debug=True)