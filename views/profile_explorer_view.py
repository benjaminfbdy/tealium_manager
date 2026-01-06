import streamlit as st
from typing import Dict, List, Any
from utils.data_processing import resolve_uids_in_component

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
    st.markdown(f"**Version :** `{profile_data.get('version')}` | **Titre :** *{profile_data.get('versionTitle')}*")
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
                st.write(components)
            else:
                for component in components:
                    with st.container():
                        st.subheader(f"{display_name.rstrip('s')} : {component.get('name', component.get('alias', 'N/A'))}")
                        
                        resolved_component = resolve_uids_in_component(component, uid_map)

                        details_cols = st.columns(2)
                        col_index = 0
                        for field, value in resolved_component.items():
                            if value is None or value == [] or value == {} or field in ['id', 'name', 'alias']:
                                continue
                            
                            with details_cols[col_index % 2]:
                                st.markdown(f"**{field.replace('_', ' ').capitalize()}**")
                                if isinstance(value, (dict, list)):
                                    st.json(value, expanded=False)
                                else:
                                    st.write(str(value))
                            col_index += 1
                        st.markdown("---")

