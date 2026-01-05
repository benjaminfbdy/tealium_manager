import streamlit as st
import pandas as pd

def display_variable_card(variable, id_map):
    """Affiche une carte détaillée pour une variable."""
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

def display_tag_card(tag, id_map):
    """Affiche une carte détaillée pour un tag."""
    title = f"🏷️ **{tag.get('name', 'Tag sans nom')}** (ID: {tag.get('id')})"
    with st.expander(title, expanded=True):
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
    """Affiche une carte détaillée pour une règle de chargement."""
    title = f"📜 **{rule.get('name', 'Règle sans nom')}** (ID: {rule.get('id')})"
    with st.expander(title, expanded=True):
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
    """Affiche une carte détaillée pour une extension."""
    title = f"🔧 **{ext.get('name', 'Extension sans nom')}** (ID: {ext.get('id')})"
    with st.expander(title, expanded=True):
        col1, col2 = st.columns(2)
        col1.markdown(f"**Scope:** `{ext.get('scope', 'N/A')}`")
        col2.markdown(f"**Type:** `{ext.get('extensionType', 'N/A')}`")

        code_value = None
        if ext.get('extensionType') == 'Javascript Code':
            config = ext.get('configuration')
            if isinstance(config, list):
                for item in config:
                    if isinstance(item, dict) and item.get('name') == 'code':
                        code_value = item.get('value')
                        break
            elif isinstance(config, str):
                code_value = config
        
        if code_value:
            with st.expander("Voir le code", expanded=False):
                st.code(code_value, language='javascript')

        config_data = ext.get('configuration')
        if config_data:
            config_to_show = None
            if isinstance(config_data, list):
                other_items = [item for item in config_data if isinstance(item, dict) and item.get('name') != 'code']
                if other_items:
                    config_to_show = other_items
            elif config_data != code_value:
                config_to_show = config_data

            if config_to_show:
                with st.expander("Voir la configuration additionnelle"):
                    if isinstance(config_to_show, list):
                        for config_item in config_to_show:
                            if isinstance(config_item, dict):
                                st.markdown(f"**{config_item.get('name', 'Paramètre')}**")
                                item_value = config_item.get('value')
                                if isinstance(item_value, str) and '\n' in item_value:
                                    st.code(item_value, language='javascript')
                                else:
                                    st.write(item_value)
                            else:
                                st.json(config_item)
                    else:
                        st.json(config_to_show)

        with st.expander("Voir les données brutes", expanded=False):
            st.json(ext)

def display_full_item(item_type, item_data, id_map):
    """Aiguille vers la bonne fonction d'affichage en fonction du type d'élément."""
    if not item_data:
        st.warning("Données de l'élément non trouvées.")
        return

    # st.write(f"Displaying item_type: {item_type}") # for debugging
    if 'tag' in item_type:
        display_tag_card(item_data, id_map)
    elif 'variable' in item_type:
        display_variable_card(item_data, id_map)
    elif 'loadRule' in item_type:
        display_load_rule_card(item_data)
    elif 'extension' in item_type:
        display_extension_card(item_data)
    else:
        st.json(item_data)
