import streamlit as st
from typing import Dict, List, Optional
import pandas as pd

def _render_tealium_section(
    all_configurations: List[Dict[str, str]],
    active_configuration_name: Optional[str]
) -> Dict[str, any]:
    """Renders the UI for managing Tealium configurations."""
    result = {"action": None, "data": None}
    st.header("Configurations Tealium")

    # --- Select Active Configuration ---
    config_names = [cfg["name"] for cfg in all_configurations]
    if not config_names:
        st.info("Aucune configuration de profil Tealium sauvegardée. Veuillez en ajouter une ci-dessous.")
        selected_config_name = None
    else:
        st.subheader("Sélectionner un Profil Actif")
        try:
            index = config_names.index(active_configuration_name) if active_configuration_name in config_names else 0
        except ValueError:
            index = 0
        
        selected_config_name = st.selectbox(
            "Choisir une configuration de profil Tealium",
            options=config_names,
            index=index,
            key="select_tealium_config_dropdown"
        )

    selected_config_details = next((cfg for cfg in all_configurations if cfg["name"] == selected_config_name), None)
    
    # --- Edit/Save/Delete Selected Configuration ---
    if selected_config_details:
        with st.expander(f"Gérer le Profil : {selected_config_name}", expanded=True):
            with st.form(f"edit_config_form_{selected_config_name}"):
                current_name = st.text_input("Nom de la Configuration", value=selected_config_details.get("name", ""), disabled=True)
                account = st.text_input("Compte (Account)", value=selected_config_details.get("account", ""))
                profile = st.text_input("Profil (Profile)", value=selected_config_details.get("profile", ""))

                cols = st.columns(4)
                if cols[0].form_submit_button("Mettre à Jour"):
                    result = {"action": "update", "data": {"name": current_name, "account": account, "profile": profile}}
                if cols[1].form_submit_button("Définir comme Actif"):
                    result = {"action": "set_active", "data": {"name": current_name}}
                if cols[2].form_submit_button("📥 Télécharger"):
                    result = {"action": "download", "data": {"name": current_name}}
                if cols[3].form_submit_button("Supprimer"):
                    result = {"action": "delete", "data": {"name": current_name}}

                if 'download_status' in st.session_state and st.session_state.download_status['name'] == current_name:
                    if st.session_state.download_status['success']:
                        st.success("✅ Téléchargement et mise en cache réussis !")
                    else:
                        st.error("❌ Échec du téléchargement. Vérifiez les logs.")
                    del st.session_state.download_status

    # --- Add New Configuration ---
    with st.expander("Ajouter un Nouveau Profil Tealium"):
        with st.form("add_new_config_form"):
            new_name = st.text_input("Nom de la Configuration")
            new_account = st.text_input("Compte (Account)")
            new_profile = st.text_input("Profil (Profile)")
            
            if st.form_submit_button("Ajouter le Profil"):
                if new_name and new_account and new_profile:
                    result = {"action": "add_new", "data": {"name": new_name, "account": new_account, "profile": new_profile}}
                else:
                    st.error("Tous les champs doivent être remplis.")
    return result

