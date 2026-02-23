import streamlit as st
import sys
import pandas as pd
import asyncio
from typing import Dict, List

# No more diagnostics needed
# st.write(f"Version de Streamlit utilisée : **{st.__version__}**")
# st.write(f"Chemin de l'exécutable Python : **{sys.executable}**")

from controllers.adobe_user_controller import get_users_for_organization, add_user, delete_user, update_user

# --- Page Config ---
st.set_page_config(page_title="Gestion des Utilisateurs Adobe", layout="wide")
st.title("👨‍💼 Gestion des Utilisateurs Adobe")

# --- State Management ---
def init_session_state():
    for key in ['user_to_edit', 'users_to_delete', 'dialog_mode', 'last_profile']:
        if key not in st.session_state:
            st.session_state[key] = None

init_session_state()

# --- DIALOGS ---
@st.dialog("Gérer l'utilisateur")
def user_dialog(config: dict, mode: str, raw_users_list: List, user_data: pd.Series = None):
    is_edit_mode = mode == 'edit'
    title = "Modifier un utilisateur" if is_edit_mode else "Ajouter un nouvel utilisateur"
    st.header(title)

    # Dynamically generate the list of available profiles from all users
    all_groups = set()
    for user in raw_users_list:
        if 'groups' in user and isinstance(user['groups'], list):
            all_groups.update(user['groups'])
    available_profiles = sorted(list(all_groups))

    with st.form("user_form"):
        email = st.text_input("Email *", value=user_data['email'] if is_edit_mode else "", disabled=is_edit_mode)
        firstname = st.text_input("Prénom", value=user_data.get('firstname', '') if is_edit_mode else "")
        lastname = st.text_input("Nom", value=user_data.get('lastname', '') if is_edit_mode else "")
        
        default_groups = user_data['groups_list'] if is_edit_mode and 'groups_list' in user_data and isinstance(user_data['groups_list'], list) else []
        product_profiles = st.multiselect("Profils de produit", options=available_profiles, default=default_groups)

        submitted = st.form_submit_button("Sauvegarder" if is_edit_mode else "Créer")
        if submitted:
            if not email: st.error("L'adresse email est obligatoire."); return
            
            st.session_state.dialog_mode = None # Close dialog on submit

            if is_edit_mode:
                # ... (Update logic, no changes needed here)
            else:
                # ... (Add logic, no changes needed here)
            st.rerun()

@st.dialog("Confirmer la suppression")
def confirm_delete_dialog(config: dict):
    # ... (Unchanged)
    pass

# --- Main View ---
try:
    adobe_profiles = st.secrets.get("adobe_profiles", {}).to_dict()
    profile_names = list(adobe_profiles.keys())
    if not profile_names: st.warning("Aucun profil Adobe trouvé."); st.stop()
except (AttributeError, TypeError):
    st.error("Configuration [adobe_profiles] invalide."); st.stop()

selected_profile_name = st.selectbox("Sélectionnez un profil Adobe", options=profile_names, key="profile_selector")

if selected_profile_name:
    selected_config = adobe_profiles[selected_profile_name]
    st.info(f"Profil actif : **{selected_profile_name}**")

    # Fetch data BEFORE the dialog router, so we can pass it to the dialog
    with st.spinner("Chargement des utilisateurs..."):
        raw_users = get_users_for_organization(
            config_tuple=tuple(sorted(selected_config.items()))
        )

    if st.button("➕ Ajouter un utilisateur"):
        st.session_state.dialog_mode = 'add'
        st.rerun()

    # --- DIALOG ROUTER ---
    if st.session_state.dialog_mode:
        dialog_kwargs = {"config": selected_config, "raw_users_list": raw_users}
        if st.session_state.dialog_mode == 'add':
            user_dialog(mode='add', **dialog_kwargs)
        elif st.session_state.dialog_mode == 'edit':
            user_dialog(mode='edit', user_data=st.session_state.user_to_edit, **dialog_kwargs)
        elif st.session_state.dialog_mode == 'delete':
            confirm_delete_dialog(config=selected_config)
    
    # --- DATA DISPLAY ---
    if raw_users:
        df = pd.json_normalize(raw_users)
        # ... (rest of the data display logic is the same)
        df["Sélection"] = False
        df['groups_list'] = df['groups'].copy()
        if 'groups' in df.columns: df['groups'] = df['groups'].apply(lambda g: ', '.join(g) if isinstance(g, list) else '')
        
        cols = df.columns.tolist()
        if 'email' in cols: cols.insert(0, cols.pop(cols.index('Sélection'))); df = df[cols]
        
        edited_df = st.data_editor(
            df,
            column_config={"Sélection": st.column_config.CheckboxColumn(required=False)},
            disabled=[c for c in df.columns if c != "Sélection"],
            use_container_width=True, hide_index=True, key=f"user_editor_{selected_profile_name}"
        )

        selected_rows = edited_df[edited_df["Sélection"]]
        
        st.write("Actions pour la sélection :")
        col1, col2, _ = st.columns([1, 1, 4])
        with col1:
            if st.button("✏️ Modifier", disabled=len(selected_rows) != 1):
                email_to_edit = selected_rows.iloc[0]["email"]
                original_df = pd.json_normalize(raw_users).set_index('email')
                st.session_state.user_to_edit = original_df.loc[email_to_edit]
                st.session_state.user_to_edit['groups_list'] = st.session_state.user_to_edit.get('groups', [])
                st.session_state.dialog_mode = 'edit'
                st.rerun()
        with col2:
            if st.button("🗑️ Supprimer", disabled=len(selected_rows) == 0):
                st.session_state.users_to_delete = selected_rows["email"].tolist()
                st.session_state.dialog_mode = 'delete'
                st.rerun()
    else:
        st.write("Aucun utilisateur trouvé pour ce profil.")

