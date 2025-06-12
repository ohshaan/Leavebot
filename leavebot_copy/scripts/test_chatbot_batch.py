import sys
import os
import json

# Add leavebot_copy as a package root for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from chatbot import chat_engine
from leavebot_copy.config.settings import DOC_EMBEDDINGS_PATH

QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), '..', 'questions.txt')

def run_batch_test(emp_id=5469, questions_file=QUESTIONS_FILE):
    # Reset chatbot state for each test session
    chat_engine.EMP_ID = emp_id

    # Re-fetch all employee data for this emp_id
    chat_engine.employee = chat_engine.fetch_employee_details(emp_id)
    chat_engine.leave_types = chat_engine.fetch_leave_types(emp_id, chat_engine.CGM_ID)
    # Pass leave_types into fetch_leave_history so each record gets its code
    chat_engine.leave_history = chat_engine.fetch_leave_history(
        emp_id, chat_engine.leave_types
    )
    chat_engine.leave_balances = {
        lt["Lpd_ID_N"]: chat_engine.fetch_leave_balance(emp_id, lt["Lpd_ID_N"], chat_engine.FROM_DATE, chat_engine.TO_DATE)
        for lt in chat_engine.leave_types
    }
    chat_engine.manager = chat_engine.get_manager_details(chat_engine.employee, chat_engine.fetch_employee_details)

    # Read questions
    with open(questions_file, 'r', encoding='utf-8') as f:
        questions = [q.strip() for q in f if q.strip()]

    for idx, q in enumerate(questions, 1):
        print(f"\n=== Q{idx}: {q} ===")

        # Re-initialize messages for each question
        messages = [
            {
                "role": "system",
                "content": (
                    "You are LeaveBot, a helpful HR and policy assistant. "
                    "If a user asks a question not directly answerable by API or calculations, use the search_policy tool to answer from company policy documents."
                )
            },
            {"role": "user", "content": q}
        ]

        # First assistant response
        response = chat_engine.openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=chat_engine.tools,
            tool_choice="auto",
            max_tokens=512,
        )
        msg = response.choices[0].message

        # Multi-step tool calling loop
        while hasattr(msg, "tool_calls") and msg.tool_calls:
            # Add the assistant message with all tool_calls (OpenAI protocol)
            messages.append({
                "role": "assistant",
                "tool_calls": [call.model_dump() for call in msg.tool_calls]
            })
            # Route and add each tool result
            for call in msg.tool_calls:
                tool_name = call.function.name
                args_json = call.function.arguments
                args_dict = json.loads(args_json) if args_json else {}
                tool_response = chat_engine.route_tool(tool_name, args_dict)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": tool_name,
                    "content": str(tool_response)
                })

            # For debugging: print the messages before next OpenAI call
            print("\n=== DEBUG: MESSAGES GOING INTO NEXT OPENAI CALL ===")
            for m in messages:
                print(m)
            print("====================================================\n")

            # Call OpenAI again, including tools!
            response = chat_engine.openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=chat_engine.tools,
                max_tokens=512,
            )
            msg = response.choices[0].message

        # Final answer (when no more tool_calls)
        answer = msg.content
        print(f"A: {answer}")

if __name__ == "__main__":
    # Optionally pass emp_id as CLI arg
    emp_id = int(sys.argv[1]) if len(sys.argv) > 1 else 5469
    run_batch_test(emp_id=emp_id)
