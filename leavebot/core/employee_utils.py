# Helper functions for employee data

from datetime import datetime

def years_of_service(emp_data):
    """Returns integer years of service for an employee (by DOJ)."""
    emp = emp_data[0] if isinstance(emp_data, list) else emp_data
    doj_str = emp.get("Emp_DOJ_D") or emp.get("Emp_ESBDate_D")
    if not doj_str:
        return 0
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            doj = datetime.strptime(doj_str, fmt)
            return (datetime.today() - doj).days // 365
        except Exception:
            continue
    return 0

def is_manager(emp_data):
    """Return True if employee manages others based on Emp_EmployeeReportsDesc_V."""
    emp = emp_data[0] if isinstance(emp_data, list) else emp_data
    return bool(emp.get("Emp_EmployeeReportsDesc_V"))

def employee_contact_summary(emp_data):
    """Return dict of main contact details for the employee."""
    emp = emp_data[0] if isinstance(emp_data, list) else emp_data
    return {
        "name": emp.get("Emp_EFullName_V", ""),
        "email": emp.get("Emp_EmailID_V", ""),
        "mobile": emp.get("Emp_Mobile_V", ""),
        "department": emp.get("Dpm_Desc_V", ""),
        "designation": emp.get("Dsm_Desc_V", ""),
        "employee_code": emp.get("Emp_Code_V", ""),
    }

def get_manager_details(emp_data, fetch_func=None):
    """
    Given employee data and a fetch function, return manager details (email, phone).
    fetch_func should be a callable taking Emp_ID_N and returning emp_data dict/list.
    """
    emp = emp_data[0] if isinstance(emp_data, list) else emp_data
    mgr_id = emp.get("Emp_ReportingToID_N")
    mgr_name = emp.get("Emp_EmployeeReportsDesc_V", "")
    if not mgr_id or not fetch_func:
        return {
            "name": mgr_name,
            "email": "",
            "mobile": "",
            "employee_code": "",
            "designation": "",
        }
    mgr_info = fetch_func(int(mgr_id))
    mgr = mgr_info[0] if isinstance(mgr_info, list) else mgr_info
    return {
        "name": mgr.get("Emp_EFullName_V", mgr_name),
        "email": mgr.get("Emp_EmailID_V", ""),
        "mobile": mgr.get("Emp_Mobile_V", ""),
        "employee_code": mgr.get("Emp_Code_V", ""),
        "designation": mgr.get("Dsm_Desc_V", ""),
    }

def get_nationality(emp_data):
    """Get employee nationality, falling back to various fields."""
    emp = emp_data[0] if isinstance(emp_data, list) else emp_data
    return emp.get("Cnt_Nationality_V") or emp.get("Emp_Nationality_V") or ""

def is_probation_completed(emp_data):
    """Check if employee's probation is completed (compare today to Emp_ProbationEndDate_D)."""
    emp = emp_data[0] if isinstance(emp_data, list) else emp_data
    end = emp.get("Emp_ProbationEndDate_D")
    if not end:
        return True
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            end_date = datetime.strptime(end, fmt)
            return datetime.today() > end_date
        except Exception:
            continue
    return True

# Add further employee inference/calculation utilities as required.
