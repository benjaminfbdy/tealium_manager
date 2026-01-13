import streamlit as st
import pandas as pd
from datetime import date, timedelta
from controllers.config_controller import get_active_adobe_configuration_details
from controllers.adobe_controller import get_report_suites, run_adobe_report
from utils.adobe_client import AdobeAnalyticsClient
from database import get_active_adobe_configuration

def render_adobe_dashboard_view():
    """
    Renders the Adobe Analytics Dashboard page with a simplified, time-series-focused interface.
    """
    st.title("📊 Adobe Analytics Dashboard Light")

    # --- Initialize session state for caching ---
    if "adobe_components" not in st.session_state: st.session_state.adobe_components = None
    if "selected_rsid" not in st.session_state: st.session_state.selected_rsid = None

    active_config = get_active_adobe_configuration_details()
    if not active_config:
        st.warning("Veuillez d'abord activer une configuration Adobe Analytics dans la page 'Configuration'.")
        return
    st.info(f"Configuration Adobe active : **{active_config.get('name')}**")

    # --- Step 1: Select Report Suite ---
    with st.spinner("Chargement des suites de rapports..."):
        suites, error_msg = get_report_suites()
    if error_msg: st.error(error_msg); return
    if not suites: st.warning("Aucune suite de rapports trouvée."); return

    suite_options = {suite['rsid']: f"{suite['name']} ({suite['rsid']})" for suite in suites}
    selected_rsid = st.selectbox("1. Choisissez une suite de rapports (RSID)", options=list(suite_options.keys()), format_func=lambda rsid: suite_options.get(rsid, rsid))

    # --- Step 2: Load components if RSID changes ---
    if selected_rsid and st.session_state.get('selected_rsid') != selected_rsid:
        st.session_state.selected_rsid = selected_rsid
        st.session_state.adobe_components = None # Reset on RSID change
        
        with st.spinner("Chargement des composants (dimensions, métriques, segments)..."):
            # Use the new controller function with caching logic
            from controllers.adobe_controller import get_or_refresh_components
            
            components, error_msg = get_or_refresh_components(selected_rsid)
            
            if error_msg:
                st.error(f"Erreur lors du chargement des composants : {error_msg}")
                st.session_state.adobe_components = None # Ensure it's cleared on error
            elif components:
                st.session_state.adobe_components = {
                    "dimensions": {item['id']: f"{item['name']} ({item.get('extraTitle', item['id'])})" for item in components.get('dimensions', [])},
                    "metrics": {item['id']: f"{item['name']} ({item['id']})" for item in components.get('metrics', [])},
                    "segments": {item['id']: f"{item['name']} ({item['id']})" for item in components.get('segments', [])},
                    "last_updated": components.get('last_updated')
                }
                
                # Show success message with cache status
                if components.get('last_updated'):
                    last_update_str = pd.to_datetime(components['last_updated'], unit='s').strftime('%Y-%m-%d %H:%M:%S')
                    st.success(f"Composants chargés depuis le cache (dernière MàJ: {last_update_str}).")
                else:
                    st.success("Composants chargés depuis l'API et mis en cache.")
            else:
                st.warning("Aucun composant n'a pu être chargé.")
                st.session_state.adobe_components = None

    # --- Step 3: Configure Report ---
    if st.session_state.selected_rsid and st.session_state.adobe_components:
        st.subheader("2. Configurez votre rapport chronologique")
        
        components = st.session_state.adobe_components
        
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Date de début", value=date.today() - timedelta(days=7))
        end_date = col2.date_input("Date de fin", value=date.today())

        granularity = st.selectbox("Granularité", options=['day', 'hour', 'week', 'month'], format_func=lambda o: {'day':'Jour', 'hour':'Heure', 'week':'Semaine', 'month':'Mois'}.get(o,o), index=0)

        selected_metric_ids = st.multiselect(
            "Métriques",
            options=list(components['metrics'].keys()),
            format_func=lambda mid: components['metrics'].get(mid, mid),
            default=["metrics/pageviews"] if "metrics/pageviews" in components['metrics'] else []
        )

        # Optional dimension to count
        dim_options = {None: "Aucune (total général)"}
        dim_options.update(components['dimensions'])
        count_dimension_id = st.selectbox("Dimension à dénombrer (Optionnel)", options=list(dim_options.keys()), format_func=lambda did: dim_options.get(did, did))

        # Optional segment
        seg_options = {None: "Aucun"}
        seg_options.update(components['segments'])
        segment_id = st.selectbox("Appliquer un segment (Optionnel)", options=list(seg_options.keys()), format_func=lambda sid: seg_options.get(sid, sid))

        st.divider()

        # --- Step 4: Run Report and Display ---
        if st.button("🚀 Lancer le rapport", type="primary"):
            if not selected_metric_ids: st.error("Veuillez sélectionner au moins une métrique."); return
            if start_date > end_date: st.error("La date de début ne peut pas être après la date de fin."); return

            start_datetime = f"{start_date.strftime('%Y-%m-%d')}T00:00:00"
            end_datetime = f"{end_date.strftime('%Y-%m-%d')}T23:59:59"
            date_range_str = f"{start_datetime}/{end_datetime}"
            
            with st.spinner("Génération du rapport en cours..."):
                try:
                    report_df = run_adobe_report(
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
                        st.error("Une erreur inattendue est survenue lors de la récupération du rapport.")
                except Exception as e:
                    st.error("Une erreur est survenue lors de la récupération du rapport. Consultez le terminal pour les logs détaillés.")
                    st.exception(e)


