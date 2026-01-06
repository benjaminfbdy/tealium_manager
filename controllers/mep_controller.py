from utils.tealium_client import TealiumClient
from database import get_active_configuration, get_cached_data, set_cached_data
from utils.data_processing import build_uid_to_name_map, diff_revisions
from typing import List, Dict, Any, Optional
import streamlit as st

def get_meps_data() -> Optional[List[Dict]]:
    """
    Fetches the revision history for the active Tealium iQ profile, using a cache,
    and filters them to only include revisions published to 'prod'.
    """
    active_config = get_active_configuration()
    if not active_config:
        st.error("Error: No active configuration found.")
        return None

    account = active_config.get("account")
    profile = active_config.get("profile")
    cache_key_prefix = f"profile_{account}_{profile}"
    
    try:
        client = TealiumClient(
            account=account,
            profile=profile,
            api_key=active_config.get("api_key"),
            email=active_config.get("email")
        )
    except ValueError as e:
        st.error(f"Error initializing TealiumClient: {e}")
        return None

    # Step 1: Get revision IDs
    revision_ids_cache_key = f"{cache_key_prefix}_revision_ids"
    revision_ids = get_cached_data(revision_ids_cache_key, ttl=300)
    if not revision_ids:
        st.info("Fetching fresh revision list from API...")
        revision_ids = client.get_revision_ids()
        if revision_ids:
            set_cached_data(revision_ids_cache_key, revision_ids)
        else:
            st.warning("No revision IDs found for the active profile.")
            return None

    # Step 2: Get details for each revision
    st.info(f"Loading details for {len(revision_ids)} revisions...")
    progress_bar = st.progress(0, text="Loading revision details...")
    
    all_revisions_details = []
    for i, rev_id in enumerate(revision_ids):
        revision_detail_cache_key = f"{cache_key_prefix}_revision_{rev_id}"
        details = get_cached_data(revision_detail_cache_key)
        if not details:
            details = client.get_revision_details(rev_id)
            if details:
                set_cached_data(revision_detail_cache_key, details)
        if details:
            all_revisions_details.append(details)
        progress_bar.progress((i + 1) / len(revision_ids), text=f"Loaded revision {rev_id}")
    progress_bar.empty()

    # Step 3: Filter for revisions published to 'prod'
    st.info("Filtering for revisions published to production...")
    prod_revisions = []
    for revision in all_revisions_details:
        publish_history = revision.get("publish_history", [])
        is_in_prod = any(env.get("environment") == "prod" for env in publish_history)
        if is_in_prod:
            prod_revisions.append(revision)
            
    st.success(f"Found {len(prod_revisions)} revisions published to prod.")
    
    # Sort by date descending
    prod_revisions.sort(key=lambda r: r.get('date'), reverse=True)
    
    return prod_revisions

def get_mep_comparison_data(rev_id_1: str, rev_id_2: str) -> Dict[str, Any]:
    """
    Fetches details for two specific revisions, builds a combined UID map,
    calculates the diff, and returns a data package for the comparison view.
    """
    active_config = get_active_configuration()
    if not active_config:
        return {"error": "No active configuration found."}
        
    account = active_config.get("account")
    profile = active_config.get("profile")
    cache_key_prefix = f"profile_{account}_{profile}"

    # Helper to get a single revision's details
    def get_single_revision(rev_id):
        cache_key = f"{cache_key_prefix}_revision_{rev_id}"
        cached = get_cached_data(cache_key)
        if cached:
            return cached
        
        try:
            client = TealiumClient(
                account=account, profile=profile, 
                api_key=active_config.get("api_key"), email=active_config.get("email")
            )
            details = client.get_revision_details(rev_id)
            if details:
                set_cached_data(cache_key, details)
            return details
        except ValueError as e:
            return {"error": f"Error initializing TealiumClient: {e}"}
    
    st.info(f"Chargement des détails pour les MEPs {rev_id_1} et {rev_id_2}...")
    details1 = get_single_revision(rev_id_1)
    details2 = get_single_revision(rev_id_2)

    if not details1 or details1.get("error") or not details2 or details2.get("error"):
        return {"error": "Impossible de charger les détails pour l'une ou les deux MEPs."}

    # Build a combined UID map to resolve all possible UIDs
    st.info("Construction de la carte de résolution des UIDs...")
    combined_data_for_map = {}
    for key in ["variables", "tags", "loadRules", "extensions", "events"]:
        combined_data_for_map[key] = details1.get(key, []) + details2.get(key, [])
    uid_map = build_uid_to_name_map(combined_data_for_map)

    # Calculate the diff
    st.info("Calcul des différences...")
    diff = diff_revisions(details1, details2)
    
    return {
        "error": False,
        "data": {
            "rev1_id": rev_id_1,
            "rev2_id": rev_id_2,
            "diff": diff,
            "uid_map": uid_map
        }
    }

