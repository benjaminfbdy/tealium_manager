import streamlit as st
from views.config_view import render_config_panel
from views.mep_history_view import render_mep_history
from views.comparison_view import render_comparison
from views.inventory_view import render_inventory_view
from controllers.config_controller import (
    get_tealium_connection_status,
    get_all_configurations,
    get_active_configuration_details,
    get_global_settings,
    handle_save_global_settings,
    handle_add_new_config,
    handle_update_config,
    handle_set_active_config,
    handle_delete_config,
    handle_download_profile,
    get_database_status,
    handle_database_reset,
    get_all_adobe_configurations,
    get_active_adobe_configuration_details,
    get_adobe_config_details_by_name,
    get_adobe_connection_status,
    handle_add_new_adobe_config,
    handle_set_active_adobe_config,
    handle_delete_adobe_config,
    test_adobe_discovery
)
from views.adobe_dashboard_view import render_adobe_dashboard_view
from views.adobe_reports_view import render_adobe_reports_view
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

st.sidebar.divider()
st.sidebar.subheader("Tealium")
if st.sidebar.button("Inventaire"):
    st.session_state.page = "inventory"
if st.sidebar.button("Historique des MEP"):
    st.session_state.page = "mep_history"

st.sidebar.divider()
st.sidebar.subheader("Adobe Analytics")
if st.sidebar.button("Requeteur"):
    st.session_state.page = "adobe_dashboard"
if st.sidebar.button("Rapports"):
    st.session_state.page = "adobe_reports"


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
        st.write(f"**Configs Tealium :** {db_status.get('configurations_count', 0)}")
        st.write(f"**Configs Adobe :** {db_status.get('adobe_configurations_count', 0)}")
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

st.sidebar.divider()
st.sidebar.caption("🚀 Tealium Manager v0.7-alpha (Branch: alpha7)")


if st.session_state.page == "home":
    st.markdown("""
    # Bienvenue sur le Tealium Manager ! 👋

    Cet outil a été conçu pour simplifier et optimiser la gestion de vos configurations Tealium iQ. Fini la navigation manuelle complexe, bonjour l'automatisation et la visibilité !

    ---

    ## 🚀 Fonctionnalités Principales

    Voici un aperçu des super-pouvoirs que cet outil met à votre disposition :

    ### 1. ⚙️ **Gestion des Configurations**
    - **Quoi ?** Centralisez tous vos accès aux comptes et profils Tealium. Gérez les API keys, les adresses e-mail et même les configurations de proxy pour les réseaux d'entreprise.
    - **Comment ?**
        1.  Allez dans la page **Configuration**.
        2.  Renseignez vos **Paramètres Globaux** (API Key, e-mail de connexion).
        3.  Ajoutez un ou plusieurs **Profils** en spécifiant le nom du compte, du profil et le serveur (EventStream/AudienceStream ou TiQ).
        4.  Sélectionnez un profil et cliquez sur **Définir comme actif** pour commencer à travailler dessus.
    
    ### 2. 🗂️ **Inventaire**
    - **Quoi ?** Générez un inventaire complet de tous les composants d'un profil (tags, variables, etc.) et exportez-le au format CSV.
    - **Comment ?**
        1.  Cliquez sur **Inventaire**.
        2.  Cliquez sur le bouton pour lancer la génération.
        3.  Une fois terminé, le fichier est prêt à être téléchargé.

    ### 3. 📜 **Historique des MEP (Mises en Production)**
    - **Quoi ?** Gardez un œil sur qui a publié quoi et quand.
    - **Comment ?**
        1.  Allez dans **Historique des MEP**.
        2.  La liste des dernières publications pour le profil actif s'affiche.

    ---

    ## 💡 Premiers Pas

    1.  Commencez par la page **Configuration** pour enregistrer vos identifiants Tealium.
    2.  Ajoutez votre premier profil et activez-le.
    3.  Lancez un **Inventaire** pour auditer vos tags.

    Bonne découverte !
    """)
