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
        "error": None,
        "debug_info": {}
    }

    try:
        # --- 0. Detect Data Root (Robustness Fix) ---
        # Tealium exports vary. Data can be at root, in 'data', in 'profile', etc.
        data_root = json_data
        root_source = "root"
        
        # Candidates to check for payload
        candidates = [
            ("root", json_data),
            ("data", json_data.get("data")),
            ("profile", json_data.get("profile")),
            ("publish_data", json_data.get("publish", {}).get("data"))
        ]

        for name, candidate in candidates:
            if isinstance(candidate, dict) and ("connectors" in candidate or "attributes" in candidate):
                data_root = candidate
                root_source = name
                break
        
        results["debug_info"]["root_source"] = root_source
        results["debug_info"]["root_keys"] = list(data_root.keys()) if isinstance(data_root, dict) else []

        # --- 1. Parse Attributes & Build Lookup Map ---
        attr_lookup = {}
        
        def _process_attributes(scope_key):
            # Attributes are usually under "attributes" -> "visitor" / "visit"
            # Handle case where attributes might be missing or None
            attributes_container = data_root.get("attributes") or {}
            attrs = attributes_container.get(scope_key, [])
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
        results["summary"]["audiences"] = len(data_root.get("audiences") or [])
        results["summary"]["connectors"] = len(data_root.get("connectors") or [])
        results["summary"]["visitor_attributes"] = len(results["visitor_attributes"])
        results["summary"]["visit_attributes"] = len(results["visit_attributes"])

        # --- 2. Parse Connectors & Mappings ---
        connector_rows = []
        connectors_list = data_root.get("connectors") or []
        for connector in connectors_list:
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