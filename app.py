import streamlit as st
import pandas as pd
import database
import security
from tealium_api.client import TealiumClient
from datetime import datetime, timedelta
import pytz # Pour la gestion des fuseaux horaires
import json

# --- Page Configuration and Styling ---
st.set_page_config(
    layout="wide",
    page_title="Tealium Manager"
)

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


# --- Initialisation au démarrage de l'app ---
# 1. Base de données et clé de chiffrement
database.init_database()
ENCRYPTION_KEY = security.load_key()

# 2. État de session
if 'client' not in st.session_state:
    st.session_state.client = None
if 'page' not in st.session_state:
    st.session_state.page = "Historique de MEP"
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

# --- Fonctions de rendu des pages ---

def render_configuration_page():
    st.title("⚙️ Configuration")

    email_db = database.load_setting("email") or ""
    encrypted_key_db = database.load_setting("encrypted_api_key")

    email = st.text_input("Email Tealium", value=email_db)
    api_key = st.text_input("Clé API Tealium (laisser vide pour ne pas changer)", type="password")
    
    profiles_in_db = database.load_all_selected_profiles()
    manual_profiles_str = "\n".join([f"{acc}/{prof}" for acc, prof in profiles_in_db])
    
    st.subheader("Configuration manuelle des profils")
    manual_profiles_input = st.text_area(
        "Contextes Compte/Profil (un par ligne)",
        value=manual_profiles_str,
        height=150,
        help="Format : nom-du-compte/nom-du-profil"
    )

    if st.button("Sauvegarder la configuration"):
        if email and (api_key or encrypted_key_db):
            try:
                database.save_setting("email", email)
                if api_key:
                    encrypted_key = security.encrypt_data(api_key, ENCRYPTION_KEY)
                    database.save_setting("encrypted_api_key", encrypted_key)
                
                # Désélectionne tout avant de sauvegarder la nouvelle liste
                database.unselect_all_profiles()

                profiles_to_save = []
                lines = [line.strip() for line in manual_profiles_input.split('\n') if line.strip()]
                for line in lines:
                    if '/' not in line:
                        st.warning(f"Ligne ignorée (format incorrect) : '{line}'")
                        continue
                    account, profile = line.split('/', 1)
                    profiles_to_save.append((account.strip(), profile.strip(), 1))
                
                if profiles_to_save:
                    database.save_profiles(profiles_to_save)
                
                st.success("Configuration manuelle sauvegardée !")
                st.session_state.client = None 
                st.rerun()

            except Exception as e:
                st.error(f"Une erreur est survenue lors de la sauvegarde: {e}")
        else:
            st.warning("L'email et la clé API sont requis pour la première configuration.")

    st.divider()

    st.subheader("💿 Gestion du Cache")
    client = st.session_state.client
    if not client:
        st.info("Connectez-vous pour pouvoir gérer le cache.")
    else:
        if st.button("Lancer la synchronisation du cache pour tous les profils", use_container_width=True):
            profiles_to_sync = database.load_all_selected_profiles()
            if not profiles_to_sync:
                st.warning("Aucun profil n'est configuré pour la synchronisation.")
            else:
                st.info(f"Synchronisation lancée pour {len(profiles_to_sync)} profil(s)...")
                overall_progress = st.progress(0, text="Progression globale")
                
                for i, (account, profile) in enumerate(profiles_to_sync):
                    st.markdown(f"**Profil `{account}/{profile}`**")
                    
                    with st.spinner(f"Récupération des publications pour {account}/{profile}..."):
                        try:
                            all_api_ids = client.get_revisions(account, profile)
                            if not all_api_ids:
                                st.text("-> Aucune publication trouvée sur l'API.")
                                continue

                            cached_ids = database.get_cached_revision_ids(account, profile)
                            missing_ids = [rid for rid in all_api_ids if rid not in cached_ids]

                            if not missing_ids:
                                st.text("-> Cache déjà à jour.")
                            else:
                                st.text(f"-> {len(missing_ids)} nouvelle(s) publication(s) à synchroniser.")
                                profile_progress = st.progress(0)
                                new_revs_to_save = []
                                for j, rev_id in enumerate(missing_ids):
                                    details = client.get_revision_details(account, profile, rev_id)
                                    if details and 'error' not in details:
                                        new_revs_to_save.append((rev_id, account, profile, json.dumps(details)))
                                    elif details and 'error' in details:
                                        st.warning(f"Impossible de synchroniser la révision {rev_id}: {details['error']}")
                                    profile_progress.progress((j + 1) / len(missing_ids))
                                
                                database.save_revisions_details(new_revs_to_save)
                                profile_progress.empty()
                                st.text("-> Synchronisation terminée.")
                        
                        except Exception as e:
                            st.error(f"Erreur lors de la synchro de `{account}/{profile}`: {e}")

                    overall_progress.progress((i + 1) / len(profiles_to_sync))
                
                overall_progress.empty()
                st.success("Synchronisation globale terminée !")
        
        if st.button("Vider le cache des révisions", type="primary", use_container_width=True):
            try:
                database.clear_revisions_cache()
                st.cache_data.clear()
                st.success("Le cache des révisions a été vidé. La prochaine synchronisation sera complète.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors du vidage du cache : {e}")


