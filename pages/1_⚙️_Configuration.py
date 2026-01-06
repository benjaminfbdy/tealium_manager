import streamlit as st
import database
import security
from tealium_api.client import TealiumClient
import asyncio
import pandas as pd
import json # Added to ensure json is imported for json.dumps


# --- Page Configuration and Styling (Removed set_page_config) ---



st.title("⚙️ Configuration")

# --- Section Connexion ---
st.subheader("1. Connexion API Tealium")

email = st.text_input("Email utilisateur", value=database.load_setting("email") or "")
api_key_input = st.text_input("Clé API (Tealium iQ)", type="password")

if st.button("Sauvegarder et Tester la connexion"):
    if email and api_key_input:
        try:
            # Test de connexion
            client = TealiumClient(email, api_key_input)
            # On tente un appel simple pour vérifier
            accounts = client.get_accounts()
            
            if accounts:
                st.success(f"Connexion réussie ! {len(accounts)} comptes trouvés.")
                
                # Sauvegarde
                database.save_setting("email", email)
                encrypted_key = security.encrypt_data(api_key_input, security.load_key())
                database.save_setting("encrypted_api_key", encrypted_key)
                
            else:
                st.error("Connexion établie mais aucun compte trouvé.")
            st.session_state.client = client # Set client even if no accounts found
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")
    else:
        st.warning("Veuillez remplir l'email et la clé API.")

# --- Section Profils ---
st.subheader("2. Sélection des Profils")

