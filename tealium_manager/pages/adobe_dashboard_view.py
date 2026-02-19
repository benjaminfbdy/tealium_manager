import streamlit as st
from views.component_renderers import setup_page
import pandas as pd
from datetime import date, timedelta
from controllers.adobe_controller import get_report_suites, run_adobe_report, get_or_refresh_components

def adobe_dashboard_page():
    """
    Renders the Adobe Analytics Dashboard page.
    """
    setup_page()
    st.title("📊 Requeteur Adobe")

    # --- Initialize session state ---
    if "adobe_components" not in st.session_state: st.session_state.adobe_components = None
    if "selected_rsid" not in st.session_state: st.session_state.selected_rsid = None

    # --- Get active config from session state ---
    active_config = st.session_state.get('active_adobe_config')
    active_profile_name = st.session_state.get('active_adobe_profile_name')

    if not active_config:
        st.warning("Veuillez d'abord activer une configuration Adobe dans la page 'Configuration Adobe'.")
        st.page_link("pages/2_Config_Adobe.py", label="Aller à la Configuration Adobe", icon="⚙️")
        st.stop()
    
    st.success(f"Configuration Adobe active : **{active_profile_name}** (`{active_config.get('global_company_id')}`)")

    # --- Step 1: Select Report Suite ---
    with st.spinner("Chargement des suites de rapports..."):
        suites, error_msg = get_report_suites(active_config)
    if error_msg: st.error(error_msg); st.stop()
    if not suites: st.warning("Aucune suite de rapports trouvée pour cette configuration."); st.stop()

    suite_options = {suite['rsid']: f"{suite['name']} ({suite['rsid']})" for suite in suites}
    selected_rsid = st.selectbox("1. Choisissez une suite de rapports (RSID)", options=list(suite_options.keys()), format_func=lambda rsid: suite_options.get(rsid, rsid))

    # --- Step 2: Load components if RSID changes ---
    if selected_rsid and st.session_state.get('selected_rsid') != selected_rsid:
        st.session_state.selected_rsid = selected_rsid
        st.session_state.adobe_components = None # Reset on RSID change
        
        with st.spinner("Chargement des composants (dimensions, métriques, segments)..."):
            components, error_msg = get_or_refresh_components(active_config, selected_rsid)
            
            if error_msg:
                st.error(f"Erreur lors du chargement des composants : {error_msg}")
            elif components:
                st.session_state.adobe_components = {
                    "dimensions": {item['id']: f"{item['name']} ({item.get('extraTitle', item['id'])})" for item in components.get('dimensions', [])},
                    "metrics": {item['id']: f"{item['name']} ({item['id']})" for item in components.get('metrics', [])},
                    "segments": {item['id']: f"{item['name']} ({item['id']})" for item in components.get('segments', [])},
                    "last_updated": components.get('last_updated')
                }
                if components.get('last_updated'):
                    last_update_str = pd.to_datetime(components['last_updated'], unit='s').strftime('%Y-%m-%d %H:%M:%S')
                    st.success(f"Composants chargés depuis le cache (dernière MàJ: {last_update_str}).")
                else:
                    st.success("Composants chargés depuis l'API et mis en cache.")
            else:
                st.warning("Aucun composant n'a pu être chargé.")

    # --- Step 3: Configure Report ---
    if st.session_state.selected_rsid and st.session_state.adobe_components:
        st.subheader("2. Configurez votre rapport")
        components = st.session_state.adobe_components
        
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Date de début", value=date.today() - timedelta(days=7))
        end_date = col2.date_input("Date de fin", value=date.today())

        granularity = st.selectbox("Granularité", options=['day', 'hour', 'week', 'month'], format_func=lambda o: {'day':'Jour', 'hour':'Heure', 'week':'Semaine', 'month':'Mois'}.get(o,o), index=0)
        selected_metric_ids = st.multiselect("Métriques", options=list(components['metrics'].keys()), format_func=lambda mid: components['metrics'].get(mid, mid), default=["metrics/pageviews"] if "metrics/pageviews" in components['metrics'] else [])
        
        dim_options = {None: "Aucune (total général)"}
        dim_options.update(components['dimensions'])
        count_dimension_id = st.selectbox("Dimension à dénombrer (Optionnel)", options=list(dim_options.keys()), format_func=lambda did: dim_options.get(did, did))

        seg_options = {None: "Aucun"}
        seg_options.update(components['segments'])
        segment_id = st.selectbox("Appliquer un segment (Optionnel)", options=list(seg_options.keys()), format_func=lambda sid: seg_options.get(sid, sid))

        st.divider()

        # --- Step 4: Run Report and Display ---
        if st.button("🚀 Lancer le rapport", type="primary"):
            if not selected_metric_ids: st.error("Veuillez sélectionner au moins une métrique."); st.stop()
            if start_date > end_date: st.error("La date de début ne peut pas être après la date de fin."); st.stop()

            date_range_str = f"{start_date.strftime('%Y-%m-%d')}T00:00:00/{end_date.strftime('%Y-%m-%d')}T23:59:59"
            
            with st.spinner("Génération du rapport..."):
                report_df = run_adobe_report(
                    adobe_config=active_config,
                    rsid=selected_rsid,
                    date_range=date_range_str,
                    metrics=selected_metric_ids,
                    granularity=granularity,
                    count_dimension=count_dimension_id,
                    segment_id=segment_id
                )
                if report_df is not None and not report_df.empty:
                    st.subheader("📈 Résultat du rapport")
                    st.line_chart(report_df)
                    st.subheader("📄 Données brutes")
                    st.dataframe(report_df)
                elif report_df is not None:
                    st.info("Aucune donnée retournée pour cette période ou cette configuration.")
                else:
                    st.error("Une erreur est survenue lors de la récupération du rapport.")

if __name__ == "__main__":
    adobe_dashboard_page()
