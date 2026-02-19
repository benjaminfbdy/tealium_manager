import pandas as pd
import json
from typing import Dict, Any

def parse_server_side_export(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses the JSON data from a Tealium server-side export.
    Extracts key components like connectors, actions, and mappings.

    Args:
        json_data: The loaded JSON data as a Python dictionary.

    Returns:
        A dictionary containing parsed data, typically as pandas DataFrames.
    """
    results = {
        "summary": {},
        "connectors": pd.DataFrame(),
        "visitor_attributes": pd.DataFrame(),
        "visit_attributes": pd.DataFrame(),
        "error": None
    }

    try:
        # --- 1. Parse Attributes & Build Lookup Map ---
        # We need this map to resolve Attribute IDs (e.g., "54") to Names (e.g., "user_email") in connector mappings
        attr_lookup = {}
        
        def _process_attributes(scope_key):
            attrs = json_data.get("attributes", {}).get(scope_key, [])
            data_list = []
            for a in attrs:
                a_id = str(a.get("id"))
                a_name = a.get("name", "Unknown")
                attr_lookup[a_id] = f"{a_name} ({scope_key})"
                
                data_list.append({
                    "ID": a_id,
                    "Nom": a_name,
                    "Type": a.get("type"),
                    "Description": a.get("description", "")
                })
            return pd.DataFrame(data_list)

        results["visitor_attributes"] = _process_attributes("visitor")
        results["visit_attributes"] = _process_attributes("visit")

        # --- Summary ---
        results["summary"]["audiences"] = len(json_data.get("audiences", []))
        results["summary"]["connectors"] = len(json_data.get("connectors", []))
        results["summary"]["visitor_attributes"] = len(results["visitor_attributes"])
        results["summary"]["visit_attributes"] = len(results["visit_attributes"])

        # --- 2. Parse Connectors & Mappings ---
        connector_rows = []
        for connector in json_data.get("connectors", []):
            conn_name = connector.get("name", "Unknown Connector")
            conn_type = connector.get("type", "Unknown Type")
            
            for action in connector.get("actions", []):
                action_name = action.get("name", "Unknown Action")
                
                # Extract Mappings
                mappings = action.get("mappings", [])
                if not mappings:
                    # Add a row even if no mappings, to show the action exists
                    connector_rows.append({
                        "Connecteur": conn_name,
                        "Type": conn_type,
                        "Action": action_name,
                        "Source (Tealium)": "-",
                        "Destination (Vendor)": "-"
                    })
                
                for m in mappings:
                    # Source is often an attribute ID
                    source_raw = str(m.get("source", ""))
                    source_resolved = attr_lookup.get(source_raw, source_raw)
                    
                    # Target is the vendor parameter name
                    target = m.get("target", "")
                    
                    connector_rows.append({
                        "Connecteur": conn_name,
                        "Type": conn_type,
                        "Action": action_name,
                        "Source (Tealium)": source_resolved,
                        "Destination (Vendor)": target
                    })
        
        results["connectors"] = pd.DataFrame(connector_rows)

    except Exception as e:
        results["error"] = f"Erreur lors du parsing du JSON : {e}"

    return results