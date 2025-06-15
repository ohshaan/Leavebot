import requests
from leavebot.config.settings import LEAVE_SUMMARY_API, ERP_BEARER_TOKEN
from ..core.cache_utils import LEAVE_BALANCE_CACHE

def fetch_leave_balance(emp_id, lpd_id, from_date, to_date):
    """
    Fetch leave balance for a specific leave type (lpd_id) and date range.
    Caches results per (emp_id, lpd_id, from_date, to_date).

    Args:
        emp_id (int): Employee ID.
        lpd_id (int): Leave policy detail ID (leave type ID).
        from_date (str): Start date in 'YYYY-MM-DD' format.
        to_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
        dict or None: The first record of leave balance data from API, or None if empty.
    """
    cache_key = (emp_id, lpd_id, from_date, to_date)
    if cache_key in LEAVE_BALANCE_CACHE:
        return LEAVE_BALANCE_CACHE[cache_key]

    headers = {
        "Authorization": f"Bearer {ERP_BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    strsql = f"{emp_id},{lpd_id},'{from_date}','{to_date}',0,0,1,0"
    url = f"{LEAVE_SUMMARY_API}?StrSql={strsql}"

    try:
        response = requests.post(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        result = data[0] if isinstance(data, list) and data else None
        LEAVE_BALANCE_CACHE[cache_key] = result
        return result
    except requests.RequestException as e:
        print(f"Failed to fetch leave balance for Emp_ID {emp_id}, Lpd_ID {lpd_id}: {e}")
        return None
