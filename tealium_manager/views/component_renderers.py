import streamlit as st
import pandas as pd
from typing import Dict, Any, List

def render_sidebar():
    """Renders the custom sidebar navigation for the application."""
    st.sidebar.title("Navigation")
    st.sidebar.divider()
    st.sidebar.subheader("Tealium")
    st.sidebar.page_link("main.py", label="Accueil")
    st.sidebar.page_link("pages/inventory_view.py", label="Inventaire")
    st.sidebar.page_link("pages/mep_history_view.py", label="Historique des MEP")

    st.sidebar.divider()
    st.sidebar.subheader("Adobe Analytics")
    st.sidebar.page_link("pages/adobe_dashboard_view.py", label="Requeteur")
    st.sidebar.page_link("pages/adobe_reports_view.py", label="Rapports")
    st.sidebar.page_link("pages/3_Adobe_User_Management.py", label="Gestion Utilisateurs")
    st.sidebar.page_link("pages/4_Adobe_Profile_Mapping.py", label="Cartographie Profils")

    st.sidebar.divider()
    st.sidebar.subheader("Configuration")
    st.sidebar.page_link("pages/1_Config_Tealium.py", label="Config Tealium")
    st.sidebar.page_link("pages/2_Config_Adobe.py", label="Config Adobe")
    st.sidebar.page_link("pages/9_Administration.py", label="Administration")

    # Session state initialization for multi-page navigation is now handled by Streamlit,
    # but we might need to keep state for active configs.
    if "active_tealium_config" not in st.session_state:
        st.session_state.active_tealium_config = None
    if "active_adobe_config" not in st.session_state:
        st.session_state.active_adobe_config = None
    if 'active_tealium_profile_name' not in st.session_state:
        st.session_state.active_tealium_profile_name = None
    if 'active_adobe_profile_name' not in st.session_state:
        st.session_state.active_adobe_profile_name = None

    st.sidebar.divider()
    st.sidebar.caption("🚀 Tealium Manager v0.9.1 (UMAPI & Proxy)")


def setup_page():
    """
    Sets the default page configuration, injects CSS, and renders the sidebar.
    This function should be called at the start of every page script.
    """
    # st.set_page_config must be called as the first Streamlit command and only once.
    try:
        st.set_page_config(
            page_title="Tealium Manager",
            layout="wide"
        )
    except st.errors.StreamlitAPIException as e:
        if "can only be called once per app" in str(e):
            pass
        else:
            raise

    # --- Hide Streamlit's default navigation ---
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Render the custom sidebar
    render_sidebar()

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
    Renders a single Tag component with detailed, business-friendly formatting.
    """
    st.caption(f"ID: {component.get('id')} | Status: {component.get('status')} | Vendor: {component.get('vendor')}")
    
    notes = component.get("notes")
    if notes:
        st.markdown(f"> {notes}")

    col1, col2 = st.columns(2)

    # --- Column 1: Rules and Targets ---
    with col1:
        # --- Load Rules ---
        st.subheader(" déclenchement")
        rules = component.get("rules", {})
        apply_rules = rules.get("apply")
        exclude_rules = rules.get("exclude")

        if not apply_rules and not exclude_rules:
             st.markdown("- **Load Rules**: `Always On`")
        else:
            if apply_rules:
                # Assuming 'apply' follows the same structure as 'exclude'
                # This part might need adjustment based on actual data structure for 'apply'
                st.markdown("- **Load Rules (Inclusion)**:")
                for rule_group in apply_rules:
                    for rule_item in rule_group.get("or", []):
                        uid = rule_item.get("uid")
                        name = uid_map.get(uid, {}).get('name', f"Unknown UID: {uid}")
                        st.markdown(f"  - `{name}`")
            if exclude_rules:
                st.markdown("- **Load Rules (Exclusion)**:")
                for rule_group in exclude_rules:
                    for rule_item in rule_group.get("or", []):
                        uid = rule_item.get("uid")
                        name = uid_map.get(uid, {}).get('name', f"Unknown UID: {uid}")
                        st.markdown(f"  - `{name}`")
        
        # --- Selected Targets ---
        st.subheader("Cibles")
        targets = component.get("selectedTargets", {})
        enabled_targets = [k.upper() for k, v in targets.items() if v is True]
        if enabled_targets:
            st.markdown(f"- **Environnements activés**: {', '.join(enabled_targets)}")
        else:
            st.markdown("- Aucun environnement activé.")

    # --- Column 2: Advanced Config ---
    with col2:
        st.subheader("Configuration Avancée")
        adv_config = component.get("advancedConfiguration", {})
        if adv_config:
            for key, value in adv_config.items():
                st.markdown(f"- **{key.replace('_', ' ').capitalize()}**: `{value}`")
        else:
            st.text("Aucune configuration avancée.")

    # --- Data Mappings (Full Width) ---
    st.subheader("Data Mappings")
    _render_mappings_table(component.get("dataMappings", []))

    # --- Vendor Specific Configuration (Full Width) ---
    vendor_config = component.get("configuration")
    if vendor_config:
        with st.expander("Voir la Configuration Spécifique au Tag (Adobe Analytics)"):
            st.json(vendor_config)

    with st.expander("Voir les données brutes complètes"):
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