import openai
import os
import json

from ..core.leave_utils import (
    total_leave_taken,
    leaves_by_type,
    available_leave_types,
    leave_type_balance,
    is_on_leave_today,
    recent_leaves,
    unapproved_leaves,
)
from ..core.employee_utils import (
    years_of_service,
    employee_contact_summary,
    get_manager_details,
)
from ..api.fetch_employee import fetch_employee_details
from ..api.fetch_leave_types import fetch_leave_types
from ..api.fetch_leave_balance import fetch_leave_balance
from ..api.fetch_leave_history import fetch_leave_history
from ..core.search_embeddings import search_embeddings
from ..core.air_ticket_utils import air_ticket_info

openai.api_key = os.getenv("OPENAI_API_KEY", "")

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
            "name": "recent_leaves",
            "description": "Returns the most recent leave applications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of records to return"}
                }
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "air_ticket_info",
            "description": "Returns air ticket eligibility information for the given leave code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_code": {"type": "string", "description": "The leave code to check air ticket eligibility for"}
                },
                "required": ["leave_code"]
            },
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
    {
        "type": "function",
        "function": {
            "name": "unapproved_leaves",
            "description": "Returns a list of all leave applications that are not approved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Optional: filter by a specific non-approved status (e.g. 'Pending', 'Rejected', 'Not Approved')"
                    }
                }
            }
        }
    },
]

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are LeaveBot, a helpful HR assistant. "
        "Whenever a user asks about leave application or how to apply for leave, "
        "always first provide clear, step-by-step instructions on using the HRM portal form and Employee Self-Service (ESS) system, "
        "including which menus to navigate and what fields to fill out. "
        "Only after giving this practical process help, provide relevant policy or eligibility information as a secondary reference. "
        "Make the practical application instructions the main focus."
    )
}


