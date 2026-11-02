"""SQLite database management and schema initialization for SyllabusPilot."""
import os
import sqlite3
from typing import Optional

DB_FILE_NAME = "syllabus_pilot.db"


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Returns the absolute path to the SQLite database file."""
    if custom_path:
        return custom_path
    
    # Store database in the project root directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, DB_FILE_NAME)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns an active SQLite connection configured with Row factory and WAL mode."""
    path = get_db_path(db_path)
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes SQLite database schemas for courses, syllabi, assessments, plans, sessions, and recovery logs."""
    conn = get_connection(db_path)
    with conn:
        # 1. Courses Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name TEXT NOT NULL,
                course_code TEXT,
                instructor_name TEXT,
                semester_start TEXT,
                semester_end TEXT,
                study_hours_recommended_per_week REAL,
                raw_syllabus_text TEXT,
                topics_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Syllabi Documents Table (Metadata)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS syllabi_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                file_name TEXT,
                file_type TEXT,
                file_hash TEXT,
                extraction_status TEXT DEFAULT 'completed',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            );
        """)

        # 3. Assessments Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                assessment_type TEXT NOT NULL,
                deadline TEXT,
                weight_percentage REAL,
                description TEXT,
                topics_json TEXT,
                source_reference TEXT,
                verification_status TEXT DEFAULT 'Verified',
                confidence_score REAL DEFAULT 0.9,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            );
        """)

        # 4. Study Plans Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                course_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_planned_hours REAL DEFAULT 0.0,
                hours_per_week REAL DEFAULT 10.0,
                available_days_json TEXT,
                preferred_time_of_day TEXT,
                session_duration_hours REAL DEFAULT 1.5,
                timezone TEXT DEFAULT 'Europe/Riga',
                summary TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            );
        """)

        # 5. Study Sessions Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                session_uid TEXT UNIQUE NOT NULL,
                course_name TEXT NOT NULL,
                assessment_name TEXT NOT NULL,
                topic TEXT NOT NULL,
                session_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_hours REAL NOT NULL,
                is_completed INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                notes TEXT,
                is_revision INTEGER DEFAULT 0,
                FOREIGN KEY (plan_id) REFERENCES study_plans(id) ON DELETE CASCADE
            );
        """)

        # 6. Replanning History Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS replan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                reason TEXT,
                missed_sessions_count INTEGER,
                redistributed_sessions_count INTEGER,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES study_plans(id) ON DELETE CASCADE
            );
        """)

        # 7. Progress Logs Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS progress_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES study_sessions(id) ON DELETE SET NULL
            );
        """)
