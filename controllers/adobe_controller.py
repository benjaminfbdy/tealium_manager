import pandas as pd
from typing import Dict, List, Optional, Any
from database import get_active_adobe_configuration
from utils.adobe_client import AdobeAnalyticsClient

def get_or_refresh_components(rsid: str, force_refresh: bool = False) -> (Optional[Dict], Optional[str]):
    """
    Gets Adobe Analytics components (dimensions, metrics, segments) for a given RSID
    by calling the client, which handles caching internally.
    
    Args:
        rsid (str): The report suite ID.
        force_refresh (bool): If True, the client will bypass its cache.

    Returns:
        A tuple: (components_dictionary, error_message)
    """
    print(f"Controller: Requesting components for RSID '{rsid}' (force_refresh: {force_refresh}).")
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

def get_report_suites() -> (List[Dict[str, str]], Optional[str]):
    """
    Fetches the list of report suites available for the active Adobe configuration.
    Returns a tuple: (list_of_suites, error_message).
    """
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