class ChatEngine:
    """Encapsulates chatbot state and interactions."""

    def __init__(self):
        self.employee = None
        self.leave_types = None
        self.leave_history = None
        self.leave_balances = None
        self.manager = None
        self.TOOL_MAP = {
            "total_leave_taken": self.tool_total_leave_taken,
            "leaves_by_type": self.tool_leaves_by_type,
            "available_leave_types": self.tool_available_leave_types,
            "leave_type_balance": self.tool_leave_type_balance,
            "years_of_service": self.tool_years_of_service,
            "employee_contact": self.tool_employee_contact,
            "manager_contact": self.tool_manager_contact,
            "is_on_leave_today": self.tool_is_on_leave_today,
            "recent_leaves": self.tool_recent_leaves,
            "air_ticket_info": self.tool_air_ticket_info,
            "search_policy": self.tool_search_policy,
            "unapproved_leaves": self.tool_unapproved_leaves,
        }

    def preload_data(self, emp_id, from_date, to_date, cgm_id=1):
        """Fetch and cache employee-related data for the session."""
        self.employee = fetch_employee_details(emp_id)
        self.leave_types = fetch_leave_types(emp_id, cgm_id)
        self.leave_history = fetch_leave_history(emp_id, self.leave_types)
        self.leave_balances = {}
        for lt in self.leave_types:
            bal = fetch_leave_balance(emp_id, lt["Lpd_ID_N"], from_date, to_date)
            if isinstance(bal, list) and bal:
                bal = bal[0]
            if bal:
                bal["Lvm_Code_V"] = lt.get("Lvm_Code_V", "")
                self.leave_balances[lt["Lpd_ID_N"]] = bal
        self.manager = get_manager_details(self.employee, fetch_employee_details)
        return (
            self.employee,
            self.leave_types,
            self.leave_history,
            self.leave_balances,
            self.manager,
        )

    # --- TOOL DEFINITIONS ---
    def tool_total_leave_taken(self, leave_code=None, **kwargs):
        return total_leave_taken(self.leave_history, self.leave_types, code_or_group=leave_code)

    def tool_leaves_by_type(self, **kwargs):
        return leaves_by_type(self.leave_history, self.leave_types)

    def tool_available_leave_types(self, **kwargs):
        return available_leave_types(self.leave_types)

    def tool_leave_type_balance(self, leave_code=None, **kwargs):
        if leave_code is None:
            return None
        return leave_type_balance(self.leave_balances, self.leave_types, code_or_desc=leave_code)

    def tool_years_of_service(self, **kwargs):
        return years_of_service(self.employee)

    def tool_employee_contact(self, **kwargs):
        return employee_contact_summary(self.employee)

    def tool_manager_contact(self, **kwargs):
        return self.manager

    def tool_is_on_leave_today(self, **kwargs):
        return is_on_leave_today(self.leave_history)

    def tool_recent_leaves(self, count=5, **kwargs):
        return recent_leaves(self.leave_history, count=count)

    def tool_air_ticket_info(self, leave_code=None, **kwargs):
        return air_ticket_info(self.leave_balances, self.leave_history, leave_code=leave_code)

    def tool_search_policy(self, question=None, **kwargs):
        results = search_embeddings(question, top_k=2)
        if not results:
            return "No relevant policy or HR information found."
        answer = ""
        for idx, chunk in enumerate(results, 1):
            answer += f"{idx}. {chunk.get('chunk', chunk.get('text','')).strip()}\n\n"
        return answer.strip()

    def tool_unapproved_leaves(self, status=None, **kwargs):
        unapproved = unapproved_leaves(self.leave_history)
        if status:
            status_lower = status.strip().lower()
            unapproved = [
                rec for rec in unapproved
                if rec.get("LeaveGrid_Status", "").strip().lower() == status_lower
            ]
        if not unapproved:
            return "You do not have any unapproved leaves."
        result = "You have the following unapproved leaves:\n"
        for rec in unapproved:
            result += (
                f"- {rec.get('LeaveGrid_Lvm_Description_V', 'Unknown Type')} "
                f"from {rec.get('LeaveGrid_Ela_FromDate_D', '')[:10]} "
                f"to {rec.get('LeaveGrid_Ela_ToDate_D', '')[:10]} "
                f"(Status: {rec.get('LeaveGrid_Status', 'Unknown')})\n"
            )
        return result.strip()

    def route_tool(self, tool_name, args=None):
        if tool_name not in self.TOOL_MAP:
            return "Tool not implemented."
        return self.TOOL_MAP[tool_name](**(args or {}))

    def fallback_with_policy_search(self, user_question, response):
        # Always run policy search for demo/verification!
        print(f"DEBUG: Running policy search for: {user_question}")
        policy_snippet = self.tool_search_policy(question=user_question)
        print(f"DEBUG: Policy search result: {policy_snippet}")
        if policy_snippet and "No relevant policy" not in policy_snippet:
            response = (
                response.strip() +
                "\n\n*Policy reference:*\n" + policy_snippet.strip()
            )
        return response

    def stream_completion(self, messages, user_input=None):
        if not messages or messages[0].get("role") != "system":
            messages = [SYSTEM_PROMPT] + messages

        response = openai.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=512,
        )
        msg = response.choices[0].message

        while hasattr(msg, "tool_calls") and msg.tool_calls:
            messages.append({
                "role": "assistant",
                "tool_calls": [call.model_dump() for call in msg.tool_calls]
            })
            for call in msg.tool_calls:
                tool_name = call.function.name
                args_json = call.function.arguments
                args_dict = json.loads(args_json) if args_json else {}
                tool_response = self.route_tool(tool_name, args_dict)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": tool_name,
                    "content": str(tool_response)
                })
            response = openai.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=messages,
                tools=tools,
                max_tokens=512,
            )
            msg = response.choices[0].message

        if user_input:
            return self.fallback_with_policy_search(user_input, msg.content if msg.content else "No answer returned.")
        else:
            return msg.content if msg.content else "No answer returned."
