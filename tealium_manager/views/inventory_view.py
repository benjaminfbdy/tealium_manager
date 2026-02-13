import streamlit as st
import pandas as pd
import datetime
import json
from controllers.config_controller import get_all_configurations
from utils.tealium_repo import get_cached_profile
from utils.settings import load_inventory_columns, save_inventory_columns

def render_inventory_view():
    st.header("🔬 Inventaire des Composants")
    st.write("Cette fonctionnalité recherche des composants dans les données locales en cache. Assurez-vous d'avoir téléchargé les profils via la page 'Configuration'.")
    st.markdown("---")

    # --- Setup and Profile Selection ---
    try:
        configurations = get_all_configurations()
        if not configurations:
            st.warning("Aucune configuration de profil n'a été trouvée. Veuillez en ajouter une via la page 'Configuration'.")
            return
        
        profile_options = {f"{p['account']}/{p['profile']} ({p['name']})": p['name'] for p in configurations}
        
        # --- Bulk Selection Logic ---
        col_sel1, col_sel2 = st.columns([3, 1])
        
        # Initialize session state for the multiselect widget if not present
        if "inventory_selected_profiles" not in st.session_state:
            st.session_state.inventory_selected_profiles = []

        with col_sel2:
            st.write("") # Spacer to align with input
            st.write("")
            if st.button("Tout sélectionner", use_container_width=True):
                st.session_state.inventory_selected_profiles = list(profile_options.keys())
                st.rerun()
            if st.button("Tout désélectionner", use_container_width=True):
                st.session_state.inventory_selected_profiles = []
                st.rerun()

        with col_sel1:
            selected_profile_display_keys = st.multiselect(
                "Sélectionnez les profils à analyser", 
                options=list(profile_options.keys()),
                key="inventory_selected_profiles"
            )
            
        selected_config_names = [profile_options[key] for key in selected_profile_display_keys]
    except Exception as e:
        st.error(f"Une erreur est survenue lors du chargement des profils : {e}")
        return

    # --- Display Cache Status ---
    if selected_config_names:
        st.subheader("Statut du Cache des Profils Sélectionnés")
        for config_name in selected_config_names:
            _, timestamp = get_cached_profile(config_name)
            display_name = next((key for key, name in profile_options.items() if name == config_name), config_name)
            if timestamp:
                st.success(f"✅ **{display_name}**: Mis en cache le {datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                st.error(f"❌ **{display_name}**: Pas de données en cache. Veuillez le télécharger.")
        st.markdown("---")

    # --- Search Inputs ---
    col1, col2 = st.columns(2)
    component_types = col1.multiselect("Types de composants", options=["Tags", "Extensions", "Load Rules", "Variables"], default=["Tags", "Extensions", "Load Rules", "Variables"])
    keywords_input = col2.text_input("Mots-clés (optionnel)", help="Laissez vide pour tout récupérer (mode Crawler). Séparez par des virgules pour filtrer.")

    # --- Search Execution ---
    if st.button("Lancer l'inventaire"):
        if not selected_config_names or not component_types:
            st.warning("Veuillez sélectionner au moins un profil et un type de composant.")
            return

        keywords = [k.strip().lower() for k in keywords_input.split(',') if k.strip()]
        inventory_data = []
        
        with st.spinner("Analyse des profils en cache..."):
            # --- Data Gathering ---
            for config_name in selected_config_names:
                full_profile_data, _ = get_cached_profile(config_name)
                if not full_profile_data: continue
                profile_details = next((key for key, name in profile_options.items() if name == config_name), config_name)
                
                search_logic = {"Tags": "tags", "Extensions": "extensions", "Load Rules": "loadRules", "Variables": "variables"}
                for comp_type_label, comp_type_key in search_logic.items():
                    if comp_type_label in component_types:
                        components = full_profile_data.get(comp_type_key) or []
                        items_to_search = components.values() if isinstance(components, dict) else components
                        
                        for item in items_to_search:
                            if isinstance(item, dict) and 'name' in item:
                                match = False
                                # If no keywords, we match everything (Crawler mode)
                                if not keywords:
                                    match = True
                                else:
                                    for keyword in keywords:
                                        if keyword in item['name'].lower():
                                            match = True
                                            break
                                
                                if match:
                                    entry = item.copy() # Start with all raw data
                                    entry['Profil'] = profile_details
                                    entry['Type de Composant'] = comp_type_label
                                    inventory_data.append(entry)
        
        # --- Store results in session state to persist across reruns for column selection ---
        st.session_state['inventory_results'] = inventory_data

    # --- Results Display ---
    if 'inventory_results' in st.session_state and st.session_state.inventory_results:
        results = st.session_state.inventory_results
        st.success(f"{len(results)} composants trouvés !")

        # --- Column Selection ---
        all_possible_columns = set(['Profil', 'Type de Composant', 'name'])
        for item in results:
            all_possible_columns.update(item.keys())
        
        default_cols = ['Profil', 'Type de Composant', 'name', 'id', 'status', 'scope', 'variable', 'type']
        
        # Ensure default cols exist in the possible columns
        valid_default_cols = [col for col in default_cols if col in all_possible_columns]
        
        # Load saved preferences or use defaults
        saved_columns = load_inventory_columns(valid_default_cols)
        # Ensure saved columns are still valid for the current result set
        valid_saved_columns = [col for col in saved_columns if col in all_possible_columns]

        with st.expander("Gérer les colonnes affichées"):
            selected_columns = st.multiselect(
                "Choisissez les colonnes",
                options=sorted(list(all_possible_columns)),
                default=valid_saved_columns
            )
            if selected_columns != valid_saved_columns:
                save_inventory_columns(selected_columns)
                # No rerun needed, just rebuild the dataframe below

        # --- DataFrame Creation and Display ---
        display_data = []
        for item in results:
            row = {}
            for col in selected_columns:
                value = item.get(col)
                # Convert complex types to JSON string for display in a dataframe
                if isinstance(value, (dict, list)):
                    row[col] = json.dumps(value)
                else:
                    row[col] = value
            display_data.append(row)
        
        if display_data:
            df = pd.DataFrame(display_data)
            st.dataframe(df)
            
            # --- CSV Export ---
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger les résultats en CSV",
                data=csv,
                file_name=f"tealium_inventory_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key='download-csv'
            )
        else:
            st.info("Sélectionnez des colonnes pour afficher les résultats.")

    elif 'inventory_results' in st.session_state:
        st.info("Aucun composant correspondant n'a été trouvé dans les profils en cache avec les critères fournis.")
