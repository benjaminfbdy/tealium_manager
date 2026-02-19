import streamlit as st
from views.component_renderers import setup_page
from controllers.config_controller import handle_download_profile, get_database_status

# --- Page Configuration ---
setup_page()

st.title("⚙️ Configuration Tealium")

# --- Initialize Session State ---
if 'active_tealium_config' not in st.session_state:
    st.session_state.active_tealium_config = None

# --- Helper Functions ---
def set_active_tealium(profile_name, profile_config):
    """Sets the selected Tealium profile as active in the session state."""
    # Merge profile-specific config with global credentials
    full_config = st.secrets.global_credentials.to_dict()
    full_config.update(profile_config)
    st.session_state.active_tealium_config = full_config
    st.session_state.active_tealium_profile_name = profile_name
    st.success(f"Profil Tealium '{profile_name}' activé pour cette session.")

# --- Load Configurations from secrets.toml ---
try:
    tealium_profiles = st.secrets.tealium_profiles.to_dict()
    global_creds = st.secrets.global_credentials
    if not all([global_creds.get("tealium_api_username"), global_creds.get("tealium_api_key")]):
        st.error("Erreur : Les identifiants globaux `tealium_api_username` et `tealium_api_key` sont requis dans votre fichier `secrets.toml`.")
        st.stop()
except Exception:
    st.error("Erreur : La section `[tealium_profiles]` ou `[global_credentials]` est mal configurée ou manquante dans votre fichier `secrets.toml`.")
    st.info("""
        Assurez-vous que votre fichier `secrets.toml` contient :
        ```toml
        [global_credentials]
        tealium_api_username = "votre_email"
        tealium_api_key = "votre_cle"

        [tealium_profiles.mon_profil]
        account = "mon_compte"
        profile = "mon_profil_name"
        ```
    """)
    st.stop()

if not tealium_profiles:
    st.warning("Aucun profil Tealium n'a été trouvé dans votre fichier `secrets.toml` sous la section `[tealium_profiles]`.")
    st.stop()

st.info(f"{len(tealium_profiles)} profil(s) Tealium trouvé(s) dans votre fichier `secrets.toml`.")
st.divider()

# --- Display Profiles ---
active_profile_name = st.session_state.get('active_tealium_profile_name')

for name, config in tealium_profiles.items():
    is_active = (name == active_profile_name)
    status = " (Actif)" if is_active else ""
    
    with st.container():
        st.subheader(f"Profil : {name}{status}")
        
        cols = st.columns([2, 2, 1, 1])
        cols[0].text(f"Compte: {config.get('account')}")
        cols[1].text(f"Profil: {config.get('profile')}")

        if not is_active:
            if cols[2].button("Activer", key=f"activate_tealium_{name}"):
                set_active_tealium(name, config)
                st.rerun()

        if is_active:
            # The download button should only be available for the active profile to avoid confusion
            if cols[3].button("Mettre en Cache", key=f"cache_tealium_{name}"):
                # We need to create the config dict expected by the controller function
                full_config_for_download = st.secrets.global_credentials.to_dict()
                full_config_for_download.update(config)

                with st.spinner(f"Mise en cache du profil '{name}'..."):
                    success = handle_download_profile(name, full_config_for_download)
                if success:
                    st.success(f"Mise en cache du profil '{name}' terminée avec succès !")
                else:
                    st.error(f"Échec de la mise en cache du profil '{name}'. Vérifiez les logs.")

        st.divider()

# --- Database Status Section ---
st.header("Statut de la Base de Données (Cache Tealium)")

db_status = get_database_status()
if db_status.get("status") == "OK":
    st.write(f"**Profils Tealium mis en cache :** {db_status.get('cached_items_count', 0)} objets")
    st.caption(f"La base de données de cache est opérationnelle.")
else:
    st.error(f"**Statut de la base de données :** {db_status.get('status')} - {db_status.get('message', '')}")
