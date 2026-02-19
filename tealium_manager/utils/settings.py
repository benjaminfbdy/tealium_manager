import json
import os
from typing import List

SETTINGS_FILE = "inventory_columns.json"

def save_inventory_columns(columns: List[str]):
    """Saves the list of selected inventory columns to a file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(columns, f)
    except IOError as e:
        print(f"Error saving column settings: {e}")

def load_inventory_columns(default_columns: List[str]) -> List[str]:
    """Loads the list of inventory columns from a file, or returns defaults."""
    if not os.path.exists(SETTINGS_FILE):
        return default_columns
    try:
        with open(SETTINGS_FILE, 'r') as f:
            columns = json.load(f)
            if isinstance(columns, list):
                return columns
            return default_columns
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading column settings, using defaults: {e}")
        return default_columns