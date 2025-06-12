import requests
from config.settings import EMPLOYEE_DETAILS_API, ERP_BEARER_TOKEN # type: ignore
from .cache_utils import EMPLOYEE_CACHE

def fetch_employee_details(emp_id):
    """
    Fetch employee profile/details for the given emp_id.
    Returns: List of dicts (API format), or raises Exception on error.
    """
    if emp_id in EMPLOYEE_CACHE:
        return EMPLOYEE_CACHE[emp_id]

    headers = {
        "Authorization": f"Bearer {ERP_BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{EMPLOYEE_DETAILS_API}?strEmp_ID_N={emp_id}"
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    EMPLOYEE_CACHE[emp_id] = data
    return data
