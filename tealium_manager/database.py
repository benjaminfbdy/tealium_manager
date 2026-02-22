import sqlite3
import json
import time
import os
import datetime
import pandas as pd
from typing import Dict, List, Optional

DB_FILE = "tealium_manager.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """
    Initializes the database. Creates tables if they don't exist
    and applies necessary schema migrations.
    This function is idempotent and safe to call multiple times.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table for global settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            api_key TEXT,
            email TEXT
        )
    """)

    # --- Schema Migration for global_settings ---
    cursor.execute("PRAGMA table_info(global_settings)")
    columns = [row['name'] for row in cursor.fetchall()]
    
    if 'proxy_user' not in columns:
        print("MIGRATING SCHEMA: Adding 'proxy_user' to 'global_settings' table.")
        cursor.execute("ALTER TABLE global_settings ADD COLUMN proxy_user TEXT")
    
    if 'proxy_password' not in columns:
        print("MIGRATING SCHEMA: Adding 'proxy_password' to 'global_settings' table.")
        cursor.execute("ALTER TABLE global_settings ADD COLUMN proxy_password TEXT")

    # Table for storing Tealium configurations (profiles)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configurations (
            name TEXT PRIMARY KEY,
            account TEXT NOT NULL,
            profile TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 0
        )
    """)
    # Table for caching LATEST profile data for inventory
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile_cache (
            config_name TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            timestamp REAL NOT NULL,
            FOREIGN KEY (config_name) REFERENCES configurations (name) ON DELETE CASCADE
        )
    """)
    # Generic cache for versioned data (used by explorer)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            timestamp REAL NOT NULL,
            etag TEXT
        )
    """)

    # Table for storing Adobe Analytics configurations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adobe_configurations (
            name TEXT PRIMARY KEY,
            auth_method TEXT NOT NULL DEFAULT 'jwt',
            global_company_id TEXT,
            api_key TEXT,
            client_secret TEXT,
            technical_account_id TEXT,
            organization_id TEXT,
            private_key TEXT,
            manual_access_token TEXT,
            secret_key_name TEXT,
            is_active BOOLEAN DEFAULT 0
        )
    """)

    # --- Schema Migration for adobe_configurations ---
    cursor.execute("PRAGMA table_info(adobe_configurations)")
    adobe_columns = [row['name'] for row in cursor.fetchall()]

    if 'auth_method' not in adobe_columns:
        print("MIGRATING SCHEMA: Adding 'auth_method' to 'adobe_configurations' table.")
        cursor.execute("ALTER TABLE adobe_configurations ADD COLUMN auth_method TEXT")
    if 'client_secret' not in adobe_columns:
        print("MIGRATING SCHEMA: Adding 'client_secret' to 'adobe_configurations' table.")
        cursor.execute("ALTER TABLE adobe_configurations ADD COLUMN client_secret TEXT")
    if 'private_key' not in adobe_columns:
        print("MIGRATING SCHEMA: Adding 'private_key' to 'adobe_configurations' table.")
        cursor.execute("ALTER TABLE adobe_configurations ADD COLUMN private_key TEXT")
    if 'manual_access_token' not in adobe_columns:
        print("MIGRATING SCHEMA: Adding 'manual_access_token' to 'adobe_configurations' table.")
        cursor.execute("ALTER TABLE adobe_configurations ADD COLUMN manual_access_token TEXT")
    if 'secret_key_name' not in adobe_columns:
        print("MIGRATING SCHEMA: Adding 'secret_key_name' to 'adobe_configurations' table.")
        cursor.execute("ALTER TABLE adobe_configurations ADD COLUMN secret_key_name TEXT")

    # Table for caching Adobe Analytics components per RSID
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adobe_components (
            rsid TEXT PRIMARY KEY,
            dimensions TEXT NOT NULL,
            metrics TEXT NOT NULL,
            segments TEXT NOT NULL,
            last_updated REAL NOT NULL
        )
    """)

    # Table for storing Saved Report Configurations (Sprint 9)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            adobe_config_name TEXT NOT NULL,
            rsid TEXT NOT NULL,
            definition TEXT NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY (adobe_config_name) REFERENCES adobe_configurations (name) ON DELETE CASCADE
        )
    """)

    # --- Schema Migration for saved_reports ---
    cursor.execute("PRAGMA table_info(saved_reports)")
    saved_reports_columns = [row['name'] for row in cursor.fetchall()]

    # --- FIX: Detect and clean up legacy/WIP schema ---
    if 'metrics' in saved_reports_columns:
        print("MIGRATING SCHEMA: Detected legacy 'saved_reports' table (WIP schema). Recreating table...")
        cursor.execute("DROP TABLE saved_reports")
        cursor.execute("""
            CREATE TABLE saved_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                adobe_config_name TEXT NOT NULL,
                rsid TEXT NOT NULL,
                definition TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (adobe_config_name) REFERENCES adobe_configurations (name) ON DELETE CASCADE
            )
        """)
        # Refresh columns list after recreation
        cursor.execute("PRAGMA table_info(saved_reports)")
        saved_reports_columns = [row['name'] for row in cursor.fetchall()]

    if saved_reports_columns and 'created_at' not in saved_reports_columns:
        print("MIGRATING SCHEMA: Adding 'created_at' to 'saved_reports' table.")
        cursor.execute("ALTER TABLE saved_reports ADD COLUMN created_at REAL DEFAULT 0")

    if saved_reports_columns and 'definition' not in saved_reports_columns:
        print("MIGRATING SCHEMA: Adding 'definition' to 'saved_reports' table.")
        cursor.execute("ALTER TABLE saved_reports ADD COLUMN definition TEXT DEFAULT '{}'")

    conn.commit()

    # Table for caching report results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_results_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            date_range_key TEXT NOT NULL,
            result_data TEXT NOT NULL,
            timestamp REAL NOT NULL,
            status TEXT,
            FOREIGN KEY (report_id) REFERENCES saved_reports (id) ON DELETE CASCADE,
            UNIQUE(report_id, date_range_key)
        )
    """)
    conn.close()

