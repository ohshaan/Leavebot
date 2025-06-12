import requests
from Leavebot.config.settings import EMPLOYEE_DETAILS_API, ERP_BEARER_TOKEN

def fetch_manager_details(manager_emp_id):
    """
    Fetches manager details using the employee details API.
    Returns the first record as dict, or None if not found.
    """
    headers = {
        "Authorization": f"Bearer {ERP_BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{EMPLOYEE_DETAILS_API}?strEmp_ID_N={manager_emp_id}"
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    # Return the first record, or None if no data
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return None

def get_manager_contact(manager_emp_id):
    """
    Returns a simplified dict with the manager's name, email, and mobile.
    """
    mgr = fetch_manager_details(manager_emp_id)
    if not mgr:
        return None
    return {
        "name": mgr.get("Emp_EDisplayName_V") or mgr.get("Emp_EFullName_V"),
        "email": mgr.get("Emp_EmailID_V"),
        "mobile": mgr.get("Emp_Mobile_V"),
        "employee_code": mgr.get("Emp_Code_V"),
        "designation": mgr.get("Dsm_Desc_V"),
    }
