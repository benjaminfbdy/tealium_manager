import streamlit as st
from views.component_renderers import setup_page
from controllers.config_controller import handle_download_profile
import database as db
import pandas as pd

# --- Page Configuration ---
setup_page()
st.title("⚙️ Configuration & Cache Tealium")
st.write("Gérez les profils Tealium définis dans `secrets.toml` et mettez en cache leur configuration.")

# --- Load Configurations from secrets.toml ---
try:
    tealium_profiles = st.secrets.tealium_profiles.to_dict()
    global_creds = st.secrets.global_credentials
    # Ensure global credentials exist
    if not all([global_creds.get("tealium_api_username"), global_creds.get("tealium_api_key")]):
        raise KeyError("Identifiants globaux manquants")
except (AttributeError, KeyError):
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

# Get cache info from the database
try:
    cached_profiles_info = {item['config_name']: item['timestamp'] for item in db.get_profile_cache_info()}
except Exception as e:
    st.error(f"Impossible de lire l'état du cache de la base de données : {e}")
    cached_profiles_info = {}

# --- Display Profiles ---
for name, config in tealium_profiles.items():
    with st.expander(f"Profil : {name}", expanded=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Compte :** `{config.get('account')}`")
            st.markdown(f"**Profil :** `{config.get('profile')}`")

            if name in cached_profiles_info:
                timestamp = pd.to_datetime(cached_profiles_info[name], unit='s').strftime('%d/%m/%Y %H:%M')
                st.info(f"✅ En cache (dernière mise à jour : {timestamp})")
            else:
                st.warning("❌ Non mis en cache")
        
        with col2:
            if st.button("Rafraîchir le cache", key=f"cache_tealium_{name}"):
                # We need to create the full config dict expected by the controller function
                full_config_for_download = global_creds.to_dict()
                full_config_for_download.update(config)

                with st.spinner(f"Mise en cache du profil '{name}'..."):
                    success = handle_download_profile(name, full_config_for_download)
                
                if success:
                    st.success(f"Mise en cache du profil '{name}' terminée avec succès !")
                    st.rerun() # Rerun to update the cache status display
                else:
                    st.error(f"Échec de la mise en cache du profil '{name}'. Vérifiez les logs pour plus de détails.")

st.divider()
st.info("💡 Le cache d'un profil contient sa configuration complète (variables, tags, extensions...). Il est utilisé par la fonctionnalité 'Inventaire'.")
