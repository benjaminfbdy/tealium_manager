from utils.tealium_client import TealiumClient
from database import (
    save_configuration, load_all_configurations, get_active_configuration, 
    set_active_configuration, delete_configuration, get_db_status, reset_database,
    save_global_credentials, load_global_credentials, cache_profile_data
)
from typing import Dict, List, Optional

def get_all_configurations() -> List[Dict[str, str]]:
    """Loads all Tealium profile configurations from the database."""
    return load_all_configurations()

def get_global_credentials() -> Dict[str, str]:
    """Loads the global API key and email."""
    return load_global_credentials()

def get_active_configuration_details() -> Optional[Dict[str, str]]:
    """Loads the details of the active Tealium configuration, including global credentials."""
    return get_active_configuration()

def get_tealium_connection_status() -> bool:
    """
    Attempts to initialize TealiumClient with the active config and authenticate.
    Returns True if authentication is successful, False otherwise.
    """
    try:
        active_config = get_active_configuration()
        if not active_config or not active_config.get("api_key"):
            return False
            
        client = TealiumClient(
            account=active_config.get("account"),
            profile=active_config.get("profile"),
            api_key=active_config.get("api_key"),
            email=active_config.get("email")
        )
        client._authenticate_v2()
        return bool(client.token_v2)
    except (ValueError, Exception) as e:
        print(f"An error occurred during Tealium connection attempt: {e}")
        return False

def handle_save_global_credentials(creds: Dict[str, str]):
    """Saves the global API key and email."""
    save_global_credentials(creds.get("api_key", ""), creds.get("email", ""))

def handle_add_new_config(config_data: Dict[str, str]) -> bool:
    """Saves a new profile configuration."""
    name = config_data.get("name")
    account = config_data.get("account")
    profile = config_data.get("profile")

    if not all([name, account, profile]):
        print("Error: All fields for new configuration must be provided.")
        return False
    
    save_configuration(name, account, profile, is_active=False)
    
    all_configs = load_all_configurations()
    if len(all_configs) == 1:
        set_active_configuration(name)
    return True

def handle_update_config(config_data: Dict[str, str]) -> bool:
    """Updates an existing profile configuration."""
    name = config_data.get("name")
    account = config_data.get("account")
    profile = config_data.get("profile")

    if not all([name, account, profile]):
        return False
    
    # We need the current active status to preserve it, which is not passed directly
    # Re-loading the config to check its status before saving.
    existing_configs = load_all_configurations()
    is_active = next((cfg.get("is_active", False) for cfg in existing_configs if cfg["name"] == name), False)
    
    save_configuration(name, account, profile, is_active)
    return True

def handle_set_active_config(name: str) -> bool:
    """Sets a configuration as active and tests its connection."""
    set_active_configuration(name)
    return get_tealium_connection_status()

def handle_delete_config(name: str):
    """Deletes a configuration from the database."""
    was_active = False
    active_config = get_active_configuration_details()
    if active_config and active_config.get("name") == name:
        was_active = True

    delete_configuration(name)
    
    if was_active:
        all_configs = load_all_configurations()
        if all_configs:
            set_active_configuration(all_configs[0]["name"])

def handle_download_profile(config_name: str) -> bool:
    """Fetches the latest profile data and caches it."""
    creds = load_global_credentials()
    configs = load_all_configurations()
    target_config = next((cfg for cfg in configs if cfg["name"] == config_name), None)

    if not target_config or not creds.get("api_key"):
        print(f"Error: Cannot download profile for '{config_name}'. Missing config or global credentials.")
        return False
        
    try:
        client = TealiumClient(
            account=target_config["account"],
            profile=target_config["profile"],
            api_key=creds["api_key"],
            email=creds["email"]
        )
        profile_data_response = client.get_profile_components()
        
        if profile_data_response.get("error"):
            print(f"Error downloading profile for '{config_name}': {profile_data_response.get('message')}")
            return False

        profile_data = profile_data_response.get("data")
        # Check if the data is present and not empty
        if profile_data:
            cache_profile_data(config_name, profile_data)
            print(f"Successfully downloaded and cached profile for '{config_name}'.")
            return True
        else:
            print(f"Error: Download for '{config_name}' resulted in empty data.")
            return False
            
    except Exception as e:
        print(f"An unexpected error occurred during profile download for '{config_name}': {e}")
        return False

def get_database_status() -> Dict:
    """Retrieves the status of the database."""
    return get_db_status()

def handle_database_reset() -> bool:
    """Handles the request to reset the database."""
    return reset_database()
