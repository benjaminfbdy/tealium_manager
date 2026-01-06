import streamlit as st
import database
import json
import ui_components

# --- Page Configuration and Styling (Removed set_page_config) ---


st.title("🔎 Explorateur de Version")

ctx = st.session_state.get('exploration_context', {})
revision_id = ctx.get('revision_id')
account = ctx.get('account')
profile = ctx.get('profile')

if not revision_id:
    st.warning("Aucune version sélectionnée. Veuillez choisir une publication dans l'Historique.")
    st.stop()

st.markdown(f"**Compte:** `{account}` | **Profil:** `{profile}` | **Version:** `{revision_id}`")

# Chargement des données
revisions_json = database.get_cached_revisions_details(account, profile)
target_revision = next((json.loads(r) for r in revisions_json if json.loads(r).get('revision_id') == revision_id), None)

if not target_revision:
    st.error("Impossible de charger les données de la révision.")
    st.stop()

# Création de la Map d'IDs pour les références croisées
id_map = {}
if 'tags' in target_revision:
    for t in target_revision['tags']: id_map[str(t['id'])] = {'name': t.get('name'), 'type': 'tag'}
if 'load_rules' in target_revision:
    for l in target_revision['load_rules']: id_map[str(l['id'])] = {'name': l.get('name'), 'type': 'loadRule'}
if 'extensions' in target_revision:
    for e in target_revision['extensions']: id_map[str(e['id'])] = {'name': e.get('name'), 'type': 'extension'}

# Interface par onglets
tabs = st.tabs(["🏷️ Tags", "📦 Variables", "📜 Load Rules", "🔧 Extensions"])

with tabs[0]:
    st.subheader(f"Tags ({len(target_revision.get('tags', []))})")
    for item in target_revision.get('tags', []):
        ui_components.display_tag_card(item, id_map)

with tabs[1]:
    st.subheader(f"Variables ({len(target_revision.get('data_sources', []))})")
    for item in target_revision.get('data_sources', []):
        ui_components.display_variable_card(item, id_map)

with tabs[2]:
    st.subheader(f"Règles de Chargement ({len(target_revision.get('load_rules', []))})")
    for item in target_revision.get('load_rules', []):
        ui_components.display_load_rule_card(item)

with tabs[3]:
    st.subheader(f"Extensions ({len(target_revision.get('extensions', []))})")
    for item in target_revision.get('extensions', []):
        ui_components.display_extension_card(item)