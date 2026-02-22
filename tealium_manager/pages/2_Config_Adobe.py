import streamlit as st
from views.component_renderers import setup_page
import pandas as pd
from controllers.adobe_controller import get_report_suites, get_or_refresh_components
from utils.adobe_repo import get_adobe_components_cache_info
import time

# --- Page Configuration ---
setup_page()
st.title("⚙️ Configuration & Cache Adobe Analytics")
st.write("Gérez les comptes Adobe définis dans `secrets.toml` et mettez en cache les composants des Report Suites (RSID) que vous utilisez le plus souvent.")

# --- Load Configurations from secrets.toml ---
try:
    adobe_profiles = st.secrets.adobe_profiles.to_dict()
except (AttributeError, KeyError):
    st.error("Erreur : La section `[adobe_profiles]` est mal configurée ou manquante dans votre fichier `secrets.toml`.")
    st.info("""
        Assurez-vous que votre fichier `secrets.toml` contient au moins un profil, par exemple :
        ```toml
        [adobe_profiles.mon_profil]
        global_company_id = "votre_id_compagnie"
        client_id = "votre_client_id"
        client_secret = "votre_client_secret"
        # etc...
        ```
    """)
    st.stop()

if not adobe_profiles:
    st.warning("Aucun profil Adobe n'a été trouvé dans votre fichier `secrets.toml` sous la section `[adobe_profiles]`.")
    st.stop()

# --- Helper function to get report suites with caching in session_state ---
@st.cache_data(ttl=3600) # Cache the list of suites for 1h to avoid repeated API calls
def _get_suites_for_profile(_config_name, adobe_config):
    suites, error = get_report_suites(adobe_config)
    if error:
        st.error(f"Erreur lors de la récupération des Report Suites pour '{_config_name}': {error}")
        return {}
    return {s['rsid']: s['name'] for s in suites}

# --- Display Profiles ---
for name, config in adobe_profiles.items():
    with st.expander(f"Compte : {name} ({config.get('global_company_id')})", expanded=True):
        
        # --- Connection and Suite Loading ---
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**Client ID:** `{config.get('client_id') or config.get('api_key')}`")
        
        # We need the full config dict for the controller functions
        full_config = dict(config)

        # Get report suites for the current profile
        suite_options = _get_suites_for_profile(name, full_config)

        if not suite_options:
            st.warning("Aucune Report Suite n'a pu être chargée pour ce compte. Vérifiez la configuration et la connexion.")
            continue

        # --- Cache Management for RSIDs ---
        st.write("---")
        st.subheader("Mise en cache des composants par Report Suite")
        
        # Get cache info from our database
        cached_rsids_info = {item['rsid']: item['last_updated'] for item in get_adobe_components_cache_info()}

        # Format options for multiselect to include cache status
        def format_rsid_option(rsid):
            name = suite_options[rsid]
            if rsid in cached_rsids_info:
                timestamp = pd.to_datetime(cached_rsids_info[rsid], unit='s').strftime('%d/%m/%Y %H:%M')
                return f"✅ {name} ({rsid}) - Cache du {timestamp}"
            return f"❌ {name} ({rsid}) - Non mis en cache"

        # Let user select which RSIDs to cache
        selected_rsids = st.multiselect(
            "Choisissez les Report Suites à mettre en cache :",
            options=list(suite_options.keys()),
            format_func=format_rsid_option,
            key=f"multiselect_{name}"
        )

        if st.button("Rafraîchir le cache pour la sélection", key=f"refresh_{name}"):
            if not selected_rsids:
                st.warning("Veuillez sélectionner au moins une Report Suite.")
            else:
                st.info(f"Lancement de la mise en cache pour {len(selected_rsids)} Report Suite(s)...")
                progress_bar = st.progress(0)
                
                # --- This is where the new, selective caching logic happens ---
                # This could be a new function in adobe_controller
                # For now, we implement the logic directly for clarity
                has_errors = False
                for i, rsid in enumerate(selected_rsids):
                    progress_text = f"Mise en cache de {suite_options[rsid]} ({rsid})... ({i+1}/{len(selected_rsids)})"
                    progress_bar.progress((i + 1) / len(selected_rsids), text=progress_text)
                    
                    with st.spinner(progress_text):
                        # The controller function already saves to cache if force_refresh=True
                        _, error_msg = get_or_refresh_components(full_config, rsid, force_refresh=True)
                    
                    if error_msg:
                        st.error(f"Erreur pour {rsid}: {error_msg}")
                        has_errors = True

                progress_bar.empty()
                if not has_errors:
                    st.success("Mise en cache terminée avec succès !")
                else:
                    st.warning("Certaines Report Suites n'ont pas pu être mises en cache. Voir les erreurs ci-dessus.")
                
                # Rerun to update cache status in the multiselect display
                st.rerun()

st.divider()
st.info("💡 Les composants (dimensions, métriques, segments) mis en cache sont utilisés dans toute l'application pour accélérer l'affichage et réduire les appels API.")
