# Fetch leave types from the HR API

import requests
from leavebot.config.settings import LEAVE_TYPE_API, ERP_BEARER_TOKEN
from .cache_utils import LEAVE_TYPES_CACHE

def fetch_leave_types(emp_id, cgm_id=1):
    """
    Fetch all available leave types for the employee.
    Returns: List of leave type dicts.
    """
    cache_key = (emp_id, cgm_id)
    if cache_key in LEAVE_TYPES_CACHE:
        return LEAVE_TYPES_CACHE[cache_key]

    headers = {
        "Authorization": f"Bearer {ERP_BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{LEAVE_TYPE_API}?Emp_ID_N={emp_id}&Cgm_ID_N={cgm_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    LEAVE_TYPES_CACHE[cache_key] = data
    return data