def _render_adobe_section(
    all_adobe_configurations: List[Dict[str, str]],
    active_adobe_config_name: Optional[str],
    adobe_config_to_edit: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """Renders the UI for managing Adobe Analytics configurations."""
    from controllers.config_controller import get_available_adobe_secret_keys

    result = {"action": None, "data": None}
    st.header("Configurations Adobe Analytics")

    # --- Discovery Test Result ---
    if 'adobe_discovery_result' in st.session_state and st.session_state.adobe_discovery_result:
        with st.expander("Résultat du Test de Découverte Adobe", expanded=True):
            st.json(st.session_state['adobe_discovery_result'])
            if st.button("Fermer le résultat du test"):
                st.session_state['adobe_discovery_result'] = None
                st.rerun()

    # --- List Existing Configurations ---
    if not all_adobe_configurations and not adobe_config_to_edit:
        st.info("Aucune configuration Adobe Analytics sauvegardée. Veuillez en ajouter une ci-dessous.")

    for config in all_adobe_configurations:
        is_active = config.get('name') == active_adobe_config_name
        status = " (Actif)" if is_active else ""
        secret_key_used = config.get('secret_key_name', 'N/A')

        with st.container():
            st.subheader(f"Profil : {config.get('name')}{status}")
            columns = st.columns([2, 2, 1, 1, 1, 1])
            columns[0].text(f"Company ID: {config.get('global_company_id')}")
            columns[1].text(f"Jeu d'identifiants: {secret_key_used}")
            
            if not is_active:
                if columns[2].button("Activer", key=f"activate_adobe_{config['name']}"):
                    result = {"action": "set_active_adobe", "data": {"name": config['name']}}

            if columns[3].button("Éditer", key=f"edit_adobe_{config['name']}"):
                result = {"action": "edit_adobe", "data": {"name": config['name']}}

            if columns[4].button("Supprimer", key=f"delete_adobe_{config['name']}"):
                result = {"action": "delete_adobe", "data": {"name": config['name']}}
            
            if columns[5].button("Tester", key=f"test_adobe_{config['name']}"):
                if not is_active:
                    st.warning(f"Veuillez d'abord activer la configuration '{config['name']}' pour la tester.")
                else:
                    result = {"action": "test_adobe_discovery", "data": {}}
            st.divider()

    # --- Add or Edit Form ---
    is_editing = adobe_config_to_edit is not None
    form_title = f"Modifier la Configuration : {adobe_config_to_edit['name']}" if is_editing else "Ajouter une Nouvelle Configuration Adobe"
    
    with st.expander(form_title, expanded=is_editing or not all_adobe_configurations):
        form_key = f"adobe_edit_form_{adobe_config_to_edit['name']}" if is_editing else "add_new_adobe_config_form"
        
        with st.form(form_key):
            st.write("Entrez les détails de votre configuration Adobe (utilise l'authentification OAuth 2.0).")
            
            cfg = adobe_config_to_edit or {}

            name = st.text_input("Nom de la Configuration", value=cfg.get("name", ""))
            global_company_id = st.text_input("Global Company ID (ex: `banque0`, `bpce1`)", value=cfg.get("global_company_id", ""))

            # --- Selectbox for Secret Key ---
            available_secret_keys = get_available_adobe_secret_keys()
            selected_secret_key = None

            if not available_secret_keys:
                st.warning("Aucun jeu d'identifiants Adobe n'a été trouvé dans votre fichier secrets.toml. Veuillez le configurer.")
            else:
                try:
                    secret_key_index = available_secret_keys.index(cfg.get("secret_key_name")) if cfg.get("secret_key_name") in available_secret_keys else 0
                except ValueError:
                    secret_key_index = 0
                
                selected_secret_key = st.selectbox(
                    "Jeu d'identifiants à utiliser (défini dans secrets.toml)",
                    options=available_secret_keys,
                    index=secret_key_index
                )

            # --- Data to be saved ---
            data_to_save = {
                "name": name,
                "original_name": cfg.get("name") if is_editing else None,
                "auth_method": "oauth", # Hardcoded to oauth
                "global_company_id": global_company_id,
                "is_active": cfg.get("is_active", False),
                "secret_key_name": selected_secret_key
            }

            st.info(f"Les identifiants (Client ID, Secret) pour cette configuration seront lus depuis le jeu '{selected_secret_key}' de votre fichier secrets.toml.")

            # --- Form Buttons ---
            submit_cols = st.columns(2)
            if submit_cols[0].form_submit_button("Enregistrer"):
                if not all([name, global_company_id]):
                    st.error("Le Nom de la Configuration et le Global Company ID sont requis.")
                elif not selected_secret_key:
                     st.error("Veuillez sélectionner un jeu d'identifiants.")
                else:
                    result = {"action": "save_adobe_config", "data": data_to_save}
            
            if is_editing and submit_cols[1].form_submit_button("Annuler"):
                result = {"action": "cancel_edit_adobe", "data": None}

    return result

def _render_adobe_cache_section():
    """Renders the UI for managing the Adobe components cache."""
    st.header("Gestion du Cache des Composants Adobe")
    
    from utils.adobe_repo import get_adobe_components_cache_info
    from controllers.adobe_controller import get_or_refresh_components
    
    cached_items = get_adobe_components_cache_info()
    
    if not cached_items:
        st.info("Aucun composant Adobe n'est actuellement en cache.")
        return

    st.write("Les composants (dimensions, métriques, segments) sont mis en cache pour accélérer le chargement du dashboard. Vous pouvez forcer un rafraîchissement ici.")
    
    for item in cached_items:
        rsid = item['rsid']
        last_updated_str = pd.to_datetime(item['last_updated'], unit='s').strftime('%Y-%m-%d %H:%M:%S')
        
        cols = st.columns([3, 2, 1])
        cols[0].text(f"Report Suite (RSID): {rsid}")
        cols[1].text(f"Dernière mise à jour : {last_updated_str}")
        if cols[2].button("Rafraîchir", key=f"refresh_cache_{rsid}"):
            with st.spinner(f"Rafraîchissement des composants pour {rsid}..."):
                _, error_msg = get_or_refresh_components(rsid, force_refresh=True)
                if error_msg:
                    st.error(f"Erreur lors du rafraîchissement pour {rsid}: {error_msg}")
                else:
                    st.success(f"Cache pour {rsid} rafraîchi avec succès !")
                    # Rerun to show the new timestamp immediately
                    st.rerun()
    st.divider()

def render_config_panel(
    is_tealium_connected: bool,
    is_adobe_connected: bool,
    all_tealium_configs: List[Dict[str, str]],
    all_adobe_configs: List[Dict[str, str]],
    active_tealium_config_name: Optional[str],
    active_adobe_config_name: Optional[str],
    global_settings: Optional[Dict[str, str]],
    adobe_config_to_edit: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """
    Renders the main configuration panel UI.
    Returns a dictionary with the action performed by the user.
    """
    action_result = {"action": None, "data": None}
    
    # --- Global Credentials (for Tealium & Proxy) ---
    st.subheader("Paramètres Globaux (Tealium & Proxy)")
    with st.expander("Gérer les identifiants partagés", expanded=not bool(global_settings)):
        with st.form("global_creds_form"):
            st.write("Identifiants de l'API Tealium (utilisés pour tous les profils)")
            api_key = st.text_input("Clé API Tealium", value=global_settings.get("api_key", ""), type="password")
            email = st.text_input("Email Tealium", value=global_settings.get("email", ""))
            
            st.divider()
            st.write("Configuration du Proxy (optionnel)")
            proxy_user = st.text_input("Utilisateur Proxy", value=global_settings.get("proxy_user", ""))
            proxy_password = st.text_input("Mot de passe Proxy", value=global_settings.get("proxy_password", ""), type="password")

            if st.form_submit_button("Enregistrer les Paramètres Globaux"):
                action_result = {
                    "action": "save_global", 
                    "data": {
                        "api_key": api_key, "email": email,
                        "proxy_user": proxy_user, "proxy_password": proxy_password
                    }
                }

    st.divider()
    
    # --- Connection Status ---
    st.subheader("Statut des Connexions")
    col1, col2 = st.columns(2)
    with col1:
        if not active_tealium_config_name:
            st.info("Aucun profil Tealium actif.")
        elif is_tealium_connected:
            st.success("✅ Connexion Tealium OK")
        else:
            st.error("❌ Connexion Tealium échouée")
    with col2:
        if not active_adobe_config_name:
            st.info("Aucune configuration Adobe active.")
        elif is_adobe_connected:
            st.success("✅ Connexion Adobe OK")
        else:
            st.error("❌ Connexion Adobe échouée")

    st.divider()

    # --- Render Sections for Tealium and Adobe ---
    tealium_result = _render_tealium_section(all_tealium_configs, active_tealium_config_name)
    if tealium_result["action"]:
        action_result = tealium_result
    
    st.divider()

    adobe_result = _render_adobe_section(all_adobe_configs, active_adobe_config_name, adobe_config_to_edit)
    if adobe_result["action"]:
        action_result = adobe_result

    # --- Render Adobe Cache Management ---
    _render_adobe_cache_section()

    return action_result