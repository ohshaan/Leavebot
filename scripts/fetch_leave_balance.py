import requests
from leavebot_copy.config.settings import LEAVE_SUMMARY_API, ERP_BEARER_TOKEN
from .cache_utils import LEAVE_BALANCE_CACHE

def fetch_leave_balance(emp_id, lpd_id, from_date, to_date):
    """
    Fetch leave balance for a specific leave type and period.
    Returns: Dict (API response), or None if no data.
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
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    result = data[0] if data else None
    LEAVE_BALANCE_CACHE[cache_key] = result
    return result
