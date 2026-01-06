import streamlit as st
import pandas as pd
import database
import security
from tealium_api.client import TealiumClient
from datetime import datetime, timedelta
import pytz # Pour la gestion des fuseaux horaires
import json

# --- Page Configuration and Styling (Removed set_page_config) ---
custom_css = """
<style>
    /* Sidebar styling */
    [data-testid="stSidebar"] > div:first-child {
        background-color: #051838;
    }
    /* Set all text within the sidebar to white */
    [data-testid="stSidebar"] * {
        color: white;
    }

    /* Main content font color */
    .main .block-container {
        color: #545f70;
    }
    
    p, ol, ul, li {
        color: #545f70;
    }

    /* Header styling */
    .app-header {
        background-color: #118aaf;
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown('<div class="app-header">Tealium Manager</div>', unsafe_allow_html=True)

def render_history_page():
    st.title("Historique des Mises en Production") # Removed page_icon
    
    if 'client' not in st.session_state or st.session_state.client is None:
        st.warning("Veuillez configurer vos accès dans la page **⚙️ Configuration**.")
        st.stop()

    client = st.session_state.client
    all_profiles = database.load_all_selected_profiles()
    if not all_profiles:
        st.info("Aucun profil configuré. Allez dans la page **⚙️ Configuration**.")
        st.stop()

    accounts = sorted(list(set([acc for acc, prof in all_profiles])))
    selected_account = st.selectbox("Choisissez un compte", options=accounts)

    if selected_account:
        profiles_for_account = sorted([prof for acc, prof in all_profiles if acc == selected_account])
        selected_profile = st.selectbox("Choisissez un profil", options=profiles_for_account)

        if selected_profile:
            st.header(f"Publications pour `{selected_account}/{selected_profile}`")

            cached_revisions_json = database.get_cached_revisions_details(selected_account, selected_profile)
            if not cached_revisions_json:
                st.info("Aucune révision en cache. Lancez une synchronisation depuis la page **⚙️ Configuration**.")
                st.stop()

            revisions_details = [json.loads(r) for r in cached_revisions_json]
            prod_revisions = [rev for rev in revisions_details if "prod" in rev.get("targets_published", [])]

            if not prod_revisions:
                st.info("Aucune publication vers la production trouvée dans le cache pour ce profil.")
            else:
                paris_tz = pytz.timezone("Europe/Paris")
                
                table_data = []
                for rev in prod_revisions:
                    try:
                        clean_time_str = " ".join(rev.get("time_created", "").split(" ")[1:])
                        utc_time = datetime.strptime(clean_time_str, "%Y.%m.%d %H:%M GMT")
                        local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(paris_tz)
                    except (ValueError, IndexError):
                        local_time = None

                    table_data.append({
                        "select": False,
                        "revision_id": rev.get("revision_id"),
                        "date": local_time,
                        "auteur": rev.get("created_by"),
                        "titre": rev.get("name", "N/A"),
                        "commentaire": rev.get("comment", "N/A")
                    })

                df = pd.DataFrame(table_data).dropna(subset=['date']).sort_values(by="date", ascending=False)
                
                st.subheader("Liste des publications")
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "select": st.column_config.CheckboxColumn("Sélection", default=False),
                        "revision_id": None,
                        "date": st.column_config.DatetimeColumn("Date Publication", format="DD/MM/YYYY HH:mm"),
                        "auteur": "Auteur", "titre": "Titre", "commentaire": "Commentaire",
                    },
                    hide_index=True, use_container_width=True
                )
                
                selected_rows = edited_df[edited_df.select]
                
                st.subheader("Actions")
                if len(selected_rows) == 1:
                    if st.button("🔎 Explorer la publication", use_container_width=True):
                        st.session_state.exploration_context = {
                            'account': selected_account, 'profile': selected_profile,
                            'revision_id': selected_rows.iloc[0]["revision_id"]
                        }
                        st.success("Chargé ! Allez sur la page **🔎 Exploration**.")
                        

                elif len(selected_rows) == 2:
                    if st.button("🔄 Comparer les 2 publications", use_container_width=True):
                        st.session_state.exploration_context = {
                            'account': selected_account, 'profile': selected_profile,
                            'revision_id_1': selected_rows.iloc[0]["revision_id"],
                            'revision_id_2': selected_rows.iloc[1]["revision_id"]
                        }
                        st.success("Chargé ! Allez sur la page **🔄 Comparaison**.")
                else:
                    st.info("Cochez 1 publication pour l'explorer, ou 2 pour les comparer.")

# Direct call for Streamlit multi-page app
render_history_page()
