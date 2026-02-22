import streamlit as st
import pandas as pd
from datetime import date, timedelta, time
import json
import asyncio

from views.component_renderers import setup_page
from utils.adobe_repo import (
    get_adobe_components_cache_info, 
    load_adobe_components,
    load_saved_reports,
    save_report_configuration,
    update_saved_report,
    delete_saved_report
)
from controllers.adobe_controller import run_custom_report, run_global_report_async

def init_session_state():
    if 'report_view_mode' not in st.session_state: st.session_state.report_view_mode = 'list'
    if 'report_to_edit' not in st.session_state: st.session_state.report_to_edit = None
    if 'report_results_df' not in st.session_state: st.session_state.report_results_df = None

def render_report_list_view():
    st.subheader("Bibliothèque de Rapports")
    if st.button("➕ Créer un nouveau rapport", type="primary"):
        st.session_state.update(report_to_edit=None, report_view_mode='builder')
        st.rerun()
    st.divider()

    saved_reports = load_saved_reports()
    if not saved_reports:
        st.info("Aucun rapport sauvegardé. Cliquez sur 'Créer un nouveau rapport' pour commencer.")
        return

    cols = st.columns([4, 2, 2, 3]); cols[0].markdown("**📑 Nom**"); cols[1].markdown("**⚙️ Compte**"); cols[2].markdown("**🎯 RSID**"); cols[3].markdown("**🛠️ Actions**")
    for report in saved_reports:
        cols = st.columns([4, 2, 2, 3])
        def_json = json.loads(report['definition'])
        cols[0].write(f"{'🔍' if def_json.get('type') == 'system_audit' else '📊'} {report['name']}")
        cols[1].caption(report['adobe_config_name']); cols[2].caption(report['rsid'])
        b_cols = cols[3].columns(3)
        if b_cols[0].button("▶️ Lancer", key=f"run_{report['id']}"): st.session_state.report_to_run = report
        if b_cols[1].button("✏️ Modifier", key=f"edit_{report['id']}"): st.session_state.update(report_to_edit=report, report_view_mode='builder'); st.rerun()
        if b_cols[2].button("🗑️ Supprimer", key=f"del_{report['id']}"): delete_saved_report(report['id']); st.rerun()

    if 'report_to_run' in st.session_state and st.session_state.report_to_run:
        st.divider(); st.subheader(f"Lancement de : {st.session_state.report_to_run['name']}")
        with st.expander("Périodes d'Analyse", expanded=True):
            add_comp = st.toggle("Ajouter une période de comparaison", key="run_add_comp")
            p1c, p2c = st.columns(2)
            with p1c:
                p1_start_d, p1_start_t = st.date_input("Date début P1", date.today() - timedelta(7)), st.time_input("Heure début P1", time(0, 0))
                p1_end_d, p1_end_t = st.date_input("Date fin P1", date.today() - timedelta(1)), st.time_input("Heure fin P1", time(23, 59))
            if add_comp:
                with p2c:
                    p2_start_d, p2_start_t = st.date_input("Date début P2", date.today() - timedelta(14)), st.time_input("Heure début P2", time(0, 0))
                    p2_end_d, p2_end_t = st.date_input("Date fin P2", date.today() - timedelta(8)), st.time_input("Heure fin P2", time(23, 59))
        
        if st.button("🚀 Exécuter maintenant", type="primary"):
            report, definition = st.session_state.report_to_run, json.loads(st.session_state.report_to_run['definition'])
            definition['periods'] = {"p1": f"{p1_start_d.strftime('%Y-%m-%d')}T{p1_start_t.strftime('%H:%M:%S')}/{p1_end_d.strftime('%Y-%m-%d')}T{p1_end_t.strftime('%H:%M:%S')}"}
            if add_comp: definition['periods']['p2'] = f"{p2_start_d.strftime('%Y-%m-%d')}T{p2_start_t.strftime('%H:%M:%S')}/{p2_end_d.strftime('%Y-%m-%d')}T{p2_end_t.strftime('%H:%M:%S')}"
            
            try: active_config = st.secrets.adobe_profiles[report['adobe_config_name']].to_dict()
            except (KeyError, AttributeError): st.error(f"Config '{report['adobe_config_name']}' introuvable."); st.stop()
            
            report_type = definition.get('type')
            if report_type == 'system_audit':
                progress_bar = st.progress(0, "Initialisation..."); completed_count = 0
                def update_progress():
                    nonlocal completed_count; completed_count += 1
                    progress_bar.progress(completed_count / 275, f"Audit: {completed_count}/275 dims.")
                with st.spinner("Lancement de l'audit..."):
                    components = load_adobe_components(report['rsid'])
                    seg_opts = {s['id']: s['name'] for s in components.get('segments', [])} if components else {}
                    result_df, msg = asyncio.run(run_global_report_async(active_config, report['rsid'], definition, update_progress, segment_map=seg_opts))
            else:
                with st.spinner("Génération du rapport..."):
                    result_df, msg = run_custom_report(active_config, report['rsid'], definition)
            
            if result_df is not None:
                st.success(f"Rapport '{report['name']}' généré !"); st.session_state.update(report_results_df=result_df, report_results_type=report_type)
            else: st.error(f"Erreur: {msg}")
            st.session_state.report_to_run = None; st.rerun()

