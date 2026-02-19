import json
import time
import pandas as pd
from typing import Dict, List, Optional
from database import get_db_connection

# --- Adobe Components Caching ---

def save_adobe_components(rsid: str, components: Dict):
    """Saves or updates the components for a given RSID in the cache."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO adobe_components (rsid, dimensions, metrics, segments, last_updated)
           VALUES (?, ?, ?, ?, ?)""",
        (
            rsid,
            json.dumps(components.get('dimensions', [])),
            json.dumps(components.get('metrics', [])),
            json.dumps(components.get('segments', [])),
            time.time()
        )
    )
    conn.commit()
    conn.close()

def load_adobe_components(rsid: str) -> Optional[Dict]:
    """Loads cached components for a given RSID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dimensions, metrics, segments, last_updated FROM adobe_components WHERE rsid = ?", (rsid,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "dimensions": json.loads(row["dimensions"]),
            "metrics": json.loads(row["metrics"]),
            "segments": json.loads(row["segments"]),
            "last_updated": row["last_updated"]
        }
    return None

def get_adobe_components_cache_info() -> List[Dict]:
    """Retrieves a list of all cached RSIDs and their last update timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rsid, last_updated FROM adobe_components")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Saved Reports Management ---

def save_report_configuration(name: str, adobe_config_name: str, rsid: str, definition: Dict):
    """Saves a report configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO saved_reports (name, adobe_config_name, rsid, definition, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, adobe_config_name, rsid, json.dumps(definition), time.time())
    )
    conn.commit()
    conn.close()

def load_saved_reports() -> List[Dict]:
    """Loads all saved reports."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM saved_reports ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_saved_report(report_id: int, name: str, adobe_config_name: str, rsid: str, definition: Dict):
    """Updates an existing report configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE saved_reports SET name = ?, adobe_config_name = ?, rsid = ?, definition = ? WHERE id = ?",
        (name, adobe_config_name, rsid, json.dumps(definition), report_id)
    )
    conn.commit()
    conn.close()

def delete_saved_report(report_id: int):
    """Deletes a saved report by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM saved_reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()

# --- Report Results Caching ---

def save_report_result(report_id: int, date_range_key: str, df: pd.DataFrame, status: str):
    """Saves a report's DataFrame result to the cache."""
    conn = get_db_connection()
    cursor = conn.cursor()
    df_json = df.to_json(orient='split', date_format='iso')
    cursor.execute(
        """INSERT OR REPLACE INTO report_results_cache 
           (report_id, date_range_key, result_data, timestamp, status) 
           VALUES (?, ?, ?, ?, ?)""",
        (report_id, date_range_key, df_json, time.time(), status)
    )
    conn.commit()
    conn.close()

def load_report_result(report_id: int, date_range_key: str, ttl: int = 86400) -> (Optional[pd.DataFrame], Optional[str]):
    """Loads a cached report result if it's not older than TTL (default 24h)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT result_data, timestamp, status FROM report_results_cache WHERE report_id = ? AND date_range_key = ?",
        (report_id, date_range_key)
    )
    row = cursor.fetchone()
    conn.close()
    if row and (time.time() - row['timestamp'] < ttl):
        df = pd.read_json(row['result_data'], orient='split')
        return df, row['status']
    return None, None

def get_all_cached_report_results() -> List[Dict]:
    """Retrieves metadata for all cached report results."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.report_id, c.date_range_key, c.timestamp, c.status, r.name as report_name, r.rsid
        FROM report_results_cache c
        LEFT JOIN saved_reports r ON c.report_id = r.id
        ORDER BY c.timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_cached_result_by_id(cache_id: int) -> Optional[Dict]:
    """Retrieves a specific cached result by its primary key ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT result_data, status FROM report_results_cache WHERE id = ?", (cache_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_cached_result(cache_id: int):
    """Deletes a specific cache entry."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM report_results_cache WHERE id = ?", (cache_id,))
    conn.commit()
    conn.close()