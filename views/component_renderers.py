import streamlit as st
import pandas as pd
from typing import Dict, Any, List

# --- Load Rule Renderers ---

def _render_conditions_table(conditions: List[List[Dict[str, Any]]]):
    """Helper to render a list of conditions into a clean table."""
    condition_list = []
    # The conditions are a list of lists (for OR groups)
    for i, condition_group in enumerate(conditions):
        for cond in condition_group:
            condition_list.append({
                "Group (OR)": i + 1,
                "Variable": cond.get("variable"),
                "Operator": cond.get("operator"),
                "Value": cond.get("value", "")
            })
    
    if condition_list:
        df = pd.DataFrame(condition_list)
        st.dataframe(df, use_container_width=True, height=min(500, (len(df) + 1) * 35))
    else:
        st.text("No conditions defined.")

def render_load_rule(component: Dict[str, Any]):
    """
    Renders a single Load Rule component in a user-friendly way.
    """
    st.caption(f"ID: {component.get('id')} | Status: {component.get('status')}")
    notes = component.get("notes")
    if notes:
        st.markdown(f"> {notes}")

    st.subheader("Conditions")
    _render_conditions_table(component.get("conditions", []))

    with st.expander("Voir les données brutes"):
        st.json(component)

# --- Tag Renderers ---

def _render_mappings_table(mappings: List[Dict[str, Any]]):
    """Helper to render a list of data mappings into a clean table."""
    mapping_list = []
    for mapping in mappings:
        # A single mapping item can have multiple destinations
        for dest in mapping.get("mappings", []):
            mapping_list.append({
                "Variable": mapping.get("variable"),
                "Mapping": dest,
                "Type": mapping.get("type")
            })
    
    if mapping_list:
        df = pd.DataFrame(mapping_list)
        st.dataframe(df, use_container_width=True, height=min(500, (len(df) + 1) * 35))
    else:
        st.text("No data mappings defined.")

def render_tag(component: Dict[str, Any], uid_map: Dict[int, Dict[str, str]]):
    """
    Renders a single Tag component in a user-friendly way.
    """
    st.caption(f"ID: {component.get('id')} | Status: {component.get('status')} | Vendor: {component.get('vendor')}")
    
    notes = component.get("notes")
    if notes:
        st.markdown(f"> {notes}")

    # Render Load Rules used by this tag
    load_rule_ids = component.get("loadRuleIds", [])
    st.subheader("Load Rules")
    if load_rule_ids:
        for uid in load_rule_ids:
            name = uid_map.get(uid, {}).get('name', f"Unknown UID: {uid}")
            st.text(f"- {name} (ID: {uid})")
    else:
        st.text("Always On (no load rules)")

    st.subheader("Data Mappings")
    _render_mappings_table(component.get("dataMappings", []))

    # Render Config
    config = component.get("config")
    if config:
        st.subheader("Configuration")
        st.json(config, expanded=False)

    with st.expander("Voir les données brutes"):
        st.json(component)

# --- Variable Renderers ---

def _render_used_in(used_in: Dict[str, List[int]], uid_map: Dict[int, Dict[str, str]]):
    """Renders the 'usedIn' object by resolving UIDs to names."""
    has_references = False
    for key, uids in used_in.items():
        if uids:
            has_references = True
            st.markdown(f"**{key.capitalize()}:**")
            for uid in uids:
                try:
                    uid = int(uid)
                    name = uid_map.get(uid, {}).get('name', f"Unknown UID: {uid}")
                    st.text(f"- {name} (ID: {uid})")
                except (ValueError, TypeError):
                    st.text(f"- Invalid UID format: {uid}")

    if not has_references:
        st.text("Not used by any other components.")

def render_variable(component: Dict[str, Any], uid_map: Dict[int, Dict[str, str]]):
    """
    Renders a single Variable component in a user-friendly way.
    """
    st.caption(f"ID: {component.get('id')} | Type: {component.get('type')}")
    
    notes = component.get("notes")
    if notes:
        st.markdown(f"> {notes}")
    
    st.subheader("Used In")
    _render_used_in(component.get("usedIn", {}), uid_map)

    with st.expander("Voir les données brutes"):
        st.json(component)

# --- Extension Renderers ---

def render_extension(component: Dict[str, Any]):
    """
    Renders a single Extension component in a user-friendly way.
    """
    st.caption(f"ID: {component.get('id')} | Status: {component.get('status')} | Scope: {component.get('scope', 'N/A')}")
    
    notes = component.get("notes")
    if notes:
        st.markdown(f"> {notes}")

    # Isolate code and configuration for special display
    code = component.get("code")
    configuration = component.get("configuration")

    if code:
        st.subheader("Code Snippet")
        st.code(code, language="javascript")

    if configuration:
        st.subheader("Configuration")
        # A simple key-value display for the config object
        for key, value in configuration.items():
            if isinstance(value, (dict, list)):
                with st.expander(f"{key}"):
                    st.json(value)
            else:
                st.text(f"{key}: {value}")
    
    with st.expander("Voir les données brutes"):
        st.json(component)