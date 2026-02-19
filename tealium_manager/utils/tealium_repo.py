import json
import time
from typing import Dict, List, Optional
from database import get_db_connection, load_global_settings

# --- Tealium Configuration Management ---

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
    conn.commit()
    conn.close()

# --- Profile Caching ---

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
    """Retrieves a cached LATEST profile and its timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data, timestamp FROM profile_cache WHERE config_name = ?", (config_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row['data']), row['timestamp']
    return None, None