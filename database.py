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
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Table for API response caching
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            timestamp REAL NOT NULL,
            etag TEXT
        )
    """)
    # Table for storing Tealium configurations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configurations (
            name TEXT PRIMARY KEY,
            account TEXT NOT NULL,
            profile TEXT NOT NULL,
            api_key TEXT NOT NULL,
            email TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# --- Caching Functions ---

def get_cached_data(cache_key: str, ttl: int = 3600) -> Optional[Dict]:
    """
    Retrieves cached data if it exists and is not older than the TTL.
    """
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
    """
    Saves data to the cache.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO api_cache (cache_key, data, timestamp, etag) VALUES (?, ?, ?, ?)",
        (cache_key, json.dumps(data), time.time(), etag)
    )
    conn.commit()
    conn.close()

# --- Configuration Management Functions ---

def save_configuration(name: str, account: str, profile: str, api_key: str, email: str, is_active: bool = False):
    """Saves or updates a Tealium configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO configurations (name, account, profile, api_key, email, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (name, account, profile, api_key, email, is_active)
    )
    conn.commit()
    conn.close()

def load_all_configurations() -> List[Dict[str, str]]:
    """Loads all saved configurations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, account, profile, api_key, email, is_active FROM configurations")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_active_configuration() -> Optional[Dict[str, str]]:
    """Gets the currently active configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, account, profile, api_key, email FROM configurations WHERE is_active = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def set_active_configuration(name: str):
    """Sets a specific configuration as active."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # First, deactivate all others
    cursor.execute("UPDATE configurations SET is_active = 0")
    # Then, activate the chosen one
    cursor.execute("UPDATE configurations SET is_active = 1 WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def delete_configuration(name: str):
    """Deletes a configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM configurations WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def get_db_status() -> Dict:
    """
    Checks the status of the database file and its contents.
    """
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
        
        cursor.execute("SELECT COUNT(*) FROM api_cache")
        cache_count = cursor.fetchone()[0]
        
        conn.close()

        return {
            "status": "OK",
            "file_size_bytes": file_size_bytes,
            "last_modified": last_modified_datetime,
            "configurations_count": config_count,
            "cached_items_count": cache_count
        }
    except Exception as e:
        return {"status": "Error", "message": str(e)}

def reset_database():
    """
    Deletes the current database file and re-initializes an empty one.
    """
    # This function is destructive. Be sure to have user confirmation in the UI.
    try:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        
        # Recreate the database from scratch
        initialize_database()
        return True
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False

# Initialize the database on startup
initialize_database()
