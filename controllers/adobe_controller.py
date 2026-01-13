import pandas as pd
from typing import Dict, List, Optional, Any
from database import get_active_adobe_configuration
from utils.adobe_client import AdobeAnalyticsClient

def get_report_suites() -> List[Dict[str, str]]:
    """
    Fetches the list of report suites available for the active Adobe configuration.
    """
    active_config = get_active_adobe_configuration()
    if not active_config:
        return []

    try:
        client = AdobeAnalyticsClient(active_config)
        suites_response = client.get_report_suites()
        # The actual list is nested under 'content'
        return suites_response.get("content", [])
    except Exception as e:
        print(f"Error fetching Adobe report suites: {e}")
        return []

def run_adobe_report(
    rsid: str,
    date_range: str,
    dimension: str,
    metrics: List[str],
    granularity: str = 'day'
) -> Optional[pd.DataFrame]:
    """
    Constructs and runs a report, then formats the result into a pandas DataFrame.
    
    Args:
        rsid: Report Suite ID.
        date_range: Date range string formatted as 'YYYY-MM-DD/YYYY-MM-DD'.
        dimension: The primary dimension for the report.
        metrics: A list of metric IDs.
        granularity: The time granularity ('day', 'hour', 'week', 'month').

    Returns:
        A pandas DataFrame containing the report data, or None on error.
    """
    active_config = get_active_adobe_configuration()
    if not active_config:
        print("No active Adobe configuration found.")
        return None

    # Map granularity to the correct Adobe dimension
    dimension_map = {
        'day': 'variables/daterangeday',
        'hour': 'variables/daterangehour',
        'week': 'variables/daterangeweek',
        'month': 'variables/daterangemonth',
    }
    time_dimension = dimension_map.get(granularity, 'variables/daterangeday')

    # Construct the report definition
    report_definition = {
        "rsid": rsid,
        "globalFilters": [
            {
                "type": "dateRange",
                "dateRange": date_range
            }
        ],
        "metricContainer": {
            "metrics": [{"id": metric, "columnId": str(i)} for i, metric in enumerate(metrics)]
        },
        "dimension": time_dimension,
        "settings": {
            "dimensionSort": "asc",
            "limit": 1000  # The client handles pagination, this is per-request limit
        }
    }

    try:
        client = AdobeAnalyticsClient(active_config)
        report_data = client.get_report(report_definition)
        
        # --- Process data into a DataFrame ---
        if not report_data or 'rows' not in report_data:
            return pd.DataFrame() # Return empty DataFrame if no data

        rows = report_data['rows']
        data_rows = []
        for row in rows:
            # The 'value' is the date string, 'data' is the list of metric values
            data_row = {'date': row['value']}
            for i, metric in enumerate(metrics):
                col_name = metric.replace('metrics/', '') # Clean name for column
                data_row[col_name] = row['data'][i]
            data_rows.append(data_row)
            
        df = pd.DataFrame(data_rows)

        if not df.empty:
            # Convert date column to datetime objects and set as index
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
        return df

    except Exception as e:
        print(f"An error occurred while running the Adobe report: {e}")
        # In a real app, you might want to raise this or handle it more gracefully
        return None
