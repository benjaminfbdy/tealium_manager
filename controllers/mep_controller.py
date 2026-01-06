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
        targets_published = revision.get("targets_published", [])
        if "prod" in targets_published:
            prod_revisions.append(revision)
            
    st.success(f"Found {len(prod_revisions)} revisions published to prod.")
    
    # Sort by date descending
    prod_revisions.sort(key=lambda r: r.get('date', ''), reverse=True)
    
    return prod_revisions

def get_mep_comparison_data(rev_id_1: str, rev_id_2: str) -> Dict[str, Any]:

    """

    Fetches details for two specific revisions using the V3 API, builds a combined UID map,

    calculates the diff, and returns a data package for the comparison view.

    """

    active_config = get_active_configuration()

    if not active_config:

        return {"error": "No active configuration found."}

        

    account = active_config.get("account")

    profile = active_config.get("profile")

    cache_key_prefix = f"profile_full_{account}_{profile}"

    

    component_types_to_fetch = ["variables", "tags", "loadRules", "extensions", "events"]



    # Helper to get a single revision's full components

    def get_single_revision_components(rev_id):

        cache_key = f"{cache_key_prefix}_revision_{rev_id}"

        cached = get_cached_data(cache_key)

        if cached and not cached.get("error"):

            st.info(f"MEP {rev_id} chargée depuis le cache.")

            return cached.get("data")

        

        try:

            client = TealiumClient(

                account=account, profile=profile, 

                api_key=active_config.get("api_key"), email=active_config.get("email")

            )

            # Use the V3 get_profile_components method

            response = client.get_profile_components(

                publish_version=rev_id, 

                component_types=component_types_to_fetch

            )

            if not response.get("error"):

                set_cached_data(cache_key, response)

                return response.get("data")

            else:

                st.error(f"API Error for revision {rev_id}: {response.get('message')}")

                return None

        except ValueError as e:

            st.error(f"Error initializing TealiumClient: {e}")

            return None

    

    st.info(f"Chargement des composants pour la MEP {rev_id_1}...")

    details1 = get_single_revision_components(rev_id_1)

    

    st.info(f"Chargement des composants pour la MEP {rev_id_2}...")

    details2 = get_single_revision_components(rev_id_2)



    if not details1 or not details2:

        st.error("Impossible de charger les composants pour l'une ou les deux MEPs.")

        return {"error": "Impossible de charger les composants pour l'une ou les deux MEPs."}



    # Build a combined UID map to resolve all possible UIDs

    st.info("Construction de la carte de résolution des UIDs...")

    combined_data_for_map = {}

    for key in component_types_to_fetch:

        list1 = details1.get(key, [])

        list2 = details2.get(key, [])

        combined_data_for_map[key] = list1 + list2

    uid_map = build_uid_to_name_map(combined_data_for_map)



    # Calculate the diff

    st.info("Calcul des différences...")

    diff = diff_revisions(details1, details2)

    

    # Remove the verbose debug logging from the diff function

    # (Assuming it's still there, this is a good place to note it)

    

    return {

        "error": False,

        "data": {

            "rev1_id": rev_id_1,

            "rev2_id": rev_id_2,

            "diff": diff,

            "uid_map": uid_map

        }

    }

