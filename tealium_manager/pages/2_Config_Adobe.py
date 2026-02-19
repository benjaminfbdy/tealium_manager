import streamlit as st
from views.component_renderers import setup_page
import pandas as pd
from controllers.config_controller import test_adobe_discovery, get_database_status
from controllers.adobe_controller import get_or_refresh_components
from utils.adobe_repo import get_adobe_components_cache_info

# --- Page Configuration ---
setup_page()

st.title("⚙️ Configuration Adobe Analytics")

# --- Initialize Session State ---
if 'active_adobe_config' not in st.session_state:
    st.session_state.active_adobe_config = None

# --- Helper Functions ---
def set_active_adobe(profile_name, profile_config):
    """Sets the selected Adobe profile as active in the session state."""
    st.session_state.active_adobe_config = profile_config
    st.session_state.active_adobe_profile_name = profile_name
    st.success(f"Profil Adobe '{profile_name}' activé pour cette session.")

def _render_adobe_cache_section():
    """Renders the UI for managing the Adobe components cache."""
    st.header("Gestion du Cache des Composants Adobe")
    st.write("Les composants (dimensions, métriques, segments) sont mis en cache pour accélérer le chargement du dashboard. Vous pouvez forcer un rafraîchissement ici.")
    
    cached_items = get_adobe_components_cache_info()
    
    if not cached_items:
        st.info("Aucun composant Adobe n'est actuellement en cache.")
        return
    
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
                    st.rerun()
    st.divider()

# --- Load Configurations from secrets.toml ---
try:
    adobe_profiles = st.secrets.adobe_profiles.to_dict()
except Exception:
    st.error("Erreur : La section `[adobe_profiles]` est mal configurée ou manquante dans votre fichier `secrets.toml`.")
    st.info("""
        Assurez-vous que votre fichier `secrets.toml` contient :
        ```toml
        [adobe_profiles.MON_PROFIL]
        global_company_id = "votre_id_compagnie"
        client_id = "votre_client_id"
        client_secret = "votre_client_secret"
        ```
    """)
    st.stop()

if not adobe_profiles:
    st.warning("Aucun profil Adobe n'a été trouvé dans votre fichier `secrets.toml` sous la section `[adobe_profiles]`.")
    st.stop()

st.info(f"{len(adobe_profiles)} profil(s) Adobe trouvé(s) dans votre fichier `secrets.toml`.")

# --- Discovery Test Result ---
if 'adobe_discovery_result' in st.session_state and st.session_state.adobe_discovery_result:
    with st.expander("Résultat du Test de Découverte Adobe", expanded=True):
        st.json(st.session_state['adobe_discovery_result'])
        if st.button("Fermer le résultat du test"):
            st.session_state['adobe_discovery_result'] = None
            st.rerun()

st.divider()

# --- Display Profiles ---
active_profile_name = st.session_state.get('active_adobe_profile_name')

for name, config in adobe_profiles.items():
    is_active = (name == active_profile_name)
    status = " (Actif)" if is_active else ""
    
    with st.container():
        st.subheader(f"Profil : {name}{status}")
        
        cols = st.columns([3, 1, 1])
        cols[0].text(f"Global Company ID: {config.get('global_company_id')}")

        if not is_active:
            if cols[1].button("Activer", key=f"activate_adobe_{name}"):
                set_active_adobe(name, config)
                st.rerun()

        if is_active:
            if cols[2].button("Tester la Connexion", key=f"test_adobe_{name}"):
                with st.spinner("Test de la connexion..."):
                    # This controller function will need refactoring to accept a dict
                    st.session_state['adobe_discovery_result'] = test_adobe_discovery(config)
                st.rerun()
        st.divider()

# --- Render Adobe Cache Management ---
_render_adobe_cache_section()
