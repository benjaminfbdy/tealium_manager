import streamlit as st
import pandas as pd
import json
from datetime import date, timedelta
from controllers.config_controller import get_all_adobe_configurations
from controllers.adobe_controller import (
    get_report_suites, 
    get_or_refresh_components, 
    handle_save_report, 
    handle_update_report,
    get_all_saved_reports, 
    handle_delete_report,
    run_saved_report,
)

def render_adobe_reports_view():
    st.title("📑 Rapports")
    
    # --- Navigation State Management ---
    # Define constants for navigation options
    NAV_EXECUTE = "🚀 Exécuter des Rapports"
    NAV_CREATE = "➕ Créer un Nouveau Rapport"
    NAV_EDIT = "✏️ Modifier le Rapport"

    if "report_nav_selection" not in st.session_state:
        st.session_state.report_nav_selection = NAV_EXECUTE
    
    if "report_to_edit" not in st.session_state:
        st.session_state.report_to_edit = None

    if "active_report_results" not in st.session_state:
        st.session_state.active_report_results = []

    # Navigation Bar
    # Dynamic label for the second tab if editing
    create_tab_label = NAV_EDIT if st.session_state.report_to_edit else NAV_CREATE
    
    # --- FIX: Decouple widget from state to allow programmatic navigation ---
    options = [NAV_EXECUTE, create_tab_label]
    try:
        nav_index = options.index(st.session_state.report_nav_selection)
    except ValueError:
        nav_index = 0

    mode = st.radio("Navigation", options, 
                    index=nav_index,
                    label_visibility="collapsed",
                    horizontal=True)
    
    # Sync state on manual change
    if mode != st.session_state.report_nav_selection:
        st.session_state.report_nav_selection = mode
        st.rerun()

    # --- TAB 1: EXECUTION ---
    if mode == NAV_EXECUTE:
        # Clear edit state if we navigate back to list manually
        if st.session_state.report_to_edit:
            st.session_state.report_to_edit = None
            st.rerun()

        st.subheader("Rapports Sauvegardés")
        saved_reports = get_all_saved_reports()
        
        if not saved_reports:
            st.info("Aucun rapport sauvegardé. Allez dans l'onglet 'Créer' pour commencer.")
        else:
            # Date selection for execution
            st.markdown("### 1. Choisissez la période")
            col_d1, col_d2 = st.columns(2)
            start_date = col_d1.date_input("Date de début", value=date.today() - timedelta(days=7), key="exec_start")
            end_date = col_d2.date_input("Date de fin", value=date.today(), key="exec_end")
            
            # Report selection
            st.markdown("### 2. Sélectionnez les rapports")
            selected_report_ids = []
            
            # Header
            cols = st.columns([1, 3, 2, 2, 1.5])
            cols[0].write("**Sel.**")
            cols[1].write("**Nom du Rapport**")
            cols[2].write("**Compte Adobe**")
            cols[3].write("**RSID**")
            cols[4].write("**Action**")
            st.divider()
            
            for report in saved_reports:
                cols = st.columns([1, 3, 2, 2, 1.5])
                if cols[0].checkbox("Sélectionner", key=f"sel_{report['id']}", label_visibility="collapsed"):
                    selected_report_ids.append(report)
                
                cols[1].write(f"**{report['name']}**")
                cols[2].caption(report['adobe_config_name'])
                cols[3].caption(report['rsid'])
                
                # Action buttons
                col_actions = cols[4].columns(2)
                if col_actions[0].button("✏️", key=f"edit_{report['id']}", help="Modifier"):
                    st.session_state.report_to_edit = report
                    st.session_state.report_nav_selection = NAV_EDIT # Switch tab explicitly
                    st.rerun()

                if col_actions[1].button("🗑️", key=f"del_{report['id']}", help="Supprimer"):
                    handle_delete_report(report['id'])
                    st.rerun()
            
            st.divider()
            
            if st.button(f"▶️ Lancer les {len(selected_report_ids)} rapports sélectionnés", type="primary"):
                if not selected_report_ids:
                    st.warning("Sélectionnez au moins un rapport.")
                else:
                    # Clear previous results
                    st.session_state.active_report_results = []
                    
                    date_range = f"{start_date.strftime('%Y-%m-%d')}T00:00:00/{end_date.strftime('%Y-%m-%d')}T23:59:59"
                    
                    progress_bar = st.progress(0)
                    
                    for i, report in enumerate(selected_report_ids):
                        # Run report
                        df, status = run_saved_report(report, date_range)
                        
                        # Store result in session state
                        st.session_state.active_report_results.append({
                            "report": report,
                            "df": df,
                            "status": status,
                            "start_date": start_date # For CSV filename
                        })
                        
                        progress_bar.progress((i + 1) / len(selected_report_ids))
                    
                    st.success("Traitement terminé !")

            # --- Display Results (Persistent) ---
            if st.session_state.active_report_results:
                st.divider()
                st.subheader("Résultats")
                
                for res in st.session_state.active_report_results:
                    report = res['report']
                    df = res['df']
                    status = res['status']
                    
                    if df is not None and not df.empty:
                        # Use expanded=True by default for results, or manage state if needed.
                        # Since we are iterating, we rely on Streamlit's key matching.
                        with st.expander(f"✅ Résultat : {report['name']}", expanded=True):
                            # Add 'Show Curve' column for interaction
                            df_display = df.copy()
                            # Add column at the end
                            df_display["📈"] = False
                            
                            # Configure columns: Hide internal IDs, format Curve checkbox
                            column_config = {
                                "_segment_id": None, # Hidden
                                "_item_id": None,    # Hidden
                                "📈": st.column_config.CheckboxColumn(
                                    "Courbe",
                                    help="Afficher l'évolution",
                                    default=False,
                                    width="small"
                                )
                            }
                            
                            edited_df = st.data_editor(
                                df_display,
                                column_config=column_config,
                                disabled=[c for c in df_display.columns if c != "📈"],
                                hide_index=True,
                                key=f"editor_{report['id']}"
                            )
                            
                            # Check for selected rows to plot curves
                            selected_rows = edited_df[edited_df["📈"] == True]
                            for idx, row in selected_rows.iterrows():
                                item_name = row.get('Segment') or row.get('Item')
                                item_id = row.get('_segment_id') or row.get('_item_id')
                                
                                if item_id:
                                    st.caption(f"📉 Évolution : **{item_name}**")
                                    
                                    # Extract time-series data directly from the row
                                    meta_cols = ['Segment', 'Item', '_segment_id', '_item_id', '📈']
                                    data_cols = [c for c in row.index if c not in meta_cols]
                                    
                                    if data_cols:
                                        chart_rows = {}
                                        for col_name in data_cols:
                                            val = row[col_name]
                                            if "(" in col_name and col_name.endswith(")"):
                                                date_part = col_name.split(" (")[0]
                                                metric_part = col_name.split(" (")[1][:-1]
                                            else:
                                                date_part = col_name
                                                metric_part = "Valeur"
                                            
                                            if date_part not in chart_rows:
                                                chart_rows[date_part] = {}
                                            chart_rows[date_part][metric_part] = val
                                        
                                        chart_df = pd.DataFrame.from_dict(chart_rows, orient='index')
                                        try:
                                            chart_df.index = pd.to_datetime(chart_df.index)
                                            chart_df.sort_index(inplace=True)
                                        except:
                                            pass 
                                        st.line_chart(chart_df)
                                    else:
                                        st.warning("Pas de données temporelles trouvées.")
                            
                            st.download_button(
                                f"Télécharger CSV ({report['name']})",
                                df.to_csv().encode('utf-8'),
                                f"{report['name']}_{res['start_date']}.csv",
                                "text/csv"
                            )
                    else:
                        st.error(f"❌ Erreur sur {report['name']}: {status}")

    # --- TAB 2: CREATION ---
    elif mode == create_tab_label:
        is_editing = st.session_state.report_to_edit is not None
        edit_data = st.session_state.report_to_edit
        edit_def = json.loads(edit_data['definition']) if is_editing and 'definition' in edit_data else {}

        st.subheader("Modifier le rapport" if is_editing else "Définir un nouveau rapport")
        
        if is_editing:
            st.info(f"Modification de : **{edit_data['name']}**")
            if st.button("Annuler l'édition"):
                st.session_state.report_to_edit = None
                st.session_state.report_nav_selection = NAV_EXECUTE
                st.rerun()
        
        # 1. Select Config
        configs = get_all_adobe_configurations()
        config_opts = {c['name']: c for c in configs}
        
        # Determine default index for config
        config_index = 0
        if is_editing and edit_data['adobe_config_name'] in list(config_opts.keys()):
            config_index = list(config_opts.keys()).index(edit_data['adobe_config_name'])

        selected_config_name = st.selectbox("Compte Adobe", options=list(config_opts.keys()), index=config_index)
        
        if selected_config_name:
            # 2. Select RSID (Need to fetch suites for this config)
            # We pass the selected config name to fetch suites specifically for it
            suites, err = get_report_suites(config_name=selected_config_name)
            
            if not suites:
                st.warning("Impossible de charger les suites. Vérifiez la connexion.")
            else:
                suite_opts = {s['rsid']: s['name'] for s in suites}
                
                rsid_index = 0
                if is_editing and edit_data['rsid'] in list(suite_opts.keys()):
                    rsid_index = list(suite_opts.keys()).index(edit_data['rsid'])

                selected_rsid = st.selectbox("Report Suite", options=list(suite_opts.keys()), format_func=lambda x: f"{suite_opts[x]} ({x})", index=rsid_index)
                
                if selected_rsid:
                    # 3. Load Components
                    # We pass the selected config name to fetch components specifically for it
                    comps, err = get_or_refresh_components(selected_rsid, config_name=selected_config_name)
                    
                    if comps:
                        # Fix: Convert lists to dicts for UI selection
                        metric_opts = {m['id']: f"{m['name']} ({m['id']})" for m in comps.get('metrics', [])}
                        dim_opts = {d['id']: f"{d['name']} ({d['id']})" for d in comps.get('dimensions', [])}
                        seg_opts = {s['id']: f"{s['name']} ({s['id']})" for s in comps.get('segments', [])}

                        # 4. Form Inputs
                        default_metrics = edit_def.get('metrics', []) if is_editing else []
                        # Filter out metrics that might not exist anymore in the current RSID components
                        default_metrics = [m for m in default_metrics if m in metric_opts]

                        metrics = st.multiselect("Métriques (Colonnes)", options=list(metric_opts.keys()), format_func=lambda x: metric_opts[x], default=default_metrics)
                        
                        granularity_opts = ["day", "week", "month", "year"]
                        granularity_default = edit_def.get('granularity', 'day') if is_editing else 'day'
                        gran_index = granularity_opts.index(granularity_default) if granularity_default in granularity_opts else 0

                        granularity = st.selectbox("Granularité Temporelle", options=granularity_opts, format_func=lambda x: {"day": "Jour", "week": "Semaine", "month": "Mois", "year": "Année"}.get(x, x), index=gran_index)

                        st.write("---")
                        st.write("**Structure des Lignes**")
                        
                        # Determine report type default
                        type_opts = ["Dimension (Top Items)", "Comparaison de Segments"]
                        default_type_index = 0
                        if is_editing:
                            if edit_def.get('type') == 'segment' or (edit_def.get('segments') and len(edit_def.get('segments')) > 0):
                                default_type_index = 1
                        
                        report_type = st.radio("Type de lignes", type_opts, help="Choisissez ce qui s'affichera en première colonne.", index=default_type_index)
                        
                        selected_dimension = None
                        selected_segments = []

                        if report_type == "Dimension (Top Items)":
                            default_dim_index = 0
                            if is_editing and edit_def.get('dimension') in dim_opts:
                                default_dim_index = list(dim_opts.keys()).index(edit_def.get('dimension'))
                            selected_dimension = st.selectbox("Dimension", options=list(dim_opts.keys()), format_func=lambda x: dim_opts[x], index=default_dim_index)
                        else:
                            default_segs = edit_def.get('segments', []) if is_editing else []
                            default_segs = [s for s in default_segs if s in seg_opts]
                            selected_segments = st.multiselect("Segments à comparer (1 par ligne)", options=list(seg_opts.keys()), format_func=lambda x: seg_opts[x], default=default_segs)
                        
                        # Save Form
                        st.write("---")
                        with st.form("save_report_form"):
                            report_name = st.text_input("Nom du Rapport (ex: KPI Mensuels Site A)", value=edit_data['name'] if is_editing else "")
                            
                            submit_label = "💾 Mettre à jour le Rapport" if is_editing else "💾 Sauvegarder le Rapport"
                            
                            if st.form_submit_button(submit_label):
                                if not report_name or not metrics:
                                    st.error("Nom et métriques requis.")
                                elif report_type == "Comparaison de Segments" and not selected_segments:
                                    st.error("Veuillez sélectionner au moins un segment.")
                                else:
                                    definition = {
                                        "metrics": metrics,
                                        "granularity": granularity,
                                        "type": "dimension" if report_type == "Dimension (Top Items)" else "segment",
                                        "dimension": selected_dimension,
                                        "segments": selected_segments
                                    }
                                    
                                    success = False
                                    if is_editing:
                                        success = handle_update_report(edit_data['id'], report_name, selected_config_name, selected_rsid, definition)
                                    else:
                                        success = handle_save_report(report_name, selected_config_name, selected_rsid, definition)
                                    
                                    if success:
                                        st.success("Rapport enregistré avec succès !")
                                        # Clear edit state and force navigation
                                        st.session_state.report_to_edit = None
                                        st.session_state.report_nav_selection = NAV_EXECUTE
                                        st.rerun()