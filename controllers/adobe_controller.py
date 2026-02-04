import pandas as pd
from typing import Dict, List, Optional, Any
from database import get_active_adobe_configuration, save_report_configuration, update_saved_report, load_saved_reports, delete_saved_report, load_adobe_configuration_by_name, load_global_settings, save_report_result, load_report_result, get_all_cached_report_results, get_cached_result_by_id, delete_cached_result
from utils.adobe_client import AdobeAnalyticsClient
import time

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

    import json
    
    # Defensive coding: handle missing or empty definition
    def_str = report.get('definition')
    if not def_str:
        return None, "La définition du rapport est vide ou corrompue (colonne manquante)."
    
    try:
        definition = json.loads(def_str)
    except json.JSONDecodeError:
        return None, "Le format de la définition du rapport est invalide."
    
    try:
        client = AdobeAnalyticsClient(config)
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
            start_time = time.time()
            
            for idx, seg_id in enumerate(segments):
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
                    "dimension": time_dimension, # We still need a dimension to get data, usually time
                    "settings": {"limit": 400} # Fetch full time series to ensure we catch data if present
                }
                
                try:
                    print(f"DEBUG: Adobe Report Payload (Segment Row): {json.dumps(report_def)}")
                    report_data = client.get_report(report_def)
                except Exception as e:
                    # If the request fails after all retries, create an error row and continue
                    seg_name = segment_map.get(seg_id, seg_id)
                    error_row = {'Segment': f"{seg_name} (Erreur)", '_segment_id': seg_id, 'status': 'Error', 'error_message': str(e)}
                    data_rows.append(error_row)
                    # Continue to the next segment
                    continue

                seg_name = segment_map.get(seg_id, seg_id) # Fallback to ID if name not found
                row_data = {'Segment': seg_name, '_segment_id': seg_id} # Keep ID hidden for logic
                
                # Pivot data: Time buckets become columns
                if report_data and 'rows' in report_data:
                    for row in report_data['rows']:
                        date_key = row['value']
                        for i, header in enumerate(col_headers):
                            val = row['data'][i] if i < len(row['data']) else 0
                            try:
                                val = float(val)
                            except (ValueError, TypeError):
                                val = 0.0
                            
                            # Column name format: "YYYY-MM-DD (metric)"
                            col_label = f"{date_key} ({header})" if len(columns) > 1 else date_key
                            row_data[col_label] = val

                data_rows.append(row_data)
                
                # --- ETA Calculation & Callback ---
                if status_callback:
                    elapsed = time.time() - start_time
                    avg_time_per_req = elapsed / (idx + 1)
                    remaining_items = len(segments) - (idx + 1)
                    est_seconds_left = int(avg_time_per_req * remaining_items)
                    percentage = (idx + 1) / len(segments)
                    status_callback(idx + 1, len(segments), est_seconds_left, percentage)
            
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