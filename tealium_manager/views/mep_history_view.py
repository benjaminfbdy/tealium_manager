import streamlit as st
from typing import List, Dict, Any
import pandas as pd

def render_mep_history(revisions_data: List[Dict[str, Any]]):
    """
    Renders the UI for exploring and comparing profile revisions (MEPs).
    """
    st.header("Historique des MEP (Mises en Prod)")

    if not revisions_data:
        st.info("Aucune MEP trouvée pour le profil actif.")
        return

    # Initialize session state for selection
    if 'selected_meps' not in st.session_state:
        st.session_state.selected_meps = []

    # --- Display Table with Checkboxes ---
    
    # Create header
    cols = st.columns([0.5, 1.5, 4, 2, 2])
    cols[0].markdown("**✅**")
    cols[1].markdown("**🆔 Version**")
    cols[2].markdown("**📝 Notes**")
    cols[3].markdown("**👤 Auteur**")
    cols[4].markdown("**🚀 Date**")
    st.markdown("---")

    # Create a scrollable container for the table rows
    with st.container(height=500):
        new_selection = []
        for rev in revisions_data:
            rev_id = rev.get("revision_id")
            # Find the prod publish date
            prod_publish_date = "N/A"
            for pub in rev.get("publish_history", []):
                if pub.get("environment") == "prod":
                    prod_publish_date = pd.to_datetime(pub.get('timestamp_iso')).strftime('%Y-%m-%d %H:%M')
                    break

            cols = st.columns([0.5, 1.5, 4, 2, 2])
            is_selected = cols[0].checkbox("Sélectionner", key=f"mep_{rev_id}", value=(rev_id in st.session_state.selected_meps), label_visibility="collapsed")
            
            if is_selected:
                new_selection.append(rev_id)

            cols[1].text(rev_id)
            cols[2].text(rev.get("comment", "N/A"))
            cols[3].text(rev.get("created_by", "N/A"))
            cols[4].text(prod_publish_date)

    # Update session state
    if sorted(new_selection) != sorted(st.session_state.selected_meps):
        st.session_state.selected_meps = new_selection
        st.rerun()

    st.markdown("---")

    # --- Contextual Action Buttons ---
    
    num_selected = len(st.session_state.selected_meps)
    
    if num_selected == 1:
        st.info(f"**1 MEP sélectionnée :** `{st.session_state.selected_meps[0]}`")
        if st.button("🔭 Explorer le profil de cette version", use_container_width=True):
            # This navigation logic will be fully implemented later
            st.session_state.page = "profile_explorer"
            st.session_state.selected_version = st.session_state.selected_meps[0]
            st.rerun()
            
    elif num_selected == 2:
        st.info(f"**2 MEPs sélectionnées pour la comparaison :**\n- `{st.session_state.selected_meps[0]}`\n- `{st.session_state.selected_meps[1]}`")
        if st.button("⚖️ Comparer les deux versions", use_container_width=True):
            st.session_state.meps_to_compare = st.session_state.selected_meps
            st.session_state.page = "comparison"
            st.rerun()

    elif num_selected > 2:
        st.warning("Veuillez sélectionner seulement 1 ou 2 MEPs à la fois.")
        
    else:
        st.info("Sélectionnez 1 MEP pour l'explorer, ou 2 pour les comparer.")
