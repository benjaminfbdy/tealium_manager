import streamlit as st
from views.component_renderers import setup_page
import pandas as pd
import datetime
import json
from utils.tealium_repo import get_cached_profile
from utils.settings import load_inventory_columns, save_inventory_columns

def render_inventory_view():
    setup_page()
    st.header("🔬 Inventaire des Composants Tealium")
    st.write("Cette fonctionnalité recherche des composants dans les données locales en cache. Assurez-vous d'avoir téléchargé les profils via la page 'Configuration Tealium'.")
    st.markdown("---")

    # --- Setup and Profile Selection ---
    try:
        profiles_from_secrets = st.secrets.get("tealium_profiles", {})
        if not profiles_from_secrets:
            st.warning("Aucune configuration de profil Tealium n'a été trouvée dans votre `secrets.toml`.")
            st.page_link("pages/1_Config_Tealium.py", label="Aller à la Configuration", icon="⚙️")
            st.stop()
        
        profile_options = {name: f"{config['account']}/{config['profile']} ({name})" for name, config in profiles_from_secrets.items()}
        
        selected_config_name = st.selectbox(
            "Sélectionnez le profil à analyser", 
            options=list(profile_options.keys()),
            format_func=lambda name: profile_options[name]
        )
            
    except Exception as e:
        st.error(f"Une erreur est survenue lors du chargement des profils depuis `secrets.toml`: {e}")
        return
    
    # --- Check Cache Status and Proceed ---
    if not selected_config_name:
        st.info("Veuillez sélectionner un profil pour commencer.")
        return

    full_profile_data, timestamp = get_cached_profile(selected_config_name)

    if not full_profile_data:
        st.error(f"Le profil '{profile_options[selected_config_name]}' n'est pas en cache. Veuillez le mettre à jour.")
        st.page_link("pages/1_Config_Tealium.py", label="Aller à la page de Configuration Tealium", icon="⚙️")
        st.stop()

    st.success(f"✅ Profil '{profile_options[selected_config_name]}' chargé depuis le cache (dernière mise à jour : {datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')})")
    st.markdown("---")

    # --- Search Inputs ---
    col1, col2 = st.columns(2)
    component_types = col1.multiselect("Types de composants", options=["Tags", "Extensions", "Load Rules", "Variables"], default=["Tags", "Extensions", "Load Rules", "Variables"])
    keywords_input = col2.text_input("Mots-clés (optionnel)", help="Laissez vide pour tout récupérer (mode Crawler). Séparez par des virgules pour filtrer.")

    # --- Search Execution ---
    if st.button("Lancer l'inventaire"):
        if not component_types:
            st.warning("Veuillez sélectionner au moins un type de composant.")
            return

        keywords = [k.strip().lower() for k in keywords_input.split(',') if k.strip()]
        inventory_data = []
        
        with st.spinner("Analyse du profil en cache..."):
            profile_display_name = profile_options[selected_config_name]
            
            search_logic = {"Tags": "tags", "Extensions": "extensions", "Load Rules": "loadRules", "Variables": "variables"}
            for comp_type_label, comp_type_key in search_logic.items():
                if comp_type_label in component_types:
                    components = full_profile_data.get(comp_type_key) or []
                    items_to_search = components.values() if isinstance(components, dict) else components
                    
                    for item in items_to_search:
                        if isinstance(item, dict) and 'name' in item:
                            match = False
                            if not keywords:
                                match = True
                            else:
                                for keyword in keywords:
                                    if keyword in item['name'].lower():
                                        match = True
                                        break
                            
                            if match:
                                entry = item.copy()
                                entry['Profil'] = profile_display_name
                                entry['Type de Composant'] = comp_type_label
                                inventory_data.append(entry)
        
        st.session_state['inventory_results'] = inventory_data

    # --- Results Display ---
    if 'inventory_results' in st.session_state and st.session_state.inventory_results:
        results = st.session_state.inventory_results
        st.success(f"{len(results)} composants trouvés !")

        all_possible_columns = set(['Profil', 'Type de Composant', 'name'])
        for item in results:
            all_possible_columns.update(item.keys())
        
        default_cols = ['Profil', 'Type de Composant', 'name', 'id', 'status', 'scope', 'variable', 'type']
        valid_default_cols = [col for col in default_cols if col in all_possible_columns]
        
        saved_columns = load_inventory_columns(valid_default_cols)
        valid_saved_columns = [col for col in saved_columns if col in all_possible_columns]

        with st.expander("Gérer les colonnes affichées"):
            selected_columns = st.multiselect(
                "Choisissez les colonnes",
                options=sorted(list(all_possible_columns)),
                default=valid_saved_columns
            )
            if selected_columns != valid_saved_columns:
                save_inventory_columns(selected_columns)

        display_data = []
        for item in results:
            row = {}
            for col in selected_columns:
                value = item.get(col)
                if isinstance(value, (dict, list)):
                    row[col] = json.dumps(value)
                else:
                    row[col] = value
            display_data.append(row)
        
        if display_data:
            df = pd.DataFrame(display_data)
            st.dataframe(df)
            
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

# Since this is now a page, we call the render function directly
if __name__ == "__main__":
    render_inventory_view()
