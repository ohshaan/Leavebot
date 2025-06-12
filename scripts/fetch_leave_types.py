# leavebot_copy/scripts/fetch_leave_types.py

import requests
from leavebot_copy.config.settings import LEAVE_TYPE_API, ERP_BEARER_TOKEN

def fetch_leave_types(emp_id, cgm_id=1):
    """
    Fetch all available leave types for the employee.
    Returns: List of leave type dicts.
    """
    headers = {
        "Authorization": f"Bearer {ERP_BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{LEAVE_TYPE_API}?Emp_ID_N={emp_id}&Cgm_ID_N={cgm_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
