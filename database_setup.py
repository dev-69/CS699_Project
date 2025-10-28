# database_setup.py
import sqlite3

DB_NAME = 'jobs.db'

def create_jobs_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, company TEXT, location TEXT, description TEXT,
        job_url TEXT UNIQUE, site TEXT, job_type TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_posted TEXT, num_applicants TEXT
    )
    ''')
    # Add indexes for faster searching
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON jobs (title)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON jobs (location)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company ON jobs (company)")

    conn.commit()
    conn.close()
    print("'jobs' table is ready.")

def create_users_table():
    """Creates the users table for authentication."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()
    print("'users' table is ready.")

# --- ADD THIS NEW FUNCTION ---
def create_saved_jobs_table():
    """
    Creates the saved_jobs table to link users to jobs.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS saved_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (job_id) REFERENCES jobs (id),
        UNIQUE(user_id, job_id) 
    )
    ''')
    # The UNIQUE constraint ensures a user can't save the same job twice.
    conn.commit()
    conn.close()
    print("'saved_jobs' table is ready.")
# --- END NEW FUNCTION ---


if __name__ == "__main__":
    create_jobs_table()
    create_users_table()
    create_saved_jobs_table()  # <-- ADD THIS LINE