if 'client' in st.session_state and st.session_state.client:
    client = st.session_state.client
    
    if st.button("📥 Récupérer la liste des comptes et profils"):
        with st.spinner("Récupération des profils en cours..."):
            try:
                accounts = client.get_accounts()
                profiles_data = []
                
                progress_bar = st.progress(0)
                if not accounts:
                    st.warning("Aucun compte trouvé via l'API. Vous pouvez ajouter des comptes/profils manuellement ci-dessous.")
                else:
                    for i, account in enumerate(accounts):
                        profiles = client.get_profiles(account)
                        for profile in profiles:
                            # Par défaut non sélectionné (0)
                            profiles_data.append((account, profile, 0))
                        progress_bar.progress((i + 1) / len(accounts))
                    
                    database.save_profiles(profiles_data)
                    st.success("Liste des profils mise à jour !")
            except Exception as e:
                st.error(f"Erreur lors de la récupération : {e}")

    st.markdown("---")
    st.subheader("Ajouter un Compte/Profil manuellement")
    manual_account = st.text_input("Nom du Compte (manuel)")
    manual_profile = st.text_input("Nom du Profil (manuel)")

    if st.button("➕ Ajouter ce Compte/Profil Manuellement"):
        if manual_account and manual_profile:
            try:
                # Vérifier si la combinaison existe déjà
                existing_profiles = database.load_profiles_by_account(manual_account)
                found = False
                for acc, prof, sel in existing_profiles:
                    if acc == manual_account and prof == manual_profile:
                        found = True
                        break
                
                if found:
                    st.info(f"Le profil '{manual_profile}' pour le compte '{manual_account}' existe déjà.")
                else:
                    # Ajouter le profil, marqué comme non sélectionné par défaut
                    database.save_profiles([(manual_account, manual_profile, 0)])
                    st.success(f"Compte '{manual_account}' et profil '{manual_profile}' ajoutés manuellement. Sélectionnez-le ci-dessous.")
            except Exception as e:
                st.error(f"Erreur lors de l'ajout manuel : {e}")
        else:
            st.warning("Veuillez saisir le nom du compte ET le nom du profil.")

    st.markdown("---") # Add a separator

    # --- Affichage et sélection des profils enregistrés ---
    st.subheader("3. Gérer les profils enregistrés")
    
    # Always try to load all profiles from DB
    conn = database.create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_name, profile_name, is_selected FROM profiles ORDER BY account_name, profile_name")
    all_profiles_db = cursor.fetchall()
    conn.close()

    if not all_profiles_db:
        st.info("Aucun compte ni profil enregistré. Utilisez les sections ci-dessus pour les ajouter.")
    else:
        st.write("Cochez les profils à utiliser et/ou à supprimer :")

        col_select, col_delete, col_account, col_profile = st.columns([0.1, 0.1, 0.4, 0.4])
        col_account.write("**Compte**")
        col_profile.write("**Profil**")
        col_select.write("**Actif**")
        col_delete.write("**Suppr.**")

        profiles_for_save = []
        profiles_to_delete = []

        for i, (account, profile, is_selected) in enumerate(all_profiles_db):
            col_select_val, col_delete_val, col_account_name_val, col_profile_name_val = st.columns([0.1, 0.1, 0.4, 0.4])
            
            # Checkbox for selection (is_selected)
            current_selection = col_select_val.checkbox("", value=bool(is_selected), key=f"select_{account}_{profile}_{i}")
            profiles_for_save.append((account, profile, 1 if current_selection else 0))

            # Checkbox for deletion
            if col_delete_val.checkbox("", key=f"delete_{account}_{profile}_{i}"):
                profiles_to_delete.append((account, profile))
            
            col_account_name_val.write(account)
            col_profile_name_val.write(profile)

        # Save selections button
        st.markdown("---") # Separator before save/delete buttons
        if st.button("Enregistrer les sélections", key="save_final_selections_button"):
            database.save_profiles(profiles_for_save)
            st.success("Sélections de profils enregistrées.")
            st.rerun()

        # Delete button
        if profiles_to_delete:
            st.warning(f"Confirmez-vous la suppression de {len(profiles_to_delete)} profil(s) sélectionné(s) ?")
            if st.button("Confirmer la suppression", key="confirm_deletion_final_button"):
                database.delete_profiles(profiles_to_delete)
                st.success(f"{len(profiles_to_delete)} profil(s) supprimé(s).")
                st.rerun()

    st.markdown("---") # Add a separator

    # --- Section Mise en cache des révisions ---
    st.subheader("4. Mise en cache des révisions")
    
    if st.button("🚀 Lancer la mise en cache des révisions des profils sélectionnés"):
        if 'client' not in st.session_state or st.session_state.client is None:
            st.error("Veuillez d'abord vous connecter à l'API Tealium.")
            st.stop()
        
        client = st.session_state.client
        selected_profiles = database.load_all_selected_profiles()
        
        if not selected_profiles:
            st.warning("Aucun profil sélectionné pour la mise en cache. Veuillez sélectionner des profils ci-dessus.")
            st.stop()

        st.info(f"Début de la mise en cache pour {len(selected_profiles)} profil(s)...")
        overall_progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_revisions_cached = 0
        total_profiles_processed = 0

        for idx, (account, profile) in enumerate(selected_profiles):
            status_text.text(f"Traitement du profil : {account}/{profile} ({idx+1}/{len(selected_profiles)})")
            
            try:
                # Get already cached revision IDs for this profile
                cached_revision_ids = database.get_cached_revision_ids(account, profile)
                
                # Fetch all revisions from Tealium API
                all_revisions = client.get_revisions(account, profile)
                
                if not all_revisions:
                    st.warning(f"Aucune révision trouvée pour {account}/{profile}.")
                    continue

                new_revisions_to_cache_count = 0
                revisions_to_save_data = []

                # Filter for new revisions and fetch details
                for rev_data in all_revisions:
                    # Check if rev_data is a dict (expected) or a string (actual based on error)
                    if isinstance(rev_data, dict):
                        rev_id = rev_data.get('revision_id')
                    else: # Assume it's a string, which is the revision_id
                        rev_id = rev_data
                    if rev_id and rev_id not in cached_revision_ids:
                        new_revisions_to_cache_count += 1
                        st.text(f"  - Récupération des détails pour la révision {rev_id}...")
                        rev_metadata = client.get_revision_details(account, profile, rev_id)
                        rev_configuration = client.get_revision_configuration(account, profile, rev_id)
                        
                        if rev_metadata and 'error' not in rev_metadata and rev_configuration and 'error' not in rev_configuration:
                            combined_details = {**rev_metadata, **rev_configuration}
                            revisions_to_save_data.append((rev_id, account, profile, json.dumps(combined_details)))
                            total_revisions_cached += 1
                        else:
                            error_msg = f"Erreur lors de la récupération des détails/configuration de la révision {rev_id} pour {account}/{profile}. "
                            if 'error' in rev_metadata: error_msg += f"Métadonnées: {rev_metadata['error']}. "
                            if 'error' in rev_configuration: error_msg += f"Configuration: {rev_configuration['error']}. "
                            st.error(error_msg)
                
                if revisions_to_save_data:
                    database.save_revisions_details(revisions_to_save_data)
                    st.success(f"{new_revisions_to_cache_count} nouvelles révisions mises en cache pour {account}/{profile}.")
                else:
                    st.info(f"Aucune nouvelle révision à mettre en cache pour {account}/{profile} (ou toutes déjà en cache).")
            
            except Exception as e:
                st.error(f"Erreur lors de la mise en cache pour {account}/{profile}: {e}")
            
            total_profiles_processed += 1
            overall_progress_bar.progress((total_profiles_processed / len(selected_profiles)))

        overall_progress_bar.empty()
        status_text.empty()
        st.success(f"Mise en cache terminée ! Total de {total_revisions_cached} révisions nouvellement mises en cache.")
        st.balloons()
    

else:
    st.info("Connectez-vous d'abord ci-dessus.")