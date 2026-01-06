import streamlit as st
from typing import Dict, Any
from views.component_renderers import (
    render_load_rule, _render_conditions_table, 
    render_tag, _render_mappings_table,
    render_variable, _render_used_in,
    render_extension
)

def _render_generic_value(value):
    """Helper to intelligently render a value, using st.json for dicts/lists and st.write for others."""
    if isinstance(value, (dict, list)):
        st.json(value, expanded=False)
    else:
        st.write(str(value))

def render_pretty_component_diff(item_before: Dict[str, Any], item_after: Dict[str, Any], component_type: str, uid_map: Dict[int, Dict[str, str]]):
    """
    Renders a structured, side-by-side diff for a component, dispatching to specialized
    renderers where available and highlighting changed values.
    """
    all_keys = sorted(list(set(item_before.keys()) | set(item_after.keys())))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Avant")
    with col2:
        st.subheader("Après")

    for key in all_keys:
        value_before = item_before.get(key)
        value_after = item_after.get(key)
        
        is_different = str(value_before) != str(value_after)
        
        # --- Renderer Dispatcher ---
        if component_type == "Load Rules" and key == "conditions" and (value_before or value_after):
            if is_different:
                with col1: st.warning(f"**{key}:**"); 
                if value_before: _render_conditions_table(value_before)
                with col2: st.warning(f"**{key}:**"); 
                if value_after: _render_conditions_table(value_after)
            else:
                 with st.expander(f"{key} (inchangé)"): _render_conditions_table(value_before)
            continue
        
        if component_type == "Tags" and key == "dataMappings" and (value_before or value_after):
            if is_different:
                with col1: st.warning(f"**{key}:**"); 
                if value_before: _render_mappings_table(value_before)
                with col2: st.warning(f"**{key}:**"); 
                if value_after: _render_mappings_table(value_after)
            else:
                 with st.expander(f"{key} (inchangé)"): _render_mappings_table(value_before)
            continue

        if component_type == "Variables" and key == "usedIn" and (value_before or value_after):
            if is_different:
                with col1: st.warning(f"**{key}:**"); 
                if value_before: _render_used_in(value_before, uid_map)
                with col2: st.warning(f"**{key}:**"); 
                if value_after: _render_used_in(value_after, uid_map)
            else:
                 with st.expander(f"{key} (inchangé)"): _render_used_in(value_before, uid_map)
            continue
        
        if component_type == "Extensions" and key == "code" and (value_before or value_after):
            if is_different:
                with col1:
                    st.warning(f"**{key}:**"); st.code(value_before, language="javascript")
                with col2:
                    st.warning(f"**{key}:**"); st.code(value_after, language="javascript")
            else:
                with st.expander(f"{key} (inchangé)"): st.code(value_before, language="javascript")
            continue
        # --- End Dispatcher ---

        # Generic rendering for all other keys
        if is_different:
            with col1:
                if value_before is not None:
                    st.warning(f"**{key}:**"); _render_generic_value(value_before)
            with col2:
                if value_after is not None:
                    st.warning(f"**{key}:**"); _render_generic_value(value_after)
        else:
            if isinstance(value_before, (dict, list)):
                 with st.expander(f"{key} (inchangé)"): _render_generic_value(value_before)
            elif value_before is not None:
                st.text(f"{key}: {str(value_before)} (inchangé)")


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
                        render_pretty_component_diff(item['before'], item['after'], display_name, uid_map)
