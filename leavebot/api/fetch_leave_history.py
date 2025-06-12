import requests
from leavebot.config.settings import LEAVE_HISTORY_API, ERP_BEARER_TOKEN
from ..core.cache_utils import LEAVE_HISTORY_CACHE

# We assume `leave_types` (fetched via fetch_leave_types) is passed in to map Lvm_ID_N → code

def fetch_leave_history(emp_id, leave_types):
    """
    Fetch leave history/applications for the given employee.
    Returns a list of leave application dicts, each enriched with `LeaveGrid_Lvm_Code_V`.
    """
    cache_key = emp_id
    if cache_key in LEAVE_HISTORY_CACHE:
        return LEAVE_HISTORY_CACHE[cache_key]

    headers = {
        "Authorization": f"Bearer {ERP_BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    str_filter = f"A.Emp_ID_N={emp_id} AND A.Ela_Status_N NOT IN (0,6) ORDER BY Ela_RefferNo_V"
    url = f"{LEAVE_HISTORY_API}?StrFilter={str_filter}"
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Build mapping from Lvm_ID_N → Lvm_Code_V
    code_by_id = {lt["Lvm_ID_N"]: lt.get("Lvm_Code_V") for lt in leave_types}
    
    # Enrich each record with its leave code
    for rec in data:
        lvm_id = rec.get("LeaveGrid_Lvm_ID_N")
        rec["LeaveGrid_Lvm_Code_V"] = code_by_id.get(lvm_id)

    LEAVE_HISTORY_CACHE[cache_key] = data
    return data