def render_report_builder_view():
    is_editing = st.session_state.report_to_edit is not None
    st.subheader("Éditeur de Rapport")
    if st.button("← Retour à la liste"):
        st.session_state.update(report_view_mode='list', report_to_edit=None); st.rerun()

    edit_data = st.session_state.report_to_edit or {}; edit_def = json.loads(edit_data.get('definition', '{}'))
    try:
        adobe_profiles = st.secrets.adobe_profiles.to_dict(); profile_opts = list(adobe_profiles.keys())
        config_idx = profile_opts.index(edit_data.get('adobe_config_name')) if is_editing and edit_data.get('adobe_config_name') in profile_opts else 0
        selected_profile = st.selectbox("Compte Adobe", options=profile_opts, index=config_idx)
        
        cached_rsids = [item['rsid'] for item in get_adobe_components_cache_info()]
        if not cached_rsids: st.warning("Aucune RSID en cache."); st.stop()
        rsid_idx = cached_rsids.index(edit_data.get('rsid')) if is_editing and edit_data.get('rsid') in cached_rsids else 0
        selected_rsid = st.selectbox("Report Suite (en cache)", options=cached_rsids, index=rsid_idx)
        
        components = load_adobe_components(selected_rsid)
        if not components: st.error("Composants introuvables."); st.stop()
        metric_opts = {m['id']: f"{m['name']}" for m in components.get('metrics', []) if m.get('id') in ['metrics/pageviews', 'metrics/visitors', 'metrics/visits']}
        seg_opts = {s['id']: s['name'] for s in components.get('segments', [])}; seg_opts_with_none = {None: "Aucun", **seg_opts}
    except (Exception) as e: st.error(f"Erreur de config/cache: {e}"); st.stop()

    st.divider()
    report_name = st.text_input("Nom du Rapport", value=edit_data.get('name', ''))
    report_type_map = {"Rapport Custom (Temporel)": "custom", "Rapport Global (Audit de Dimensions)": "system_audit"}
    report_type_display = st.radio("Type de Rapport", list(report_type_map.keys()), index=1 if edit_def.get('type') == 'system_audit' else 0, horizontal=True)
    report_type = report_type_map[report_type_display]

    if 'builder_cols' not in st.session_state or (is_editing and edit_data.get('id') != st.session_state.get('last_edit_id')):
        st.session_state.builder_cols = edit_def.get('columns', [{"id": 0}]); st.session_state.last_edit_id = edit_data.get('id')

    if report_type == "custom":
        granularity = st.selectbox("Granularité", ["minute", "hour", "day", "week", "month"], index=2)
        st.markdown("###### Colonnes"); cols = st.session_state.builder_cols
        for i, col in enumerate(cols):
            c1, c2, c3 = st.columns([3,3,1]); col['metric'] = c1.selectbox(f"Métrique C{i+1}", list(metric_opts.keys()), format_func=lambda m: metric_opts.get(m,m), key=f"c_met_{i}", index=list(metric_opts.keys()).index(col.get('metric')) if col.get('metric') in metric_opts else 0)
            col['segment'] = c2.selectbox(f"Segment C{i+1}", list(seg_opts_with_none.keys()), format_func=lambda s: seg_opts_with_none[s], key=f"c_seg_{i}", index=list(seg_opts_with_none.keys()).index(col.get('segment')) if col.get('segment') in seg_opts_with_none else 0)
            if c3.button("🗑️", key=f"c_del_{i}"): cols.pop(i); st.rerun()
        if st.button("➕ Ajouter colonne"): cols.append({"id": len(cols)}); st.rerun()
        definition = {"type": "custom", "columns": cols, "granularity": granularity}
    else:
        metric = st.selectbox("Métrique à auditer", list(metric_opts.keys()), format_func=lambda m: metric_opts.get(m,m), index=list(metric_opts.keys()).index(edit_def.get('metric')) if 'metric' in edit_def and edit_def.get('metric') in metric_opts else 0)
        st.markdown("###### Colonnes (Segments)"); cols = st.session_state.builder_cols
        for i, col in enumerate(cols):
            c1, c2 = st.columns([6,1]); col['segment'] = c1.selectbox(f"Segment C{i+1}", list(seg_opts.keys()), format_func=lambda s: seg_opts[s], key=f"g_seg_{i}", index=list(seg_opts.keys()).index(col.get('segment')) if col.get('segment') in seg_opts else 0)
            if c2.button("🗑️", key=f"g_del_{i}"): cols.pop(i); st.rerun()
        if st.button("➕ Ajouter colonne"): cols.append({"id": len(cols)}); st.rerun()
        definition = {"type": "system_audit", "metric": metric, "columns": cols}

    st.divider()
    if st.button("💾 Sauvegarder", type="primary"):
        if not report_name: st.error("Le nom est obligatoire."); st.stop()
        if is_editing: update_saved_report(edit_data['id'], report_name, selected_profile, selected_rsid, definition)
        else: save_report_configuration(report_name, selected_profile, selected_rsid, definition)
        st.success("Rapport sauvegardé !"); st.session_state.update(report_view_mode='list', report_to_edit=None)
        if 'builder_cols' in st.session_state: del st.session_state.builder_cols
        if 'last_edit_id' in st.session_state: del st.session_state.last_edit_id
        st.rerun()

def main():
    setup_page(); st.title("📑 Rapports Adobe"); init_session_state()
    if st.session_state.report_view_mode == 'list': render_report_list_view()
    else: render_report_builder_view()
    
    if st.session_state.report_results_df is not None:
        st.divider(); st.subheader("📊 Dernier Résultat Généré")
        results_df = st.session_state.report_results_df
        if results_df.empty: st.info("Rapport généré, mais aucune donnée trouvée.")
        else:
            df_display = results_df.copy()
            if st.session_state.get('report_results_type') == 'custom' and isinstance(df_display.index, pd.DatetimeIndex):
                st.line_chart(df_display); df_display.index = df_display.index.strftime('%d/%m/%y %H:%M')
            st.dataframe(df_display)
            st.download_button("📥 Télécharger en CSV", df_display.to_csv(index=(st.session_state.get('report_results_type') == 'custom')).encode('utf-8'), "report.csv")
        if st.button("Fermer le résultat"): st.session_state.report_results_df = None; st.rerun()

if __name__ == "__main__":
    main()
