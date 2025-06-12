import requests
from leavebot.config.settings import LEAVE_SUMMARY_API, ERP_BEARER_TOKEN

def fetch_leave_balance(emp_id, lpd_id, from_date, to_date):
    """
    Fetch leave balance for a specific leave type and period.
    Returns: Dict (API response), or None if no data.
    """
    headers = {
        "Authorization": f"Bearer {ERP_BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    strsql = f"{emp_id},{lpd_id},'{from_date}','{to_date}',0,0,1,0"
    url = f"{LEAVE_SUMMARY_API}?StrSql={strsql}"
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None
