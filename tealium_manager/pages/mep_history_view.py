import streamlit as st
from views.component_renderers import setup_page
from typing import List, Dict, Any
import pandas as pd
from controllers.mep_controller import get_meps_data

def render_mep_history(revisions_data: List[Dict[str, Any]]):
    """
    Renders the UI for exploring and comparing profile revisions (MEPs).
    """
    if not revisions_data:
        st.info("Aucune MEP (Mise en Prod) trouvée pour le profil actif.")
        return

    # Initialize session state for selection
    if 'selected_meps' not in st.session_state:
        st.session_state.selected_meps = []

    # --- Display Table with Checkboxes ---
    st.subheader("Révisions Publiées en Production")
    
    # Create header
    cols = st.columns([0.5, 1.5, 4, 2, 2])
    cols[0].markdown("**✅**")
    cols[1].markdown("**🆔 Version**")
    cols[2].markdown("**📝 Notes**")
    cols[3].markdown("**👤 Auteur**")
    cols[4].markdown("**🚀 Date**")
    st.markdown("---")

    with st.container(height=500):
        new_selection = []
        for rev in revisions_data:
            rev_id = rev.get("revision_id")
            prod_publish_date = "N/A"
            for pub in rev.get("publish_history", []):
                if pub.get("environment") == "prod":
                    prod_publish_date = pd.to_datetime(pub.get('timestamp_iso')).strftime('%Y-%m-%d %H:%M')
                    break

            cols = st.columns([0.5, 1.5, 4, 2, 2])
            is_selected = cols[0].checkbox("Select", key=f"mep_{rev_id}", value=(rev_id in st.session_state.selected_meps), label_visibility="collapsed")
            
            if is_selected:
                new_selection.append(rev_id)

            cols[1].text(rev_id)
            cols[2].text(rev.get("comment", "N/A"))
            cols[3].text(rev.get("created_by", "N/A"))
            cols[4].text(prod_publish_date)

    if sorted(new_selection) != sorted(st.session_state.selected_meps):
        st.session_state.selected_meps = new_selection
        st.rerun()

    st.markdown("---")
    
    # --- Contextual Action Buttons ---
    num_selected = len(st.session_state.selected_meps)
    
    if num_selected == 1:
        st.info(f"**1 MEP sélectionnée :** `{st.session_state.selected_meps[0]}`")
        if st.button("🔭 Explorer le profil de cette version", use_container_width=True, disabled=True): # TODO: Re-implement explorer
            st.warning("La fonction d'exploration n'est pas encore ré-implémentée.")
            
    elif num_selected == 2:
        st.info(f"**2 MEPs sélectionnées pour la comparaison :**\n- `{st.session_state.selected_meps[0]}`\n- `{st.session_state.selected_meps[1]}`")
        if st.button("⚖️ Comparer les deux versions", use_container_width=True, disabled=True): # TODO: Re-implement comparison
            st.warning("La fonction de comparaison n'est pas encore ré-implémentée.")

    elif num_selected > 2:
        st.warning("Veuillez sélectionner seulement 1 ou 2 MEPs à la fois.")
        
    else:
        st.info("Sélectionnez 1 MEP pour l'explorer, ou 2 pour les comparer.")

def mep_history_page():
    """Main function to render the MEP History page."""
    setup_page()
    st.title("📜 Historique des MEP (Mises en Prod)")

    active_config = st.session_state.get('active_tealium_config')
    active_profile_name = st.session_state.get('active_tealium_profile_name')

    if not active_config:
        st.warning("Veuillez d'abord sélectionner un profil actif dans la page 'Configuration Tealium'.")
        st.page_link("pages/1_Config_Tealium.py", label="Aller à la Configuration Tealium", icon="⚙️")
        st.stop()

    st.success(f"Profil actif : **{active_profile_name}** (`{active_config.get('account')}/{active_config.get('profile')}`)")
    
    with st.spinner("Chargement de l'historique des MEPs..."):
        meps_data = get_meps_data(active_config)
    
    render_mep_history(meps_data)

if __name__ == "__main__":
    mep_history_page()
