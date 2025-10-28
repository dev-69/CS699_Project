# database_migrate.py
import sqlite3

DB_NAME = 'jobs.db'

def add_new_columns():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("Adding 'date_posted' and 'num_applicants' columns to 'jobs' table...")
    
    try:
        # Add date_posted column
        cursor.execute("ALTER TABLE jobs ADD COLUMN date_posted TEXT")
        print("- Added 'date_posted'")
    except sqlite3.OperationalError as e:
        print(f"Could not add 'date_posted': {e}") # (Probably already exists)

    try:
        # Add num_applicants column
        cursor.execute("ALTER TABLE jobs ADD COLUMN num_applicants TEXT") # Text, as it might be '100+'
        print("- Added 'num_applicants'")
    except sqlite3.OperationalError as e:
        print(f"Could not add 'num_applicants': {e}") # (Probably already exists)
    
    conn.commit()
    conn.close()
    print("Database migration complete.")

if __name__ == "__main__":
    add_new_columns()