import pandas as pd
from typing import Dict, List, Optional, Any
from urllib.parse import quote
import streamlit as st
import json
import time
import asyncio
import aiohttp
import math

from utils.adobe_repo import (
    save_report_configuration, 
    update_saved_report, 
    load_saved_reports, 
    delete_saved_report, 
    save_report_result, 
    load_report_result, 
    get_all_cached_report_results, 
    get_cached_result_by_id, 
    delete_cached_result
)
from utils.adobe_client import AdobeAnalyticsClient
import logging

logger = logging.getLogger(__name__)

# --- Proxy Helpers ---
def _create_proxies_dict() -> Optional[Dict]:
    """Helper to create a proxy dictionary if credentials are provided in secrets."""
    try:
        proxy_section = st.secrets.get("proxy")
        if proxy_section:
            proxy_config = dict(proxy_section)
            proxy_user = proxy_config.get("user")
            proxy_password = proxy_config.get("password")
            if proxy_user and proxy_password:
                proxy_host = proxy_config.get("host", "your.proxy.host.com")
                proxy_port = proxy_config.get("port", "8080")
                encoded_user = quote(proxy_user)
                encoded_password = quote(proxy_password)
                proxy_auth_url = f"http://{encoded_user}:{encoded_password}@{proxy_host}:{proxy_port}"
                return {"http": proxy_auth_url, "https": proxy_auth_url}
    except Exception:
        pass
    return None

def _prepare_config_with_proxies(config: Dict) -> Dict:
    """Ensures the config dict has proxy settings if available in secrets."""
    if not config: return {}
    config_copy = dict(config)
    proxies = _create_proxies_dict()
    if proxies:
        config_copy['proxies'] = proxies
    return config_copy

def get_or_refresh_components(adobe_config: Dict, rsid: str, force_refresh: bool = False) -> (Optional[Dict], Optional[str]):
    """Gets Adobe Analytics components for a given RSID using the provided configuration."""
    if not adobe_config: return None, "Aucune configuration Adobe n'a été fournie."
    try:
        adobe_config = _prepare_config_with_proxies(adobe_config)
        client = AdobeAnalyticsClient(adobe_config)
        components = client.get_adobe_dashboard_components(rsid, force_refresh=force_refresh)
        if components.get("error"): return None, components.get("error")
        return components, None
    except Exception as e:
        error_message = f"Une erreur inattendue est survenue lors de la récupération des composants Adobe: {e}"
        print(error_message)
        return None, error_message

def get_report_suites(adobe_config: Dict) -> (List[Dict[str, str]], Optional[str]):
    """Fetches the list of report suites available for the provided Adobe configuration."""
    if not adobe_config: return [], "Aucune configuration Adobe n'a été fournie."
    try:
        adobe_config = _prepare_config_with_proxies(adobe_config)
        client = AdobeAnalyticsClient(adobe_config)
        suites_response = client.get_report_suites()
        if suites_response.get("error_code") == "403025":
            return [], f"Erreur Adobe (403): Permissions insuffisantes. Détail: {suites_response.get('message')}"
        content = suites_response.get("content")
        if content is None and not suites_response.get("error_code"):
             return [], f"Réponse inattendue de l'API Adobe. Contenu manquant."
        return content or [], None
    except Exception as e:
        return [], f"Erreur de communication avec l'API Adobe: {e}"

