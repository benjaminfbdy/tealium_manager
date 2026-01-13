import sqlite3
import json
import time
import os
import datetime
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
            is_active BOOLEAN DEFAULT 0
        )
    """)

    conn.commit()
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

# --- Tealium Configuration Management Functions ---

def save_configuration(name: str, account: str, profile: str, is_active: bool = False):
    """Saves or updates a Tealium profile configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO configurations (name, account, profile, is_active) VALUES (?, ?, ?, ?)",
        (name, account, profile, is_active)
    )
    conn.commit()
    conn.close()

def load_all_configurations() -> List[Dict[str, str]]:
    """Loads all saved Tealium configurations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, account, profile, is_active FROM configurations")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_active_configuration() -> Optional[Dict[str, str]]:
    """Gets the currently active Tealium configuration, including global settings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    global_settings = load_global_settings()

    cursor.execute("SELECT name, account, profile FROM configurations WHERE is_active = 1")
    active_config_row = cursor.fetchone()
    
    conn.close()

    if active_config_row:
        active_config = dict(active_config_row)
        active_config.update(global_settings)
        return active_config
    
    # Return just global settings if no profile is active
    return global_settings if global_settings else None

def set_active_configuration(name: str):
    """Sets a specific Tealium configuration as active."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE configurations SET is_active = 0")
    cursor.execute("UPDATE configurations SET is_active = 1 WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def delete_configuration(name: str):
    """Deletes a Tealium configuration and its associated caches."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM configurations WHERE name = ?", (name,))
    cursor.execute("DELETE FROM profile_cache WHERE config_name = ?", (name,))
    # Also potentially clear related items from the generic api_cache if needed, though not strictly enforced by schema
    conn.commit()
    conn.close()

# --- Adobe Analytics Configuration Management Functions ---

def save_adobe_configuration(config: Dict):
    """Saves or updates an Adobe Analytics configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Define all possible fields to ensure we handle missing ones gracefully
    fields = [
        'name', 'auth_method', 'global_company_id', 'api_key', 'client_secret',
        'technical_account_id', 'organization_id', 'private_key', 
        'manual_access_token', 'is_active'
    ]
    
    # Prepare data tuple, using None for missing keys
    data_tuple = tuple(config.get(field) for field in fields)
    
    # Using 'INSERT OR REPLACE' based on the primary key 'name'
    cursor.execute(
        f"""INSERT OR REPLACE INTO adobe_configurations ({', '.join(fields)}) 
            VALUES ({', '.join(['?'] * len(fields))})""",
        data_tuple
    )
    conn.commit()
    conn.close()

def load_all_adobe_configurations() -> List[Dict[str, str]]:
    """Loads all saved Adobe Analytics configurations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Exclude sensitive fields from the main list view
    cursor.execute("SELECT name, auth_method, global_company_id, api_key, technical_account_id, organization_id, is_active FROM adobe_configurations")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_active_adobe_configuration() -> Optional[Dict[str, str]]:
    """Gets the currently active Adobe Analytics configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adobe_configurations WHERE is_active = 1")
    active_config_row = cursor.fetchone()
    conn.close()
    return dict(active_config_row) if active_config_row else None

def set_active_adobe_configuration(name: str):
    """Sets a specific Adobe Analytics configuration as active."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE adobe_configurations SET is_active = 0")
    cursor.execute("UPDATE adobe_configurations SET is_active = 1 WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def delete_adobe_configuration(name: str):
    """Deletes an Adobe Analytics configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM adobe_configurations WHERE name = ?", (name,))
    conn.commit()
    conn.close()

# --- Caching Functions ---

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

def cache_profile_data(config_name: str, data: Dict):
    """Saves LATEST profile data to the specific profile cache."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO profile_cache (config_name, data, timestamp) VALUES (?, ?, ?)",
        (config_name, json.dumps(data), time.time())
    )
    conn.commit()
    conn.close()

def get_cached_profile(config_name: str) -> (Optional[Dict], Optional[float]):
    """
    Retrieves a cached LATEST profile and its timestamp by its configuration name.
    Returns (data, timestamp) or (None, None).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data, timestamp FROM profile_cache WHERE config_name = ?", (config_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row['data']), row['timestamp']
    return None, None

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
        conn.close()

        return {
            "status": "OK",
            "file_size_bytes": file_size_bytes,
            "last_modified": last_modified_datetime,
            "configurations_count": config_count,
            "adobe_configurations_count": adobe_config_count,
            "cached_items_count": profile_cache_count + api_cache_count
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

