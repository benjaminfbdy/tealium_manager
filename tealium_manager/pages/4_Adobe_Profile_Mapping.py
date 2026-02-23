import streamlit as st
import pandas as pd
from typing import List, Dict

from controllers.adobe_user_controller import get_users_for_organization

st.set_page_config(page_title="Cartographie des Profils Adobe", layout="wide")
st.title("🗺️ Cartographie des Profils de Produit Adobe")

# --- Main View ---
try:
    adobe_profiles = st.secrets.get("adobe_profiles", {}).to_dict()
    profile_names = list(adobe_profiles.keys())
    if not profile_names:
        st.warning("Aucun profil Adobe trouvé dans [adobe_profiles] dans secrets.toml.")
        st.stop()
except (AttributeError, TypeError):
    st.error("Configuration [adobe_profiles] invalide dans secrets.toml.")
    st.stop()

selected_profile_name = st.selectbox("Sélectionnez un profil Adobe à analyser", options=profile_names)

if selected_profile_name:
    selected_config = adobe_profiles[selected_profile_name]
    st.info(f"Analyse des profils pour : **{selected_profile_name}**")

    # Fetch user data using the cached controller function
    with st.spinner("Chargement des données utilisateur..."):
        raw_users = get_users_for_organization(
            config_tuple=tuple(sorted(selected_config.items()))
        )

    if raw_users:
        # --- Data Processing Logic ---
        profile_mapping = {}
        for user in raw_users:
            user_email = user.get("email")
            if not user_email:
                continue
            
            groups = user.get("groups", [])
            if not isinstance(groups, list):
                continue

            for group_name in groups:
                if group_name not in profile_mapping:
                    profile_mapping[group_name] = []
                profile_mapping[group_name].append(user_email)
        
        if not profile_mapping:
            st.warning("Aucun utilisateur n'est assigné à un profil de produit dans cette organisation.")
            st.stop()
            
        st.header(f"Distribution des {len(raw_users)} utilisateurs dans {len(profile_mapping)} profils")

        # --- Display Logic ---
        sorted_profiles = sorted(profile_mapping.keys())

        for profile_name in sorted_profiles:
            members = profile_mapping[profile_name]
            with st.expander(f"**{profile_name}** ({len(members)} membres)"):
                st.dataframe(pd.DataFrame({"Membres": members}), use_container_width=True, hide_index=True)
    else:
        st.write("Aucun utilisateur trouvé pour ce profil.")

# Add the link to this new page in the sidebar navigation
# I need to modify `views/component_renderers.py` for this.
