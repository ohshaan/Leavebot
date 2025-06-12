import openai
import os
import json

# All imports below use the leavebot package structure, so no manual path
# manipulation is required when this module is executed as part of the package.

from ..core.leave_utils import (
    total_leave_taken,
    leaves_by_type,
    available_leave_types,
    leave_type_balance,
    is_on_leave_today,
    recent_leaves,
)
from ..core.employee_utils import (
    years_of_service,
    employee_contact_summary,
    get_manager_details
)
from ..api.fetch_employee import fetch_employee_details
from ..api.fetch_leave_types import fetch_leave_types
from ..api.fetch_leave_balance import fetch_leave_balance
from ..api.fetch_leave_history import fetch_leave_history  # now expects (emp_id, leave_types)
from ..core.search_embeddings import search_embeddings  # RAG tool
from ..core.air_ticket_utils import air_ticket_info


# Setup OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY", "")

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
        }

    # --- DATA PRELOAD ---
    def preload_data(self, emp_id, from_date, to_date, cgm_id=1):
        """Fetch and cache employee-related data for the session."""
        self.employee = fetch_employee_details(emp_id)
        self.leave_types = fetch_leave_types(emp_id, cgm_id)
        self.leave_history = fetch_leave_history(emp_id, self.leave_types)
        self.leave_balances = {
            lt["Lpd_ID_N"]: fetch_leave_balance(emp_id, lt["Lpd_ID_N"], from_date, to_date)
            for lt in self.leave_types
        }
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
        """Returns total leave days taken, optionally filtered by code or group."""
        return total_leave_taken(self.leave_history, self.leave_types, code_or_group=leave_code)

    def tool_leaves_by_type(self, **kwargs):
        """Returns dict of leave codes with days taken for each."""
        return leaves_by_type(self.leave_history, self.leave_types)

    def tool_available_leave_types(self, **kwargs):
        """Lists all leave types available for the employee."""
        return available_leave_types(self.leave_types)

    def tool_leave_type_balance(self, leave_code=None, **kwargs):
        """Returns balance for a specific leave code or description."""
        if leave_code is None:
            return None
        return leave_type_balance(self.leave_balances, self.leave_types, code_or_desc=leave_code)

    def tool_years_of_service(self, **kwargs):
        """Returns number of years the employee has been with the company."""
        return years_of_service(self.employee)

    def tool_employee_contact(self, **kwargs):
        """Returns the contact summary for the employee."""
        return employee_contact_summary(self.employee)

    def tool_manager_contact(self, **kwargs):
        """Returns the manager's contact information."""
        return self.manager

    def tool_is_on_leave_today(self, **kwargs):
        """Returns whether the employee is on leave today."""
        return is_on_leave_today(self.leave_history)

    def tool_recent_leaves(self, count=5, **kwargs):
        """Returns the most recent leave applications."""
        return recent_leaves(self.leave_history, count=count)

    def tool_air_ticket_info(self, **kwargs):
        """Returns air ticket eligibility information."""
        return air_ticket_info(self.leave_balances, self.leave_history)

    def tool_search_policy(self, question=None, **kwargs):
        """Search HR policy docs for answers to policy questions."""
        results = search_embeddings(question, top_k=2)
        if not results:
            return "No relevant policy or HR information found."
        answer = ""
        for idx, chunk in enumerate(results, 1):
            answer += f"{idx}. {chunk['chunk'].strip()}\n\n"
        return answer.strip()

    # ---- TOOL ROUTER ----
    def route_tool(self, tool_name, args=None):
        if tool_name not in self.TOOL_MAP:
            return "Tool not implemented."
        return self.TOOL_MAP[tool_name](**(args or {}))

    # ---- CHATBOT LOOP (WITH MULTI-STEP TOOL CALLING SUPPORT) ----
    def stream_completion(self, messages):
        """Stream the assistant's reply and return the full text."""
        response = openai.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=messages,
            tools=tools,
            max_tokens=512,
            stream=True,
        )
        full = ""
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                full += delta.content
        print()
        return full

    def run_chat(self, emp_id=5469, from_date="2024-01-01", to_date="2024-12-31", history_length=20):
        self.preload_data(emp_id, from_date, to_date)

        print("LeaveBot: Ask your question (type 'exit' to quit):")
        messages = [{
            "role": "system",
            "content": (
                "You are LeaveBot, a helpful HR and policy assistant. "
                "If a user asks a question not directly answerable by API or calculations, use the search_policy tool."
            ),
        }]

        while True:
            user_input = input("User: ")
            if user_input.strip().lower() == "exit":
                break

            messages.append({"role": "user", "content": user_input})
            try:
                response = openai.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=512,
                )
            except openai.AuthenticationError:
                print(
                    "OpenAI authentication failed. Please set the OPENAI_API_KEY environment variable with a valid API key."
                )
                return

            msg = response.choices[0].message

            # Handle any function calls
            while hasattr(msg, "tool_calls") and msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "tool_calls": [c.model_dump() for c in msg.tool_calls],
                })
                for call in msg.tool_calls:
                    name = call.function.name
                    args = json.loads(call.function.arguments) if call.function.arguments else {}
                    result = self.route_tool(name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": name,
                        "content": str(result),
                    })
                try:
                    response = openai.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                        messages=messages,
                        tools=tools,
                        max_tokens=512,
                    )
                except openai.AuthenticationError:
                    print(
                        "OpenAI authentication failed. Please set the OPENAI_API_KEY environment variable with a valid API key."
                    )
                    return
                msg = response.choices[0].message

            final_text = self.stream_completion(messages)
            messages.append({"role": "assistant", "content": final_text})

            if history_length:
                messages = [messages[0]] + messages[-history_length:]


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
            "description": "Returns air ticket eligibility information.",
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


def run_chat(emp_id=5469, from_date="2024-01-01", to_date="2024-12-31", history_length=20):
    """Convenience wrapper that runs the chat with a fresh ChatEngine."""
    ChatEngine().run_chat(emp_id, from_date, to_date, history_length)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Interactive LeaveBot chat")
    parser.add_argument("--emp-id", type=int, default=5469, help="Employee ID")
    parser.add_argument("--from-date", default="2024-01-01", help="Start date for balances/history")
    parser.add_argument("--to-date", default="2024-12-31", help="End date for balances/history")
    parser.add_argument("--history-length", type=int, default=20, help="Number of messages of history to retain")
    args = parser.parse_args()

    run_chat(args.emp_id, args.from_date, args.to_date, args.history_length)
