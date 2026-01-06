import streamlit as st
from typing import Dict, List, Optional

def render_config_panel(
    is_authenticated: bool,
    all_configurations: List[Dict[str, str]],
    active_configuration_name: Optional[str] = None
) -> Dict[str, any]:
    """
    Renders the configuration panel UI for multi-account/profile management.
    Returns a dictionary with the action performed by the user and relevant data.
    """
    st.header("Configuration Tealium")
    result = {"action": None, "data": None}

    # --- Select Active Configuration ---
    config_names = [cfg["name"] for cfg in all_configurations]
    if not config_names:
        st.info("Aucune configuration sauvegardée. Veuillez en ajouter une nouvelle.")
        selected_config_name = None
    else:
        st.subheader("Sélectionner une Configuration Existante")
        selected_config_name = st.selectbox(
            "Choisir une configuration",
            options=config_names,
            index=config_names.index(active_configuration_name) if active_configuration_name in config_names else 0,
            key="select_config_dropdown"
        )

    selected_config_details = next(
        (cfg for cfg in all_configurations if cfg["name"] == selected_config_name),
        {"name": "", "account": "", "profile": "", "api_key": "", "email": "", "is_active": False}
    )

    st.markdown("---")

    # --- Edit/Save/Delete Selected Configuration ---
    if selected_config_name:
        st.subheader(f"Détails de la Configuration : {selected_config_name}")
        with st.form(f"edit_config_form_{selected_config_name}"):
            current_name = st.text_input("Nom de la Configuration", value=selected_config_details.get("name", ""), key="edit_name", disabled=True)
            account = st.text_input("Account", value=selected_config_details.get("account", ""), key="edit_account", help="Votre nom de compte Tealium (ex: 'mycompany')")
            profile = st.text_input("Profile", value=selected_config_details.get("profile", ""), key="edit_profile", help="Le nom du profil Tealium (ex: 'main_profile' ou 'dev_profile')")
            api_key = st.text_input("API Key", value=selected_config_details.get("api_key", ""), type="password", key="edit_api_key", help="Votre clé API Tealium iQ")
            email = st.text_input("Email", value=selected_config_details.get("email", ""), key="edit_email", help="L'adresse email associée à votre clé API")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.form_submit_button("Mettre à Jour et Tester"):
                    result["action"] = "update"
                    result["data"] = {
                        "name": current_name,
                        "account": account,
                        "profile": profile,
                        "api_key": api_key,
                        "email": email,
                        "is_active": selected_config_details["is_active"] # Keep current active status
                    }
            with col2:
                if st.form_submit_button("Définir comme Active"):
                    result["action"] = "set_active"
                    result["data"] = {"name": current_name}
            with col3:
                if st.form_submit_button("Supprimer", help="Supprimer cette configuration de la base de données"):
                    result["action"] = "delete"
                    result["data"] = {"name": current_name}
        
        if selected_config_details["is_active"]:
            st.success(f"'{selected_config_name}' est la configuration active.")
        elif selected_config_name:
            st.warning(f"'{selected_config_name}' n'est pas la configuration active.")
            
    st.markdown("---")

    # --- Add New Configuration ---
    st.subheader("Ajouter une Nouvelle Configuration")
    with st.form("add_new_config_form"):
        new_name = st.text_input("Nom de la Nouvelle Configuration", key="add_name", help="Nom unique pour identifier cette configuration")
        new_account = st.text_input("Account", key="add_account")
        new_profile = st.text_input("Profile", key="add_profile")
        new_api_key = st.text_input("API Key", type="password", key="add_api_key")
        new_email = st.text_input("Email", key="add_email")
        
        if st.form_submit_button("Ajouter et Tester"):
            if new_name and new_account and new_profile and new_api_key and new_email:
                result["action"] = "add_new"
                result["data"] = {
                    "name": new_name,
                    "account": new_account,
                    "profile": new_profile,
                    "api_key": new_api_key,
                    "email": new_email,
                    "is_active": False # New configs are not active by default
                }
            else:
                st.error("Tous les champs de la nouvelle configuration doivent être remplis.")

    st.markdown("---")

    # --- Global Connection Status (based on active config) ---
    st.subheader("Statut Global de la Connexion")
    if is_authenticated:
        st.success("Connexion à l'API Tealium établie avec succès via la configuration active ! 🎉")
    else:
        st.error("Échec de la connexion à l'API Tealium via la configuration active. 😢")
        st.warning("Veuillez vérifier les identifiants de la configuration active ou en sélectionner une autre.")

    return result
