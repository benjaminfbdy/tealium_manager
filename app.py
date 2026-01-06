import streamlit as st
import database
import security
from tealium_api.client import TealiumClient
# No longer need pandas, datetime, pytz, json here as they are only used in history page.

# --- Page Configuration and Styling ---
st.set_page_config(
    layout="wide",
    page_title="Tealium Manager",
    page_icon="✨",
    initial_sidebar_state="expanded"
)

custom_css = """
<style>
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

# No direct rendering in app.py to prevent it from appearing in the sidebar.
# Global styles are defined in custom_css and can be applied by individual pages
# that include st.markdown('<div class="app-header">Tealium Manager</div>', unsafe_allow_html=True)


# --- Initialisation au démarrage de l'app ---
# 1. Base de données et clé de chiffrement
database.init_database()
ENCRYPTION_KEY = security.load_key()

# 2. État de session
if 'client' not in st.session_state:
    st.session_state.client = None
# st.session_state.page is no longer explicitly managed for navigation, Streamlit handles it.
if 'exploration_context' not in st.session_state:
    st.session_state.exploration_context = {}

# 3. Tentative de connexion automatique
if st.session_state.client is None:
    email = database.load_setting("email")
    encrypted_api_key = database.load_setting("encrypted_api_key")
    if email and encrypted_api_key:
        try:
            api_key = security.decrypt_data(encrypted_api_key, ENCRYPTION_KEY)
            st.session_state.client = TealiumClient(username=email, api_key=api_key)
        except Exception as e:
            print(f"Échec de la connexion auto: {e}")
            st.session_state.client = None

# No direct page rendering logic here anymore. Streamlit's multi-page will handle it.
