from utils.tealium_client import TealiumClient
from utils.adobe_client import AdobeAnalyticsClient
from database import (
    save_configuration, load_all_configurations, get_active_configuration, 
    set_active_configuration, delete_configuration,
    save_adobe_configuration, load_all_adobe_configurations, get_active_adobe_configuration,
    set_active_adobe_configuration, delete_adobe_configuration,
    get_db_status, reset_database,
    save_global_settings, load_global_settings, cache_profile_data
)
from typing import Dict, List, Optional

# --- Helper Functions ---

def _create_proxies_dict(settings: Dict) -> Optional[Dict]:
    """Helper to create a proxy dictionary if credentials are provided."""
    proxy_user = settings.get("proxy_user")
    proxy_password = settings.get("proxy_password")
    if proxy_user and proxy_password:
        proxy_host = "proxy-users.intranet.bpce-it.fr"
        proxy_port = "8080"
        proxy_url_base = f"{proxy_host}:{proxy_port}"
        proxy_auth_url = f"http://{proxy_user}:{proxy_password}@{proxy_url_base}"
        return {"http": proxy_auth_url, "https": proxy_auth_url}
    return None

# --- Global Settings ---

def get_global_settings() -> Dict[str, str]:
    """Loads the global settings (API key, email, proxy)."""
    return load_global_settings()

def handle_save_global_settings(settings: Dict[str, str]):
    """Saves the global settings (API key, email, proxy)."""
    save_global_settings(
        settings.get("api_key", ""), 
        settings.get("email", ""),
        settings.get("proxy_user", ""),
        settings.get("proxy_password", "")
    )

# --- Tealium Configuration ---

def get_all_configurations() -> List[Dict[str, str]]:
    """Loads all Tealium profile configurations from the database."""
    return load_all_configurations()

def get_active_configuration_details() -> Optional[Dict[str, str]]:
    """Loads the details of the active Tealium configuration, including global settings."""
    return get_active_configuration()

def get_tealium_connection_status() -> bool:
    """
    Attempts to initialize TealiumClient with the active config and authenticate.
    Returns True if authentication is successful, False otherwise.
    """
    active_config = get_active_configuration()
    if not active_config or not all(active_config.get(k) for k in ["account", "profile", "api_key", "email"]):
        return False
        
    try:
        proxies = _create_proxies_dict(active_config)
        client = TealiumClient(
            account=active_config.get("account"),
            profile=active_config.get("profile"),
            api_key=active_config.get("api_key"),
            email=active_config.get("email"),
            proxies=proxies
        )
        client._authenticate_v2()
        return bool(client.token_v2)
    except Exception as e:
        print(f"An error occurred during Tealium connection attempt: {e}")
        return False

def handle_add_new_config(config_data: Dict[str, str]) -> bool:
    """Saves a new Tealium profile configuration."""
    name = config_data.get("name")
    account = config_data.get("account")
    profile = config_data.get("profile")

    if not all([name, account, profile]):
        print("Error: All fields for new Tealium configuration must be provided.")
        return False
    
    save_configuration(name, account, profile, is_active=False)
    
    all_configs = load_all_configurations()
    if len(all_configs) == 1:
        set_active_configuration(name)
    return True

def handle_update_config(config_data: Dict[str, str]) -> bool:
    """Updates an existing Tealium profile configuration."""
    # This function is not fully utilized in the current UI but is kept for future use.
    name = config_data.get("name")
    account = config_data.get("account")
    profile = config_data.get("profile")

    if not all([name, account, profile]):
        return False
    
    existing_configs = load_all_configurations()
    is_active = next((cfg.get("is_active", False) for cfg in existing_configs if cfg["name"] == name), False)
    
    save_configuration(name, account, profile, is_active)
    return True

def handle_set_active_config(name: str) -> bool:
    """Sets a Tealium configuration as active and tests its connection."""
    set_active_configuration(name)
    return get_tealium_connection_status()