elif st.session_state.page == "config":
    st.title("Gestion des Configurations")
    
    # --- Initialize session state for editing ---
    if 'adobe_config_to_edit' not in st.session_state:
        st.session_state.adobe_config_to_edit = None

    # --- Load all data from controller ---
    global_settings = get_global_settings()
    
    # Tealium Data
    all_tealium_configs = get_all_configurations()
    active_tealium_config = get_active_configuration_details()
    active_tealium_config_name = active_tealium_config.get("name") if active_tealium_config else None
    is_tealium_connected = get_tealium_connection_status()

    # Adobe Data
    all_adobe_configs = get_all_adobe_configurations()
    active_adobe_config = get_active_adobe_configuration_details()
    active_adobe_config_name = active_adobe_config.get("name") if active_adobe_config else None
    is_adobe_connected = get_adobe_connection_status()

    # --- Render the unified config panel ---
    action_result = render_config_panel(
        is_tealium_connected=is_tealium_connected,
        is_adobe_connected=is_adobe_connected,
        all_tealium_configs=all_tealium_configs,
        all_adobe_configs=all_adobe_configs,
        active_tealium_config_name=active_tealium_config_name,
        active_adobe_config_name=active_adobe_config_name,
        global_settings=global_settings,
        adobe_config_to_edit=st.session_state.adobe_config_to_edit
    )

    # --- Process action from the panel ---
    if action_result["action"]:
        action = action_result["action"]
        data = action_result.get("data", {})
        
        with st.spinner("Traitement..."):
            # Global settings
            if action == "save_global":
                handle_save_global_settings(data)
                st.success("Paramètres globaux enregistrés.")
            
            # Tealium actions
            elif action == "add_new":
                if handle_add_new_config(data):
                    st.success(f"Profil Tealium '{data['name']}' ajouté.")
                else:
                    st.error(f"Erreur lors de l'ajout du profil Tealium '{data['name']}'.")
            elif action == "update":
                if handle_update_config(data):
                    st.success(f"Profil Tealium '{data['name']}' mis à jour.")
            elif action == "set_active":
                if handle_set_active_config(data["name"]):
                    st.success(f"'{data['name']}' est maintenant le profil Tealium actif et la connexion est réussie.")
                else:
                    st.error(f"'{data['name']}' a été défini comme actif, mais la connexion a échoué.")
            elif action == "delete":
                handle_delete_config(data["name"])
                st.success(f"Profil Tealium '{data['name']}' supprimé.")
            elif action == "download":
                st.session_state['download_status'] = {"name": data["name"], "success": handle_download_profile(data["name"])}
            
            # Adobe actions
            elif action == "save_adobe_config":
                if handle_add_new_adobe_config(data):
                    st.success(f"Configuration Adobe '{data['name']}' enregistrée.")
                    st.session_state.adobe_config_to_edit = None # Exit edit mode on success
                else:
                    st.error(f"Erreur lors de l'enregistrement de la configuration Adobe '{data['name']}'.")
            elif action == "edit_adobe":
                # Fetch full config details and store in session state to enter edit mode
                st.session_state.adobe_config_to_edit = get_adobe_config_details_by_name(data["name"])
            elif action == "cancel_edit_adobe":
                st.session_state.adobe_config_to_edit = None
            elif action == "set_active_adobe":
                if handle_set_active_adobe_config(data["name"]):
                    st.success(f"'{data['name']}' est maintenant la configuration Adobe active et la connexion est réussie.")
                else:
                    st.error(f"'{data['name']}' a été définie comme active, mais la connexion a échoué.")
            elif action == "delete_adobe":
                handle_delete_adobe_config(data["name"])
                st.success(f"Configuration Adobe '{data['name']}' supprimée.")
                # If we deleted the config being edited, exit edit mode
                if st.session_state.adobe_config_to_edit and st.session_state.adobe_config_to_edit['name'] == data["name"]:
                    st.session_state.adobe_config_to_edit = None

            elif action == "test_adobe_discovery":
                st.session_state['adobe_discovery_result'] = test_adobe_discovery()

        st.rerun()

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
elif st.session_state.page == "adobe_dashboard":
    render_adobe_dashboard_view()
elif st.session_state.page == "adobe_reports":
    render_adobe_reports_view()
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
