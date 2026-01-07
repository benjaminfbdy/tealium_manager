import pandas as pd
from typing import Dict, Optional, Any, List
from utils.mapping_logic import parse_target_mappings, parse_eventstream_mappings, parse_tiq_mappings, compare_mappings
from utils.tealium_client import TealiumClient
from database import load_global_credentials

def process_mappings(target_df: pd.DataFrame, eventstream_data: Optional[Dict], tiq_profile_config: Optional[Dict]) -> pd.DataFrame:
    """
    Main controller function to orchestrate the mapping comparison.
    """
    all_results = []

    # 1. Parse the target reference file into a standard dictionary
    target_map = parse_target_mappings(target_df)

    # 2. Process EventStream file if provided
    if eventstream_data:
        print("Processing EventStream data...")
        es_map = parse_eventstream_mappings(eventstream_data)
        es_results = compare_mappings(target_map, "EventStream", es_map)
        all_results.extend(es_results)

    # 3. Process Tealium iQ profile if provided
    if tiq_profile_config:
        print(f"Processing Tealium iQ profile: {tiq_profile_config['name']}")
        
        # Fetch the latest profile data from the API
        creds = load_global_credentials()
        if not creds.get('api_key'):
            raise ValueError("Les identifiants globaux (clé API) ne sont pas configurés.")
        
        client = TealiumClient(
            account=tiq_profile_config["account"],
            profile=tiq_profile_config["profile"],
            api_key=creds["api_key"],
            email=creds["email"]
        )
        
        profile_data_response = client.get_profile_components(component_types=['tags'])
        if profile_data_response.get("error"):
            raise ConnectionError(f"Erreur API pour le profil TiQ : {profile_data_response.get('message')}")
        
        # Parse the mappings from the fetched data
        tiq_map = parse_tiq_mappings(profile_data_response.get("data"))
        tiq_results = compare_mappings(target_map, f"TiQ - {tiq_profile_config['name']}", tiq_map)
        all_results.extend(tiq_results)

    # 4. Create and return the final DataFrame
    if not all_results:
        return pd.DataFrame(columns=['variable_cible', 'mapping_cible', 'source', 'mapping_actuel', 'status'])
        
    final_df = pd.DataFrame(all_results)
    # Reorder columns for better readability
    final_df = final_df[['source', 'variable_cible', 'mapping_cible', 'mapping_actuel', 'status']]
    return final_df
