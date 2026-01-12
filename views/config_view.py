import streamlit as st
from typing import Dict, List, Optional

def render_config_panel(
    is_authenticated: bool,
    all_configurations: List[Dict[str, str]],
    active_configuration_name: Optional[str] = None,
    global_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """
    Renders the configuration panel UI for multi-account/profile management.
    Returns a dictionary with the action performed by the user and relevant data.
    """
    st.header("Configuration Tealium")
    result = {"action": None, "data": None}
    
    # --- Global Credentials ---
    st.subheader("Identifiants Globaux")
    with st.expander("Gérer la clé API, l'email et le Proxy", expanded=not bool(global_credentials)):
        with st.form("global_creds_form"):
            st.write("Identifiants de l'API Tealium")
            api_key = st.text_input("Clé API Tealium", value=global_credentials.get("api_key", ""), type="password")
            email = st.text_input("Email Tealium", value=global_credentials.get("email", ""))
            
            st.markdown("---")
            st.write("Configuration du Proxy (optionnel)")
            proxy_user = st.text_input("Utilisateur Proxy", value=global_credentials.get("proxy_user", ""))
            proxy_password = st.text_input("Mot de passe Proxy", value=global_credentials.get("proxy_password", ""), type="password")

            if st.form_submit_button("Enregistrer les Paramètres Globaux"):
                result["action"] = "save_global"
                result["data"] = {
                    "api_key": api_key, 
                    "email": email,
                    "proxy_user": proxy_user,
                    "proxy_password": proxy_password
                }
    
    st.markdown("---")

    # --- Select Active Configuration ---
    config_names = [cfg["name"] for cfg in all_configurations]
    if not config_names:
        st.info("Aucune configuration de profil sauvegardée. Veuillez en ajouter une nouvelle.")
        selected_config_name = None
    else:
        st.subheader("Sélectionner un Profil Actif")
        selected_config_name = st.selectbox(
            "Choisir une configuration de profil",
            options=config_names,
            index=config_names.index(active_configuration_name) if active_configuration_name in config_names else 0,
            key="select_config_dropdown"
        )

    selected_config_details = next(
        (cfg for cfg in all_configurations if cfg["name"] == selected_config_name),
        None
    )
    
    st.markdown("---")

    # --- Edit/Save/Delete Selected Configuration ---
    if selected_config_details:
        st.subheader(f"Gérer le Profil : {selected_config_name}")
        with st.form(f"edit_config_form_{selected_config_name}"):
            current_name = st.text_input("Nom de la Configuration", value=selected_config_details.get("name", ""), disabled=True)
            account = st.text_input("Compte (Account)", value=selected_config_details.get("account", ""))
            profile = st.text_input("Profil (Profile)", value=selected_config_details.get("profile", ""))

            cols = st.columns(4)
            if cols[0].form_submit_button("Mettre à Jour"):
                result["action"] = "update"
                result["data"] = {"name": current_name, "account": account, "profile": profile}
            
            if cols[1].form_submit_button("Définir comme Actif"):
                result["action"] = "set_active"
                result["data"] = {"name": current_name}

            if cols[2].form_submit_button("📥 Télécharger"):
                result["action"] = "download"
                result["data"] = {"name": current_name}

            if cols[3].form_submit_button("Supprimer"):
                result["action"] = "delete"
                result["data"] = {"name": current_name}

            # Display download status message inside the form if available
            if 'download_status' in st.session_state and st.session_state.download_status['name'] == current_name:
                if st.session_state.download_status['success']:
                    st.success("✅ Téléchargement et mise en cache réussis !")
                else:
                    st.error("❌ Échec du téléchargement. Vérifiez les logs pour plus de détails.")
                # Clear the status so it doesn't show on the next rerun
                del st.session_state.download_status

    
    st.markdown("---")

    # --- Add New Configuration ---
    st.subheader("Ajouter un Nouveau Profil")
    with st.form("add_new_config_form"):
        new_name = st.text_input("Nom de la Configuration")
        new_account = st.text_input("Compte (Account)")
        new_profile = st.text_input("Profil (Profile)")
        
        if st.form_submit_button("Ajouter le Profil"):
            if new_name and new_account and new_profile:
                result["action"] = "add_new"
                result["data"] = {"name": new_name, "account": new_account, "profile": new_profile}
            else:
                st.error("Tous les champs doivent être remplis.")

    st.markdown("---")
    
    # --- Global Connection Status ---
    st.subheader("Statut de la Connexion")
    if not global_credentials or not global_credentials.get("api_key"):
        st.warning("Veuillez enregistrer vos identifiants globaux (clé API et email) pour tester la connexion.")
    elif not active_configuration_name:
        st.info("Veuillez ajouter et activer un profil pour tester la connexion.")
    elif is_authenticated:
        st.success("Connexion à l'API Tealium établie avec succès via la configuration active ! 🎉")
    else:
        st.error("Échec de la connexion à l'API Tealium via la configuration active. 😢 Vérifiez vos identifiants et la configuration du profil.")

    return result
