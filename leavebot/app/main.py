import streamlit as st
import os
import sys

# Ensure correct package import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from leavebot.chatbot.chat_engine import ChatEngine
from leavebot.api.fetch_employee import fetch_employee_details
from leavebot.config.settings import EMPLOYEE_DETAILS_API
from leavebot.core.search_embeddings import search_embeddings

# --- Page config ---
st.set_page_config(page_title="LeaveBot HR Assistant")
st.title("🤖 LeaveBot - HR Assistant Chatbot")

# --- Query param for employee ---
query_params = st.query_params
emp_id_raw = query_params.get("emp_id", ["5469"])
if len(emp_id_raw) == 1 and emp_id_raw[0].isdigit():
    emp_id = int(emp_id_raw[0])
else:
    emp_id = int("".join(emp_id_raw))

api_url = f"{EMPLOYEE_DETAILS_API}?strEmp_ID_N={emp_id}"

# --- Validate Employee ID ---
emp_data = fetch_employee_details(emp_id)
if not emp_data:
    st.error(f"❌ No employee found with ID {emp_id}. Please check the emp_id in the URL.")
    st.stop()

# --- Initialize Chat Engine and history ---
if "chat_engine" not in st.session_state:
    st.session_state.chat_engine = ChatEngine()
    st.session_state.chat_history = []
    st.session_state.chat_engine.preload_data(emp_id=emp_id, from_date="2024-01-01", to_date="2024-12-31")

chat_engine = st.session_state.chat_engine

# --- Show chat history ---
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask me about your leaves, eligibility, or HR policy...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build messages for OpenAI function-calling
    messages = [
        {"role": "system", "content": "You are LeaveBot, a helpful HR and policy assistant. For any question not answerable from leave records or data, always use the search_policy tool to search the HR policy and FAQ."},
    ] + st.session_state.chat_history

    # 1. Try OpenAI ChatEngine (with tool calling, including search_policy)
    try:
        response = chat_engine.stream_completion(messages)
    except Exception as e:
        response = f"❌ Error: {str(e)}"

    # Show initial assistant response
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)

    # 2. Fallback: If answer is generic or fallback, try semantic doc search directly
    fallback_phrases = [
        "couldn't find", "not found", "please check", "consult hr", "no relevant"
    ]
    answer_lower = (response or "").lower()
    if any(phrase in answer_lower for phrase in fallback_phrases):
        doc_results = search_embeddings(user_input, top_k=1)
        if doc_results and doc_results[0]["similarity"] > 0.72:  # Adjust threshold as needed
            policy_answer = doc_results[0]['chunk']
            st.session_state.chat_history.append({"role": "assistant", "content": policy_answer})
            with st.chat_message("assistant"):
                st.markdown(f"**Policy Reference:**\n{policy_answer}")

 