# air_ticket_utils.py

from datetime import datetime, timedelta

def is_air_ticket_eligible(leave_balance):
    """Return True if this leave type grants air ticket eligibility."""
    return str(leave_balance.get("Airticket", "0")) == "1"

def get_air_ticket_percent(leave_balance):
    """Return percentage (float) of air ticket eligible for this leave type."""
    try:
        return float(leave_balance.get("AirTicketPercent", 0))
    except (TypeError, ValueError):
        return 0.0

def next_air_ticket_eligibility(anniv_date, last_ticket_date=None, period_years=2):
    """
    Returns the next date when the employee will be eligible for air ticket.
    If last_ticket_date is None, assumes from anniv_date.
    """
    if not anniv_date:
        return None
    try:
        anniv = datetime.strptime(anniv_date, "%d-%b-%Y")
    except (TypeError, ValueError):
        try:
            anniv = datetime.strptime(anniv_date, "%Y-%m-%d")
        except (TypeError, ValueError):
            return None
    last = datetime.strptime(last_ticket_date, "%Y-%m-%d") if last_ticket_date else anniv
    return (last + timedelta(days=period_years*365)).strftime("%Y-%m-%d")

def has_claimed_air_ticket(leave_history, year=None):
    """
    Returns True if the employee has claimed air ticket in given year (or any year if not specified).
    """
    for rec in leave_history:
        ticket_req = str(rec.get("Ela_AirTicketReq_N", "0"))
        app_date = rec.get("LeaveGrid_Ela_AppDate_D", "")[:10]
        if year and app_date and not app_date.startswith(str(year)):
            continue
        if ticket_req == "1":
            return True
    return False


def air_ticket_info(leave_balances, leave_history):
    """Return eligibility details for employee air ticket."""
    eligible_balance = None
    for lb in leave_balances.values():
        if is_air_ticket_eligible(lb):
            eligible_balance = lb
            break

    if not eligible_balance:
        return {"eligible": False}

    percent = get_air_ticket_percent(eligible_balance)
    anniv = eligible_balance.get("Emp_AnnivDate_D")

    last_claim = None
    for rec in leave_history:
        if str(rec.get("Ela_AirTicketReq_N", "0")) == "1":
            date = rec.get("LeaveGrid_dtTravelDate") or rec.get("LeaveGrid_Ela_FromDate_D")
            if date and (not last_claim or date > last_claim):
                last_claim = date

    next_date = next_air_ticket_eligibility(anniv, last_claim) if anniv else None
    return {
        "eligible": True,
        "percent": percent,
        "next_eligible_date": next_date,
        "last_claim_date": last_claim,
    }

# Add additional helper functions here as required.
