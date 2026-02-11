import pandas as pd
from typing import Dict, List, Optional, Any
from database import get_active_adobe_configuration, save_report_configuration, update_saved_report, load_saved_reports, delete_saved_report, load_adobe_configuration_by_name, load_global_settings, save_report_result, load_report_result, get_all_cached_report_results, get_cached_result_by_id, delete_cached_result
from utils.adobe_client import AdobeAnalyticsClient
import time
import concurrent.futures
import random
import asyncio
import aiohttp

def get_or_refresh_components(rsid: str, force_refresh: bool = False, config_name: Optional[str] = None) -> (Optional[Dict], Optional[str]):
    """
    Gets Adobe Analytics components (dimensions, metrics, segments) for a given RSID
    by calling the client, which handles caching internally.
    
    Args:
        rsid (str): The report suite ID.
        force_refresh (bool): If True, the client will bypass its cache.
        config_name (str, optional): Specific configuration to use. Defaults to active config.

    Returns:
        A tuple: (components_dictionary, error_message)
    """
    print(f"Controller: Requesting components for RSID '{rsid}' (force_refresh: {force_refresh}, config: {config_name}).")
    
    if config_name:
        # Load specific config and merge with global settings (proxy)
        raw_config = load_adobe_configuration_by_name(config_name)
        if not raw_config:
            return None, f"Configuration '{config_name}' introuvable."
        
        global_settings = load_global_settings()
        active_config = global_settings.copy()
        active_config.update(raw_config)
    else:
        active_config = get_active_adobe_configuration()

    if not active_config:
        return None, "Aucune configuration Adobe active n'est définie pour contacter l'API."

    try:
        client = AdobeAnalyticsClient(active_config)
        # The client method now handles caching internally.
        components = client.get_adobe_dashboard_components(rsid, force_refresh=force_refresh)
        
        if components.get("error"):
            return None, components.get("error")
        
        return components, None
        
    except Exception as e:
        error_message = f"Une erreur inattendue est survenue lors de la récupération des composants Adobe: {e}"
        print(error_message)
        return None, error_message

def get_report_suites(config_name: Optional[str] = None) -> (List[Dict[str, str]], Optional[str]):
    """
    Fetches the list of report suites available for the active Adobe configuration.
    Returns a tuple: (list_of_suites, error_message).
    """
    if config_name:
        # Load specific config and merge with global settings (proxy)
        raw_config = load_adobe_configuration_by_name(config_name)
        if not raw_config:
            return [], f"Configuration '{config_name}' introuvable."
        
        global_settings = load_global_settings()
        active_config = global_settings.copy()
        active_config.update(raw_config)
    else:
        active_config = get_active_adobe_configuration()

    if not active_config:
        return [], "Aucune configuration Adobe active trouvée."

    try:
        client = AdobeAnalyticsClient(active_config)
        suites_response = client.get_report_suites()

        if suites_response.get("error_code") == "403025":
            error_message = f"Erreur Adobe (403): Le profil du service n'a pas les permissions suffisantes. " \
                            f"Veuillez vérifier que les identifiants sont associés à un 'Product Profile' " \
                            f"dans l'Adobe Admin Console qui donne accès à Adobe Analytics. " \
                            f"(Détail API: {suites_response.get('message')})"
            return [], error_message

        content = suites_response.get("content")
        if content is None and not suites_response.get("error_code"):
             # This could happen on a 200 OK but with an unexpected body, and not an Adobe error format
             return [], f"Réponse inattendue de l'API Adobe. Le contenu attendu ('content') est manquant. Réponse: {str(suites_response)[:200]}"

        return content or [], None # Success, return empty list if content is there but None/empty
        
    except Exception as e:
        print(f"Error fetching Adobe report suites: {e}")
        return [], f"Une erreur de communication est survenue avec l'API Adobe: {e}"

