import requests
from leavebot.config.settings import LEAVE_TYPE_API, ERP_BEARER_TOKEN
from ..core.cache_utils import LEAVE_TYPES_CACHE

def fetch_leave_types(emp_id, cgm_id=1):
    """
    Fetch all available leave types for the employee from the HR API.

    Caches the result per (emp_id, cgm_id) in-memory to avoid redundant API calls.

    Args:
        emp_id (int): Employee ID.
        cgm_id (int): Company Group Master ID.

    Returns:
        list[dict]: List of leave type dictionaries.
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

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Cache the data for subsequent calls
        LEAVE_TYPES_CACHE[cache_key] = data
        return data
    except requests.RequestException as e:
        # Log error appropriately; here we just print
        print(f"Failed to fetch leave types for Emp_ID {emp_id}: {e}")
        # Optionally return empty list or raise exception
        return []
