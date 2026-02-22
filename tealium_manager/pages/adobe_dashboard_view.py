import streamlit as st
from views.component_renderers import setup_page
import pandas as pd
from datetime import date, timedelta
from controllers.adobe_controller import run_adobe_report
from utils.adobe_repo import get_adobe_components_cache_info, load_adobe_components

def adobe_dashboard_page():
    """
    Renders the Adobe Analytics Dashboard (requeteur) page,
    using a cache-first approach for components.
    """
    setup_page()
    st.title("📊 Requeteur Adobe")
    st.write("Construisez des requêtes en utilisant les composants (dimensions, métriques) préalablement mis en cache.")

    # --- 1. Select Adobe Account from secrets.toml ---
    try:
        adobe_profiles = st.secrets.adobe_profiles.to_dict()
        if not adobe_profiles:
            st.warning("Aucun profil Adobe n'est configuré dans `secrets.toml`.")
            st.page_link("pages/2_Config_Adobe.py", label="Aller à la Configuration", icon="⚙️")
            st.stop()
    except (AttributeError, KeyError):
        st.error("La section `[adobe_profiles]` est mal configurée ou manquante dans `secrets.toml`.")
        st.stop()

    profile_options = list(adobe_profiles.keys())
    selected_profile_name = st.selectbox("1. Choisissez un compte Adobe", options=profile_options)

    if not selected_profile_name:
        st.stop()

    active_config = adobe_profiles[selected_profile_name]
    st.success(f"Compte actif : **{selected_profile_name}** (`{active_config.get('global_company_id')}`)")

    # --- 2. Select a CACHED Report Suite ---
    try:
        all_cached_rsids_info = get_adobe_components_cache_info()
        # We don't have company_id in the cache table, so for now we show all cached RSIDs.
        # A potential improvement would be to add company_id to the adobe_components table.
        cached_rsid_options = {item['rsid']: item['rsid'] for item in all_cached_rsids_info}

        if not cached_rsid_options:
            st.warning("Aucune Report Suite n'a de composants en cache. Veuillez en sélectionner et rafraîchir depuis la page de configuration.")
            st.page_link("pages/2_Config_Adobe.py", label="Aller à la Configuration Adobe", icon="⚙️")
            st.stop()

        def format_rsid_option(rsid):
            # We don't have the RSID name here, just the ID.
            return rsid

        selected_rsid = st.selectbox(
            "2. Choisissez une Report Suite (uniquement celles en cache)",
            options=list(cached_rsid_options.keys()),
            format_func=format_rsid_option
        )

    except Exception as e:
        st.error(f"Erreur lors de la lecture du cache des composants : {e}")
        st.stop()

    # --- 3. Load components from cache and build the report ---
    if selected_rsid:
        components = load_adobe_components(selected_rsid)
        
        if not components:
            st.error(f"Impossible de charger les composants pour la RSID '{selected_rsid}' depuis le cache, bien qu'elle soit listée. Le cache est peut-être corrompu.")
            st.stop()
        
        last_update_str = pd.to_datetime(components.get('last_updated', 0), unit='s').strftime('%d/%m/%Y %H:%M')
        st.info(f"Composants chargés depuis le cache (dernière mise à jour : {last_update_str}).")

        st.subheader("3. Configurez votre rapport")
        
        # Prepare component dictionaries for selectboxes
        comp_dims = {item['id']: f"{item['name']} ({item.get('extraTitle', item['id'])})" for item in components.get('dimensions', [])}
        comp_mets = {item['id']: f"{item['name']} ({item['id']})" for item in components.get('metrics', [])}
        comp_segs = {item['id']: f"{item['name']} ({item['id']})" for item in components.get('segments', [])}
        
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Date de début", value=date.today() - timedelta(days=7))
        end_date = col2.date_input("Date de fin", value=date.today())

        granularity = st.selectbox("Granularité", options=['day', 'hour', 'week', 'month'], format_func=lambda o: {'day':'Jour', 'hour':'Heure', 'week':'Semaine', 'month':'Mois'}.get(o,o), index=0)
        selected_metric_ids = st.multiselect("Métriques", options=list(comp_mets.keys()), format_func=lambda mid: comp_mets.get(mid, mid), default=["metrics/pageviews"] if "metrics/pageviews" in comp_mets else [])
        
        dim_options = {None: "Aucune (total général)"}
        dim_options.update(comp_dims)
        count_dimension_id = st.selectbox("Dimension à dénombrer (Optionnel)", options=list(dim_options.keys()), format_func=lambda did: dim_options.get(did, did))

        seg_options = {None: "Aucun"}
        seg_options.update(comp_segs)
        segment_id = st.selectbox("Appliquer un segment (Optionnel)", options=list(seg_options.keys()), format_func=lambda sid: seg_options.get(sid, sid))

        st.divider()

        # --- 4. Run Report and Display ---
        if st.button("🚀 Lancer le rapport", type="primary"):
            if not selected_metric_ids: st.error("Veuillez sélectionner au moins une métrique."); st.stop()
            if start_date > end_date: st.error("La date de début ne peut pas être après la date de fin."); st.stop()

            date_range_str = f"{start_date.strftime('%Y-%m-%d')}T00:00:00/{end_date.strftime('%Y-%m-%d')}T23:59:59"
            
            with st.spinner("Génération du rapport... (appel API en cours)"):
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
