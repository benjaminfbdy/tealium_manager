import pandas as pd
from typing import Dict, List, Any

def parse_target_mappings(df: pd.DataFrame) -> Dict[str, str]:
    """
    Parses the target reference dataframe into a standardized dictionary.
    Assumes Adobe variables are in column 1 ('VARIABLE AA') and Tealium variables in column 4 ('NOM TECHNIQUE').
    """
    # The user stated column 1 and 4, which are likely index 0 and 3 if there's no header,
    # or columns with specific names if there are headers.
    # The previous version assumed 'VARIABLE AA' and 'NOM TECHNIQUE'. Let's make it more robust.
    if len(df.columns) < 4:
        raise ValueError("Le fichier de référentiel cible doit avoir au moins 4 colonnes.")
    
    # Use column indices as per user description. iloc is 0-indexed.
    adobe_var_col = df.columns[0]
    tealium_var_col = df.columns[3]

    target_df = df[[adobe_var_col, tealium_var_col]].copy()
    target_df.dropna(inplace=True)
    
    target_map = {}
    for _, row in target_df.iterrows():
        adobe_var = str(row[adobe_var_col]).strip().lower()
        tealium_var = str(row[tealium_var_col]).strip()
        if not adobe_var.startswith('event'):
            target_map[adobe_var] = tealium_var
            
    return target_map

def parse_eventstream_mappings(es_data: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Parses mappings from an EventStream JSON data structure.
    Returns a dict of {adobe_variable: tealium_source}.
    """
    if not isinstance(es_data, list):
        raise ValueError("Le format du JSON EventStream n'est pas reconnu. Une liste de mappings est attendue.")

    es_map = {}
    for mapping_item in es_data:
        if isinstance(mapping_item, dict) and 'tealium_source' in mapping_item and 'adobe_variable' in mapping_item:
            adobe_var = mapping_item['adobe_variable'].strip().lower()
            tealium_source = mapping_item['tealium_source'].strip()
            
            # Ignore event mappings as requested
            if not adobe_var.startswith('event'):
                es_map[adobe_var] = tealium_source
        else:
            print(f"Warning: Ignored invalid item in EventStream JSON: {mapping_item}")
            
    return es_map

def parse_tiq_mappings(profile_data: Dict) -> Dict[str, str]:
    """
    Finds the Adobe Analytics tag and parses its dataMappings into a standardized dictionary.
    Returns a dict of {adobe_variable: tealium_variable}.
    """
    if not isinstance(profile_data, dict):
        return {}

    adobe_tag = None
    tags = profile_data.get('tags') or []
    items_to_search = tags.values() if isinstance(tags, dict) else tags
    
    for tag in items_to_search:
        if isinstance(tag, dict) and 'adobe analytics' in tag.get('name', '').lower():
            adobe_tag = tag
            break
    
    if not adobe_tag:
        raise ValueError("Aucun tag 'Adobe Analytics' trouvé dans le profil Tealium iQ.")

    tiq_map = {}
    data_mappings = adobe_tag.get('dataMappings', [])
    for mapping_item in data_mappings:
        if not isinstance(mapping_item, dict) or 'variable' not in mapping_item or 'mappings' not in mapping_item:
            continue

        tealium_variable = mapping_item['variable']
        adobe_vars = mapping_item['mappings']

        if tealium_variable and isinstance(adobe_vars, list):
            for adobe_var_raw in adobe_vars:
                # adobe_var_raw could be "eVar70", " prop71", "event1:event1"
                adobe_var_cleaned = adobe_var_raw.strip().lower()
                
                # Ignore events
                if 'event' in adobe_var_cleaned:
                    continue
                
                # The key is the adobe variable, value is the tealium variable
                tiq_map[adobe_var_cleaned] = tealium_variable
                
    return tiq_map

def compare_mappings(target_mappings: Dict[str, str], source_name: str, source_mappings: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Compares a source mapping dictionary against a target mapping dictionary.
    Both dictionaries are expected to be {adobe_variable: tealium_variable}.
    Comparison is case-insensitive for Adobe variables (already lowercased).
    """
    results = []
    checked_source_vars = set()

    # 1. Iterate through the target reference to find OK, KO, and Missing mappings
    for target_adobe_var, target_tealium_var in target_mappings.items():
        target_adobe_var_lower = target_adobe_var.lower()

        result_row = {
            'variable_adobe': target_adobe_var,
            'mapping_cible': target_tealium_var,
            'source': source_name,
            'mapping_actuel': 'N/A',
            'status': 'Manquant'
        }

        if target_adobe_var_lower in source_mappings:
            checked_source_vars.add(target_adobe_var_lower)
            source_tealium_var = source_mappings[target_adobe_var_lower]
            result_row['mapping_actuel'] = source_tealium_var

            # Prepare variables for comparison, handling special EventStream case
            source_to_compare = source_tealium_var.lower()
            target_to_compare = target_tealium_var.lower()

            if 'eventstream' in source_name.lower() and source_to_compare.startswith('datalayer.'):
                source_to_compare = source_to_compare.replace('datalayer.', '', 1)

            if source_to_compare == target_to_compare:
                result_row['status'] = 'OK'
            else:
                result_row['status'] = 'KO'
        
        results.append(result_row)

    # 2. Iterate through the source to find extra mappings
    for source_adobe_var, source_tealium_var in source_mappings.items():
        if source_adobe_var not in checked_source_vars:
            results.append({
                'variable_adobe': source_adobe_var,
                'mapping_cible': 'N/A',
                'source': source_name,
                'mapping_actuel': source_tealium_var,
                'status': 'Extra'
            })

    return results