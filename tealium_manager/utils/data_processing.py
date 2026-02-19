import copy
import json
from typing import Dict, Any, List
import datetime
import pytz

def format_tealium_timestamp(ts: str) -> str:
    """
    Converts a Tealium version timestamp string into a human-readable French time format.
    Example: '202601061747' -> '06/01/2026 18h47'
    """
    if not ts or len(ts) != 12:
        return ts # Return original string if format is invalid
    
    try:
        # 1. Parse the string into a naive datetime object assuming UK time
        # Tealium's timestamps are based on UK time (GMT/BST)
        dt_naive = datetime.datetime.strptime(ts, "%Y%m%d%H%M")

        # 2. Localize the naive datetime to the 'Europe/London' timezone
        london_tz = pytz.timezone('Europe/London')
        dt_london = london_tz.localize(dt_naive)

        # 3. Convert the London time to the 'Europe/Paris' timezone
        paris_tz = pytz.timezone('Europe/Paris')
        dt_paris = dt_london.astimezone(paris_tz)

        # 4. Format the final datetime object
        return dt_paris.strftime('%d/%m/%Y %Hh%M')
        
    except (ValueError, pytz.exceptions.PyTZError) as e:
        print(f"Warning: Could not format timestamp '{ts}'. Error: {e}")
        return ts # Return original on error

def build_uid_to_name_map(profile_data: Dict[str, Any]) -> Dict[int, Dict[str, str]]:
    """
    Builds a map from component UID to its name and type for easy lookup.
    
    Args:
        profile_data: The full profile data dictionary from the Tealium API.

    Returns:
        A dictionary where keys are UIDs (int) and values are dicts 
        containing the component's name and type.
        Example: {101: {'name': 'My Tag', 'type': 'Tag'}, 205: {'name': 'page_name', 'type': 'Variable'}}
    """
    uid_map = {}
    
    component_types = {
        "variables": "Variable",
        "loadRules": "Load Rule",
        "extensions": "Extension",
        "tags": "Tag",
        "events": "Event"
    }

    for key, component_type_name in component_types.items():
        components = profile_data.get(key)
        if isinstance(components, list):
            for component in components:
                uid = component.get("id")
                # Variables use 'alias' for their display name in some contexts, 'name' in others.
                name = component.get("name") or component.get("alias")
                
                if uid:
                    # UIDs from the API can be strings, ensure they are ints for consistent keys
                    try:
                        uid = int(uid)
                        uid_map[uid] = {"name": name or f"Untitled {component_type_name}", "type": component_type_name}
                    except (ValueError, TypeError):
                        print(f"Warning: Could not process UID '{uid}' for a {component_type_name}.")

    return uid_map



def _resolve_recursive(data: Any, uid_map: Dict[int, Dict[str, str]]) -> Any:
    """Helper function to recursively traverse and resolve UIDs."""
    if isinstance(data, dict):
        # Specific logic for Tealium's 'rules' structure
        if "and" in data and "or" in data:
            try:
                uid_to_resolve = int(data.get("uid"))
                if uid_to_resolve in uid_map:
                    resolved_info = uid_map[uid_to_resolve]
                    return f"{resolved_info['name']} ({resolved_info['type']})"
            except (ValueError, TypeError, AttributeError):
                pass # Fallback to iterating through the dict

        return {key: _resolve_recursive(value, uid_map) for key, value in data.items()}

    if isinstance(data, list):
        # Logic to resolve a list of UIDs (like in 'usedIn')
        if all(isinstance(x, (int, str)) for x in data):
            resolved_list = []
            for item in data:
                try:
                    uid_to_resolve = int(item)
                    if uid_to_resolve in uid_map:
                        resolved_info = uid_map[uid_to_resolve]
                        resolved_list.append(f"{resolved_info['name']} ({resolved_info['type']})")
                    else:
                        resolved_list.append(item) # Keep original if not found
                except (ValueError, TypeError):
                    resolved_list.append(item) # Keep original if not a valid UID
            if resolved_list:
                 return resolved_list

        return [_resolve_recursive(item, uid_map) for item in data]

    return data

