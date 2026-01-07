import streamlit as st
import pandas as pd
import json
from controllers.config_controller import get_all_configurations
from controllers.mapping_controller import process_mappings

def render_mapping_checker_view():
    st.header("🔎 Vérificateur de Mapping Adobe Analytics")

    st.info("""
    **Objectif**: Comparer les mappings Adobe Analytics de différentes sources (Tealium iQ, EventStream) 
    à un référentiel cible pour identifier les écarts.
    """)

    # --- 1. File Uploaders and Profile Selection ---
    st.subheader("1. Charger les sources de données")
    col1, col2, col3 = st.columns(3)

    with col1:
        target_file = st.file_uploader(
            "Référentiel Cible (CSV)", 
            type=['csv'],
            help="Fichier CSV avec les mappings attendus, séparateur ';'"
        )

    with col2:
        eventstream_file = st.file_uploader(
            "Fichier Mapping EventStream (JSON, optionnel)", 
            type=['json']
        )
    
    with col3:
        try:
            configurations = get_all_configurations()
            profile_options = {p['name']: p for p in configurations}
            tiq_profile_name = st.selectbox(
                "Profil Tealium iQ (optionnel)", 
                options=[None] + list(profile_options.keys())
            )
        except Exception as e:
            st.error(f"Impossible de charger les profils TiQ : {e}")
            tiq_profile_name = None

    # --- 2. Comparison Execution ---
    st.subheader("2. Lancer la comparaison")
    if st.button("Analyser les mappings"):
        if not target_file:
            st.warning("Veuillez charger le fichier de référentiel cible (CSV).")
        elif not eventstream_file and not tiq_profile_name:
            st.warning("Veuillez fournir au moins une source de données à comparer (fichier EventStream ou profil TiQ).")
        else:
            with st.spinner("Analyse en cours..."):
                try:
                    # Load data from uploaded files, handling potential encoding issues
                    try:
                        target_df = pd.read_csv(target_file, sep=';', encoding='utf-8')
                    except UnicodeDecodeError:
                        target_file.seek(0) # Reset file pointer after the failed read attempt
                        target_df = pd.read_csv(target_file, sep=';', encoding='latin1')

                    es_data = None
                    if eventstream_file:
                        es_data = json.load(eventstream_file)

                    # Get selected TiQ profile config
                    tiq_profile_config = profile_options.get(tiq_profile_name) if tiq_profile_name else None

                    # Process and get results
                    results_df = process_mappings(target_df, es_data, tiq_profile_config)

                    # --- 3. Display Results ---
                    st.subheader("3. Synthèse de la comparaison")
                    
                    # Display metrics
                    ok_count = len(results_df[results_df['status'] == 'OK'])
                    missing_count = len(results_df[results_df['status'] == 'Manquant'])
                    ko_count = len(results_df[results_df['status'] == 'KO'])
                    extra_count = len(results_df[results_df['status'] == 'Extra'])

                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    m_col1.metric("Mappings 'OK'", ok_count)
                    m_col2.metric("Mappings 'Manquant'", missing_count, delta_color="inverse")
                    m_col3.metric("Mappings 'KO'", ko_count, delta_color="inverse")
                    m_col4.metric("Mappings 'Extra'", extra_count)
                    
                    # Display dataframe with filters
                    st.write("Détails des mappings :")
                    status_filter = st.multiselect(
                        "Filtrer par statut",
                        options=results_df['status'].unique(),
                        default=results_df['status'].unique()
                    )
                    
                    filtered_df = results_df[results_df['status'].isin(status_filter)]
                    st.dataframe(filtered_df)

                except Exception as e:
                    st.error(f"Une erreur est survenue lors du traitement : {e}")
                    st.exception(e) # Show full traceback for debugging

