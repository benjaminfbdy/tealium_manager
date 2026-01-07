import streamlit as st
import pandas as pd
import datetime
from controllers.config_controller import get_all_configurations
from database import get_cached_profile

def render_inventory_view():
    st.header("🔬 Inventaire des Composants")
    st.write("Cette fonctionnalité recherche des composants dans les données locales en cache. Assurez-vous d'avoir téléchargé les profils via la page 'Configuration'.")
    st.markdown("---")

    # 1. Profile Selection
    try:
        configurations = get_all_configurations()
        if not configurations:
            st.warning("Aucune configuration de profil n'a été trouvée. Veuillez en ajouter une via la page 'Configuration'.")
            return
            
        profile_options = {f"{p['account']}/{p['profile']} ({p['name']})": p['name'] for p in configurations}
        selected_profile_display_keys = st.multiselect(
            "Sélectionnez les profils à analyser",
            options=list(profile_options.keys()),
        )
        selected_config_names = [profile_options[key] for key in selected_profile_display_keys]

    except Exception as e:
        st.error(f"Une erreur est survenue lors du chargement des profils : {e}")
        return

    # Display cache status for selected profiles
    if selected_config_names:
        st.subheader("Statut du Cache des Profils Sélectionnés")
        for config_name in selected_config_names:
            _, timestamp = get_cached_profile(config_name)
            display_name = next((key for key, name in profile_options.items() if name == config_name), config_name)
            if timestamp:
                cache_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                st.success(f"✅ **{display_name}**: Mis en cache le {cache_time}")
            else:
                st.error(f"❌ **{display_name}**: Pas de données en cache. Veuillez le télécharger depuis la page 'Configuration'.")
        st.markdown("---")


    col1, col2 = st.columns(2)
    with col1:
        component_types = st.multiselect(
            "Types de composants",
            options=["Tags", "Extensions", "Load Rules", "Variables"],
            default=["Tags", "Extensions", "Load Rules", "Variables"]
        )
    with col2:
        keywords_input = st.text_input(
            "Mots-clés (séparés par des virgules, sensibles à la casse)",
            help="Exemple: adobe, facebook"
        )

    if st.button("Lancer l'inventaire"):
        if not selected_config_names:
            st.warning("Veuillez sélectionner au moins un profil.")
            return
        if not keywords_input:
            st.warning("Veuillez entrer au moins un mot-clé.")
            return
        if not component_types:
            st.warning("Veuillez sélectionner au moins un type de composant.")
            return

        keywords = [k.strip() for k in keywords_input.split(',')]
        
        inventory_data = []
        
        with st.spinner("Analyse des profils en cache..."):
            for config_name in selected_config_names:
                full_profile_data, timestamp = get_cached_profile(config_name)
                
                if not full_profile_data:
                    continue

                profile_details = next((key for key, name in profile_options.items() if name == config_name), config_name)

                for keyword in keywords:
                    if not keyword: continue
                    
                    search_logic = {
                        "Tags": "tags",
                        "Extensions": "extensions",
                        "Load Rules": "loadRules",
                        "Variables": "variables"
                    }

                    for comp_type_label, comp_type_key in search_logic.items():
                        if comp_type_label in component_types:
                            components = full_profile_data.get(comp_type_key)
                            items_to_search = []
                            
                            if isinstance(components, dict):
                                items_to_search = components.values()
                            elif isinstance(components, list):
                                items_to_search = components
                            
                            for item in items_to_search:
                                # Ensure item is a dict and has a name
                                if not isinstance(item, dict) or 'name' not in item:
                                    continue

                                item_name = item.get('name', '')
                                if keyword.lower() in item_name.lower():
                                    # UID can be 'id' or 'uid' depending on component type
                                    uid = item.get('id', item.get('uid', 'N/A'))
                                    entry = {"Profil": profile_details, "Composant": comp_type_label, "Nom": item_name, "UID": uid}
                                    if 'status' in item: entry['Statut'] = item.get('status')
                                    if 'type' in item: entry['Type'] = item.get('type')
                                    if 'scope' in item: entry['Scope'] = item.get('scope')
                                    inventory_data.append(entry)
        
        if inventory_data:
            st.success(f"{len(inventory_data)} composants trouvés !")
            df = pd.DataFrame(inventory_data)
            all_cols = ["Profil", "Composant", "Nom", "UID", "Statut", "Type", "Scope"]
            df_cols = [col for col in all_cols if col in df.columns]
            st.dataframe(df[df_cols])
        else:
            st.info("Aucun composant correspondant n'a été trouvé dans les profils en cache avec les critères fournis.")
