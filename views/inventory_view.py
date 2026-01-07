
import streamlit as st
import pandas as pd
from controllers.config_controller import get_all_configurations
from database import get_cached_profile

def render_inventory_view():
    st.header("🔬 Inventaire des Composants")

    # 1. Profile Selection
    try:
        configurations = get_all_configurations()
        if not configurations:
            st.warning("Aucune configuration de profil n'a été trouvée. Veuillez en ajouter via la page 'Configuration'.")
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

    col1, col2 = st.columns(2)
    with col1:
        component_types = st.multiselect(
            "Types de composants",
            options=["Tags", "Extensions", "Load Rules", "Variables"],
            default=["Tags", "Extensions"]
        )
    with col2:
        keywords_input = st.text_input(
            "Mots-clés (séparés par des virgules)",
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

        keywords = [k.strip().lower() for k in keywords_input.split(',')]
        
        inventory_data = []
        profiles_to_download = []
        progress_bar = st.progress(0)
        total_steps = len(selected_config_names)
        
        with st.spinner("Analyse des profils..."):
            for i, config_name in enumerate(selected_config_names):
                full_profile_data = get_cached_profile(config_name)
                
                if not full_profile_data:
                    profiles_to_download.append(config_name)
                    continue

                # Find the display key for the current config name to show in the table
                profile_details = next((key for key, name in profile_options.items() if name == config_name), config_name)

                for keyword in keywords:
                    # Safely search in Tags
                    if "Tags" in component_types:
                        for uid, item in full_profile_data.get('tags', {}).items():
                            if keyword in item.get('name', '').lower():
                                inventory_data.append({"Profil": profile_details, "Composant": "Tag", "Nom": item.get('name'), "UID": uid, "Statut": item.get('status'), "Type": item.get('type')})
                    # Safely search in Extensions
                    if "Extensions" in component_types:
                        for uid, item in full_profile_data.get('extensions', {}).items():
                            if keyword in item.get('name', '').lower():
                                inventory_data.append({"Profil": profile_details, "Composant": "Extension", "Nom": item.get('name'), "UID": uid, "Statut": item.get('status'), "Scope": item.get('scope')})
                    # Safely search in Load Rules
                    if "Load Rules" in component_types:
                        for uid, item in full_profile_data.get('loadRules', {}).items():
                            if keyword in item.get('name', '').lower():
                                inventory_data.append({"Profil": profile_details, "Composant": "Load Rule", "Nom": item.get('name'), "UID": uid, "Statut": item.get('status')})
                    # Safely search in Variables
                    if "Variables" in component_types:
                        for uid, item in full_profile_data.get('variables', {}).items():
                            if keyword in item.get('name', '').lower():
                                inventory_data.append({"Profil": profile_details, "Composant": "Variable", "Nom": item.get('name'), "UID": uid, "Type": item.get('type')})
                
                progress_bar.progress((i + 1) / total_steps)

        if profiles_to_download:
            st.warning("Certains profils n'ont pas de données en cache. Veuillez les télécharger depuis la page 'Configuration'.")
            for name in profiles_to_download:
                st.write(f"- {name}")

        if inventory_data:
            st.success(f"{len(inventory_data)} composants trouvés !")
            df = pd.DataFrame(inventory_data)
            all_cols = ["Profil", "Composant", "Nom", "UID", "Statut", "Type", "Scope"]
            df_cols = [col for col in all_cols if col in df.columns]
            st.dataframe(df[df_cols])
        else:
            st.info("Aucun composant correspondant n'a été trouvé dans les profils analysés.")

