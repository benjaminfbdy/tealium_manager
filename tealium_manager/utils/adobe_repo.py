import json
import time
import pandas as pd
from typing import Dict, List, Optional
from database import get_db_connection, load_global_settings

# --- Adobe Analytics Configuration Management ---

def save_adobe_configuration(config: Dict):
    """Saves or updates an Adobe Analytics configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    fields = [
        'name', 'auth_method', 'global_company_id', 'api_key', 'client_secret',
        'technical_account_id', 'organization_id', 'private_key', 
        'manual_access_token', 'is_active'
    ]
    
    data_values = []
    for field in fields:
        value = config.get(field)
        if value is None and field in ['technical_account_id', 'organization_id', 'private_key']:
            data_values.append('')
        else:
            data_values.append(value)
    data_tuple = tuple(data_values)

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
    cursor.execute("SELECT name, auth_method, global_company_id, api_key, technical_account_id, organization_id, is_active FROM adobe_configurations")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_active_adobe_configuration() -> Optional[Dict[str, str]]:
    """Gets the currently active Adobe Analytics configuration, including global proxy settings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    global_settings = load_global_settings()

    cursor.execute("SELECT * FROM adobe_configurations WHERE is_active = 1")
    active_config_row = cursor.fetchone()
    
    conn.close()

    if active_config_row:
        active_config = dict(active_config_row)
        merged_config = global_settings.copy()
        merged_config.update(active_config)
        return merged_config
    
    return None

def load_adobe_configuration_by_name(name: str) -> Optional[Dict[str, str]]:
    """Gets a single, full Adobe Analytics configuration by its unique name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adobe_configurations WHERE name = ?", (name,))
    config_row = cursor.fetchone()
    conn.close()
    return dict(config_row) if config_row else None

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

def rename_adobe_configuration(old_name: str, new_name: str) -> bool:
    """
    Renames an Adobe configuration.
    Since 'name' is the PRIMARY KEY, this involves creating a new record,
    linking dependent rows (saved_reports) to it, and deleting the old one.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        
        # 1. Check if new name already exists
        cursor.execute("SELECT 1 FROM adobe_configurations WHERE name = ?", (new_name,))
        if cursor.fetchone():
            raise ValueError(f"Une configuration nommée '{new_name}' existe déjà.")

        # 2. Copy old config to new config
        cursor.execute("SELECT * FROM adobe_configurations WHERE name = ?", (old_name,))
        old_row = cursor.fetchone()
        if not old_row:
            raise ValueError(f"Configuration '{old_name}' introuvable.")
        
        keys = old_row.keys()
        values = [new_name if k == 'name' else old_row[k] for k in keys]
        placeholders = ', '.join(['?'] * len(keys))
        col_names = ', '.join(keys)
        
        cursor.execute(f"INSERT INTO adobe_configurations ({col_names}) VALUES ({placeholders})", values)
        
        # 3. Update dependent tables (saved_reports)
        cursor.execute("UPDATE saved_reports SET adobe_config_name = ? WHERE adobe_config_name = ?", (new_name, old_name))
        
        # 4. Delete old config
        cursor.execute("DELETE FROM adobe_configurations WHERE name = ?", (old_name,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error renaming adobe config: {e}")
        raise e
    finally:
        conn.close()

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