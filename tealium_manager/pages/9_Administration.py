import streamlit as st
from views.component_renderers import setup_page
from controllers.config_controller import get_database_status, handle_database_reset

# --- Page Configuration ---
setup_page()

st.title("🔩 Administration Système")

st.warning("⚠️ Les actions sur cette page sont potentiellement destructrices. Utilisez avec prudence.")

# --- Database Management in Sidebar ---
st.header("Gestion de la Base de Données")

with st.container(border=True):
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
        col1, col2 = st.columns(2)
        col1.metric("Taille du fichier", size_str)
        col1.metric("Profils Tealium mis en cache", db_status.get('cached_items_count', 0))
        col2.metric("Composants Adobe mis en cache", db_status.get('cached_adobe_components_count', 0))
        col2.metric("Rapports Sauvegardés", db_status.get('saved_reports_count', 0))
        st.caption(f"Dernière modification: {db_status.get('last_modified')}")

    else:
        st.error(f"**Statut :** {db_status.get('status')}")
        st.write(db_status.get("message", ""))

    st.divider()

    st.subheader("Réinitialisation de la Base de Données")
    st.write("Cette action supprimera **toutes** les données mises en cache (profils Tealium, composants Adobe, rapports sauvegardés). Les configurations dans votre fichier `secrets.toml` ne seront pas affectées.")

    if 'confirm_reset' not in st.session_state:
        st.session_state.confirm_reset = False

    if st.button("Réinitialiser la Base de Données", type="primary"):
        st.session_state.confirm_reset = True
    
    if st.session_state.confirm_reset:
        st.warning("**ATTENTION :** Cette action est irréversible.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔴 Confirmer la Réinitialisation", use_container_width=True):
                if handle_database_reset():
                    st.success("Base de données réinitialisée avec succès.")
                    st.session_state.confirm_reset = False
                    st.rerun()
                else:
                    st.error("Erreur lors de la réinitialisation de la base de données.")
        with col2:
            if st.button("Annuler", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()