def run_adobe_report(
    rsid: str,
    date_range: str,
    metrics: List[str],
    granularity: str = 'day',
    count_dimension: Optional[str] = None,
    segment_id: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Constructs and runs a report, then formats the result into a pandas DataFrame.
    - If count_dimension is NOT provided, it runs a simple time-series report.
    - If count_dimension IS provided, it runs a time-series report with a breakdown by that dimension.
    """
    active_config = get_active_adobe_configuration()
    if not active_config:
        print("No active Adobe configuration found.")
        return None

    client = AdobeAnalyticsClient(active_config)
    dimension_map = {
        'day': 'variables/daterangeday',
        'hour': 'variables/daterangehour',
        'week': 'variables/daterangeweek',
        'month': 'variables/daterangemonth'
    }
    time_dimension = dimension_map.get(granularity, 'variables/daterangeday')

    # --- Build Report Definition ---
    global_filters = [{"type": "dateRange", "dateRange": date_range}]
    if segment_id:
        global_filters.append({"type": "segment", "segmentId": segment_id})

    report_definition = {
        "rsid": rsid,
        "globalFilters": global_filters,
        "metricContainer": {
            "metrics": [{"id": metric, "columnId": str(i)} for i, metric in enumerate(metrics)]
        },
        "dimension": time_dimension, # Time is always the primary dimension
        "settings": {
            "limit": 400, # Max days in a year approx.
            "dimensionSort": "asc",
            "page": 0
        }
    }

    # If a dimension to count is selected, add it as a breakdown.
    # The API will return the total for the primary time dimension, which is what we want.
    if count_dimension:
        report_definition["breakdowns"] = [count_dimension]

    # --- Execute Report and Process Data ---
    try:
        report_data = client.get_report(report_definition)
        
        if not report_data or 'rows' not in report_data or not report_data['rows']:
            print("Adobe report returned no rows.")
            return pd.DataFrame()

        # --- Data Processing ---
        # The structure is a simple time-series, regardless of breakdown.
        # The breakdown data is ignored as we only need the daily totals.
        data_rows = []
        metric_cols = [m.replace('metrics/', '') for m in metrics]

        for row in report_data['rows']:
            data_row = {'date': row['value']}
            for i, col_name in enumerate(metric_cols):
                data_row[col_name] = row['data'][i]
            data_rows.append(data_row)
            
        if not data_rows:
            return pd.DataFrame()

        df = pd.DataFrame(data_rows)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df

    except Exception as e:
        print(f"An error occurred while running the Adobe report: {e}")
        return None

# --- Saved Reports Management ---

def handle_save_report(name: str, adobe_config_name: str, rsid: str, definition: Dict) -> bool:
    try:
        save_report_configuration(name, adobe_config_name, rsid, definition)
        return True
    except Exception as e:
        print(f"Error saving report: {e}")
        return False

def handle_update_report(report_id: int, name: str, adobe_config_name: str, rsid: str, definition: Dict) -> bool:
    try:
        update_saved_report(report_id, name, adobe_config_name, rsid, definition)
        return True
    except Exception as e:
        print(f"Error updating report: {e}")
        return False

def get_all_saved_reports() -> List[Dict]:
    return load_saved_reports()

def handle_delete_report(report_id: int):
    delete_saved_report(report_id)

def run_saved_report(report: Dict, date_range: str, status_callback=None, force_refresh: bool = False) -> (Optional[pd.DataFrame], str):
    """
    Runs a saved report using its stored configuration.
    Checks for a cached result first unless force_refresh is True.
    """
    import json
    
    # Defensive coding: handle missing or empty definition
    def_str = report.get('definition')
    if not def_str:
        return None, "La définition du rapport est vide."
    
    try:
        definition = json.loads(def_str)
    except json.JSONDecodeError:
        return None, "Le format de la définition du rapport est invalide."

    report_id = report['id']
    # Create a stable key for the date range by removing special characters
    date_range_key = date_range.replace('/', '_').replace(':', '').replace('-', '')

    # 1. Check cache first
    if not force_refresh:
        # TTL of 1 day (86400 seconds)
        cached_df, cached_status = load_report_result(report_id, date_range_key, ttl=86400)
        if cached_df is not None:
            print(f"Loaded report {report_id} for range {date_range} from cache.")
            # The status from cache might be "OK" or "Aucune donnée."
            return cached_df, f"{cached_status} (Cache)"

    config_name = report['adobe_config_name']
    config = load_adobe_configuration_by_name(config_name)
    
    if not config:
        return None, f"Configuration Adobe '{config_name}' introuvable."

    # Merge global settings (Proxy) into config
    global_settings = load_global_settings()
    full_config = global_settings.copy()
    full_config.update(config)
    
    # --- DISPATCHER: Check Report Type ---
    if definition.get('type') == 'system_audit':
        # For audit, date_range passed from UI might be ignored if specific ranges are saved, 
        # OR we can use it as an override. For now, let's use the saved ranges in definition.
        df = run_system_audit_report(full_config, report['rsid'], definition, status_callback)
        if df is not None and not df.empty:
            save_report_result(report_id, date_range_key, df, "OK")
            return df, "OK"
        else:
            return pd.DataFrame(), "Erreur ou aucune donnée (Audit)."

    try:
        client = AdobeAnalyticsClient(full_config)
        # Reconstruct arguments for the client report
        # We need to map the definition back to the structure run_adobe_report builds, 
        # OR just build the report_definition dict directly here.
        
        # Let's rebuild the report definition dict manually to be safe
        # --- NEW LOGIC: Handle 'columns' with potential segment filters ---
        columns = definition.get('columns', [])
        # Fallback for legacy reports
        if not columns and 'metrics' in definition:
            columns = [{"metric_id": m, "segment_id": None} for m in definition['metrics']]

        granularity = definition.get('granularity', 'day')
        report_type = definition.get('type', 'dimension') # 'dimension' or 'segment'
        
        # Fallback/Inference: If 'segments' list exists, it's a Segment Comparison report
        if definition.get('segments') and isinstance(definition['segments'], list) and len(definition['segments']) > 0:
            report_type = 'segment'
        
        # Map granularity to time dimension
        time_dim_map = {
            'day': 'variables/daterangeday',
            'week': 'variables/daterangeweek',
            'month': 'variables/daterangemonth',
            'year': 'variables/daterangeyear'
        }
        time_dimension = time_dim_map.get(granularity, 'variables/daterangeday')
        
        global_filters = [{"type": "dateRange", "dateRange": date_range}]
        
        # --- Resolve Segment Names ---
        # We fetch components to map IDs to Names for better readability
        segment_map = {}
        if report_type == 'segment' or definition.get('segments'):
             # We need the config name to load the right cache
             comps, _ = get_or_refresh_components(report['rsid'], config_name=report['adobe_config_name'])
             if comps and 'segments' in comps:
                 segment_map = {s['id']: s['name'] for s in comps['segments']}

        data_rows = []
        
        # Build API Metric Objects
        api_metrics = []
        metric_filters = [] # List to hold API 2.0 MetricFilter definitions
        col_headers = [] # To map result columns back to readable names
        
        for i, col in enumerate(columns):
            m_id = col.get('metric_id')
            if not m_id:
                continue # Skip columns without metric
                
            s_id = col.get('segment_id')
            
            metric_obj = {"id": m_id, "columnId": str(i)}
            if s_id:
                # API 2.0 requires defining a metricFilter referencing the segment
                # Simplified ID to ensure compatibility (numeric string like "0", "1")
                filter_ref_id = str(i)
                metric_filters.append({
                    "id": filter_ref_id,
                    "type": "segment",
                    "segmentId": s_id
                })
                metric_obj["filters"] = [filter_ref_id]
            
            api_metrics.append(metric_obj)
            
            # Prepare header name for later
            m_name = m_id.split('/')[-1] # Fallback name
            s_name = segment_map.get(s_id, "Seg") if s_id else None
            
            if s_name:
                col_headers.append(f"{m_name} ({s_name})")
            else:
                col_headers.append(m_name)

        if report_type == 'segment':
            # Mode: Compare Segments (Rows = Segments)
            # We run one report per segment to get the totals/metrics for that segment
            segments = definition.get('segments', [])
            
            # --- ASYNC OPTIMIZATION START ---
            # 1. Prepare Auth
            client._ensure_token()
            access_token = client.access_token
            api_key = client.api_key
            company_id = client.global_company_id
            
            async def fetch_segment_row(session, seg_id, semaphore):
                url = f"https://analytics.adobe.io/api/{company_id}/reports"
                
                # Clone filters and add specific segment
                current_filters = global_filters.copy()
                current_filters.append({"type": "segment", "segmentId": seg_id})
                
                metric_container = {"metrics": api_metrics}
                if metric_filters:
                    metric_container["metricFilters"] = metric_filters

                report_def = {
                    "rsid": report['rsid'],
                    "globalFilters": current_filters,
                    "metricContainer": metric_container,
                    "dimension": time_dimension,
                    "settings": {"limit": 400}
                }
                
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "Authorization": f"Bearer {access_token}"
                }
                
                async with semaphore:
                    for attempt in range(4): # Retry logic
                        try:
                            async with session.post(url, json=report_def, headers=headers) as response:
                                if response.status == 200:
                                    return await response.json(), seg_id, None
                                elif response.status == 429:
                                    sleep_time = (2 ** (attempt + 1)) + random.uniform(0, 1)
                                    await asyncio.sleep(sleep_time)
                                    continue
                                else:
                                    text = await response.text()
                                    return None, seg_id, f"Error {response.status}: {text}"
                        except Exception as e:
                            return None, seg_id, str(e)
                    return None, seg_id, "Max retries exceeded"

            async def main_segment_loop():
                semaphore = asyncio.Semaphore(10) # Limit concurrency
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for seg_id in segments:
                        tasks.append(fetch_segment_row(session, seg_id, semaphore))
                    
                    results = []
                    completed = 0
                    total = len(segments)
                    start_time = time.time()

                    for future in asyncio.as_completed(tasks):
                        report_data, seg_id, error = await future
                        
                        # Process Result
                        seg_name = segment_map.get(seg_id, seg_id)
                        
                        if error:
                            row_data = {'Segment': f"{seg_name} (Erreur)", '_segment_id': seg_id, 'status': 'Error', 'error_message': error}
                        else:
                            row_data = {'Segment': seg_name, '_segment_id': seg_id}
                            if report_data and 'rows' in report_data:
                                for row in report_data['rows']:
                                    date_key = row['value']
                                    for i, header in enumerate(col_headers):
                                        val = row['data'][i] if i < len(row['data']) else 0
                                        try: val = float(val)
                                        except: val = 0.0
                                        col_label = f"{date_key} ({header})" if len(columns) > 1 else date_key
                                        row_data[col_label] = val
                        
                        results.append(row_data)
                        
                        # Update Progress
                        completed += 1
                        if status_callback:
                            elapsed = time.time() - start_time
                            avg_time = elapsed / completed
                            rem = int(avg_time * (total - completed))
                            status_callback(completed, total, rem, completed/total)
                    
                    return results

            # Run Async Loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    data_rows = loop.run_until_complete(main_segment_loop())
                else:
                    data_rows = asyncio.run(main_segment_loop())
            except RuntimeError:
                data_rows = asyncio.run(main_segment_loop())
            # --- ASYNC OPTIMIZATION END ---
            
            df = pd.DataFrame(data_rows)
            # Fill NaNs with 0 for missing dates in some segments
            df.fillna(0, inplace=True)
            
            # Save result to cache before returning
            save_report_result(report_id, date_range_key, df, "OK")
            return df, "OK"

        else:
            # Mode: Dimension Breakdown (Rows = Dimension Items, e.g. Pages)
            target_dimension = definition.get('dimension', time_dimension)
            
            metric_container = {"metrics": api_metrics}
            if metric_filters:
                metric_container["metricFilters"] = metric_filters

            # We need a breakdown by time to get columns per granularity
            # Structure: Dimension -> Breakdown (Time) -> Metrics
            report_def = {
                "rsid": report['rsid'],
                "globalFilters": global_filters,
                "metricContainer": metric_container,
                "dimension": target_dimension,
                "settings": {"limit": 50, "dimensionSort": "desc"}, # Top 50 items
                "breakdowns": [
                    {
                        "dimension": time_dimension,
                        "settings": {"limit": 400} # Cover the date range
                    }
                ]
            }
            
            print(f"DEBUG: Adobe Report Payload (Dimension): {json.dumps(report_def)}")
            
            report_data = client.get_report(report_def)
            
            if not report_data or 'rows' not in report_data:
                empty_df = pd.DataFrame()
                save_report_result(report_id, date_range_key, empty_df, "Aucune donnée.")
                return empty_df, "Aucune donnée."

            for row in report_data.get('rows', []):
                data_row = {'Item': row['value'], '_item_id': row.get('itemId', row['value'])} 
                
                # Iterate over the time breakdown (nested rows)
                if 'rows' in row:
                    for date_row in row['rows']:
                        date_key = date_row['value']
                        for i, header in enumerate(col_headers):
                            val = date_row['data'][i] if i < len(date_row['data']) else 0
                            try:
                                val = float(val)
                            except:
                                val = 0.0
                            
                            col_label = f"{date_key} ({header})" if len(columns) > 1 else date_key
                            data_row[col_label] = val
                            
                data_rows.append(data_row)
            
        if not data_rows:
            empty_df = pd.DataFrame()
            save_report_result(report_id, date_range_key, empty_df, "Aucune donnée.")
            return empty_df, "Aucune donnée."

        df = pd.DataFrame(data_rows)
        df.fillna(0, inplace=True)
        
        # --- Sort Columns Chronologically ---
        # Identify metadata columns that should stay at the start
        meta_cols_order = ['Segment', 'Item', '_segment_id', '_item_id']
        present_meta = [c for c in meta_cols_order if c in df.columns]
        
        # Identify data columns
        data_cols = [c for c in df.columns if c not in present_meta]
        
        if len(columns) > 1:
            # Custom sort: Group by Metric (Header order), then by Date
            def get_sort_key(col_name):
                # Expected format: "YYYY-MM-DD (Header Name)"
                # We split from left to separate Date and Header safely
                try:
                    date_part, header_part_raw = col_name.split(' (', 1)
                    header_name = header_part_raw[:-1] # Remove trailing ')'
                    
                    # Primary sort key: Index of the header in the definition list
                    header_index = col_headers.index(header_name) if header_name in col_headers else 9999
                    return (header_index, date_part)
                except ValueError:
                    return (9999, col_name)

            data_cols.sort(key=get_sort_key)
        else:
            # Single metric: just sort by date (alphabetical works for ISO dates)
            data_cols.sort()
        
        # Reorder DataFrame
        df = df[present_meta + data_cols]
        
        save_report_result(report_id, date_range_key, df, "OK")
        return df, "OK"

    except Exception as e:
        return None, str(e)

# --- History Management ---

def get_report_history() -> List[Dict]:
    """Fetches the list of all historical report executions."""
    return get_all_cached_report_results()

def load_historical_report_dataframe(cache_id: int) -> Optional[pd.DataFrame]:
    """Loads the DataFrame for a specific history item."""
    result = get_cached_result_by_id(cache_id)
    if result and result.get('result_data'):
        try:
            return pd.read_json(result['result_data'], orient='split')
        except Exception as e:
            print(f"Error loading cached JSON for history {cache_id}: {e}")
    return None

def delete_report_history_item(cache_id: int):
    delete_cached_result(cache_id)

def format_date_range_readable(key: str) -> str:
    """Converts '20230101T000000_20230131T235959' to '2023-01-01 au 2023-01-31'."""
    try:
        parts = key.split('_')
        start = parts[0][:8] # YYYYMMDD
        end = parts[1][:8]
        return f"{start[:4]}-{start[4:6]}-{start[6:]} au {end[:4]}-{end[4:6]}-{end[6:]}"
    except:
        return key

def _get_union_date_range(range1: str, range2: str) -> str:
    """
    Calculates a date range that covers both input ranges.
    Input format: YYYY-MM-DDTHH:MM:SS/YYYY-MM-DDTHH:MM:SS
    """
    try:
        start1, end1 = range1.split('/')
        start2, end2 = range2.split('/')
        return f"{min(start1, start2)}/{max(end1, end2)}"
    except:
        return range1 # Fallback

def run_system_audit_report(adobe_config_dict, rsid, definition, status_callback=None):
    """
    Runs a massive audit on all 200 eVars and 75 props for two segments and two date ranges.
    OPTIMIZED: Uses asyncio + aiohttp and Adobe API 2.0 'predicates' to fetch 4 data points in 1 call.
    """
    # Extract parameters from definition
    date_range_1 = definition.get('range1')
    date_range_2 = definition.get('range2')
    segment_id_1 = definition.get('segment1')
    segment_id_2 = definition.get('segment2')

    # Calculate global range covering both periods to satisfy API requirement (Error 400 fix)
    # while allowing metric filters to narrow it down to specific ranges.
    global_range = _get_union_date_range(date_range_1, date_range_2)

    # 1. Define the list of dimensions to audit
    # Production scope: 200 eVars + 75 Props
    dimensions_to_audit = [f"variables/evar{i}" for i in range(1, 201)] + \
                          [f"variables/prop{i}" for i in range(1, 76)]
    
    # 2. Prepare Authentication (Sync)
    # We get the token once using the sync client to avoid complexity in async
    try:
        sync_client = AdobeAnalyticsClient(adobe_config_dict)
        sync_client._ensure_token()
        access_token = sync_client.access_token
        api_key = sync_client.api_key
        company_id = sync_client.global_company_id
    except Exception as e:
        print(f"Auth Error: {e}")
        return pd.DataFrame()

    # 3. Async Worker Function
    async def fetch_dimension_data(session, dim_id, semaphore):
        url = f"https://analytics.adobe.io/api/{company_id}/reports"
        
        # Construct Optimized Payload (4 columns in 1 call)
        # Columns: 0=Seg1_P1, 1=Seg2_P1, 2=Seg1_P2, 3=Seg2_P2
        
        # We use atomic filters combined in the metric definition (AND logic)
        metric_filters = [
            {"id": "d1", "type": "dateRange", "dateRange": date_range_1},
            {"id": "d2", "type": "dateRange", "dateRange": date_range_2},
            {"id": "s1", "type": "segment", "segmentId": segment_id_1},
            {"id": "s2", "type": "segment", "segmentId": segment_id_2}
        ]

        metrics = [
            {"id": "metrics/pageviews", "columnId": "0", "filters": ["d1", "s1"]}, # Seg1 + P1
            {"id": "metrics/pageviews", "columnId": "1", "filters": ["d1", "s2"]}, # Seg2 + P1
            {"id": "metrics/pageviews", "columnId": "2", "filters": ["d2", "s1"]}, # Seg1 + P2
            {"id": "metrics/pageviews", "columnId": "3", "filters": ["d2", "s2"]}  # Seg2 + P2
        ]

        payload = {
            "rsid": rsid,
            "globalFilters": [
                {"type": "dateRange", "dateRange": global_range}
            ],
            "metricContainer": {
                "metrics": metrics,
                "metricFilters": metric_filters
            },
            "dimension": dim_id,
            "search": {
                "excludeItemIds": ["0"]
            },
            "settings": {
                "limit": 1, # We just want totals, top 1 is enough to trigger summaryData calculation
                "page": 0
            }
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "Authorization": f"Bearer {access_token}"
        }

        async with semaphore:
            # Retry Loop for 429 errors
            for attempt in range(5):
                try:
                    async with session.post(url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Parse results from summaryData -> filteredTotals
                            # Order matches columnIds: 0, 1, 2, 3
                            totals = data.get('summaryData', {}).get('filteredTotals', [0, 0, 0, 0])
                            # Ensure we have 4 values (pad with 0 if missing)
                            totals = totals + [0] * (4 - len(totals))
                            
                            return {
                                "Dimension": dim_id,
                                "Seg1_P1": totals[0],
                                "Seg2_P1": totals[1],
                                "Seg1_P2": totals[2],
                                "Seg2_P2": totals[3]
                            }
                        elif response.status == 429:
                            sleep_time = (2 ** (attempt + 1)) + random.uniform(0, 1)
                            # print(f"⚠️ 429 Rate Limit for {dim_id}. Retrying in {sleep_time:.2f}s...")
                            await asyncio.sleep(sleep_time)
                            continue # Retry
                        elif response.status == 206:
                            # Partial content: Check if dimension is disabled
                            try:
                                data = await response.json()
                                col_errors = data.get("columns", {}).get("columnErrors", [])
                                for err in col_errors:
                                    if err.get("errorCode") in ["not_enabled_dimension_global", "dimension_not_enabled", "unauthorized_dimension"]:
                                        return {"Dimension": dim_id, "Seg1_P1": "Non actif", "Seg2_P1": "Non actif", "Seg1_P2": "Non actif", "Seg2_P2": "Non actif"}
                                
                                # If 206 but not disabled (other partial error), treat as error
                                print(f"⚠️ 206 Partial for {dim_id}: {col_errors}")
                                return {"Dimension": dim_id, "Seg1_P1": "Erreur", "Seg2_P1": "Erreur", "Seg1_P2": "Erreur", "Seg2_P2": "Erreur"}
                            except:
                                return {"Dimension": dim_id, "Seg1_P1": "Erreur", "Seg2_P1": "Erreur", "Seg1_P2": "Erreur", "Seg2_P2": "Erreur"}
                        else:
                            text = await response.text()
                            print(f"❌ Error {response.status} for {dim_id}: {text}")
                            return {"Dimension": dim_id, "Seg1_P1": -1, "Seg2_P1": -1, "Seg1_P2": -1, "Seg2_P2": -1}
                except Exception as e:
                    print(f"❌ Exception for {dim_id}: {e}")
                    return {"Dimension": dim_id, "Seg1_P1": -1, "Seg2_P1": -1, "Seg1_P2": -1, "Seg2_P2": -1}
            
            # If all retries failed
            return {"Dimension": dim_id, "Seg1_P1": -1, "Seg2_P1": -1, "Seg1_P2": -1, "Seg2_P2": -1}

    # 4. Main Async Loop
    async def main_loop():
        # Configure Proxy for aiohttp if needed
        # Note: aiohttp uses a different proxy format than requests
        # We'll assume direct connection or system proxy for simplicity unless specified
        # If proxy needed: connector = aiohttp.TCPConnector(ssl=False)
        
        # Limit concurrency to avoid 429s
        semaphore = asyncio.Semaphore(10) 
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            total = len(dimensions_to_audit)
            
            for dim in dimensions_to_audit:
                tasks.append(fetch_dimension_data(session, dim, semaphore))
            
            # Use as_completed to update progress bar
            results = []
            completed = 0
            for future in asyncio.as_completed(tasks):
                res = await future
                results.append(res)
                completed += 1
                if status_callback:
                    status_callback(completed, total, 0, completed/total)
            
            return results

    # 5. Run Asyncio
    # Check if there is an existing loop (Streamlit might have one)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we are already in a loop (e.g. inside a Jupyter notebook or some Streamlit runners)
            # we should use create_task, but here we are in a sync function called by Streamlit.
            # Ideally we use asyncio.run() but it fails if loop is running.
            # Fallback: nest_asyncio or run_until_complete if not running.
            final_list = loop.run_until_complete(main_loop())
        else:
            final_list = asyncio.run(main_loop())
    except RuntimeError:
        # "There is no current event loop in thread" -> Create new one
        final_list = asyncio.run(main_loop())

    # 6. Format DataFrame
    
    # Sort by eVar number then Prop number
    def sort_key(x):
        d = x['Dimension']
        if 'evar' in d: return 1000 + int(d.replace('variables/evar', ''))
        if 'prop' in d: return 2000 + int(d.replace('variables/prop', ''))
        return 9999
        
    final_list.sort(key=sort_key)
    
    df = pd.DataFrame(final_list)
    
    # Reorder columns if they exist
    cols = ["Dimension", "Seg1_P1", "Seg2_P1", "Seg1_P2", "Seg2_P2"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    
    return df