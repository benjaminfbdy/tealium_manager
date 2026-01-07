import streamlit as st
from typing import Dict, List, Any
from utils.data_processing import resolve_uids_in_component, format_tealium_timestamp
from views.component_renderers import render_load_rule, render_tag, render_variable, render_extension

def render_profile_explorer(data_package: Dict[str, Any]):
    """
    Renders the UI for exploring Tealium iQ profile components using a tabbed layout.
    """
    profile_data = data_package.get("profile", {})
    uid_map = data_package.get("uid_map", {})

    if not profile_data:
        st.warning("Aucune donnée de profil à afficher.")
        return
        
    st.header(f"Explorateur de Profil : {profile_data.get('account')} / {profile_data.get('profile')}")
    
    version_ts = profile_data.get('version', '')
    formatted_ts = format_tealium_timestamp(version_ts)
    st.markdown(f"**Version :** `{version_ts}` ({formatted_ts}) | **Titre :** *{profile_data.get('versionTitle')}*")
    st.markdown("---")

    component_map = {
        "Variables": "variables",
        "Tags": "tags",
        "Load Rules": "loadRules",
        "Extensions": "extensions",
        "Events": "events",
        "Version IDs": "versionIds"
    }

    tab_names = [f"{name} ({len(profile_data.get(key, []))})" for name, key in component_map.items()]
    tabs = st.tabs(tab_names)

    for i, (display_name, key) in enumerate(component_map.items()):
        with tabs[i]:
            components = profile_data.get(key)
            if not components:
                st.info(f"Aucun(e) {display_name} trouvé(e) pour ce profil.")
                continue

            if key == "versionIds": # Special handling for simple list
                versions_data = []
                for v_id in components:
                    versions_data.append({"Version ID": v_id, "Date (Heure de Paris)": format_tealium_timestamp(v_id)})
                st.dataframe(versions_data, use_container_width=True)
            else:
                for component in components:
                    component_title = component.get('name', component.get('alias', 'N/A'))
                    with st.expander(f"**{component_title}**"):
                        
                        # --- Dispatcher for custom renderers ---
                        if display_name == "Load Rules":
                            render_load_rule(component)
                        elif display_name == "Tags":
                            render_tag(component, uid_map)
                        elif display_name == "Variables":
                            render_variable(component, uid_map)
                        elif display_name == "Extensions":
                            render_extension(component)
                        else:
                            # Generic fallback renderer
                            resolved_component = resolve_uids_in_component(component, uid_map)
                            details_cols = st.columns(2)
                            col_index = 0
                            for field, value in resolved_component.items():
                                if value is None or value == [] or value == {} or field in ['id', 'name', 'alias', 'notes']:
                                    continue
                                
                                with details_cols[col_index % 2]:
                                    st.markdown(f"**{field.replace('_', ' ').capitalize()}**")
                                    if isinstance(value, (dict, list)):
                                        st.json(value, expanded=False)
                                    else:
                                        st.write(str(value))
                                col_index += 1
