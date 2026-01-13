import streamlit as st
from typing import Dict, List, Optional

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
    active_adobe_config_name: Optional[str]
) -> Dict[str, any]:
    """Renders the UI for managing Adobe Analytics configurations."""
    result = {"action": None, "data": None}
    st.header("Configurations Adobe Analytics")

    if not all_adobe_configurations:
        st.info("Aucune configuration Adobe Analytics sauvegardée. Veuillez en ajouter une ci-dessous.")

    for config in all_adobe_configurations:
        is_active = config.get('name') == active_adobe_config_name
        status = " (Actif)" if is_active else ""
        auth_method_display = "JWT" if config.get('auth_method') == 'jwt' else "Token Manuel"
        with st.container():
            st.subheader(f"Profil : {config.get('name')}{status}")
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            col1.text(f"Company ID: {config.get('global_company_id')}")
            col2.text(f"Méthode d'auth: {auth_method_display}")
            
            if not is_active:
                if col3.button("Définir comme Actif", key=f"activate_adobe_{config['name']}"):
                    result = {"action": "set_active_adobe", "data": {"name": config['name']}}

            if col4.button("Supprimer", key=f"delete_adobe_{config['name']}"):
                result = {"action": "delete_adobe", "data": {"name": config['name']}}
            st.divider()

    with st.expander("Ajouter/Modifier une Configuration Adobe"):
        with st.form("add_new_adobe_config_form"):
            st.write("Entrez les détails de votre projet Adobe Developer Console.")
            
            name = st.text_input("Nom de la Configuration (ex: 'Mon Projet EMEA')")
            auth_method = st.radio(
                "Méthode d'authentification",
                options=['jwt', 'manual'],
                format_func=lambda x: "JWT (Service Account)" if x == 'jwt' else "Token Manuel",
                horizontal=True
            )
            
            api_key = st.text_input("Clé API (Client ID)")
            global_company_id = st.text_input("Global Company ID")

            data_to_save = {
                "name": name,
                "auth_method": auth_method,
                "api_key": api_key,
                "global_company_id": global_company_id,
                "is_active": False # Default value
            }

            if auth_method == 'jwt':
                st.info("Pour l'authentification JWT, tous les champs suivants sont requis.")
                data_to_save["client_secret"] = st.text_input("Client Secret", type="password")
                data_to_save["technical_account_id"] = st.text_input("Technical account ID")
                data_to_save["organization_id"] = st.text_input("Organization ID")
                data_to_save["private_key"] = st.text_area("Clé Privée (contenu du fichier .key)")
            
            else: # manual
                st.info("Collez un 'Access Token' valide généré depuis la console Adobe Developer.")
                data_to_save["manual_access_token"] = st.text_area("Access Token Manuel")

            if st.form_submit_button("Enregistrer la Configuration Adobe"):
                # Basic validation
                if not all([name, api_key, global_company_id]):
                    st.error("Le nom, l'API Key et le Global Company ID sont toujours requis.")
                else:
                    result = {"action": "add_new_adobe", "data": data_to_save}
                    
    return result

def render_config_panel(
    is_tealium_connected: bool,
    is_adobe_connected: bool,
    all_tealium_configs: List[Dict[str, str]],
    all_adobe_configs: List[Dict[str, str]],
    active_tealium_config_name: Optional[str],
    active_adobe_config_name: Optional[str],
    global_settings: Optional[Dict[str, str]]
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

    adobe_result = _render_adobe_section(all_adobe_configs, active_adobe_config_name)
    if adobe_result["action"]:
        action_result = adobe_result

    return action_result