def render_history_page():
    st.title("Historique des Mises en Production")
    client = st.session_state.client

    if not client:
        st.info("Veuillez configurer l'application pour commencer.")
        st.stop()

    all_profiles = database.load_all_selected_profiles()
    if not all_profiles:
        st.warning("Aucun profil configuré. Allez dans 'Configuration' pour en ajouter.")
        st.stop()

    accounts = sorted(list(set([acc for acc, prof in all_profiles])))
    selected_account = st.selectbox("Choisissez un compte", options=accounts)

    if selected_account:
        profiles_for_account = sorted([prof for acc, prof in all_profiles if acc == selected_account])
        selected_profile = st.selectbox("Choisissez un profil", options=profiles_for_account)

        if selected_profile:
            st.header(f"Publications pour `{selected_account}/{selected_profile}`")

            cached_revisions_json = database.get_cached_revisions_details(selected_account, selected_profile)
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

                df = pd.DataFrame(table_data)
                df = df.dropna(subset=['date']) # On retire les lignes où la date n'a pas pu être parsée
                df = df.sort_values(by="date", ascending=False)
                st.subheader("Liste des publications")
                
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "select": st.column_config.CheckboxColumn("Sélection", default=False),
                        "revision_id": None,
                        "date": st.column_config.DatetimeColumn(
                            "Date Publication",
                            format="DD/MM/YYYY HH:mm",
                        ),
                        "auteur": st.column_config.TextColumn("Auteur"),
                        "titre": st.column_config.TextColumn("Titre"),
                        "commentaire": st.column_config.TextColumn("Commentaire"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                selected_rows = edited_df[edited_df.select]
                
                st.subheader("Actions")
                if len(selected_rows) == 1:
                    if st.button("🔎 Explorer la publication", use_container_width=True):
                        st.session_state.page = "Exploration"
                        st.session_state.exploration_context = {
                            'account': selected_account,
                            'profile': selected_profile,
                            'revision_id': selected_rows.iloc[0]["revision_id"]
                        }
                        st.rerun()

                elif len(selected_rows) == 2:
                    if st.button("🔄 Comparer les 2 publications", use_container_width=True):
                        st.session_state.page = "Comparaison"
                        st.session_state.exploration_context = {
                            'account': selected_account,
                            'profile': selected_profile,
                            'revision_id_1': selected_rows.iloc[0]["revision_id"],
                            'revision_id_2': selected_rows.iloc[1]["revision_id"]
                        }
                        st.rerun()
                else:
                    st.info("Cochez 1 publication pour l'explorer, ou 2 pour les comparer.")

def render_exploration_page():
    context = st.session_state.exploration_context
    st.title(f"🔎 Exploration de la révision `{context['revision_id']}`")
    st.caption(f"Compte : `{context['account']}` | Profil : `{context['profile']}`")

    if st.button("⬅️ Retour à l'historique"):
        st.session_state.page = "Historique de MEP"
        st.session_state.exploration_context = {}
        st.rerun()

    @st.cache_data
    def get_config(account, profile, revision_id):
        return st.session_state.client.get_revision_configuration(account, profile, revision_id)

    with st.spinner("Chargement et analyse de la configuration complète..."):
        config = get_config(context['account'], context['profile'], context['revision_id'])

    if not config or (isinstance(config, dict) and 'error' in config):
        st.error("Impossible de charger les détails de la configuration.")
        if isinstance(config, dict) and 'error' in config:
            st.warning(config['error'])
        st.stop()

    id_map = {}
    for item_type in ['tags', 'variables', 'loadRules', 'extensions', 'events']:
        for item in config.get(item_type) or []:
            id_map[str(item['id'])] = {"name": item.get('name', "Sans nom"), "type": item_type.rstrip('s')}

    def display_variable_card(variable):
        title = f"📦 **{variable.get('name')}** (ID: {variable.get('id')})"
        with st.expander(title):
            col1, col2 = st.columns(2)
            col1.markdown(f"**Type:** `{variable.get('type')}`")
            col2.markdown(f"**Alias:** `{variable.get('alias') or 'Aucun'}`")
            st.markdown(f"**Identifiant Unique:** `{variable.get('uniqueIdentifier', 'N/A')}`")

            if variable.get('notes'):
                st.info(f"**Notes:** {variable.get('notes')}")

            used_in = variable.get('usedIn', {})
            if any(used_in.values()):
                st.markdown("**Utilisé dans :**")
                used_in_filtered = {k: v for k, v in used_in.items() if v}
                for key, ids in used_in_filtered.items():
                    st.markdown(f"_{key.capitalize()}_ ({len(ids)}):")
                    for item_id in ids:
                        looked_up = id_map.get(str(item_id), {"name": f"ID Inconnu: {item_id}", "type": "unknown"})
                        st.markdown(f"- **{looked_up['name']}** (`{looked_up['type']}` ID: `{item_id}`)")
            
            with st.expander("Voir les données brutes", expanded=False):
                st.json(variable)

    def display_tag_card(tag):
        title = f"🏷️ **{tag.get('name', 'Tag sans nom')}** (ID: {tag.get('id')})"
        with st.expander(title):
            col1, col2 = st.columns(2)
            col1.markdown(f"**Type (Tag ID):** `{tag.get('tagID', 'N/A')}`")
            col2.markdown(f"**Statut:** `{'Actif' if tag.get('status') == 'active' else 'Inactif'}`")
            
            load_rule_ids = tag.get('loadRuleIDs', [])
            if load_rule_ids:
                st.markdown("**Règles de chargement :**")
                for rule_id in load_rule_ids:
                    looked_up = id_map.get(str(rule_id), {"name": f"ID Inconnu: {rule_id}", "type": "loadRule"})
                    st.markdown(f"- **{looked_up['name']}** (`{looked_up['type']}` ID: `{rule_id}`)")
            
            mappings = tag.get('dataMappings', [])
            if mappings:
                with st.expander(f"Voir les {len(mappings)} Data Mappings"):
                    mapping_data = []
                    for m in mappings:
                        mapping_data.append({
                            "Source": m.get('variable'),
                            "Type": m.get('type'),
                            "Destination(s)": ", ".join(m.get('mappings', []))
                        })
                    st.dataframe(pd.DataFrame(mapping_data), use_container_width=True)

            if tag.get('template') and tag['template'].get('content'):
                with st.expander("Voir le code du template", expanded=False):
                    st.code(tag['template']['content'], language='javascript')
            
            config_data = tag.get('configuration', {})
            if config_data:
                with st.expander("Voir la configuration du tag"):
                     st.json(config_data)

            with st.expander("Voir les données brutes", expanded=False):
                st.json(tag)

    def display_load_rule_card(rule):
        title = f"📜 **{rule.get('name', 'Règle sans nom')}** (ID: {rule.get('id')})"
        with st.expander(title):
            st.markdown("**Conditions :**")
            conditions = rule.get('conditions', [])
            if not conditions:
                st.info("Aucune condition définie.")
            else:
                for i, cond_group in enumerate(conditions):
                    if i > 0:
                        st.markdown("<p style='text-align: center; color: grey;'>OU</p>", unsafe_allow_html=True)
                    
                    and_group_df_data = []
                    for and_cond in cond_group:
                        and_group_df_data.append({
                            "Source": and_cond.get('variable', 'N/A'),
                            "Comparaison": and_cond.get('operator', 'N/A'),
                            "Valeur": and_cond.get('value', 'N/A')
                        })
                    st.dataframe(pd.DataFrame(and_group_df_data), use_container_width=True)

            with st.expander("Voir les données brutes", expanded=False):
                st.json(rule)

    def display_extension_card(ext):
        title = f"🔧 **{ext.get('name', 'Extension sans nom')}** (ID: {ext.get('id')})"
        with st.expander(title):
            col1, col2 = st.columns(2)
            col1.markdown(f"**Scope:** `{ext.get('scope', 'N/A')}`")
            col2.markdown(f"**Type:** `{ext.get('extensionType', 'N/A')}`")

            config_data = ext.get('configuration', {})
            code_value = None

            # --- Trouver et afficher le code JS en priorité ---
            if ext.get('extensionType') == 'Javascript Code':
                if isinstance(config_data, str):
                    code_value = config_data
                elif isinstance(config_data, list):
                    for item in config_data:
                        if isinstance(item, dict) and item.get('name') == 'code':
                            code_value = item.get('value')
                            break
            
            if code_value:
                with st.expander("Voir le code", expanded=False):
                    st.code(code_value, language='javascript')

            # --- Afficher le reste de la configuration ---
            config_to_show = []
            if isinstance(config_data, list):
                # Filtrer pour ne garder que les dictionnaires qui ne sont pas du code
                config_to_show = [
                    item for item in config_data 
                    if isinstance(item, dict) and item.get('name') != 'code'
                ]
            elif isinstance(config_data, dict):
                 # Si c'est un dictionnaire, on le met dans une liste pour l'affichage
                 config_to_show = [config_data]

            if config_to_show:
                with st.expander("Voir la configuration additionnelle"):
                    for config_item in config_to_show:
                        if not isinstance(config_item, dict):
                            st.json(config_item)
                            continue

                        st.markdown(f"**{config_item.get('name', 'Paramètre')}**")
                        item_value = config_item.get('value')
                        
                        if isinstance(item_value, str) and '\\n' in item_value:
                            st.code(item_value, language='javascript')
                        else:
                            st.write(item_value)

            with st.expander("Voir les données brutes", expanded=False):
                st.json(ext)

    # --- Display Tabs ---
    tab_tags, tab_vars, tab_rules, tab_ext = st.tabs(["🏷️ Tags", "📦 Variables", "📜 Règles de chargement", "🔧 Extensions"])

    with tab_tags:
        items = config.get('tags') or []
        st.subheader(f"{len(items)} Tag(s)")
        for item in sorted(items, key=lambda x: x.get('name', '')):
            display_tag_card(item)

    with tab_vars:
        items = config.get('variables') or []
        st.subheader(f"{len(items)} Variable(s)")
        for item in sorted(items, key=lambda x: x.get('name', '')):
            display_variable_card(item)
    
    with tab_rules:
        items = config.get('loadRules') or []
        st.subheader(f"{len(items)} Règle(s) de chargement")
        for item in sorted(items, key=lambda x: x.get('name', '')):
            display_load_rule_card(item)

    with tab_ext:
        items = config.get('extensions') or []
        st.subheader(f"{len(items)} Extension(s)")
        for item in sorted(items, key=lambda x: x.get('name', '')):
            display_extension_card(item)


from deepdiff import DeepDiff
import re

def render_comparison_page():
    context = st.session_state.exploration_context
    st.title("🔄 Comparaison de publications")
    
    rev_ids = sorted([context['revision_id_1'], context['revision_id_2']])
    rev_a_id, rev_b_id = rev_ids[0], rev_ids[1]

    st.caption(f"Révision A: `{rev_a_id}` | Révision B: `{rev_b_id}`")
    st.caption(f"Compte : `{context['account']}` | Profil : `{context['profile']}`")

    if st.button("⬅️ Retour à l'historique"):
        st.session_state.page = "Historique de MEP"
        st.session_state.exploration_context = {}
        st.rerun()

    @st.cache_data
    def get_config(account, profile, revision_id):
        return st.session_state.client.get_revision_configuration(account, profile, revision_id)

    with st.spinner("Chargement des configurations..."):
        config_a = get_config(context['account'], context['profile'], rev_a_id)
        config_b = get_config(context['account'], context['profile'], rev_b_id)

    if not config_a or (isinstance(config_a, dict) and 'error' in config_a):
        st.error(f"Impossible de charger la configuration pour la révision A ({rev_a_id}).")
        if isinstance(config_a, dict): st.warning(f"Détails: {config_a.get('error')}")
        st.stop()

    if not config_b or (isinstance(config_b, dict) and 'error' in config_b):
        st.error(f"Impossible de charger la configuration pour la révision B ({rev_b_id}).")
        if isinstance(config_b, dict): st.warning(f"Détails: {config_b.get('error')}")
        st.stop()

    # Normalise les données pour une comparaison robuste basée sur les ID
    def normalize_config(config):
        normalized = {}
        for key in ['tags', 'extensions', 'loadRules', 'variables', 'events']:
            items = config.get(key)
            if items: # Vérifie si la liste n'est pas None ou vide
                normalized[key] = {str(item['id']): item for item in items if 'id' in item}
        return normalized

    config_a_norm = normalize_config(config_a)
    config_b_norm = normalize_config(config_b)

    # Comparaison avec DeepDiff sur les données normalisées
    diff = DeepDiff(
        config_a_norm, config_b_norm, 
        ignore_order=True,
        report_repetition=True,
        exclude_regex_paths=r"\['version'\]|template|versionTitle|minorVersion|parentVersion|creation|environmentVersions|versionDetails"
    )

    if not diff:
        st.success("🎉 Aucune différence de configuration trouvée entre ces deux révisions !")
        st.balloons()
        st.stop()

    with st.expander("Voir le détail brut des différences (format JSON)"):
        st.json(diff.to_json(), expanded=False)

    st.write("---")
    st.subheader("Analyse détaillée des changements")

    def display_diff_value(column, value):
        """Affiche intelligemment une valeur de diff."""
        if isinstance(value, (dict, list)):
            column.json(value)
        elif isinstance(value, str) and ('\n' in value or value.strip().startswith(('//', '/*'))):
            # Heuristique simple pour détecter du code : multiligne ou commentaire JS
            column.code(value, language='javascript')
        else:
            # Pour les strings simples, nombres, booléens, etc.
            column.write(value)

    def display_changes(change_type, changes_dict, cfg_a, cfg_b):
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
            for path in changes_dict:
                # New regex to safely handle quoted strings and numbers in paths
                match = re.findall(r"\[(?:'([^']+)'|(\d+))\]", path)
                cleaned_matches = [m[0] or m[1] for m in match]

                if not cleaned_matches or len(cleaned_matches) < 1:
                    st.warning(f"Impossible de traiter le chemin : `{path}`")
                    continue
                
                item_type = cleaned_matches[0]
                item_id = cleaned_matches[1] if len(cleaned_matches) > 1 else None

                if not item_id:
                    st.warning(f"Impossible d'extraire l'ID de : `{path}`")
                    continue

                item_data = None
                if change_type == 'dictionary_item_added':
                    item_data = cfg_b.get(item_type, {}).get(item_id, {})
                else: # removed
                    item_data = cfg_a.get(item_type, {}).get(item_id, {})
                
                name = item_data.get('name', f"ID: {item_id}") if item_data else f"ID: {item_id}"
                st.markdown(f"**{item_type.rstrip('s').capitalize()} : {name}**")
                st.json(item_data)
        else:
            for path, value in changes_dict.items():
                # Matches parts inside brackets, like ['tags'] or [0]
                match = re.findall(r"\[(?:'([^']+)'|(\d+))\]", path)
                cleaned_matches = [m[0] or m[1] for m in match]

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

                elif change_type in ['iterable_item_added', 'iterable_item_removed']:
                     display_diff_value(st, value)

                elif change_type in ['dictionary_item_added', 'dictionary_item_removed']:
                    item_data = value
                    with st.expander("Détails de l'élément"):
                        st.json(item_data)
                
                else: # Fallback pour autres types (ex: type_changes)
                     st.write("Détails de la modification :")
                     display_diff_value(st, value)
    
    change_types_to_process = [
        'dictionary_item_added', 'dictionary_item_removed', 'values_changed',
        'iterable_item_added', 'iterable_item_removed', 'type_changes'
    ]
    for change_type in change_types_to_process:
        if change_type in diff:
            display_changes(change_type, diff[change_type], config_a_norm, config_b_norm)



# --- Menu de Navigation & Routage ---
main_pages = ["Historique de MEP", "Configuration"]
# The sidebar is now always visible
with st.sidebar:
    st.title("Menu")
    if st.session_state.client:
        st.success(f"Connecté en tant que\n**{st.session_state.client.api_username}**")
        
        is_on_subpage = st.session_state.page not in main_pages
        
        # Determine index, default to first page if we are on a sub-page
        try:
            current_index = main_pages.index(st.session_state.page)
        except ValueError:
            current_index = 0 # Default to the first main page

        selected_page = st.radio("Navigation", main_pages, index=current_index, key="nav_radio")
        
        if selected_page != st.session_state.page and not is_on_subpage:
            st.session_state.page = selected_page
            # Clear exploration context when navigating away via sidebar
            st.session_state.exploration_context = {}
            st.rerun()
        
        if is_on_subpage:
            st.info("Utilisez le bouton 'Retour' dans la page pour revenir à la liste.")
    else:
        st.error("Non connecté")
        st.radio("Navigation", ["Configuration"], disabled=True)
        if st.session_state.page != "Configuration":
            st.session_state.page = "Configuration"
            st.rerun()

# --- Routage principal ---
if st.session_state.page == "Historique de MEP":
    render_history_page()
elif st.session_state.page == "Configuration":
    render_configuration_page()
elif st.session_state.page == "Exploration":
    render_exploration_page()
elif st.session_state.page == "Comparaison":
    render_comparison_page()