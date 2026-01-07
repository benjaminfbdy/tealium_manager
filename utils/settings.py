import json
import os
from typing import List

SETTINGS_FILE = 'settings.json'

def load_settings() -> dict:
    """Loads the entire settings file."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_settings(settings: dict):
    """Saves the entire settings dictionary to the file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def load_inventory_columns(default_columns: List[str]) -> List[str]:
    """
    Loads the saved column preferences for the inventory view.
    Returns default columns if no settings are found.
    """
    settings = load_settings()
    return settings.get('inventory_columns', default_columns)

def save_inventory_columns(columns: List[str]):
    """Saves the column preferences for the inventory view."""
    settings = load_settings()
    settings['inventory_columns'] = columns
    save_settings(settings)
