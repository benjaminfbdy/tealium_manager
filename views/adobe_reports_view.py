import streamlit as st
import pandas as pd
import json
from datetime import date, timedelta
import concurrent.futures
import math
from controllers.config_controller import get_all_adobe_configurations
from controllers.adobe_controller import (
    get_report_suites, 
    get_or_refresh_components, 
    handle_save_report, 
    handle_update_report,
    get_all_saved_reports, 
    handle_delete_report,
    run_saved_report,
    get_report_history,
    load_historical_report_dataframe,
    delete_report_history_item,
    format_date_range_readable
)
import threading
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except ImportError:
    # Fallback pour les anciennes versions de Streamlit
    from streamlit.scriptrunner import add_script_run_ctx, get_script_run_ctx
from database import save_report_result

def render_adobe_reports_view():
    st.title("📑 Rapports")
    
    # --- Navigation State Management ---
    # Define constants for navigation options
    NAV_EXECUTE = "🚀 Exécuter des Rapports"
    NAV_CREATE = "➕ Créer un Nouveau Rapport"
    NAV_EDIT = "✏️ Modifier le Rapport"
    NAV_HISTORY = "📜 Historique"

    if "report_nav_selection" not in st.session_state:
        st.session_state.report_nav_selection = NAV_EXECUTE
    
    if "report_to_edit" not in st.session_state:
        st.session_state.report_to_edit = None

    if "active_report_results" not in st.session_state:
        st.session_state.active_report_results = []

    if "history_view_id" not in st.session_state:
        st.session_state.history_view_id = None

    # Navigation Bar
    # Dynamic label for the second tab if editing
    create_tab_label = NAV_EDIT if st.session_state.report_to_edit else NAV_CREATE
    
    # --- FIX: Decouple widget from state to allow programmatic navigation ---
    options = [NAV_EXECUTE, create_tab_label, NAV_HISTORY]
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
            st.subheader(f"2. Sélectionnez les rapports ({len(saved_reports)})")
            selected_report_ids = []
            
            # Header
            cols = st.columns([0.5, 4, 2, 2, 1.5])
            cols[0].markdown("**✅**")
            cols[1].markdown("**📑 Rapport**")
            cols[2].markdown("**⚙️ Compte**")
            cols[3].markdown("**🎯 RSID**")
            cols[4].markdown("**🛠️**")
            st.divider()
            
            for report in saved_reports:
                def_json = json.loads(report['definition'])
                is_audit = def_json.get('type') == 'system_audit'
                icon = "🔍" if is_audit else "📊"
                type_label = "Audit Système" if is_audit else "Custom"

                cols = st.columns([0.5, 4, 2, 2, 1.5])
                if cols[0].checkbox("Sélectionner", key=f"sel_{report['id']}", label_visibility="collapsed"):
                    selected_report_ids.append(report)
                
                cols[1].write(f"{icon} **{report['name']}**")
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
            
            col_exec_1, col_exec_2, col_exec_3 = st.columns([2, 1, 1])
            use_parallel = col_exec_2.checkbox("⚡ Exécution Parallèle", value=False, help="Lance les rapports simultanément. Idéal pour plusieurs organisations.")
            force_refresh = col_exec_3.checkbox("🔄 Forcer", value=False, help="Ignore le cache et relance les rapports depuis l'API Adobe.")
            
            if col_exec_1.button(f"▶️ Lancer ({len(selected_report_ids)})", type="primary"):
                if not selected_report_ids:
                    st.warning("Sélectionnez au moins un rapport.")
                else:
                    # Clear previous results
                    st.session_state.active_report_results = []
                    
                    date_range = f"{start_date.strftime('%Y-%m-%d')}T00:00:00/{end_date.strftime('%Y-%m-%d')}T23:59:59"

                    if use_parallel:
                        # --- Parallel Execution ---
                        st.info(f"Lancement de {len(selected_report_ids)} rapports en parallèle...")
                        
                        # Create placeholders for status updates
                        status_placeholders = {report['id']: st.empty() for report in selected_report_ids}
                        
                        # Capture du contexte Streamlit actuel (Main Thread)
                        ctx = get_script_run_ctx()

                        def run_wrapper(rep):
                            # Attacher le contexte au thread courant (Worker Thread)
                            if ctx:
                                add_script_run_ctx(threading.current_thread(), ctx)
                                
                            ph = status_placeholders[rep['id']]
                            ph.text(f"⏳ {rep['name']} : Démarrage...")
                            
                            # Callback for ETA inside the report
                            def update_progress(curr, total, est_rem, percent):
                                mins, secs = divmod(est_rem, 60)
                                progress_percent = int(percent * 100)
                                ph.text(f"⏳ {rep['name']} : {progress_percent}% ({curr}/{total}). Reste env. {mins}m {secs}s")

                            df, status = run_saved_report(rep, date_range, status_callback=update_progress, force_refresh=force_refresh)
                            
                            if status == "OK":
                                ph.success(f"✅ {rep['name']} : Terminé !")
                            else:
                                ph.error(f"❌ {rep['name']} : Erreur ({status})")
                                
                            return {"report": rep, "df": df, "status": status, "start_date": start_date, "date_range": date_range}

                        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                            futures = [executor.submit(run_wrapper, report) for report in selected_report_ids]
                            for future in concurrent.futures.as_completed(futures):
                                try:
                                    result = future.result()
                                    st.session_state.active_report_results.append(result)
                                except Exception as e:
                                    st.error(f"Erreur fatale thread : {e}")

                    else:
                        # --- Sequential Execution ---
                        progress_bar = st.progress(0, text="Démarrage...")
                        
                        for i, report in enumerate(selected_report_ids):
                            # Callback for ETA
                            def update_progress_seq(curr, total, est_rem, percent):
                                mins, secs = divmod(est_rem, 60)
                                # Update the progress bar with percentage and text
                                progress_bar.progress(percent, text=f"Traitement de : {report['name']} ({curr}/{total}). Reste env. {mins}m {secs}s")

                            progress_bar.progress(i / len(selected_report_ids), text=f"Traitement de : {report['name']}...")
                            df, status = run_saved_report(report, date_range, status_callback=update_progress_seq, force_refresh=force_refresh)
                            
                            st.session_state.active_report_results.append({
                                "report": report, "df": df, "status": status, "start_date": start_date, "date_range": date_range
                            })
                        progress_bar.empty() # Clear bar on completion
                    
                    st.success("Traitement terminé !")

            # --- Display Results (Persistent) ---
            if st.session_state.active_report_results:
                st.divider()
                st.subheader("Résultats")
                
                for res in st.session_state.active_report_results:
                    report = res['report']
                    df = res['df']
                    status = res['status']
                    
                    is_cached = "(Cache)" in status
                    clean_status = status.replace(" (Cache)", "")

                    if clean_status == "OK" and df is not None and not df.empty:
                        expander_title = f"✅ Résultat : {report['name']}"
                        if is_cached:
                            expander_title = f"💾 {expander_title} (depuis le cache)"
                        
                        with st.expander(expander_title, expanded=True):
                            # Separate successful rows from error rows
                            error_rows = df[df.get('status') == 'Error'] if 'status' in df.columns else pd.DataFrame()
                            success_rows = df[df.get('status') != 'Error'] if 'status' in df.columns else df
                            
                            # --- CLEANUP FOR AUDIT REPORTS ---
                            # If this is an audit report, rename columns to remove IDs if possible
                            # We need to infer it's an audit report from columns or definition
                            def_json = json.loads(report['definition'])
                            if def_json.get('type') == 'system_audit':
                                # Rename columns Seg1_P1, etc.
                                s1_id = def_json.get('segment1')
                                s2_id = def_json.get('segment2')
                                
                                # Attempt to load names from cache to display readable headers
                                comps, _ = get_or_refresh_components(report['rsid'], config_name=report['adobe_config_name'])
                                seg_map = {s['id']: s['name'] for s in comps.get('segments', [])} if comps else {}
                                
                                s1_name = seg_map.get(s1_id, s1_id) if s1_id else "Seg1"
                                s2_name = seg_map.get(s2_id, s2_id) if s2_id else "Seg2"
                                
                                # --- UI Tweak: Shorten Segment Names for Headers ---
                                # Try to keep only the part after " - " or ":" to save space
                                def shorten_name(name):
                                    if " - " in name:
                                        return name.split(" - ")[-1].strip()
                                    if ":" in name:
                                        return name.split(":")[-1].strip()
                                    return name
                                
                                s1_short = shorten_name(s1_name)
                                s2_short = shorten_name(s2_name)

                                # Apply rounding (Ceiling) to numeric columns
                                for col in ["Seg1_P1", "Seg2_P1", "Seg1_P2", "Seg2_P2"]:
                                    if col in success_rows.columns:
                                        # Apply only to numeric values, ignore "Non actif" strings
                                        success_rows[col] = success_rows[col].apply(lambda x: int(math.ceil(x)) if isinstance(x, (int, float)) else x)

                                # Calculate Variations (Numeric)
                                def calc_variation(curr, prev):
                                    # Handle non-numeric values (e.g. "Non actif", "Erreur")
                                    if not isinstance(curr, (int, float)) or not isinstance(prev, (int, float)):
                                        return None
                                    if prev == 0:
                                        return 100.0 if curr > 0 else 0.0
                                    # Round up to nearest integer (Ceiling)
                                    val = ((curr - prev) / prev) * 100.0
                                    return math.ceil(val)

                                if "Seg1_P1" in success_rows.columns and "Seg1_P2" in success_rows.columns:
                                    success_rows[f"Var {s1_short} (%)"] = success_rows.apply(lambda x: calc_variation(x["Seg1_P2"], x["Seg1_P1"]), axis=1)
                                if "Seg2_P1" in success_rows.columns and "Seg2_P2" in success_rows.columns:
                                    success_rows[f"Var {s2_short} (%)"] = success_rows.apply(lambda x: calc_variation(x["Seg2_P2"], x["Seg2_P1"]), axis=1)

                                rename_map = {
                                    "Seg1_P1": f"{s1_short}\n(P1)",
                                    "Seg2_P1": f"{s2_short}\n(P1)",
                                    "Seg1_P2": f"{s1_short}\n(P2)",
                                    "Seg2_P2": f"{s2_short}\n(P2)",
                                }
                                success_rows = success_rows.rename(columns=rename_map)
                                
                                # Reorder columns for readability
                                cols = ["Dimension", f"{s1_short}\n(P1)", f"{s1_short}\n(P2)", f"Var {s1_short} (%)", f"{s2_short}\n(P1)", f"{s2_short}\n(P2)", f"Var {s2_short} (%)"]
                                # Filter to ensure columns exist (in case of partial data)
                                cols = [c for c in cols if c in success_rows.columns]
                                success_rows = success_rows[cols]

                            if not error_rows.empty:
                                st.error(f"{len(error_rows)} segment(s) n'ont pas pu être chargés :")
                                for _, row in error_rows.iterrows():
                                    st.text(f"- {row['Segment']}: {row['error_message']}")
                                
                                # --- Retry Logic ---
                                if st.button("🔄 Réessayer les segments échoués", key=f"retry_{report['id']}"):
                                    failed_seg_ids = error_rows['_segment_id'].tolist()
                                    
                                    # Create temp definition with only failed segments
                                    def_dict = json.loads(report['definition'])
                                    def_dict['segments'] = failed_seg_ids
                                    
                                    temp_report = report.copy()
                                    temp_report['definition'] = json.dumps(def_dict)
                                    temp_report['id'] = -1 # Dummy ID to prevent overwriting main cache with partial data
                                    
                                    with st.spinner(f"Nouvelle tentative pour {len(failed_seg_ids)} segments..."):
                                        # Run with force_refresh=True to bypass cache
                                        retry_df, retry_status = run_saved_report(temp_report, res['date_range'], force_refresh=True)
                                        
                                        if retry_df is not None and not retry_df.empty:
                                            # Merge logic:
                                            # 1. Keep original success rows
                                            # 2. Append new results (whether success or error)
                                            
                                            # Filter out the old error rows for these segments from the original DF
                                            # (We keep success rows and error rows that were NOT in this retry batch, if any)
                                            clean_df = df[~df['_segment_id'].isin(failed_seg_ids)]
                                            
                                            # Concat
                                            merged_df = pd.concat([clean_df, retry_df], ignore_index=True)
                                            
                                            # Update Session State
                                            res['df'] = merged_df
                                            
                                            # Update Main Cache with the full merged result
                                            date_range_key = res['date_range'].replace('/', '_').replace(':', '').replace('-', '')
                                            save_report_result(report['id'], date_range_key, merged_df, "OK")
                                            
                                            st.success("Réessai terminé ! Mise à jour...")
                                            st.rerun()

                            if success_rows.empty:
                                continue # Skip the rest if only errors occurred

                            # Add 'Show Curve' column for interaction
                            df_display = success_rows.copy()
                            # Add column at the end
                            df_display["📈"] = False
                            
                            # --- Apply Color Coding to Variations (Display Only) ---
                            def format_variation_display(val):
                                if val is None or not isinstance(val, (int, float)):
                                    return val
                                
                                if val == -100:
                                    return f"🔴 {int(val)}%" # Critical
                                elif val <= -20:
                                    return f"🔻 {int(val)}%" # Significant Drop
                                elif val < 0:
                                    return f"🔸 {int(val)}%" # Slight Drop
                                elif val == 0:
                                    return f"⚪ {int(val)}%" # Stable
                                else:
                                    return f"💚 +{int(val)}%" # Growth

                            # Apply to all columns containing "Var"
                            var_cols = [c for c in df_display.columns if "Var" in c and "(%)" in c]
                            for vc in var_cols:
                                df_display[vc] = df_display[vc].apply(format_variation_display)
                            
                            # Configure columns: Hide internal IDs, format Curve checkbox
                            column_config = {
                                "_segment_id": None, # Hidden
                                "_item_id": None,    # Hidden
                                "status": None,
                                "error_message": None,
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
                            selected_rows_to_plot = edited_df[edited_df["📈"] == True]
                            for idx, row in selected_rows_to_plot.iterrows():
                                item_name = row.get('Segment') or row.get('Item')
                                item_id = row.get('_segment_id') or row.get('_item_id')
                                
                                if item_id:
                                    st.caption(f"📉 Évolution : **{item_name}**")
                                    
                                    # --- CHART LOGIC DISPATCHER ---
                                    is_audit_report = False
                                    if 'definition' in report:
                                        def_j = json.loads(report['definition'])
                                        if def_j.get('type') == 'system_audit':
                                            is_audit_report = True

                                    if is_audit_report:
                                        # --- AUDIT CHART (Bar Chart P1 vs P2) ---
                                        # Extract values from the row using the known column structure
                                        # Columns are like "Site\n(P1)", "Site\n(P2)", etc.
                                        # We need to find them dynamically as names might change
                                        chart_data = {}
                                        for col in row.index:
                                            if "\n(P1)" in col:
                                                seg_name = col.replace("\n(P1)", " (P1)")
                                                chart_data[seg_name] = row[col]
                                            elif "\n(P2)" in col:
                                                seg_name = col.replace("\n(P2)", " (P2)")
                                                chart_data[seg_name] = row[col]
                                        
                                        # Filter out non-numeric (e.g. "Non actif")
                                        chart_data = {k: v for k, v in chart_data.items() if isinstance(v, (int, float))}
                                        
                                        if chart_data:
                                            st.bar_chart(chart_data)
                                        else:
                                            st.warning("Pas de données chiffrées à afficher pour cette dimension.")

                                    else:
                                        # --- STANDARD TIME SERIES CHART ---
                                        meta_cols = ['Segment', 'Item', '_segment_id', '_item_id', '📈', 'status', 'error_message']
                                        data_cols = [c for c in row.index if c not in meta_cols and isinstance(row[c], (int, float))]
                                        
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
                                success_rows.to_csv(index=False).encode('utf-8'),
                                f"{report['name']}_{res['start_date']}.csv",
                                "text/csv"
                            )
                    elif clean_status == "Aucune donnée.":
                        expander_title = f"ℹ️ Aucune donnée pour {report['name']}"
                        if is_cached:
                            expander_title = f"💾 {expander_title} (depuis le cache)"
                        st.info(expander_title)

                    else:
                        st.error(f"❌ Erreur sur {report['name']}: {status}")

    # --- TAB 2: CREATION ---
    elif mode == create_tab_label:
        is_editing = st.session_state.report_to_edit is not None
        edit_data = st.session_state.report_to_edit
        edit_def = json.loads(edit_data['definition']) if is_editing and 'definition' in edit_data else {}

        # --- Initialize Builder State ---
        # We use a specific key in session_state to hold the columns being built
        if "builder_columns" not in st.session_state or not is_editing:
             # Default start with one empty column if not editing or if state not set
             if "builder_columns" not in st.session_state:
                st.session_state.builder_columns = [{"id": 0, "metric_id": None, "segment_id": None}]

        # --- Report Type Selection ---
        report_mode = st.radio("Type de Rapport", ["📊 Standard (Custom)", "🔍 Audit Système (Dimensions)"], horizontal=True)
        st.divider()

        st.subheader("Modifier le rapport" if is_editing else "Définir un nouveau rapport")
        
        if is_editing:
            st.info(f"Modification de : **{edit_data['name']}**")
            if st.button("Annuler l'édition"):
                st.session_state.report_to_edit = None
                st.session_state.report_nav_selection = NAV_EXECUTE
                if "builder_columns" in st.session_state: del st.session_state.builder_columns
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
                        # Add None option for segments
                        seg_opts_with_none = {None: "Aucun (Global)"}
                        seg_opts = {s['id']: f"{s['name']} ({s['id']})" for s in comps.get('segments', [])}
                        seg_opts_with_none.update(seg_opts)
                        
                        dim_opts = {d['id']: f"{d['name']} ({d['id']})" for d in comps.get('dimensions', [])}

                        definition_payload = {}

                        if report_mode == "🔍 Audit Système (Dimensions)":
                            st.info("Ce mode configure un audit complet des 275 dimensions (eVars & Props) sur deux segments et deux périodes.")
                            
                            col_audit_1, col_audit_2 = st.columns(2)
                            
                            # Helpers to find default indices
                            def find_default(options, keyword):
                                for i, label in enumerate(options.values()):
                                    if keyword.lower() in label.lower(): return i
                                return 0

                            idx_site = find_default(seg_opts, "site")
                            idx_app = find_default(seg_opts, "app")
                            
                            # Pre-fill if editing
                            if is_editing and edit_def.get('type') == 'system_audit':
                                s1_val = edit_def.get('segment1')
                                s2_val = edit_def.get('segment2')
                                if s1_val in seg_opts: idx_site = list(seg_opts.keys()).index(s1_val)
                                if s2_val in seg_opts: idx_app = list(seg_opts.keys()).index(s2_val)

                            seg1 = col_audit_1.selectbox("Segment 1 (ex: Site)", options=list(seg_opts.keys()), format_func=lambda x: seg_opts[x], index=idx_site, key="audit_s1")
                            seg2 = col_audit_2.selectbox("Segment 2 (ex: App)", options=list(seg_opts.keys()), format_func=lambda x: seg_opts[x], index=idx_app, key="audit_s2")
                            
                            st.markdown("#### Périodes par défaut (Sauvegardées)")
                            c_d1, c_d2 = st.columns(2)
                            # Defaults
                            def_d1_s = date.today() - timedelta(days=14)
                            def_d1_e = date.today() - timedelta(days=8)
                            def_d2_s = date.today() - timedelta(days=7)
                            def_d2_e = date.today() - timedelta(days=1)
                            
                            d1_s = c_d1.date_input("Début P1", value=def_d1_s)
                            d1_e = c_d1.date_input("Fin P1", value=def_d1_e)
                            d2_s = c_d2.date_input("Début P2", value=def_d2_s)
                            d2_e = c_d2.date_input("Fin P2", value=def_d2_e)
                            
                            definition_payload = {
                                "type": "system_audit",
                                "segment1": seg1,
                                "segment2": seg2,
                                "range1": f"{d1_s}T00:00:00/{d1_e}T23:59:59",
                                "range2": f"{d2_s}T00:00:00/{d2_e}T23:59:59"
                            }

                        else:
                            # --- STANDARD REPORT BUILDER ---
                            st.markdown("### 🏗️ Colonnes (Métriques & Filtres)")
                            st.caption("Définissez les colonnes de votre tableau. Chaque colonne est une métrique, potentiellement filtrée par un segment.")

                        # Load existing columns if editing and not yet loaded into state
                        if is_editing and "builder_columns_loaded" not in st.session_state:
                            loaded_cols = []
                            # Support legacy format (list of metric IDs)
                            if "metrics" in edit_def and isinstance(edit_def["metrics"], list):
                                for i, m_id in enumerate(edit_def["metrics"]):
                                    loaded_cols.append({"id": i, "metric_id": m_id, "segment_id": None})
                            # Support new format (list of objects)
                            elif "columns" in edit_def:
                                for i, col in enumerate(edit_def["columns"]):
                                    loaded_cols.append({"id": i, "metric_id": col.get("metric_id"), "segment_id": col.get("segment_id")})
                            
                            if loaded_cols:
                                st.session_state.builder_columns = loaded_cols
                            st.session_state.builder_columns_loaded = True

                        # Render Column Builder
                        cols_to_remove = []
                        for idx, col_data in enumerate(st.session_state.builder_columns):
                            with st.container():
                                c1, c2, c3 = st.columns([3, 3, 1])
                                
                                # Metric Selector
                                current_metric = col_data.get("metric_id")
                                if current_metric not in metric_opts: current_metric = None
                                
                                new_metric = c1.selectbox(f"Métrique (Col {idx+1})", options=list(metric_opts.keys()), format_func=lambda x: metric_opts[x], index=list(metric_opts.keys()).index(current_metric) if current_metric else 0, key=f"b_met_{idx}")
                                st.session_state.builder_columns[idx]["metric_id"] = new_metric

                                # Segment Filter Selector
                                current_seg = col_data.get("segment_id")
                                if current_seg not in seg_opts_with_none: current_seg = None
                                
                                new_seg = c2.selectbox(f"Filtre Segment (Col {idx+1})", options=list(seg_opts_with_none.keys()), format_func=lambda x: seg_opts_with_none[x], index=list(seg_opts_with_none.keys()).index(current_seg) if current_seg else 0, key=f"b_seg_{idx}")
                                st.session_state.builder_columns[idx]["segment_id"] = new_seg

                                # Remove Button
                                if c3.button("🗑️", key=f"b_del_{idx}"):
                                    cols_to_remove.append(idx)
                        
                        # Process removals
                        if cols_to_remove:
                            for rm_idx in sorted(cols_to_remove, reverse=True):
                                st.session_state.builder_columns.pop(rm_idx)
                            st.rerun()

                        if st.button("➕ Ajouter une colonne"):
                            new_id = len(st.session_state.builder_columns)
                            st.session_state.builder_columns.append({"id": new_id, "metric_id": list(metric_opts.keys())[0] if metric_opts else None, "segment_id": None})
                            st.rerun()

                        st.divider()

                        # --- 5. Global Settings ---
                        granularity_opts = ["day", "week", "month", "year"]
                        granularity_default = edit_def.get('granularity', 'day') if is_editing else 'day'
                        gran_index = granularity_opts.index(granularity_default) if granularity_default in granularity_opts else 0

                        granularity = st.selectbox("Granularité Temporelle", options=granularity_opts, format_func=lambda x: {"day": "Jour", "week": "Semaine", "month": "Mois", "year": "Année"}.get(x, x), index=gran_index)

                        st.markdown("### 🧱 Structure des Lignes")
                        
                        # Determine report type default
                        type_opts = ["Dimension (Top Items)", "Comparaison de Segments"]
                        default_type_index = 0
                        if is_editing:
                            if edit_def.get('type') == 'segment' or (edit_def.get('segments') and len(edit_def.get('segments')) > 0):
                                default_type_index = 1
                        
                        report_type = st.radio("Type de lignes", type_opts, help="Choisissez ce qui s'affichera en première colonne (l'axe vertical).", index=default_type_index)
                        
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
                            
                            # --- Bulk Selection Logic ---
                            # Initialize session state for selection if not present
                            if "selected_segments_state" not in st.session_state:
                                st.session_state.selected_segments_state = default_segs
                            
                            # Bulk Add Expander
                            with st.expander("🔍 Sélection en masse (Recherche & Liste)"):
                                st.markdown("#### 1. Par mot-clé")
                                c_search, c_btn = st.columns([3, 1])
                                search_term = c_search.text_input("Rechercher des segments contenant :", key="seg_search_input")
                                if c_btn.button("Ajouter (Recherche)"):
                                    if search_term:
                                        matches = [sid for sid, sname in seg_opts.items() if search_term.lower() in sname.lower()]
                                        current_set = set(st.session_state.selected_segments_state)
                                        current_set.update(matches)
                                        new_selection = list(current_set)
                                        st.session_state.selected_segments_state = new_selection
                                        st.session_state["segment_multiselect"] = new_selection # Force widget update
                                        st.success(f"{len(matches)} segments ajoutés !")
                                        st.rerun()
                                
                                st.divider()
                                st.markdown("#### 2. Par liste de noms")
                                st.caption("Collez ici une liste de noms exacts de segments (un par ligne).")
                                bulk_text = st.text_area("Liste de noms", height=150, key="bulk_seg_text")
                                
                                if st.button("Ajouter depuis la liste"):
                                    if bulk_text and comps and 'segments' in comps:
                                        lines = [l.strip() for l in bulk_text.split('\n') if l.strip()]
                                        
                                        # Build lookup map: Lowercase Name -> List of IDs
                                        name_lookup = {}
                                        for s in comps['segments']:
                                            n_lower = s['name'].lower()
                                            if n_lower not in name_lookup:
                                                name_lookup[n_lower] = []
                                            name_lookup[n_lower].append(s['id'])
                                        
                                        found_ids = []
                                        missing_names = []
                                        
                                        for line in lines:
                                            line_lower = line.lower()
                                            if line_lower in name_lookup:
                                                found_ids.extend(name_lookup[line_lower])
                                            else:
                                                missing_names.append(line)
                                        
                                        if found_ids:
                                            current_set = set(st.session_state.selected_segments_state)
                                            current_set.update(found_ids)
                                            new_selection = list(current_set)
                                            st.session_state.selected_segments_state = new_selection
                                            st.session_state["segment_multiselect"] = new_selection # Force widget update
                                            
                                            msg = f"{len(found_ids)} segments ajoutés !"
                                            if missing_names:
                                                st.warning(f"Segments introuvables ({len(missing_names)}) : {', '.join(missing_names[:5])}...")
                                                st.caption("💡 Si ces segments existent, essayez de rafraîchir le cache dans l'onglet 'Configuration' > 'Gestion du Cache'.")
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.warning("Aucun segment correspondant trouvé.")

                            selected_segments = st.multiselect("Segments à comparer (1 par ligne)", options=list(seg_opts.keys()), format_func=lambda x: seg_opts[x], default=st.session_state.selected_segments_state, key="segment_multiselect")
                            
                            # Sync manual changes back to state
                            if selected_segments != st.session_state.selected_segments_state:
                                st.session_state.selected_segments_state = selected_segments
                        
                            definition_payload = {
                                "type": "dimension" if report_type == "Dimension (Top Items)" else "segment",
                                "columns": st.session_state.builder_columns,
                                "granularity": granularity,
                                "dimension": selected_dimension,
                                "segments": selected_segments
                            }

                        # Save Form
                        st.write("---")
                        with st.form("save_report_form"):
                            report_name = st.text_input("Nom du Rapport (ex: KPI Mensuels Site A)", value=edit_data['name'] if is_editing else "")
                            
                            submit_label = "💾 Mettre à jour le Rapport" if is_editing else "💾 Sauvegarder le Rapport"
                            
                            if st.form_submit_button(submit_label):
                                if not report_name:
                                    st.error("Le nom du rapport est requis.")
                                elif report_mode == "📊 Standard (Custom)" and not st.session_state.builder_columns:
                                    st.error("Au moins une colonne est requise.")
                                elif report_mode == "📊 Standard (Custom)" and report_type == "Comparaison de Segments" and not selected_segments:
                                    st.error("Veuillez sélectionner au moins un segment.")
                                else:
                                    success = False
                                    if is_editing:
                                        success = handle_update_report(edit_data['id'], report_name, selected_config_name, selected_rsid, definition_payload)
                                    else:
                                        success = handle_save_report(report_name, selected_config_name, selected_rsid, definition_payload)
                                    
                                    if success:
                                        st.success("Rapport enregistré avec succès !")
                                        # Clear edit state and force navigation
                                        st.session_state.report_to_edit = None
                                        if "builder_columns" in st.session_state: del st.session_state.builder_columns
                                        if "builder_columns_loaded" in st.session_state: del st.session_state.builder_columns_loaded
                                        if "selected_segments_state" in st.session_state: del st.session_state.selected_segments_state
                                        st.session_state.report_nav_selection = NAV_EXECUTE
                                        st.rerun()

    # --- TAB 3: HISTORY ---
    elif mode == NAV_HISTORY:
        st.subheader("Historique des Exécutions")
        st.caption("Retrouvez ici les résultats des rapports précédemment exécutés (stockés localement).")

        history_items = get_report_history()

        if not history_items:
            st.info("Aucun historique disponible.")
        else:
            # --- History List ---
            with st.container(height=400):
                # Header
                cols = st.columns([1.5, 3, 3, 1.5, 1])
                cols[0].markdown("**📅 Date**")
                cols[1].markdown("**📑 Rapport**")
                cols[2].markdown("**🗓️ Période**")
                cols[3].markdown("**🚦 Statut**")
                cols[4].markdown("**👁️**")
                st.divider()

                for item in history_items:
                    cols = st.columns([1.5, 3, 3, 1.5, 1])
                    
                    exec_date = pd.to_datetime(item['timestamp'], unit='s').strftime('%d/%m %H:%M')
                    readable_range = format_date_range_readable(item['date_range_key'])
                    report_name = item['report_name'] or "Rapport Supprimé"
                    
                    # Status Icons
                    status_raw = item['status']
                    status_display = status_raw
                    if "OK" in status_raw:
                        status_display = "✅ OK"
                    elif "Aucune donnée" in status_raw:
                        status_display = "ℹ️ Vide"
                    elif "Error" in status_raw:
                        status_display = "❌ Erreur"
                    
                    if "(Cache)" in status_raw:
                        status_display = f"💾 {status_display.replace(' (Cache)', '')}"

                    cols[0].text(exec_date)
                    cols[1].write(f"**{report_name}**")
                    cols[2].caption(readable_range)
                    cols[3].write(status_display)
                    
                    # Actions
                    action_cols = cols[4].columns(2)
                    if action_cols[0].button("👁️", key=f"view_hist_{item['id']}", help="Voir le résultat"):
                        st.session_state.history_view_id = item['id']
                        st.rerun()
                    
                    if action_cols[1].button("🗑️", key=f"del_hist_{item['id']}", help="Supprimer de l'historique"):
                        delete_report_history_item(item['id'])
                        if st.session_state.history_view_id == item['id']:
                            st.session_state.history_view_id = None
                        st.rerun()

            st.divider()

            # --- Detail View ---
            if st.session_state.history_view_id:
                # Find metadata for title
                selected_meta = next((i for i in history_items if i['id'] == st.session_state.history_view_id), None)
                
                if selected_meta:
                    st.subheader(f"Détail : {selected_meta['report_name']}")
                    st.caption(f"Période : {format_date_range_readable(selected_meta['date_range_key'])}")
                    
                    with st.spinner("Chargement des données archivées..."):
                        df_hist = load_historical_report_dataframe(st.session_state.history_view_id)
                    
                    if df_hist is not None and not df_hist.empty:
                        # Reuse display logic (simplified)
                        # Separate successful rows from error rows
                        error_rows = df_hist[df_hist.get('status') == 'Error'] if 'status' in df_hist.columns else pd.DataFrame()
                        success_rows = df_hist[df_hist.get('status') != 'Error'] if 'status' in df_hist.columns else df_hist

                        if not error_rows.empty:
                            st.error(f"{len(error_rows)} segment(s) en erreur.")

                        if not success_rows.empty:
                            # Add 'Show Curve' column for interaction
                            df_display = success_rows.copy()
                            df_display["📈"] = False
                            
                            column_config = {
                                "_segment_id": None, "_item_id": None, "status": None, "error_message": None,
                                "📈": st.column_config.CheckboxColumn("Courbe", width="small")
                            }
                            
                            edited_df = st.data_editor(
                                df_display,
                                column_config=column_config,
                                disabled=[c for c in df_display.columns if c != "📈"],
                                hide_index=True,
                                key="history_editor"
                            )
                            
                            # Simple Chart Logic
                            selected_rows = edited_df[edited_df["📈"] == True]
                            if not selected_rows.empty:
                                st.caption("Aperçu graphique (données brutes)")
                                # Just plot the numeric columns for simplicity in history view
                                numeric_cols = selected_rows.select_dtypes(include=['number']).columns
                                st.line_chart(selected_rows[numeric_cols].T)

                            st.download_button(
                                "Télécharger CSV",
                                success_rows.to_csv(index=False).encode('utf-8'),
                                f"history_{selected_meta['report_name']}.csv",
                                "text/csv"
                            )
                    else:
                        st.warning("Impossible de charger les données ou données vides.")