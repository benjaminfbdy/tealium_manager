import pandas as pd
from typing import Dict, List

def parse_target_mappings(df: pd.DataFrame) -> Dict[str, str]:
    """
    Parses the target reference dataframe into a standardized dictionary.
    Assumes Adobe variables are in column 'VARIABLE AA' and technical names in 'NOM TECHNIQUE'.
    """
    # Ensure required columns exist
    if 'VARIABLE AA' not in df.columns or 'NOM TECHNIQUE' not in df.columns:
        raise ValueError("Le fichier de référentiel cible doit contenir les colonnes 'VARIABLE AA' and 'NOM TECHNIQUE'.")

    # Select, clean, and convert to dictionary
    target_df = df[['VARIABLE AA', 'NOM TECHNIQUE']].copy()
    target_df.dropna(subset=['NOM TECHNIQUE'], inplace=True)
    target_df['NOM TECHNIQUE'] = target_df['NOM TECHNIQUE'].astype(str).str.strip()
    target_df['VARIABLE AA'] = target_df['VARIABLE AA'].astype(str).str.strip()
    
    # Create a dictionary of {technical_name: adobe_variable}
    # If there are duplicate technical names, this will keep the last one found.
    target_map = pd.Series(target_df['VARIABLE AA'].values, index=target_df['NOM TECHNIQUE']).to_dict()
    
    return target_map

def parse_eventstream_mappings(es_data: List[Dict[str, str]]) -> Dict[str, str]:

    """

    Parses mappings from an EventStream JSON data structure.

    

    ASSUMPTION: The JSON is a list of dictionaries, where each dict has

    a 'source' key (the technical UDO name) and a 'destination' key 

    (the Adobe Analytics variable).

    Example: [{"source": "page_name", "destination": "eVar50"}, ...]

    """

    if not isinstance(es_data, list):

        # This could be another format, e.g. a dict. For now, we raise an error.

        # This can be improved if other formats are discovered.

        raise ValueError("Le format du JSON EventStream n'est pas reconnu. Une liste de mappings est attendue.")



    es_map = {}

    for mapping_item in es_data:

        if isinstance(mapping_item, dict) and 'source' in mapping_item and 'destination' in mapping_item:

            technical_name = mapping_item['source'].strip()

            adobe_var = mapping_item['destination'].strip()

            es_map[technical_name] = adobe_var

        else:

            # Handle cases where items in the list don't match the expected structure

            print(f"Warning: Ignored invalid item in EventStream JSON: {mapping_item}")

            

    return es_map



def parse_tiq_mappings(profile_data: Dict) -> Dict[str, str]:



    """



    Finds the Adobe Analytics tag and parses its dataMappings into a standardized dictionary.



    """



    if not isinstance(profile_data, dict):



        return {}







    # 1. Find the Adobe Analytics tag



    adobe_tag = None



    tags = profile_data.get('tags') or []



    items_to_search = tags.values() if isinstance(tags, dict) else tags



    



    for tag in items_to_search:



        if isinstance(tag, dict) and 'adobe analytics' in tag.get('name', '').lower():



            adobe_tag = tag



            break # Found the first one, assume it's the main one



    



    if not adobe_tag:



        # If no tag is found, we can't proceed.



        raise ValueError("Aucun tag 'Adobe Analytics' trouvé dans le profil Tealium iQ.")







    # 2. Parse its dataMappings



    tiq_map = {}



    data_mappings = adobe_tag.get('dataMappings', [])



    for mapping_item in data_mappings:



        if not isinstance(mapping_item, dict) or 'variable' not in mapping_item or 'mappings' not in mapping_item:



            continue







        technical_name = mapping_item['variable']



        adobe_vars = mapping_item['mappings']







        if technical_name and isinstance(adobe_vars, list) and adobe_vars:



            # The 'mappings' array can contain multiple values, like ['eVar7', 'campaign'].



            # We'll take the first one as the primary Adobe variable.



            # We also clean up potential leading/trailing spaces.



            main_adobe_var = adobe_vars[0].strip()



            tiq_map[technical_name] = main_adobe_var



            



    return tiq_map







def compare_mappings(target_mappings: Dict[str, str], source_name: str, source_mappings: Dict[str, str]) -> List[Dict[str, str]]:







    """







    Compares a source mapping dictionary against a target mapping dictionary.







    Returns a list of result rows.







    """







    results = []







    







    # Keep track of source variables that have been checked







    checked_source_vars = set()















    # 1. Iterate through the target reference to find OK, KO, and Missing mappings







    for target_tech_name, target_adobe_var in target_mappings.items():







        result_row = {







            'variable_cible': target_tech_name,







            'mapping_cible': target_adobe_var,







            'source': source_name,







            'mapping_actuel': '',







            'status': ''







        }















        if target_tech_name in source_mappings:







            checked_source_vars.add(target_tech_name)







            source_adobe_var = source_mappings[target_tech_name]







            result_row['mapping_actuel'] = source_adobe_var















            if source_adobe_var == target_adobe_var:







                result_row['status'] = 'OK'







            else:







                result_row['status'] = 'KO'







        else:







            result_row['status'] = 'Manquant'







            result_row['mapping_actuel'] = 'N/A'







        







        results.append(result_row)















    # 2. Iterate through the source to find extra mappings







    for source_tech_name, source_adobe_var in source_mappings.items():







        if source_tech_name not in checked_source_vars:







            results.append({







                'variable_cible': 'N/A',







                'mapping_cible': 'N/A',







                'source': source_name,







                'mapping_actuel': f"{source_tech_name} -> {source_adobe_var}",







                'status': 'Extra'







            })















    return results


