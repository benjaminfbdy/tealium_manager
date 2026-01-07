
import streamlit as st
import pandas as pd
from controllers.profile_controller import get_all_profiles
from utils.tealium_client import TealiumClient

def render_inventory_view():
    st.header("🔬 Inventaire des Composants")

    # 1. Profile Selection
    try:
        profiles = get_all_profiles()
        profile_options = {f"{p['account']}/{p['profile']}": p for p in profiles}
        selected_profiles_keys = st.multiselect(
            "Sélectionnez les profils à analyser",
            options=list(profile_options.keys()),
        )
    except FileNotFoundError:
        st.warning("Le fichier de configuration des profils n'a pas été trouvé. Veuillez d'abord configurer vos profils.")
        return
    except Exception as e:
        st.error(f"Une erreur est survenue lors du chargement des profils : {e}")
        return

    # 2. Keyword Input
    keywords_input = st.text_input(
        "Entrez des mots-clés à rechercher (séparés par des virgules)",
        help="Exemple: adobe analytics, at internet, facebook"
    )

    # 3. Crawl Button
    if st.button("Lancer l'inventaire"):
        if not selected_profiles_keys:
            st.warning("Veuillez sélectionner au moins un profil.")
        elif not keywords_input:
            st.warning("Veuillez entrer au moins un mot-clé.")
        else:
            keywords = [k.strip().lower() for k in keywords_input.split(',')]
            selected_profiles = [profile_options[key] for key in selected_profiles_keys]
            
            with st.spinner("Analyse des profils en cours..."):
                inventory_data = []
                progress_bar = st.progress(0)
                total_profiles = len(selected_profiles)

                for i, profile_config in enumerate(selected_profiles):
                    try:
                        client = TealiumClient(profile_config)
                        profile_details = f"{profile_config['account']}/{profile_config['profile']}"
                        
                        # Fetch latest version
                        revision_list = client.get_revisions()
                        if not revision_list:
                            st.warning(f"Aucune révision trouvée pour {profile_details}.")
                            continue
                        
                        latest_revision = revision_list[0] 
                        full_profile_data = client.get_profile(latest_revision['id'])

                        # Search for components
                        for keyword in keywords:
                            # Search in Tags
                            if 'tags' in full_profile_data:
                                for uid, tag in full_profile_data['tags'].items():
                                    if keyword in tag.get('name', '').lower():
                                        inventory_data.append({
                                            "Profil": profile_details,
                                            "Composant": "Tag",
                                            "Nom": tag.get('name'),
                                            "UID": uid,
                                            "Statut": tag.get('status'),
                                            "Type": tag.get('type')
                                        })
                            
                            # Search in Extensions
                            if 'extensions' in full_profile_data:
                                for uid, ext in full_profile_data['extensions'].items():
                                    if keyword in ext.get('name', '').lower():
                                        inventory_data.append({
                                            "Profil": profile_details,
                                            "Composant": "Extension",
                                            "Nom": ext.get('name'),
                                            "UID": uid,
                                            "Statut": ext.get('status'),
                                            "Scope": ext.get('scope')
                                        })

                    except Exception as e:
                        st.error(f"Erreur lors de l'analyse du profil {profile_config.get('account')}/{profile_config.get('profile')}: {e}")

                    progress_bar.progress((i + 1) / total_profiles)

            if inventory_data:
                st.success(f"{len(inventory_data)} composants trouvés !")
                df = pd.DataFrame(inventory_data)
                
                # Reorder columns for better readability
                df = df[["Profil", "Composant", "Nom", "UID", "Statut", "Type", "Scope"]]
                
                st.dataframe(df)
            else:
                st.info("Aucun composant correspondant aux mots-clés n'a été trouvé dans les profils sélectionnés.")

