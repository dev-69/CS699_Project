import sqlite3
import os
import pandas as pd

DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "jobs.db")
CSV_PATH = os.path.join(DATA_DIR, "all_jobs.csv")

os.makedirs(DATA_DIR, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                company TEXT,
                location TEXT,
                salary TEXT,
                experience TEXT,
                description TEXT,
                job_url TEXT UNIQUE,
                site TEXT,
                date_posted TEXT
            )
        """)
    return conn


def insert_job(conn, job):
    try:
        with conn:
            conn.execute("""
                INSERT OR IGNORE INTO jobs
                (title, company, location, salary, experience, description, job_url, site, date_posted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get("title"),
                job.get("company"),
                job.get("location"),
                job.get("salary", "Not Disclosed"),
                job.get("experience", "N/A"),
                job.get("description", "N/A"),
                job.get("job_url"),
                job.get("site"),
                job.get("date_posted")
            ))
    except sqlite3.Error:
        pass


def export_to_csv(output_path="data/all_jobs.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM jobs", conn)
        df.to_csv(output_path, index=False)
        return df
    finally:
        conn.close()


def save_to_csv(job):
    df_job = pd.DataFrame([job])

    if not os.path.exists(CSV_PATH):
        df_job.to_csv(CSV_PATH, index=False)
        return

    df_job.to_csv(CSV_PATH, mode="a", header=False, index=False)


def load_all_jobs():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM jobs", conn)
    conn.close()
    return df


def load_all_jobs_csv():
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()
    try:
        return pd.read_csv(CSV_PATH)
    except:
        return pd.DataFrame()
