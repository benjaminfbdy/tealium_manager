from utils.tealium_client import TealiumClient
from database import (
    save_configuration, load_all_configurations, get_active_configuration, 
    set_active_configuration, delete_configuration, get_db_status, reset_database
)
from typing import Dict, List, Optional

def get_all_configurations() -> List[Dict[str, str]]:
    """
    Loads all Tealium configurations from the database.
    """
    return load_all_configurations()

def get_active_configuration_details() -> Optional[Dict[str, str]]:
    """
    Loads the details of the active Tealium configuration.
    """
    return get_active_configuration()

def get_tealium_connection_status(credentials: Optional[Dict[str, str]] = None) -> bool:
    """
    Attempts to initialize TealiumClient and authenticate.
    If credentials are provided, uses them; otherwise, loads the active config from database/env.
    Returns True if authentication is successful, False otherwise.
    """
    try:
        if credentials:
            client = TealiumClient(
                account=credentials.get("account"),
                profile=credentials.get("profile"),
                api_key=credentials.get("api_key"),
                email=credentials.get("email")
            )
        else:
            # If no specific credentials provided, try to use the active one
            active_config = get_active_configuration()
            if active_config:
                client = TealiumClient(
                    account=active_config.get("account"),
                    profile=active_config.get("profile"),
                    api_key=active_config.get("api_key"),
                    email=active_config.get("email")
                )
            else:
                # If no active config, client init might fail (ValueError), caught below
                client = TealiumClient()
        
        client._authenticate_v2() # Attempt to authenticate
        if client.token:
            return True
        else:
            return False
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during Tealium connection attempt: {e}")
        return False

def handle_add_new_config(config_data: Dict[str, str]) -> bool:
    """
    Saves a new configuration to the database and tests the connection.
    Sets it as active if it's the first one, or if explicitly requested.
    Returns True if the connection is successful, False otherwise.
    """
    name = config_data.get("name")
    account = config_data.get("account")
    profile = config_data.get("profile")
    api_key = config_data.get("api_key")
    email = config_data.get("email")

    if not all([name, account, profile, api_key, email]):
        print("Error: All fields for new configuration must be provided.")
        return False
    
    # Save (or update if name exists)
    save_configuration(name, account, profile, api_key, email, is_active=False) # Initially not active
    
    # If this is the only config, make it active
    all_configs = load_all_configurations()
    if len(all_configs) == 1:
        set_active_configuration(name)

    return get_tealium_connection_status(config_data)

def handle_update_config(config_data: Dict[str, str]) -> bool:
    """
    Updates an existing configuration in the database and tests the connection.
    Returns True if the connection is successful, False otherwise.
    """
    name = config_data.get("name")
    account = config_data.get("account")
    profile = config_data.get("profile")
    api_key = config_data.get("api_key")
    email = config_data.get("email")
    is_active = config_data.get("is_active", False) # Preserve active status

    if not all([name, account, profile, api_key, email]):
        print("Error: All fields for configuration update must be provided.")
        return False
    
    save_configuration(name, account, profile, api_key, email, is_active) # is_active from UI
    return get_tealium_connection_status(config_data)

def handle_set_active_config(name: str) -> bool:
    """
    Sets a configuration as active and tests its connection.
    Returns True if the connection is successful, False otherwise.
    """
    set_active_configuration(name)
    # Load the newly active config's details to pass to get_tealium_connection_status
    active_config = get_active_configuration()
    if active_config and active_config["name"] == name:
        return get_tealium_connection_status(active_config)
    return False # Should not happen if set_active_configuration works

def handle_delete_config(name: str):
    """
    Deletes a configuration from the database.
    """
    delete_configuration(name)
    # If the deleted config was active, deactivate it and potentially set another as active if only one remains
    all_configs = load_all_configurations()
    if not all_configs:
        pass # No configs left
    elif not get_active_configuration(): # If deleted config was active and no other is active
        # Set the first remaining config as active
        set_active_configuration(all_configs[0]["name"])

def get_database_status() -> Dict:
    """
    Retrieves the status of the database.
    """
    return get_db_status()

def handle_database_reset() -> bool:
    """
    Handles the request to reset the database.
    """
    return reset_database()
