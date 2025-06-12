from leavebot_copy.scripts.fetch_employee import fetch_employee_details
from leavebot_copy.scripts.fetch_leave_types import fetch_leave_types
from leavebot_copy.scripts.fetch_leave_balance import fetch_leave_balance
from leavebot_copy.scripts.fetch_leave_history import fetch_leave_history
from leavebot_copy.scripts.fetch_manager import get_manager_contact   # <--- NEW
from leavebot_copy.scripts.search_embeddings import search_embeddings

def pretty_print(title, obj):
    import json
    print(f"\n--- {title} ---")
    print(json.dumps(obj, indent=2, ensure_ascii=False))

EMP_ID = 432
CGM_ID = 1
FROM_DATE = "2024-01-01"
TO_DATE = "2024-12-31"

# 1. Test Employee Details
try:
    emp = fetch_employee_details(EMP_ID)
    pretty_print("Employee Details", emp)
except Exception as e:
    print(f"[ERROR] Employee Details: {e}")
    emp = None

# 1b. Test Manager Contact Info
try:
    if emp and isinstance(emp, list) and len(emp) > 0:
        manager_id = emp[0].get("Emp_ReportingToID_N")
        if manager_id:
            mgr_contact = get_manager_contact(manager_id)
            pretty_print("Manager Contact", mgr_contact)
        else:
            print("[INFO] No manager ID found in employee details.")
    else:
        print("[ERROR] Cannot fetch manager, employee details not loaded.")
except Exception as e:
    print(f"[ERROR] Manager Contact: {e}")

# 2. Test Leave Types
try:
    leave_types = fetch_leave_types(EMP_ID, CGM_ID)
    pretty_print("Leave Types", leave_types)
except Exception as e:
    print(f"[ERROR] Leave Types: {e}")

# 3. Test Leave Balances for Each Type
try:
    for lt in leave_types:
        lpd_id = lt["Lpd_ID_N"]
        leave_code = lt.get("Lvm_Code_V")
        balance = fetch_leave_balance(EMP_ID, lpd_id, FROM_DATE, TO_DATE)
        pretty_print(f"Leave Balance ({leave_code})", balance)
except Exception as e:
    print(f"[ERROR] Leave Balances: {e}")

# 4. Test Leave History
try:
    history = fetch_leave_history(EMP_ID)
    pretty_print("Leave History", history)
except Exception as e:
    print(f"[ERROR] Leave History: {e}")

# 5. Test Document Embedding Search
try:
    results = search_embeddings("leave policy")
    pretty_print("Embedding Search (leave policy)", results)
except Exception as e:
    print(f"[ERROR] Embedding Search: {e}")
