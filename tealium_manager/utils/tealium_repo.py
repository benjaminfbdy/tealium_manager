import json
import time
from typing import Dict, Optional
from database import get_db_connection

# --- Profile Caching ---

def cache_profile_data(profile_name: str, data: Dict):
    """Saves LATEST profile data to the specific profile cache, using the profile name as key."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO profile_cache (config_name, data, timestamp) VALUES (?, ?, ?)",
        (profile_name, json.dumps(data), time.time())
    )
    conn.commit()
    conn.close()

def get_cached_profile(profile_name: str) -> (Optional[Dict], Optional[float]):
    """Retrieves a cached LATEST profile and its timestamp by its name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data, timestamp FROM profile_cache WHERE config_name = ?", (profile_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row['data']), row['timestamp']
    return None, None