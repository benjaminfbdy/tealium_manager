import streamlit as st
from utils.tealium_client import TealiumClient
from utils.comparison_logic import compare_profiles
from controllers.config_controller import get_all_configurations
from database import load_global_settings

def process_comparison(profile_name):
    """
    Processes the comparison between the latest and live versions of a single profile.
    """
    all_configs = get_all_configurations()
    
    profile_config = next((config for config in all_configs if config['name'] == profile_name), None)

    if not profile_config:
        st.error(f"Could not find the selected profile: {profile_name}")
        return None

    global_settings = load_global_settings()
    api_key = global_settings.get("api_key")
    email = global_settings.get("email")
    proxies = global_settings.get("proxies")

    if not api_key or not email:
        st.error("API credentials are not set. Please configure them in the settings.")
        return None

    try:
        client = TealiumClient(
            account=profile_config['account'],
            profile=profile_config['profile'],
            api_key=api_key,
            email=email,
            proxies=proxies
        )

        with st.spinner("Fetching revisions list..."):
            revisions = client.get_revisions()
            if not revisions:
                st.error("Could not fetch revisions for this profile. The profile might be empty or an error occurred.")
                return None
        
        latest_rev_id = revisions[0]
        live_rev_id = None
        
        with st.spinner("Finding live revision..."):
            for rev_id in revisions:
                details = client.get_revision_details(rev_id)
                if details and details.get('publish_date'):
                    live_rev_id = rev_id
                    break 

        if not live_rev_id:
            st.warning("This profile has never been published. Cannot perform comparison.")
            return None

        if latest_rev_id == live_rev_id:
            return {"is_same": True}

        with st.spinner(f"Fetching data for live version ({live_rev_id})..."):
            live_data_response = client.get_profile_components(publish_version=live_rev_id)
            if live_data_response.get("error"):
                st.error(f"Failed to fetch live version data: {live_data_response.get('message')}")
                return None
            live_data = live_data_response.get("data", {})

        with st.spinner(f"Fetching data for latest version ({latest_rev_id})..."):
            latest_data_response = client.get_profile_components(publish_version=latest_rev_id)
            if latest_data_response.get("error"):
                st.error(f"Failed to fetch latest version data: {latest_data_response.get('message')}")
                return None
            latest_data = latest_data_response.get("data", {})

        diff = compare_profiles(live_data, latest_data)
        return diff

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None