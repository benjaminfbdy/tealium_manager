import json

def _sort_value(value):
    """Recursively sort lists to allow order-insensitive comparison."""
    if isinstance(value, list):
        # Don't sort lists of dictionaries, as their order might be meaningful
        # and they lack a natural sort order.
        if all(isinstance(i, dict) for i in value):
            return value 
        try:
            return sorted(_sort_value(v) for v in value)
        except (TypeError):
            # Not all items are of the same type, can't sort
            return [_sort_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _sort_value(v) for k, v in value.items()}
    return value

def _are_items_equal(item1, item2):
    """
    Compare two items (dicts), ignoring order of elements in lists.
    """
    # Use json.dumps for a quick but potentially fragile check
    # A more robust solution would be a recursive dict comparison
    # that handles list sorting.
    
    # By normalizing (sorting) lists within the structure, we can do a direct string comparison.
    sorted_item1 = _sort_value(item1)
    sorted_item2 = _sort_value(item2)
    
    # Pretty print with sorting ensures consistent key order
    s1 = json.dumps(sorted_item1, sort_keys=True)
    s2 = json.dumps(sorted_item2, sort_keys=True)
    
    return s1 == s2


def compare_items(list1, list2, key_field='uid'):
    """
    Compares two lists of dictionaries based on a key field.
    """
    added = []
    removed = []
    modified = []

    map1 = {item[key_field]: item for item in list1}
    map2 = {item[key_field]: item for item in list2}

    keys1 = set(map1.keys())
    keys2 = set(map2.keys())

    added_keys = keys2 - keys1
    for key in added_keys:
        added.append(map2[key])

    removed_keys = keys1 - keys2
    for key in removed_keys:
        removed.append(map1[key])

    common_keys = keys1 & keys2
    for key in common_keys:
        item1 = map1[key]
        item2 = map2[key]

        if not _are_items_equal(item1, item2):
            modified.append({"before": item1, "after": item2})
            
    return {"added": added, "removed": removed, "modified": modified}


def compare_profiles(profile1_data, profile2_data):
    """
    Compares two Tealium profiles and returns a dictionary of differences.
    """
    if not profile1_data or not profile2_data:
        return {"error": "One or both profile data objects are empty."}

    profile1_props = profile1_data.get('profile', {}).get('properties', {})
    profile2_props = profile2_data.get('profile', {}).get('properties', {})

    diff = {}
    
    # Components to compare
    components = {
        "tags": 'tags',
        "variables": 'variables',
        "extensions": 'extensions',
        "loadRules": 'loadRules'
    }

    for name, key in components.items():
        diff[name] = compare_items(
            profile1_props.get(key, []),
            profile2_props.get(key, [])
        )

    return diff
