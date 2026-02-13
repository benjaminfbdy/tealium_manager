from utils.tealium_client import TealiumClient
from database import get_active_configuration, get_cached_data, set_cached_data
from utils.data_processing import build_uid_to_name_map
from typing import Dict, List, Optional
import streamlit as st

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

def get_profile_data(version_id: Optional[str] = None) -> Dict:
    """
    Fetches a specific version of profile data and builds a UID map, using a cache.
    If version_id is None, fetches the latest version.
    Returns a dict containing the data (profile + map) or an error.
    """
    active_config = get_active_configuration()
    if not active_config:
        return {"error": True, "message": "Aucune configuration active n'a été trouvée."}

    account = active_config.get("account")
    profile = active_config.get("profile")
    
    # Make cache key version-specific
    cache_key_suffix = version_id if version_id else "latest"
    cache_key = f"profile_{account}_{profile}_{cache_key_suffix}"
    
    # 1. Try to get data from cache
    cached_data = get_cached_data(cache_key)
    if cached_data:
        st.info(f"Données de la version '{cache_key_suffix}' chargées depuis le cache. ⚡️")
        uid_map = build_uid_to_name_map(cached_data)
        return {"error": False, "data": {"profile": cached_data, "uid_map": uid_map}}

    # 2. If cache miss, fetch from API
    st.info(f"Récupération des données de la version '{cache_key_suffix}' depuis l'API...")
    progress_bar = st.progress(0, text="Initialisation de la connexion...")

    try:
        proxies = _create_proxies_dict(active_config)
        client = TealiumClient(
            account=account,
            profile=profile,
            api_key=active_config.get("api_key"),
            email=active_config.get("email"),
            proxies=proxies
        )
    except ValueError as e:
        progress_bar.empty()
        return {"error": True, "message": f"Erreur lors de l'initialisation du client Tealium : {e}"}

    component_types = ["loadRules", "tags", "extensions", "variables", "events", "versionIds"]
    progress_bar.progress(30, text=f"Appel API pour la version '{cache_key_suffix}'...")
    
    # Pass the version_id to the client
    response_dict = client.get_profile_components(
        component_types=component_types,
        publish_version=version_id
    )
    
    progress_bar.progress(90, text="Données reçues, traitement en cours...")

    # 3. Check for errors
    if response_dict.get('error'):
        progress_bar.empty()
        return response_dict 
    
    # 4. If success, process and cache
    profile_data = response_dict.get('data')
    if profile_data:
        profile_data["account"] = account
        profile_data["profile"] = profile
        set_cached_data(cache_key, profile_data)
        
        uid_map = build_uid_to_name_map(profile_data)
        
        progress_bar.progress(100, text="Terminé !")
        progress_bar.empty()
        
        return {"error": False, "data": {"profile": profile_data, "uid_map": uid_map}}
    else:
        progress_bar.empty()
        return {"error": True, "message": "L'API a retourné une réponse vide sans erreur explicite."}
