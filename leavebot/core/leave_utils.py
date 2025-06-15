# leave_utils.py
from datetime import datetime
from collections import Counter, defaultdict

def build_leave_mappings(leave_types):
    """
    Build code-to-description, description-to-code, and code-to-Lpd_ID_N mappings from API data.
    """
    code_to_desc = {
        lt["Lvm_Code_V"]: lt["Lvm_Description_V"]
        for lt in leave_types
        if lt.get("Lvm_Code_V")
    }
    desc_to_code = {
        lt["Lvm_Description_V"]: lt["Lvm_Code_V"]
        for lt in leave_types
        if lt.get("Lvm_Description_V")
    }
    code_to_lpdid = {
        lt["Lvm_Code_V"]: lt["Lpd_ID_N"]
        for lt in leave_types
        if lt.get("Lvm_Code_V") and lt.get("Lpd_ID_N") is not None
    }
    return code_to_desc, desc_to_code, code_to_lpdid

def build_leave_type_groups(leave_types):
    """
    Build groupings like 'sick', 'casual', 'annual', 'emergency' based on keywords in descriptions.
    Returns: dict of {group_name: set_of_codes}
    """
    groups = defaultdict(set)
    for lt in leave_types:
        code = lt.get("Lvm_Code_V", "")
        desc = (lt.get("Lvm_Description_V") or "").upper()
        if "SICK" in desc:
            groups["sick"].add(code)
        if "CASUAL" in desc:
            groups["casual"].add(code)
        if "ANNUAL" in desc:
            groups["annual"].add(code)
        if "EMERGENCY" in desc:
            groups["emergency"].add(code)
    return dict(groups)

def total_leave_taken(leave_history, leave_types, code_or_group=None):
    """
    Sum leave days taken for a specific code, description, or group.
    Only includes approved leaves.
    """
    code_to_desc, desc_to_code, _ = build_leave_mappings(leave_types)
    groups = build_leave_type_groups(leave_types)

    if not code_or_group:
        codes = {rec.get("LeaveGrid_Lvm_Code_V") for rec in leave_history}
    else:
        grp = groups.get(str(code_or_group).lower())
        if grp:
            codes = grp
        elif code_or_group in code_to_desc:
            codes = {code_or_group}
        elif code_or_group in desc_to_code:
            codes = {desc_to_code[code_or_group]}
        else:
            codes = {code_or_group}

    total = 0.0
    for rec in leave_history:
        if rec.get("LeaveGrid_Status") != "Approved":
            continue
        if rec.get("LeaveGrid_Lvm_Code_V") in codes:
            try:
                total += float(rec.get("LeaveGrid_Ela_Tot", 0) or 0)
            except ValueError:
                continue
    return total

def leaves_by_type(leave_history, leave_types):
    """
    Returns dict: {description: total_days} for user display, only approved leaves.
    """
    code_to_desc, _, _ = build_leave_mappings(leave_types)
    result = {}
    for rec in leave_history:
        if rec.get("LeaveGrid_Status") != "Approved":
            continue
        code = rec.get("LeaveGrid_Lvm_Code_V")
        try:
            days = float(rec.get("LeaveGrid_Ela_Tot", 0) or 0)
        except ValueError:
            days = 0.0
        if code:
            desc = code_to_desc.get(code, code)
            result[desc] = result.get(desc, 0.0) + days
    return result

def format_leave_summary(summary_dict):
    """
    Formats the leave summary for user-friendly display.
    """
    if not summary_dict:
        return "No approved leave records found."
    lines = ["Leave Summary:"]
    for desc, days in summary_dict.items():
        lines.append(f"- {desc}: {days:.1f} days taken")
    return "\n".join(lines)

def is_on_leave_today(leave_history):
    """
    Return True if employee is on leave today (for any type, only approved leaves).
    """
    today = datetime.today().date()
    for rec in leave_history:
        if rec.get("LeaveGrid_Status") != "Approved":
            continue
        from_str = (rec.get("LeaveGrid_Ela_FromDate_D") or "")[:10]
        to_str   = (rec.get("LeaveGrid_Ela_ToDate_D")   or "")[:10]
        try:
            fdate = datetime.strptime(from_str, "%Y-%m-%d").date()
            tdate = datetime.strptime(to_str,   "%Y-%m-%d").date()
            if fdate <= today <= tdate:
                return True
        except ValueError:
            continue
    return False

