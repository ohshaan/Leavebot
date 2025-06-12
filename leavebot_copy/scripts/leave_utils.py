# leavebot_copy/scripts/leave_utils.py
from scripts.fetch_leave_types import fetch_leave_types
from scripts.fetch_leave_history import fetch_leave_history
from scripts.leave_utils import total_leave_taken, leaves_by_type, leave_codes_summary

lt = fetch_leave_types(5469, 1)
lh = fetch_leave_history(5469, lt)

print(leave_codes_summary(lh))              # see which codes actually came back
print(total_leave_taken(lh, lt, "sick"))    # should now count SL/SLN/SLH
print(leaves_by_type(lh, lt))               # should show each code + desc + days

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
    Build groupings like 'sick', 'casual', 'annual' based on keywords in descriptions.
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
    Sum leave days taken.
    - If code_or_group is a known group (e.g. 'sick'), sum for all codes in that group.
    - If it's a code (e.g. 'AL'), sum for just that code.
    - If it's a description (e.g. 'Annual Leave'), map to code.
    - If None, sum all leaves.
    """
    code_to_desc, desc_to_code, _ = build_leave_mappings(leave_types)
    groups = build_leave_type_groups(leave_types)

    # Resolve input into one or more codes
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
        if rec.get("LeaveGrid_Lvm_Code_V") in codes:
            try:
                total += float(rec.get("LeaveGrid_Ela_Tot", 0) or 0)
            except ValueError:
                continue
    return total

def leaves_by_type(leave_history, leave_types):
    """
    Return dict of total leave days taken, keyed by leave code,
    with description and days.
    """
    result = {}
    for rec in leave_history:
        code = rec.get("LeaveGrid_Lvm_Code_V")
        try:
            days = float(rec.get("LeaveGrid_Ela_Tot", 0) or 0)
        except ValueError:
            days = 0.0
        if code:
            result[code] = result.get(code, 0.0) + days

    code_to_desc, _, _ = build_leave_mappings(leave_types)
    return {
        code: {"desc": code_to_desc.get(code, ""), "days": days}
        for code, days in result.items()
    }

def is_on_leave_today(leave_history):
    """
    Return True if employee is on leave today (for any type).
    """
    today = datetime.today().date()
    for rec in leave_history:
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
