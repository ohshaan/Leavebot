import openai
import os
import json

from leavebot_copy.scripts.leave_utils import (
    total_leave_taken,
    leaves_by_type,
    available_leave_types,
    leave_type_balance,
    is_on_leave_today
)
from leavebot_copy.scripts.employee_utils import (
    years_of_service,
    employee_contact_summary,
    get_manager_details
)
from leavebot_copy.scripts.fetch_employee import fetch_employee_details
from leavebot_copy.scripts.fetch_leave_types import fetch_leave_types
from leavebot_copy.scripts.fetch_leave_balance import fetch_leave_balance
from leavebot_copy.scripts.fetch_leave_history import fetch_leave_history  # now expects (emp_id, leave_types)
from leavebot_copy.scripts.search_embeddings import search_embeddings  # RAG tool


# Setup OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY", "")

# Pre-fetch/cached API data for the session (do once per session/user)
EMP_ID     = 5469
CGM_ID     = 1
FROM_DATE  = "2024-01-01"
TO_DATE    = "2024-12-31"

employee    = fetch_employee_details(EMP_ID)
leave_types = fetch_leave_types(EMP_ID, CGM_ID)
# Pass leave_types into fetch_leave_history so each record gets its code
leave_history = fetch_leave_history(EMP_ID, leave_types)

# Build leave_balances keyed by Lpd_ID_N
leave_balances = {
    lt["Lpd_ID_N"]: fetch_leave_balance(EMP_ID, lt["Lpd_ID_N"], FROM_DATE, TO_DATE)
    for lt in leave_types
}

manager = get_manager_details(employee, fetch_employee_details)

# --- TOOL DEFINITIONS ---

def tool_total_leave_taken(leave_code=None, **kwargs):
    """Returns total leave days taken, optionally filtered by code or group."""
    return total_leave_taken(leave_history, leave_types, code_or_group=leave_code)

def tool_leaves_by_type(**kwargs):
    """Returns dict of leave codes with days taken for each."""
    return leaves_by_type(leave_history, leave_types)

def tool_available_leave_types(**kwargs):
    """Lists all leave types available for the employee."""
    return available_leave_types(leave_types)

def tool_leave_type_balance(leave_code=None, **kwargs):
    """Returns balance for a specific leave code or description."""
    if leave_code is None:
        return None
    return leave_type_balance(leave_balances, leave_types, code_or_desc=leave_code)

def tool_years_of_service(**kwargs):
    """Returns number of years the employee has been with the company."""
    return years_of_service(employee)

def tool_employee_contact(**kwargs):
    """Returns the contact summary for the employee."""
    return employee_contact_summary(employee)

def tool_manager_contact(**kwargs):
    """Returns the manager's contact information."""
    return manager

def tool_is_on_leave_today(**kwargs):
    """Returns whether the employee is on leave today."""
    return is_on_leave_today(leave_history)

def tool_search_policy(question=None, **kwargs):
    """Search HR policy docs for answers to policy questions."""
    results = search_embeddings(question, top_k=2)
    if not results:
        return "No relevant policy or HR information found."
    answer = ""
    for idx, chunk in enumerate(results, 1):
        answer += f"{idx}. {chunk['chunk'].strip()}\n\n"
    return answer.strip()

# --- TOOL MAP ---
TOOL_MAP = {
    "total_leave_taken":   tool_total_leave_taken,
    "leaves_by_type":      tool_leaves_by_type,
    "available_leave_types": tool_available_leave_types,
    "leave_type_balance":  tool_leave_type_balance,
    "years_of_service":    tool_years_of_service,
    "employee_contact":    tool_employee_contact,
    "manager_contact":     tool_manager_contact,
    "is_on_leave_today":   tool_is_on_leave_today,
    "search_policy":       tool_search_policy,
}

# --- TOOL SCHEMA ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "total_leave_taken",
            "description": "Returns total leave days taken, optionally filtered by leave code or group.",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_code": {"type": "string", "description": "Leave code or group (e.g. 'AL' or 'sick')"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "leaves_by_type",
            "description": "Returns a dict of leave codes and total days taken for each.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "available_leave_types",
            "description": "Lists all leave types available for the employee.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "leave_type_balance",
            "description": "Returns leave balance for a specific leave code or description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_code": {"type": "string", "description": "Leave code or description"}
                },
                "required": ["leave_code"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "years_of_service",
            "description": "Returns number of years the employee has been with the company.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "employee_contact",
            "description": "Returns the contact summary for the employee.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manager_contact",
            "description": "Returns the manager's contact information.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "is_on_leave_today",
            "description": "Returns whether the employee is on leave today.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search HR policy for answers to questions not covered by API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "HR or policy question"}
                },
                "required": ["question"]
            },
        },
    },
]

# ---- TOOL ROUTER ----
def route_tool(tool_name, args=None):
    if tool_name not in TOOL_MAP:
        return "Tool not implemented."
    return TOOL_MAP[tool_name](**(args or {}))

# ---- CHATBOT LOOP (WITH MULTI-STEP TOOL CALLING SUPPORT) ----
def run_chat():
    print("LeaveBot: Ask your question (type 'exit' to quit):")
    messages = [{
        "role": "system",
        "content": (
            "You are LeaveBot, a helpful HR and policy assistant. "
            "If a user asks a question not directly answerable by API or calculations, use the search_policy tool."
        )
    }]

    while True:
        user_input = input("User: ")
        if user_input.strip().lower() == "exit":
            break

        messages.append({"role": "user", "content": user_input})
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=512,
        )

        msg = response.choices[0].message

        # Handle any function calls
        while hasattr(msg, "tool_calls") and msg.tool_calls:
            messages.append({
                "role": "assistant",
                "tool_calls": [c.model_dump() for c in msg.tool_calls]
            })
            for call in msg.tool_calls:
                name = call.function.name
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                result = route_tool(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": str(result)
                })
            response = openai.chat.completions.create(
                model="gpt-4o", messages=messages, tools=tools, max_tokens=512
            )
            msg = response.choices[0].message

        print("LeaveBot:", msg.content)
        messages.append({"role": "assistant", "content": msg.content})


if __name__ == "__main__":
    run_chat()