def next_leave_balance_reset(leave_types):
    """
    Return the next reset date based on the first available Emp_AnnivDate_D in leave_types.
    """
    for lt in leave_types:
        anniv = lt.get("Emp_AnnivDate_D")
        if anniv:
            for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(anniv, fmt).date()
                except ValueError:
                    continue
            return anniv  # fallback string
    return None

def available_leave_types(leave_types):
    """
    Return a list of available leave codes and descriptions.
    """
    return [
        {"code": lt["Lvm_Code_V"], "desc": lt["Lvm_Description_V"]}
        for lt in leave_types
        if lt.get("Lvm_Code_V")
    ]

def leave_type_balance(leave_balances, leave_types, code_or_desc):
    """
    Return leave balance for a specific leave code or description.
    leave_balances is a dict of {Lpd_ID_N: balance_data}
    code_or_desc is a string, e.g. "AL" or "Annual Leave"
    """
    code_to_desc, desc_to_code, code_to_lpdid = build_leave_mappings(leave_types)

    if code_or_desc in code_to_lpdid:
        lpd_id = code_to_lpdid[code_or_desc]
    elif code_or_desc in desc_to_code and desc_to_code[code_or_desc] in code_to_lpdid:
        lpd_id = code_to_lpdid[desc_to_code[code_or_desc]]
    else:
        return None

    bal = leave_balances.get(lpd_id, {})
    return bal.get("Balance")

def leave_codes_summary(leave_history):
    """
    Debug utility: Return a Counter of codes found in leave_history.
    """
    return Counter(rec.get("LeaveGrid_Lvm_Code_V") for rec in leave_history)

def recent_leaves(leave_history, count=5):
    """
    Return a list of the most recent approved leave records.
    """
    def parse_date(date_str):
        if not date_str:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d-%b-%Y"):
            try:
                return datetime.strptime(date_str[:19], fmt)
            except Exception:
                continue
        return None

    filtered = [rec for rec in leave_history if rec.get("LeaveGrid_Status") == "Approved"]
    sorted_history = sorted(
        filtered,
        key=lambda rec: parse_date(rec.get("LeaveGrid_Ela_FromDate_D")) or datetime.min,
        reverse=True,
    )

    result = []
    for rec in sorted_history[: int(count)]:
        result.append(
            {
                "code": rec.get("LeaveGrid_Lvm_Code_V"),
                "description": rec.get("LeaveGrid_Lvm_Description_V"),
                "from": (rec.get("LeaveGrid_Ela_FromDate_D") or "")[:10],
                "to": (rec.get("LeaveGrid_Ela_ToDate_D") or "")[:10],
                "status": rec.get("LeaveGrid_Status"),
            }
        )
    return result

def get_air_ticket_eligibility(leave_balance_record):
    """
    Returns human-readable air ticket eligibility based on Airticket flag.
    """
    flag = leave_balance_record.get("Airticket")
    if flag == "1":
        return "Eligible"
    if flag == "0":
        return "Not Eligible"
    return "Unknown"

def get_employee_full_name(employee_record):
    """
    Returns the employee's full name for display.
    """
    return (
        employee_record.get("Emp_EFullName_V")
        or employee_record.get("Emp_EDisplayName_V")
        or "Unknown"
    )

def get_employee_anniversary(employee_record):
    """
    Returns anniversary date in ISO (YYYY-MM-DD) format if available.
    """
    raw_date = employee_record.get("Emp_AnnivDate_D")
    if not raw_date:
        return "Unknown"
    try:
        dt = datetime.strptime(raw_date, "%d-%b-%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return raw_date  # fallback to original
def unapproved_leaves(leave_history):
    """
    Returns a list of leave records that are not approved (status != 'Approved').
    """
    return [
        rec for rec in leave_history
        if rec.get("LeaveGrid_Status", "").strip().lower() != "approved"
    ]


def get_user_leave_overview(employee_record, leave_balances, leave_history, leave_types):
    """
    Returns a ready-to-display summary of the employee's leave and air ticket status.
    """
    name = get_employee_full_name(employee_record)
    anniversary = get_employee_anniversary(employee_record)
    air_ticket_elig = (
        get_air_ticket_eligibility(leave_balances[0])
        if leave_balances and "Airticket" in leave_balances[0]
        else "Unknown"
    )
    leave_summary = leaves_by_type(leave_history, leave_types)
    return f"""Employee: {name}
Anniversary: {anniversary}
Air Ticket Eligibility: {air_ticket_elig}

{format_leave_summary(leave_summary)}
"""

# Uncomment to test directly
# if __name__ == "__main__":
#     # You can put test loads here for debugging
#     pass
