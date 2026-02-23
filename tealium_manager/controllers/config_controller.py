import streamlit as st
from typing import Dict, Optional
from urllib.parse import quote

# Import clients and repo functions that are still needed (for caching, etc.)
from utils.tealium_client import TealiumClient
from utils.adobe_client import AdobeClient
from utils.tealium_repo import cache_profile_data
from database import get_db_status, reset_database

# --- Helper Functions ---

def _create_proxies_dict() -> Optional[Dict]:
    """Helper to create a proxy dictionary if credentials are provided in secrets."""
    try:
        # Check if proxy section exists and is not empty
        if 'proxy' in st.secrets and st.secrets.proxy:
            proxy_config = st.secrets.proxy.to_dict()
            proxy_user = proxy_config.get("user")
            proxy_password = proxy_config.get("password")
            if proxy_user and proxy_password:
                proxy_host = proxy_config.get("host", "your.proxy.host.com")
                proxy_port = proxy_config.get("port", "8080")
                encoded_user = quote(proxy_user)
                encoded_password = quote(proxy_password)
                proxy_auth_url = f"http://{encoded_user}:{encoded_password}@{proxy_host}:{proxy_port}"
                return {"http": proxy_auth_url, "https": proxy_auth_url}
    except AttributeError:
        # This can happen if st.secrets.proxy is not a table.
        return None
    return None

def _get_adobe_client(config: Dict) -> Optional[AdobeClient]:
    """Initializes and returns an AdobeClient from a config dictionary."""
    if not config:
        return None
    try:
        # Add proxy settings to the Adobe client config if they exist
        proxies = _create_proxies_dict()
        if proxies:
            config['proxies'] = proxies
        return AdobeClient(config)
    except Exception as e:
        print(f"Error instantiating AdobeClient: {e}")
        return None

# --- Tealium Actions ---

def get_tealium_connection_status(config: Dict) -> bool:
    """Attempts to initialize TealiumClient with a given config and authenticate."""
    if not config or not all(config.get(k) for k in ["account", "profile", "tealium_api_username", "tealium_api_key"]):
        return False
    try:
        proxies = _create_proxies_dict()
        client = TealiumClient(
            account=config.get("account"),
            profile=config.get("profile"),
            api_key=config.get("tealium_api_key"),
            email=config.get("tealium_api_username"),
            proxies=proxies
        )
        client._authenticate_v2()
        return bool(client.token_v2)
    except Exception as e:
        print(f"An error occurred during Tealium connection attempt: {e}")
        return False

def handle_download_profile(profile_name: str, config: Dict) -> bool:
    """Fetches the latest profile data and caches it, using the profile name as the key."""
    if not config or not all(config.get(k) for k in ["account", "profile", "tealium_api_username", "tealium_api_key"]):
        print(f"Error: Cannot download profile for '{profile_name}'. Missing config data.")
        return False
        
    try:
        proxies = _create_proxies_dict()
        client = TealiumClient(
            account=config["account"],
            profile=config["profile"],
            api_key=config["tealium_api_key"],
            email=config["tealium_api_username"],
            proxies=proxies
        )
        component_types_to_fetch = ["tags", "extensions", "loadRules", "variables"]
        profile_data_response = client.get_profile_components(component_types=component_types_to_fetch)
        
        if profile_data_response.get("error"):
            print(f"Error downloading profile '{profile_name}': {profile_data_response.get('message')}")
            return False

        profile_data = profile_data_response.get("data")
        if profile_data:
            cache_profile_data(profile_name, profile_data) # Use the secrets-defined name as the unique key
            print(f"Successfully downloaded and cached profile for '{profile_name}'.")
            return True
        else:
            print(f"Error: Download for '{profile_name}' resulted in empty data.")
            return False
            
    except Exception as e:
        print(f"An unexpected error during profile download for '{profile_name}': {e}")
        return False

# --- Adobe Actions ---

def get_adobe_connection_status(config: Dict) -> bool:
    """Initializes AdobeClient with a given config and gets a token."""
    client = _get_adobe_client(config)
    if not client:
        return False
    try:
        client._ensure_token()
        return bool(client.access_token)
    except Exception as e:
        print(f"An error occurred during Adobe connection attempt: {e}")
        return False

def test_adobe_discovery(config: Dict) -> Dict:
    """Calls the Adobe discovery/me endpoint for a given config."""
    client = _get_adobe_client(config)
    if not client:
        return {"error": "Impossible d'initialiser le client Adobe avec la configuration fournie."}
    try:
        discovery_info = client.discover_me()
        return discovery_info
    except Exception as e:
        print(f"Error during Adobe discovery test: {e}")
        return {"error": str(e)}

# --- DB Status and Maintenance ---

def get_database_status() -> Dict:
    """Retrieves the status of the database."""
    return get_db_status()

def handle_database_reset() -> bool:
    """Handles the request to reset the database."""
    return reset_database()

