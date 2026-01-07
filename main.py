import streamlit as st
from views.config_view import render_config_panel
from views.profile_explorer_view import render_profile_explorer
from views.mep_history_view import render_mep_history
from views.comparison_view import render_comparison
from views.inventory_view import render_inventory_view
from controllers.config_controller import (
    get_tealium_connection_status,
    get_all_configurations,
    get_active_configuration_details,
    handle_add_new_config,
    handle_update_config,
    handle_set_active_config,
    handle_delete_config,
    get_database_status,
    handle_database_reset
)
from controllers.profile_controller import get_profile_data
from controllers.mep_controller import get_meps_data, get_mep_comparison_data

# --- Page Configuration ---
st.set_page_config(
    page_title="Tealium Manager",
    page_icon="https://tealium.com/wp-content/uploads/2021/04/tealium_favicon.png",
    layout="wide"
)

# --- Custom Styling (CSS) ---
st.markdown("""
<style>
    /* Remove Streamlit's default header and top margin */
    header {visibility: hidden;}
    .stApp { margin-top: -80px; }
    .block-container {
        padding-top: 0rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #051838;
    }
    [data-testid="stSidebar"] * {
        color: white;
    }
    [data-testid="stSidebar"] .stButton button {
        background-color: #2a3950;
        color: white !important;
        border: 1px solid white;
        width: 100%;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #4f6480;
        border-color: white;
        color: white;
    }
    [data-testid="stSidebar"] .stButton button:active {
        background-color: #1a2330 !important;
        border-color: white;
        color: white;
    }
    /* Ensure text within the button is white */
    [data-testid="stSidebar"] .stButton button p {
        color: white;
    }

    /* Header */
    .app-header {
        background-color: #118aaf;
        color: white;
        padding: 4rem 2rem; /* Increased padding */
        border-radius: 0;
        margin-bottom: 1rem;
        font-size: 2.5rem;
        font-weight: bold;
        margin-left: -1rem;
        margin-right: -1rem;
    }

    /* Main font color */
    h1, h2, h3, h4, h5, h6, p, div, span, label, input, button, table, th, td {
        color: #545f70;
    }
    /* Override for elements that should remain white */
    .app-header, [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown('<p class="app-header"></p>', unsafe_allow_html=True)


# --- Sidebar Navigation ---
st.sidebar.title("Navigation")

# Initialize session state for navigation
if "page" not in st.session_state:
    st.session_state.page = "home"

if st.sidebar.button("Accueil"):
    st.session_state.page = "home"
if st.sidebar.button("Configuration"):
    st.session_state.page = "config"
if st.sidebar.button("Explorateur de Profil"):
    st.session_state.page = "profile_explorer"
if st.sidebar.button("Historique des MEP"):
    st.session_state.page = "mep_history"
if st.sidebar.button("Inventaire"):
    st.session_state.page = "inventory"


# --- Database Management in Sidebar ---
st.sidebar.divider()
with st.sidebar.expander("⚙️ Gestion Base de Données", expanded=False):
    db_status = get_database_status()
    
    if db_status.get("status") == "OK":
        file_size = db_status.get('file_size_bytes', 0)
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.2f} KB"
        else:
            size_str = f"{file_size} Bytes"

        st.info(f"**Statut :** {db_status.get('status')}")
        st.write(f"**Taille :** {size_str}")
        st.write(f"**Configs :** {db_status.get('configurations_count')}")
        st.write(f"**Cache :** {db_status.get('cached_items_count')} objets")
        st.caption(f"Dernière modif.: {db_status.get('last_modified')}")

    else:
        st.error(f"**Statut :** {db_status.get('status')}")
        st.write(db_status.get("message", ""))

    if 'confirm_reset' not in st.session_state:
        st.session_state.confirm_reset = False

    if st.button("Réinitialiser la BDD", key="reset_init"):
        st.session_state.confirm_reset = True
    
    if st.session_state.confirm_reset:
        st.warning("**ATTENTION :** Action irréversible. Vous allez supprimer toutes les configurations et le cache.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔴 Confirmer", key="reset_confirm", use_container_width=True):
                if handle_database_reset():
                    st.success("Base de données réinitialisée.")
                    st.session_state.confirm_reset = False
                    st.rerun()
                else:
                    st.error("Erreur lors de la réinitialisation.")
        with col2:
            if st.button("Annuler", key="reset_cancel", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()


if st.session_state.page == "home":
    st.write("Utilisez le panneau latéral pour naviguer dans l'application.")
elif st.session_state.page == "config":
    st.subheader("Gestion des Configurations Tealium")
    
    # Get all configurations and the active one
    all_configurations = get_all_configurations()
    active_config_details = get_active_configuration_details()
    active_config_name = active_config_details.get("name") if active_config_details else None

    # Determine connection status based on the active configuration
    is_connected = False
    if active_config_details:
        with st.spinner(f"Vérification de la connexion pour '{active_config_name}'..."):
            is_connected = get_tealium_connection_status(active_config_details)
    
    # Render the config panel and capture user action
    action_result = render_config_panel(is_connected, all_configurations, active_config_name)

    if action_result["action"]:
        action = action_result["action"]
        data = action_result["data"]

        with st.spinner("Traitement de la requête..."):
            if action == "add_new":
                if handle_add_new_config(data):
                    st.success(f"Configuration '{data['name']}' ajoutée et testée avec succès.")
                else:
                    st.error(f"Échec de l'ajout ou de la connexion pour '{data['name']}'.")
            elif action == "update":
                if handle_update_config(data):
                    st.success(f"Configuration '{data['name']}' mise à jour et testée avec succès.")
                else:
                    st.error(f"Échec de la mise à jour ou de la connexion pour '{data['name']}'.")
            elif action == "set_active":
                if handle_set_active_config(data["name"]):
                    st.success(f"Configuration '{data['name']}' définie comme active et testée avec succès.")
                else:
                    st.error(f"Échec de la définition comme active ou de la connexion pour '{data['name']}'.")
            elif action == "delete":
                handle_delete_config(data["name"])
                st.success(f"Configuration '{data['name']}' supprimée.")
        st.rerun() # Rerun to reflect updated list and status
elif st.session_state.page == "profile_explorer":
    st.subheader("Explorateur de Composants de Profil Tealium")
    active_config_details = get_active_configuration_details()
    if not active_config_details:
        st.warning("Veuillez sélectionner et activer une configuration Tealium pour explorer un profil.")
    else:
        # Initialize session state for version selection
        if 'selected_version' not in st.session_state:
            st.session_state.selected_version = "latest"

        # Fetch data for the selected version
        version_to_load = st.session_state.selected_version if st.session_state.selected_version != "latest" else None
        profile_response = get_profile_data(version_id=version_to_load)

        # Handle potential errors first
        if profile_response.get("error"):
            st.error(f"**Échec du chargement des données de profil.**")
            st.info(f"Message : {profile_response.get('message', 'Erreur inconnue.')}")
            if "status_code" in profile_response:
                st.caption(f"Status Code de l'API : {profile_response['status_code']}")
            if "body" in profile_response and profile_response["body"]:
                with st.expander("Voir la réponse complète de l'API"):
                    st.json(profile_response["body"])
        
        # If successful, display the version selector and the data
        elif profile_response.get("data"):
            profile_data = profile_response.get("data", {}).get("profile", {})
            version_ids = ["latest"] + profile_data.get("versionIds", [])
            
            # Find the index of the currently loaded version for the selectbox default
            current_version = profile_data.get("version")
            try:
                # If a specific version was loaded, find it. Otherwise, default to 'latest'.
                current_index = version_ids.index(current_version) if version_to_load else 0
            except ValueError:
                current_index = 0

            # Display the version selector
            selected = st.selectbox(
                "Choisissez une version de profil à explorer :",
                options=version_ids,
                index=current_index,
                key="version_selector"
            )
            
            # If selection changes, update session state and rerun
            if selected != st.session_state.selected_version:
                st.session_state.selected_version = selected
                st.rerun()

            # Render the explorer with the loaded data
            render_profile_explorer(profile_response.get("data"))
        else:
            st.error("Une erreur inattendue est survenue : aucune donnée reçue.")
elif st.session_state.page == "mep_history":
    st.subheader("Historique des MEP du Profil Tealium")
    active_config_details = get_active_configuration_details()
    if not active_config_details:
        st.warning("Veuillez sélectionner et activer une configuration Tealium pour voir l'historique des MEP.")
    else:
        with st.spinner(f"Chargement de l'historique des MEP pour '{active_config_details.get('name')}'..."):
            meps_data = get_meps_data()
        
        if meps_data:
            render_mep_history(meps_data)
        else:
            st.info("Aucune MEP trouvée pour le profil actif.")
elif st.session_state.page == "inventory":
    render_inventory_view()
elif st.session_state.page == "comparison":
    st.subheader("Comparaison de MEPs")
    if 'meps_to_compare' in st.session_state and len(st.session_state.meps_to_compare) == 2:
        rev_id_1, rev_id_2 = st.session_state.meps_to_compare
        
        with st.spinner(f"Chargement et comparaison des MEPs {rev_id_1} et {rev_id_2}..."):
            comparison_response = get_mep_comparison_data(rev_id_1, rev_id_2)

        if comparison_response.get("error"):
            st.error(f"**Échec de la comparaison :** {comparison_response.get('message', 'Erreur inconnue.')}")
        else:
            render_comparison(comparison_response.get("data"))
    else:
        st.warning("Veuillez retourner à la page des MEPs et sélectionner exactement deux versions à comparer.")
        if st.button("Retour à l'historique des MEPs"):
            st.session_state.page = "mep_history"
            st.rerun()
