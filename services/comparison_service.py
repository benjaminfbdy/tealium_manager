from deepdiff import DeepDiff

def normalize_config(config):
    """
    Normalizes a Tealium configuration object by converting lists of items 
    (tags, variables, etc.) into dictionaries keyed by their ID.
    This allows for a more robust comparison that is not dependent on item order.
    """
    normalized = {}
    for key in ['tags', 'extensions', 'loadRules', 'variables', 'events']:
        items = config.get(key)
        if items:  # Check if the list is not None or empty
            normalized[key] = {str(item['id']): item for item in items if 'id' in item}
    return normalized

def get_diff(config_a, config_b):
    """
    Performs a deep comparison between two normalized configuration objects.
    """
    config_a_norm = normalize_config(config_a)
    config_b_norm = normalize_config(config_b)

    # DeepDiff comparison on the normalized data
    diff = DeepDiff(
        config_a_norm, config_b_norm,
        ignore_order=True,
        report_repetition=True,
        # Exclude paths that are noisy and not useful for comparison
        exclude_regex_paths=r"\\['version'\]|template|versionTitle|minorVersion|parentVersion|creation|environmentVersions|versionDetails"
    )
    return diff
