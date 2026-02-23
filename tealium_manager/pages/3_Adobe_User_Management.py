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
                # --- UPDATE LOGIC ---
                user_data = st.session_state.user_to_edit
                commands = []

                # 1. Check for firstname/lastname changes
                update_payload = {}
                if user_data.get('firstname') != firstname:
                    update_payload['firstname'] = firstname
                if user_data.get('lastname') != lastname:
                    update_payload['lastname'] = lastname
                
                if update_payload:
                    commands.append({'update': update_payload})

                # 2. Check for group changes
                # Handle cases where a user may not have any groups (value can be NaN)
                raw_original_groups = user_data.get('groups_list')
                original_groups = set(raw_original_groups) if isinstance(raw_original_groups, list) else set()
                new_groups = set(product_profiles)

                groups_to_add = list(new_groups - original_groups)
                if groups_to_add:
                    commands.append({'add': {'group': groups_to_add}})
                
                groups_to_remove = list(original_groups - new_groups)
                if groups_to_remove:
                    commands.append({'remove': {'group': groups_to_remove}})

                if not commands:
                    st.toast("Aucune modification détectée.", icon="🤷")
                else:
                    with st.spinner("Mise à jour de l'utilisateur..."):
                        result = asyncio.run(update_user(
                            config=config,
                            email=email,
                            commands=commands
                        ))
                    if result.get("success"):
                        st.session_state.last_op_success_message = f"Utilisateur {email} mis à jour avec succès !"
                        get_users_for_organization.clear() # Clear cache on success
                    else:
                        st.error(f"Erreur lors de la mise à jour : {result.get('error', 'Erreur inconnue')}")
            else:
                # --- ADD LOGIC ---
                with st.spinner(f"Ajout de l'utilisateur {email}..."):
                    result = asyncio.run(add_user(
                        config=config,
                        email=email,
                        firstname=firstname,
                        lastname=lastname,
                        groups=product_profiles
                    ))
                if result.get("success"):
                    st.session_state.last_op_success_message = f"Utilisateur {email} ajouté avec succès !"
                    get_users_for_organization.clear() # Clear cache on success
                else:
                    st.error(f"Erreur lors de l'ajout : {result.get('error', 'Erreur inconnue')}")
            
            st.rerun()

@st.dialog("Confirmer la suppression")
def confirm_delete_dialog(config: dict):
    """Dialog to confirm user deletion."""
    users_to_delete = st.session_state.get('users_to_delete', [])
    st.warning(f"Êtes-vous sûr de vouloir supprimer définitivement {len(users_to_delete)} utilisateur(s) ? Cette action est irréversible.", icon="⚠️")
    
    with st.expander("Utilisateurs à supprimer"):
        for email in users_to_delete:
            st.markdown(f"- `{email}`")

    st.write("")

    col1, col2, _ = st.columns([2, 2, 1])
    with col1:
        if st.button("🔴 Confirmer la suppression"):
            success_count = 0
            error_count = 0
            error_messages = []

            with st.spinner(f"Suppression de {len(users_to_delete)} utilisateur(s) en cours..."):
                for email in users_to_delete:
                    result = asyncio.run(delete_user(config=config, email=email))
                    if result.get("success"):
                        success_count += 1
                    else:
                        error_count += 1
                        error_messages.append(f"`{email}`: {result.get('error', 'Erreur inconnue')}")
            
            if success_count > 0:
                st.session_state.last_op_success_message = f"{success_count} utilisateur(s) ont été supprimé(s) avec succès."
                get_users_for_organization.clear()
            
            if error_count > 0:
                errors = "\\n".join(error_messages)
                st.session_state.last_op_error_message = f"Échec de la suppression pour {error_count} utilisateur(s) :\\n{errors}"

            st.session_state.dialog_mode = None
            st.rerun()

    with col2:
        if st.button("Annuler"):
            st.session_state.dialog_mode = None
            st.rerun()

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

    # Display success message from previous operation if any
    if "last_op_success_message" in st.session_state and st.session_state.last_op_success_message:
        st.success(st.session_state.last_op_success_message, icon="✅")
        st.session_state.last_op_success_message = None # Clear after displaying

    # Display error message from previous operation if any
    if "last_op_error_message" in st.session_state and st.session_state.last_op_error_message:
        st.error(st.session_state.last_op_error_message, icon="❌")
        st.session_state.last_op_error_message = None # Clear after displaying

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
        # Keep a copy of the original groups list for the edit dialog
        df['groups_list'] = df['groups'].copy()
        if 'groups' in df.columns:
            df['groups'] = df['groups'].apply(lambda g: ', '.join(g) if isinstance(g, list) else '')

        grid_key = f"user_grid_{selected_profile_name}"
        
        # Retrieve selection from session state
        selected_indices = []
        if grid_key in st.session_state:
            selected_indices = st.session_state[grid_key].selection.rows
        
        selected_rows = df.iloc[selected_indices]

        # --- Actions and Selection Count ---
        st.write(f"**{len(selected_rows)}** utilisateur(s) sélectionné(s)")
        
        st.write("Actions pour la sélection :")
        col1, col2, _ = st.columns([1, 1, 4])
        with col1:
            if st.button("✏️ Modifier", disabled=len(selected_rows) != 1):
                email_to_edit = selected_rows.iloc[0]["email"]
                # Re-normalize to get a fresh DataFrame for accurate data lookup
                original_df = pd.json_normalize(raw_users)
                user_to_edit = original_df[original_df['email'] == email_to_edit].iloc[0].copy()
                user_to_edit['groups_list'] = user_to_edit.get('groups', [])
                
                st.session_state.user_to_edit = user_to_edit
                st.session_state.dialog_mode = 'edit'
                st.rerun()
        with col2:
            if st.button("🗑️ Supprimer", disabled=len(selected_rows) == 0):
                st.session_state.users_to_delete = selected_rows["email"].tolist()
                st.session_state.dialog_mode = 'delete'
                st.rerun()

        # --- Data Grid ---
        # Don't display 'groups_list', it's for internal use
        display_df = df.drop(columns=['groups_list'], errors='ignore')
        st.dataframe(
            display_df,
            key=grid_key,
            on_select="rerun",
            selection_mode="multi-row",
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("Aucun utilisateur trouvé pour ce profil.")