async def _fetch_global_audit_worker(session, adobe_config, dimension_id, dimension_name, definition, status_callback):
    results = {"Dimension": dimension_name, "status": "OK"}
    periods = definition['periods']
    
    async def _get_period_data(period_key):
        period_range = periods.get(period_key)
        if not period_range: return {}

        metric_container = {"metrics": []}
        metric_filters = []
        col_mapping = {}
        metric_to_audit = definition.get("metric", "metrics/pageviews")

        for i, col_def in enumerate(definition['columns']):
            segment_id = col_def.get('segment')
            col_id = f"c{i}"
            col_mapping[col_id] = f"C{i+1}"
            metric_def = {"id": metric_to_audit, "columnId": col_id}
            if segment_id:
                filter_id = f"s{i}"
                metric_def["filters"] = [filter_id]
                metric_filters.append({"id": filter_id, "type": "segment", "segmentId": segment_id})
            metric_container["metrics"].append(metric_def)
        if metric_filters:
            metric_container["metricFilters"] = metric_filters
        
        report_def = {"rsid": definition['rsid'], "globalFilters": [{"type": "dateRange", "dateRange": period_range}], "metricContainer": metric_container, "dimension": dimension_id, "settings": {"limit": 1, "page": 0}}
        url = f"https://analytics.adobe.io/api/{adobe_config['global_company_id']}/reports"
        headers = {"Authorization": f"Bearer {session.headers['Authorization']}", "x-api-key": adobe_config['client_id'], "Content-Type": "application/json"}

        for attempt in range(3):
            try:
                async with session.post(url, json=report_def, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        period_results = {}
                        if 'rows' in data and data['rows']:
                            for i, val in enumerate(data['rows'][0]['data']):
                                period_results[f"{col_mapping[f'c{i}']}_{period_key.upper()}"] = val
                        else:
                             for i in range(len(definition['columns'])):
                                period_results[f"{col_mapping[f'c{i}']}_{period_key.upper()}"] = 0
                        return period_results
                    elif response.status == 400:
                        text = await response.text()
                        if "oberon" in text or "invalid_dimension" in text: return {"status": "Non activée"}
                        return {"status": f"Erreur 400"}
                    elif response.status == 429: await asyncio.sleep(2 * (attempt + 1)); continue
                    else: return {"status": f"Erreur HTTP {response.status}"}
            except Exception: return {"status": "Exception"}
        return {"status": "Échec retries"}

    p1_results = await _get_period_data('p1')
    if "status" in p1_results: results.update(p1_results)
    else: results.update(p1_results or {})
    
    if periods.get('p2') and results['status'] == 'OK':
        p2_results = await _get_period_data('p2')
        if "status" in p2_results: results.update(p2_results)
        else: results.update(p2_results or {})

    if status_callback: status_callback()
    return results

async def run_global_report_async(adobe_config: Dict, rsid: str, definition: Dict, status_callback: any, segment_map: Dict = None) -> (Optional[pd.DataFrame], str):
    try:
        definition['rsid'] = rsid
        client = AdobeAnalyticsClient(adobe_config)
        client._ensure_token()
        dimensions_to_audit = [(f"variables/evar{i}", f"eVar{i}") for i in range(1, 201)] + [(f"variables/prop{i}", f"Prop{i}") for i in range(1, 76)]
        headers = {"Authorization": f"Bearer {client.access_token}"}
        semaphore = asyncio.Semaphore(10)

        async def sem_task(task):
            async with semaphore: return await task
        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [sem_task(_fetch_global_audit_worker(session, adobe_config, dim_id, dim_name, definition, status_callback)) for dim_id, dim_name in dimensions_to_audit]
            results = await asyncio.gather(*tasks)

        df = pd.DataFrame(results)
        if segment_map is None: segment_map = {}

        def shorten_name(name: str) -> str:
            if not isinstance(name, str): return "Segment"
            if " - " in name: return name.split(" - ")[-1].strip()
            return name[:20] + "..." if len(name) > 23 else name

        final_columns_ordered, rename_map = ["Dimension", "status"], {}
        for i, col_def in enumerate(definition['columns']):
            seg_id, seg_name = col_def.get('segment'), shorten_name(segment_map.get(col_def.get('segment'), f"C{i+1}"))
            p1_old, p2_old = f"C{i+1}_P1", f"C{i+1}_P2"
            p1_new, p2_new = f"{seg_name} P1", f"{seg_name} P2"
            rename_map.update({p1_old: p1_new, p2_old: p2_new})

        df.rename(columns=rename_map, inplace=True)

        for i, col_def in enumerate(definition['columns']):
            seg_name = shorten_name(segment_map.get(col_def.get('segment'), f"C{i+1}"))
            p1_col, p2_col, var_col = f"{seg_name} P1", f"{seg_name} P2", f"Var. %"
            final_columns_ordered.extend([p1_col, p2_col, var_col] if definition['periods'].get('p2') else [p1_col])
            if definition['periods'].get('p2') and p1_col in df.columns and p2_col in df.columns:
                df[p1_col], df[p2_col] = pd.to_numeric(df[p1_col], errors='coerce').fillna(0), pd.to_numeric(df[p2_col], errors='coerce').fillna(0)
                df[var_col] = ((df[p2_col] - df[p1_col]) / df[p1_col].replace(0, pd.NA) * 100).round(0)
        
        return df[[col for col in final_columns_ordered if col in df.columns]], "OK"
    except Exception as e:
        logger.error(f"Erreur fatale dans run_global_report: {e}", exc_info=True)
        return None, str(e)

def run_custom_report(adobe_config: Dict, rsid: str, definition: Dict) -> (Optional[pd.DataFrame], str):
    try:
        client, granularity = AdobeAnalyticsClient(adobe_config), definition['granularity']
        time_dimension = {'minute': 'variables/daterangeminute', 'hour': 'variables/daterangehour', 'day': 'variables/daterangeday', 'week': 'variables/daterangeweek', 'month': 'variables/daterangemonth'}.get(granularity, 'variables/daterangeday')

        def _execute_for_period(period_range: str, columns: List[Dict]) -> Optional[pd.DataFrame]:
            metric_container, metric_filters, column_id_map = {"metrics": []}, [], {}
            for i, col in enumerate(columns):
                metric_id, segment_id, column_id = col.get('metric'), col.get('segment'), f"c{i}"
                metric_def = {"id": metric_id, "columnId": column_id}
                if segment_id:
                    filter_id = f"s{i}"
                    metric_def["filters"] = [filter_id]
                    metric_filters.append({"id": filter_id, "type": "segment", "segmentId": segment_id})
                metric_container["metrics"].append(metric_def)
                metric_name, seg_name = metric_id.replace('metrics/', ''), segment_id or 'total'
                column_id_map[column_id] = f"{metric_name}_{seg_name}"
            if metric_filters: metric_container["metricFilters"] = metric_filters
            
            report_def = {"rsid": rsid, "globalFilters": [{"type": "dateRange", "dateRange": period_range}], "metricContainer": metric_container, "dimension": time_dimension, "settings": {"limit": 5000, "page": 0, "dimensionSort": "asc"}}
            report_data = client.get_report(report_def)

            if not report_data or 'rows' not in report_data: return pd.DataFrame()
            data_rows = [{'date': pd.to_datetime(row['value']), **{column_id_map.get(f"c{i}", f"c{i}"): val for i, val in enumerate(row['data'])}} for row in report_data['rows']]
            return pd.DataFrame(data_rows).set_index('date') if data_rows else pd.DataFrame()

        df_p1 = _execute_for_period(definition['periods']['p1'], definition['columns'])
        if df_p1 is None: return None, "Erreur P1."
        if df_p1.empty: return pd.DataFrame(), "OK"

        if definition['periods'].get('p2'):
            df_p2 = _execute_for_period(definition['periods']['p2'], definition['columns'])
            if df_p2 is None: return None, "Erreur P2."
            full_index = df_p1.index.union(df_p2.index)
            df_p1, df_p2 = df_p1.reindex(full_index, fill_value=0), df_p2.reindex(full_index, fill_value=0)
            df_merged = pd.merge(df_p1, df_p2, left_index=True, right_index=True, how='outer', suffixes=('_P1', '_P2'))
            for col_base in df_p1.columns:
                p1_col, p2_col, var_col = f"{col_base}_P1", f"{col_base}_P2", f"Var_{col_base}"
                df_merged[var_col] = ((df_merged[p2_col] - df_merged[p1_col]) / df_merged[p1_col].replace(0, pd.NA) * 100)
            return df_merged.fillna(0), "OK"
        return df_p1, "OK"
    except Exception as e:
        logger.error(f"Erreur fatale dans run_custom_report: {e}", exc_info=True)
        return None, str(e)
