import streamlit as st
import pandas as pd
from datetime import date, timedelta
from controllers.config_controller import get_active_adobe_configuration_details
from controllers.adobe_controller import get_report_suites, run_adobe_report

def render_adobe_dashboard_view():
    """
    Renders the Adobe Analytics Dashboard page.
    """
    st.title("📊 Adobe Analytics Dashboard Light")

    active_config = get_active_adobe_configuration_details()
    if not active_config:
        st.warning("Veuillez d'abord activer une configuration Adobe Analytics dans la page 'Configuration'.")
        return

    st.info(f"Configuration Adobe active : **{active_config.get('name')}**")

    # --- Step 1: Select Report Suite ---
    with st.spinner("Chargement des suites de rapports..."):
        suites = get_report_suites()
    
    if not suites:
        st.error("Impossible de charger les suites de rapports. Vérifiez la configuration et la connexion.")
        return

    suite_options = {suite['rsid']: f"{suite['name']} ({suite['rsid']})" for suite in suites}
    selected_rsid = st.selectbox(
        "1. Choisissez une suite de rapports (RSID)",
        options=list(suite_options.keys()),
        format_func=lambda rsid: suite_options[rsid]
    )

    # --- Step 2: Configure Report ---
    st.subheader("2. Configurez votre rapport")
    
    # Date Range
    today = date.today()
    last_week = today - timedelta(days=7)
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Date de début", value=last_week)
    end_date = col2.date_input("Date de fin", value=today)

    # Granularity and Metrics
    col3, col4 = st.columns(2)
    granularity = col3.selectbox(
        "Granularité",
        options=['day', 'hour', 'week', 'month'],
        index=0  # Default to 'day'
    )
    
    available_metrics = {
        "Pages Vues": "metrics/pageviews",
        "Visites": "metrics/visits",
        "Visiteurs Uniques": "metrics/visitors",
        "Occurrences": "metrics/occurrences",
        "Temps passé (secondes)": "metrics/timespent",
    }
    selected_metrics_names = col4.multiselect(
        "Métriques",
        options=list(available_metrics.keys()),
        default=list(available_metrics.keys())[0] # Default to Page Views
    )
    selected_metric_ids = [available_metrics[name] for name in selected_metrics_names]

    st.divider()

    # --- Step 3: Run Report and Display ---
    if st.button("🚀 Lancer le rapport", type="primary"):
        if not selected_rsid:
            st.error("Veuillez sélectionner une suite de rapports.")
            return
        if not selected_metric_ids:
            st.error("Veuillez sélectionner au moins une métrique.")
            return
        if start_date > end_date:
            st.error("La date de début ne peut pas être après la date de fin.")
            return

        date_range_str = f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        
        with st.spinner(f"Chargement des données pour '{suite_options[selected_rsid]}' ..."):
            report_df = run_adobe_report(
                rsid=selected_rsid,
                date_range=date_range_str,
                dimension="time", # Controller will handle mapping this
                metrics=selected_metric_ids,
                granularity=granularity
            )

        if report_df is not None and not report_df.empty:
            st.subheader("📈 Graphique chronologique")
            st.line_chart(report_df)
            
            st.subheader("📄 Données brutes")
            st.dataframe(report_df)
        elif report_df is not None:
             st.info("Aucune donnée retournée pour cette période ou cette configuration.")
        else:
            st.error("Une erreur est survenue lors de la récupération du rapport. Consultez les logs pour plus de détails.")