def handle_delete_config(name: str):
    """Deletes a Tealium configuration from the database."""
    was_active = False
    active_config = get_active_configuration_details()
    if active_config and active_config.get("name") == name:
        was_active = True

    delete_configuration(name)
    
    if was_active:
        all_configs = load_all_configurations()
        if all_configs:
            set_active_configuration(all_configs[0]["name"])

# --- Adobe Analytics Configuration ---

def get_all_adobe_configurations() -> List[Dict[str, str]]:
    """Loads all Adobe Analytics configurations from the database."""
    return load_all_adobe_configurations()

def get_active_adobe_configuration_details() -> Optional[Dict[str, str]]:
    """Loads the details of the active Adobe Analytics configuration."""
    return get_active_adobe_configuration()

def get_adobe_connection_status() -> bool:
    """
    Attempts to initialize AdobeAnalyticsClient and get a token.
    Returns True if successful, False otherwise.
    """
    active_config = get_active_adobe_configuration()
    if not active_config:
        return False
    try:
        client = AdobeAnalyticsClient(active_config)
        client._ensure_token()
        return bool(client.access_token)
    except Exception as e:
        print(f"An error occurred during Adobe connection attempt: {e}")
        return False

def handle_add_new_adobe_config(config_data: Dict[str, str]) -> bool:
    """Saves a new Adobe Analytics configuration after validating based on auth method."""
    auth_method = config_data.get("auth_method")
    
    # Basic validation for common fields
    if not all(config_data.get(k) for k in ["name", "api_key", "global_company_id"]):
        print("Error: Name, API Key, and Global Company ID are always required.")
        return False
        
    # Method-specific validation
    if auth_method == 'jwt':
        required_keys = ["client_secret", "technical_account_id", "organization_id", "private_key"]
        if not all(config_data.get(k) for k in required_keys):
            print("Error: For JWT auth, all secret and ID fields are required.")
            return False
    elif auth_method == 'manual':
        if not config_data.get("manual_access_token"):
            print("Error: For Manual Token auth, the Access Token is required.")
            return False
    else:
        print(f"Error: Unknown auth method '{auth_method}'.")
        return False

    # The save function is designed to handle the flexible dict
    save_adobe_configuration(config_data)
    
    all_configs = load_all_adobe_configurations()
    if len(all_configs) == 1:
        set_active_adobe_configuration(config_data["name"])
    return True

def handle_set_active_adobe_config(name: str) -> bool:
    """Sets an Adobe configuration as active and tests its connection."""
    set_active_adobe_configuration(name)
    return get_adobe_connection_status()

def handle_delete_adobe_config(name: str):
    """Deletes an Adobe configuration from the database."""
    was_active = False
    active_config = get_active_adobe_configuration_details()
    if active_config and active_config.get("name") == name:
        was_active = True

    delete_adobe_configuration(name)

    if was_active:
        all_configs = load_all_adobe_configurations()
        if all_configs:
            set_active_adobe_configuration(all_configs[0]["name"])


# --- Other Controller Functions ---

def handle_download_profile(config_name: str) -> bool:
    """Fetches the latest profile data and caches it."""
    settings = get_global_settings()
    configs = load_all_configurations()
    target_config = next((cfg for cfg in configs if cfg["name"] == config_name), None)

    if not target_config or not settings.get("api_key"):
        print(f"Error: Cannot download profile for '{config_name}'. Missing config or global credentials.")
        return False
        
    try:
        proxies = _create_proxies_dict(settings)
        client = TealiumClient(
            account=target_config["account"],
            profile=target_config["profile"],
            api_key=settings["api_key"],
            email=settings["email"],
            proxies=proxies
        )
        component_types_to_fetch = ["tags", "extensions", "loadRules", "variables"]
        profile_data_response = client.get_profile_components(component_types=component_types_to_fetch)
        
        if profile_data_response.get("error"):
            print(f"Error downloading profile for '{config_name}': {profile_data_response.get('message')}")
            return False

        profile_data = profile_data_response.get("data")
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

