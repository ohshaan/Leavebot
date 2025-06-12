import requests
from leavebot_copy.config.settings import EMPLOYEE_DETAILS_API, ERP_BEARER_TOKEN

def fetch_employee_details(emp_id):
    """
    Fetch employee profile/details for the given emp_id.
    Returns: List of dicts (API format), or raises Exception on error.
    """
    headers = {
        "Authorization": f"Bearer {ERP_BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{EMPLOYEE_DETAILS_API}?strEmp_ID_N={emp_id}"
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()
