
import streamlit as st
import re
from services import comparison_service

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

# --- UI Helper Functions ---

def display_diff_value(column, value):
    """Renders a diff value intelligently based on its type."""
    if isinstance(value, (dict, list)):
        column.json(value)
    elif isinstance(value, str) and ('\n' in value or value.strip().startswith(('//', '/*'))):
        column.code(value, language='javascript')
    else:
        column.write(value)

def display_changes(change_type, changes_dict, cfg_a, cfg_b):
    """Displays a section of changes based on the change type."""
    titles = {
        'dictionary_item_added': "✨ Éléments Ajoutés",
        'dictionary_item_removed': "🗑️ Éléments Supprimés",
        'values_changed': "✏️ Champs Modifiés",
        'type_changes': "🔄 Types Modifiés",
        'iterable_item_added': "➕ Ajouts dans une liste",
        'iterable_item_removed': "➖ Retraits d'une liste",
    }
    st.markdown(f"#### {titles.get(change_type, change_type)}")

    if change_type in ['dictionary_item_added', 'dictionary_item_removed']:
            match = re.findall(r"\[(?:'([^']+)'|(\d+))\]", path)

            if not cleaned_matches or len(cleaned_matches) < 1:
                st.warning(f"Impossible de traiter le chemin : `{path}`")
                continue
            
            item_type, item_id = cleaned_matches[0], (cleaned_matches[1] if len(cleaned_matches) > 1 else None)
            if not item_id:
                st.warning(f"Impossible d'extraire l'ID de : `{path}`")
                continue

            item_data = cfg_a.get(item_type, {}).get(item_id, {}) if change_type == 'dictionary_item_removed' else cfg_b.get(item_type, {}).get(item_id, {})
            name = item_data.get('name', f"ID: {item_id}") if item_data else f"ID: {item_id}"
            st.markdown(f"**{item_type.rstrip('s').capitalize()} : {name}**")
            st.json(item_data)
            match = re.findall(r"\[(?:'([^']+)'|(\d+))\]", path)

            if not cleaned_matches or len(cleaned_matches) < 2:
                st.write(f"Chemin non reconnu: `{path}`")
                continue
            
            item_type, item_id = cleaned_matches[0], cleaned_matches[1]
            item_a = cfg_a.get(item_type, {}).get(item_id, {})
            item_b = cfg_b.get(item_type, {}).get(item_id, {})
            name = item_a.get('name') or item_b.get('name') or f"ID: {item_id}"
            field_path = " -> ".join(cleaned_matches[2:])
            st.markdown(f"**{item_type.rstrip('s').capitalize()} : {name} (ID: {item_id})** - Chemin : `{field_path}`")

            if change_type == 'values_changed':
                col1, col2 = st.columns(2)
                col1.write("**Avant (A)**")
                display_diff_value(col1, value['old_value'])
                col2.write("**Après (B)**")
                display_diff_value(col2, value['new_value'])
            else:
                display_diff_value(st, value)

# --- Main Page Logic ---

def render_comparison_page():
    if 'exploration_context' not in st.session_state or not st.session_state.exploration_context.get('revision_id_1'):
        st.warning("Aucune comparaison sélectionnée. Veuillez choisir 2 révisions depuis la page d'accueil 'Historique MEP'.")
        st.stop()

    context = st.session_state.exploration_context
    rev_ids = sorted([context['revision_id_1'], context['revision_id_2']])
    rev_a_id, rev_b_id = rev_ids[0], rev_ids[1]

    st.title("🔄 Comparaison de publications")
    st.caption(f"Révision A: `{rev_a_id}` | Révision B: `{rev_b_id}`")
    st.caption(f"Compte : `{context['account']}` | Profil : `{context['profile']}`")
    st.info("Utilisez le menu latéral pour naviguer vers une autre page.")

    @st.cache_data
    def get_config(account, profile, revision_id):
        if 'client' in st.session_state and st.session_state.client:
            return st.session_state.client.get_revision_configuration(account, profile, revision_id)
        return None

    with st.spinner("Chargement des configurations..."):
        config_a = get_config(context['account'], context['profile'], rev_a_id)
        config_b = get_config(context['account'], context['profile'], rev_b_id)

    if not config_a or (isinstance(config_a, dict) and 'error' in config_a):
        st.error(f"Impossible de charger la configuration pour la révision A ({rev_a_id}).")
        st.stop()
    if not config_b or (isinstance(config_b, dict) and 'error' in config_b):
        st.error(f"Impossible de charger la configuration pour la révision B ({rev_b_id}).")
        st.stop()
    
    # Use the service to get the diff
    diff = comparison_service.get_diff(config_a, config_b)

    if not diff:
        st.success("🎉 Aucune différence de configuration trouvée entre ces deux révisions !")
        st.balloons()
        st.stop()

    with st.expander("Voir le détail brut des différences (format JSON)"):
        st.json(diff.to_json(), expanded=False)

    st.write("---")
    st.subheader("Analyse détaillée des changements")

    # Normalize configs just for the display part
    config_a_norm = comparison_service.normalize_config(config_a)
    config_b_norm = comparison_service.normalize_config(config_b)
    
    change_types_to_process = ['dictionary_item_added', 'dictionary_item_removed', 'values_changed', 'iterable_item_added', 'iterable_item_removed', 'type_changes']
    for change_type in change_types_to_process:
        if change_type in diff:
            display_changes(change_type, diff[change_type], config_a_norm, config_b_norm)

# Run the page
render_comparison_page()
