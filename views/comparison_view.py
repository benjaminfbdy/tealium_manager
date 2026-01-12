import streamlit as st
from typing import Dict, Any
from views.component_renderers import (
    render_load_rule, _render_conditions_table, 
    render_tag, _render_mappings_table,
    render_variable,
    render_extension
)
from controllers.comparison_controller import process_comparison
from controllers.config_controller import get_all_configurations
from utils.comparison_logic import _are_items_equal


def render_profile_comparison_page():
    """
    Renders the UI for the profile comparison feature.
    """
    st.title("Comparaison de la version live et de la dernière version")

    all_configs = get_all_configurations()
    if not all_configs:
        st.warning("Veuillez configurer au moins un profil pour utiliser l'outil de comparaison.")
        return

    profile_names = [config['name'] for config in all_configs]

    profile_name = st.selectbox("Sélectionnez un profil à comparer", options=profile_names, index=0)

    if st.button("Comparer les versions"):
        st.info(f"Comparaison des versions pour '{profile_name}'...")
        diff = process_comparison(profile_name)
        
        if diff:
            if diff.get("is_same"):
                st.success("Aucune modification non publiée. La dernière version est la version live.")
            else:
                render_profile_comparison(diff, f"{profile_name} (Live)", f"{profile_name} (Dernière)")



def render_profile_comparison(diff: Dict[str, Any], profile1_name: str, profile2_name: str):
    """
    Renders the comparison results between two profiles.
    """
    st.header(f"Comparaison entre '{profile1_name}' et '{profile2_name}'")

    component_map = {
        "Variables": "variables",
        "Tags": "tags",
        "Load Rules": "loadRules",
        "Extensions": "extensions"
    }

    has_changes = any(
        diff.get(key, {}).get("added") or diff.get(key, {}).get("removed") or diff.get(key, {}).get("modified")
        for key in component_map.values()
    )

    if not has_changes:
        st.success("Aucune différence détectée entre ces deux profils.")
        return

    tabs_to_create = [name for name, key in component_map.items() if diff[key]["added"] or diff[key]["removed"] or diff[key]["modified"]]
    
    if not tabs_to_create:
        st.info("Aucune différence sémantique détectée après filtrage.")
        return

    tab_list = st.tabs(tabs_to_create)
    tab_map = {name: tab for name, tab in zip(tabs_to_create, tab_list)}

    uid_map = {}

    for display_name, key in component_map.items():
        if display_name not in tab_map:
            continue
            
        with tab_map[display_name]:
            component_diff = diff.get(key, {})
            added = component_diff.get("added", [])
            removed = component_diff.get("removed", [])
            modified = component_diff.get("modified", [])

            if added:
                st.subheader(f"✅ {len(added)} Ajout(s) dans '{profile2_name}'")
                for item in added:
                    with st.expander(f"Nouveau: {item.get('name', item.get('title', item.get('uid', 'N/A')))}"):
                        if display_name == "Load Rules": render_load_rule(item)
                        elif display_name == "Tags": render_tag(item, uid_map)
                        elif display_name == "Variables": render_variable(item, uid_map)
                        elif display_name == "Extensions": render_extension(item)
                        else: st.json(item)

            if removed:
                st.subheader(f"❌ {len(removed)} Suppression(s) de '{profile1_name}'")
                for item in removed:
                    with st.expander(f"Supprimé: {item.get('name', item.get('title', item.get('uid', 'N/A')))}"):
                        if display_name == "Load Rules": render_load_rule(item)
                        elif display_name == "Tags": render_tag(item, uid_map)
                        elif display_name == "Variables": render_variable(item, uid_map)
                        elif display_name == "Extensions": render_extension(item)
                        else: st.json(item)

            if modified:
                st.subheader(f"🔄 {len(modified)} Modification(s)")
                for item in modified:
                    expander_title = item.get('after', {}).get('name', item.get('after', {}).get('title', 'N/A'))
                    with st.expander(f"Modifié: **{expander_title}**"):
                        render_pretty_component_diff(
                            item['before'], 
                            item['after'], 
                            display_name, 
                            profile1_name, 
                            profile2_name, 
                            uid_map={}
                        )


def _render_generic_value(value):
    """Helper to intelligently render a value, using st.json for dicts/lists and st.write for others."""
    if isinstance(value, (dict, list)):
        st.json(value, expanded=False)
    else:
        st.write(str(value))