def resolve_uids_in_component(component: Dict[str, Any], uid_map: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
    """
    Recursively finds fields with UID references within a component and replaces 
    the UIDs with their corresponding names from the uid_map.
    
    Args:
        component: The component dictionary to process (e.g., a single tag or variable).
        uid_map: The UID-to-name lookup map.

    Returns:
        A new component dictionary with UIDs resolved to names.
    """
    if not isinstance(component, dict):
        return component
        
    # Deep copy to avoid modifying the original data
    resolved_component = copy.deepcopy(component)
    
    # Process specific known fields that contain UIDs
    fields_to_resolve = ['usedIn', 'rules', 'eventTrigger']
    for field in fields_to_resolve:
        if field in resolved_component:
            resolved_component[field] = _resolve_recursive(resolved_component[field], uid_map)
            
    # Handle tag-scoped extensions where 'scope' is a list of tag UIDs
    if resolved_component.get('object') == 'extension' and isinstance(resolved_component.get('scope'), str):
        try:
            # Check if scope is a comma-separated list of numbers
            uids = [int(s.strip()) for s in resolved_component['scope'].split(',')]
            resolved_names = [uid_map.get(uid, {}).get('name', f'Unknown Tag ID {uid}') for uid in uids]
            resolved_component['scope'] = f"Tag Scoped: {', '.join(resolved_names)}"
        except ValueError:
            # Scope is not a list of UIDs (e.g., 'DOM Ready'), so we leave it as is
            pass

    return resolved_component

def _normalize_for_diff(data):
    """Recursively sorts lists and dictionary keys to make comparison order-independent."""
    if isinstance(data, dict):
        return {k: _normalize_for_diff(v) for k, v in sorted(data.items())}
    if isinstance(data, list):
        # For lists of dicts, we need a stable sorting key. str() is a decent heuristic.
        try:
            return sorted([_normalize_for_diff(x) for x in data], key=str)
        except TypeError:
            # Cannot sort lists with mixed types (e.g., dict and None)
            return [_normalize_for_diff(x) for x in data]
    return data

def are_semantically_equal(comp1: Dict, comp2: Dict) -> bool:
    """
    Compares two components semantically, ignoring list order and irrelevant fields.
    """
    # Create copies to manipulate
    c1 = copy.deepcopy(comp1)
    c2 = copy.deepcopy(comp2)

    # List of keys to ignore during comparison (e.g., internal versioning)
    keys_to_ignore = ["version", "minorVersion", "_rev", "environmentVersions"]
    for key in keys_to_ignore:
        c1.pop(key, None)
        c2.pop(key, None)
        
    # Normalize by sorting all lists and dict keys recursively
    normalized_c1 = _normalize_for_diff(c1)
    normalized_c2 = _normalize_for_diff(c2)

    return normalized_c1 == normalized_c2

def diff_revisions(rev1: Dict[str, Any], rev2: Dict[str, Any]) -> Dict[str, Dict[str, List]]:
    """
    Compares two revision data dictionaries and identifies additions, deletions, and modifications.
    """
    diff_results = {}
    component_keys = ["variables", "tags", "loadRules", "extensions", "events"]

    for key in component_keys:
        diff_results[key] = {"added": [], "removed": [], "modified": []}

        items1 = {item['id']: item for item in rev1.get(key, []) if 'id' in item}
        items2 = {item['id']: item for item in rev2.get(key, []) if 'id' in item}

        all_ids = set(items1.keys()).union(items2.keys())

        for item_id in all_ids:
            item1 = items1.get(item_id)
            item2 = items2.get(item_id)

            if item1 and not item2:
                diff_results[key]["removed"].append(item1)
            elif not item1 and item2:
                diff_results[key]["added"].append(item2)
            elif item1 and item2:
                if not are_semantically_equal(item1, item2):
                    diff_results[key]["modified"].append({"before": item1, "after": item2})
    
    print("DEBUG: Final diff object being returned:")
    print(json.dumps(diff_results, indent=2))
    return diff_results


def format_date_range_readable(date_key: str) -> str:
    """
    Converts a date range key string into a human-readable format.
    Example: "20231026T000000_20231101T235959" -> "26/10/2023 - 01/11/2023"
    Example: "AUDIT_EXEC_20231026" -> "Audit du 26/10/2023"
    """
    if not date_key:
        return "N/A"
    
    try:
        if date_key.startswith("AUDIT_EXEC_"):
            date_part = date_key.replace("AUDIT_EXEC_", "")
            dt_obj = datetime.datetime.strptime(date_part, "%Y%m%d")
            return f"Audit du {dt_obj.strftime('%d/%m/%Y')}"
        
        if "_" in date_key:
            start_str, end_str = date_key.split('_')
            start_dt = datetime.datetime.strptime(start_str, "%Y%m%dT%H%M%S")
            end_dt = datetime.datetime.strptime(end_str, "%Y%m%dT%H%M%S")
            return f"{start_dt.strftime('%d/%m/%Y')} - {end_dt.strftime('%d/%m/%Y')}"
    except (ValueError, TypeError):
        return date_key
        
    return date_key