# --- Global Settings Functions ---

def save_global_settings(api_key: str, email: str, proxy_user: str = "", proxy_password: str = ""):
    """Saves or updates the global settings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO global_settings (id, api_key, email, proxy_user, proxy_password) VALUES (1, ?, ?, ?, ?)",
            (api_key, email, proxy_user, proxy_password)
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Database error on save: {e}. A reset might be needed if this persists.")
    finally:
        conn.close()


def load_global_settings() -> Dict[str, str]:
    """Loads the global settings, ensuring all expected keys are present."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure a default row exists, especially for the first run.
    cursor.execute("INSERT OR IGNORE INTO global_settings (id) VALUES (1)")

    cursor.execute("SELECT * FROM global_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    settings = dict(row) if row else {}

    # Default dictionary to ensure all keys are present
    defaults = {
        'api_key': '',
        'email': '',
        'proxy_user': '',
        'proxy_password': ''
    }
    
    # Merge defaults with settings from DB
    defaults.update(settings)

    # Ensure no None values are returned, replace with empty strings
    for key, value in defaults.items():
        if value is None:
            defaults[key] = ''
            
    return defaults

# --- Caching Functions (Legacy/Generic) ---

def get_cached_data(cache_key: str, ttl: int = 3600) -> Optional[Dict]:
    """Retrieves generic cached data if it exists and is not older than the TTL."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data, timestamp FROM api_cache WHERE cache_key = ?", (cache_key,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data, timestamp = row
        if time.time() - timestamp < ttl:
            return json.loads(data)
    return None

def set_cached_data(cache_key: str, data: Dict, etag: Optional[str] = None):
    """Saves data to the generic cache."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO api_cache (cache_key, data, timestamp, etag) VALUES (?, ?, ?, ?)",
        (cache_key, json.dumps(data), time.time(), etag)
    )
    conn.commit()
    conn.close()

def get_profile_cache_info() -> List[Dict]:
    """Retrieves metadata (name, timestamp) for all cached Tealium profiles."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT config_name, timestamp FROM profile_cache")
        cached_profiles = [dict(row) for row in cursor.fetchall()]
        return cached_profiles
    except sqlite3.Error as e:
        print(f"Error fetching profile cache info: {e}")
        return []
    finally:
        conn.close()

# --- DB Status and Maintenance ---

def get_db_status() -> Dict:
    """Checks the status of the database file and its contents."""
    if not os.path.exists(DB_FILE):
        return {"status": "Not Found", "message": "Database file does not exist."}

    try:
        file_size_bytes = os.path.getsize(DB_FILE)
        last_modified_timestamp = os.path.getmtime(DB_FILE)
        last_modified_datetime = datetime.datetime.fromtimestamp(last_modified_timestamp).strftime('%Y-%m-%d %H:%M:%S')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM configurations")
        config_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM adobe_configurations")
        adobe_config_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM profile_cache")
        profile_cache_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM api_cache")
        api_cache_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM adobe_components")
        adobe_components_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM saved_reports")
        saved_reports_count = cursor.fetchone()[0]
        conn.close()

        return {
            "status": "OK",
            "file_size_bytes": file_size_bytes,
            "last_modified": last_modified_datetime,
            "configurations_count": config_count,
            "adobe_configurations_count": adobe_config_count,
            "cached_items_count": profile_cache_count + api_cache_count,
            "cached_adobe_components_count": adobe_components_count,
            "saved_reports_count": saved_reports_count
        }
    except Exception as e:
        return {"status": "Error", "message": str(e)}

def reset_database():
    """Deletes the current database file and re-initializes an empty one."""
    try:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        initialize_database()
        return True
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False

# Initialize the database on startup
initialize_database()