def render_pretty_component_diff(item_before: Dict[str, Any], item_after: Dict[str, Any], component_type: str, profile1_name: str, profile2_name: str, uid_map: Dict[int, Dict[str, str]]):
    """
    Renders a structured, side-by-side diff for a component, dispatching to specialized
    renderers where available and highlighting changed values.
    """
    all_keys = sorted(list(set(item_before.keys()) | set(item_after.keys())))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"Dans {profile1_name}")
    with col2:
        st.subheader(f"Dans {profile2_name}")

    for key in all_keys:
        value_before = item_before.get(key)
        value_after = item_after.get(key)
        
        is_different = not _are_items_equal(value_before, value_after)

        if not is_different:
            continue

        if component_type == "Load Rules" and key == "conditions" and (value_before or value_after):
            with col1: st.warning(f"**{key}:**"); 
            if value_before: _render_conditions_table(value_before)
            with col2: st.warning(f"**{key}:**"); 
            if value_after: _render_conditions_table(value_after)
            continue
        
        if component_type == "Tags" and key == "dataMappings" and (value_before or value_after):
            with col1: st.warning(f"**{key}:**"); 
            if value_before: _render_mappings_table(value_before)
            with col2: st.warning(f"**{key}:**"); 
            if value_after: _render_mappings_table(value_after)
            continue
        
        if component_type == "Extensions" and key == "code" and (value_before or value_after):
            with col1:
                st.warning(f"**{key}:**"); st.code(value_before or "", language="javascript")
            with col2:
                st.warning(f"**{key}:**"); st.code(value_after or "", language="javascript")
            continue

        with col1:
            if value_before is not None:
                st.warning(f"**{key}:**"); _render_generic_value(value_before)
        with col2:
            if value_after is not None:
                st.warning(f"**{key}:**"); _render_generic_value(value_after)


def render_comparison(comparison_data: Dict[str, Any]):
    """
    Renders the comparison results between two revisions using a tabbed, side-by-side UI.
    """
    rev1_id = comparison_data.get("rev1_id", "N/A")
    rev2_id = comparison_data.get("rev2_id", "N/A")
    diff = comparison_data.get("diff", {})
    uid_map = comparison_data.get("uid_map", {})

    st.header(f"Comparaison entre MEP `{rev1_id}` et `{rev2_id}`")

    component_map = {
        "Variables": "variables", "Tags": "tags", "Load Rules": "loadRules",
        "Extensions": "extensions", "Events": "events"
    }

    has_changes = any(
        diff.get(key, {}).get("added") or diff.get(key, {}).get("removed") or diff.get(key, {}).get("modified")
        for key in component_map.values()
    )

    if not has_changes:
        st.info("Aucune différence détectée entre ces deux versions."); return

    tabs_to_create = [name for name, key in component_map.items() if diff.get(key, {}).get("added") or diff.get(key, {}).get("removed") or diff.get(key, {}).get("modified")]
    
    if not tabs_to_create:
        st.info("Aucune différence sémantique détectée après filtrage."); return
        
    tab_list = st.tabs(tabs_to_create)
    tab_map = {name: tab for name, tab in zip(tabs_to_create, tab_list)}

    for display_name, key in component_map.items():
        if display_name not in tab_map: continue
            
        with tab_map[display_name]:
            component_diff = diff.get(key, {}); added = component_diff.get("added", []); removed = component_diff.get("removed", []); modified = component_diff.get("modified", [])

            if added:
                st.subheader(f"✅ {len(added)} Ajout(s)")
                for item in added:
                    with st.expander(item.get('name', item.get('alias', 'N/A'))):
                        if display_name == "Load Rules": render_load_rule(item)
                        elif display_name == "Tags": render_tag(item, uid_map)
                        elif display_name == "Variables": render_variable(item, uid_map)
                        elif display_name == "Extensions": render_extension(item)
                        else: st.json(item)

            if removed:
                st.subheader(f"❌ {len(removed)} Suppression(s)")
                for item in removed:
                    with st.expander(item.get('name', item.get('alias', 'N/A'))):
                        if display_name == "Load Rules": render_load_rule(item)
                        elif display_name == "Tags": render_tag(item, uid_map)
                        elif display_name == "Variables": render_variable(item, uid_map)
                        elif display_name == "Extensions": render_extension(item)
                        else: st.json(item)

            if modified:
                st.subheader(f"🔄 {len(modified)} Modification(s)")
                for item in modified:
                    expander_title = item.get('after', {}).get('name', item.get('after', {}).get('alias', 'N/A'))
                    with st.expander(f"**{expander_title}**"):
                        render_pretty_component_diff(item['before'], item['after'], display_name, rev1_id, rev2_id, uid_map)
