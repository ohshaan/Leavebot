import os
from dotenv import load_dotenv

load_dotenv()

EMPLOYEE_DETAILS_API = os.getenv("EMPLOYEE_DETAILS_API", "http://localhost/api/EmployeeMasterApi/HrmGetEmployeeDetails/")
LEAVE_TYPE_API = os.getenv("LEAVE_TYPE_API", "http://localhost/api/LeaveApplicationApi/FillLeaveType")
LEAVE_HISTORY_API = os.getenv("LEAVE_HISTORY_API", "http://localhost/api/LeaveApplicationApi/HrmGetLeaveApplicationDetails")
LEAVE_SUMMARY_API = os.getenv("LEAVE_SUMMARY_API", "http://localhost/api/LeaveApplicationApi")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ERP_BEARER_TOKEN = os.getenv("ERP_BEARER_TOKEN", "")

RAW_DATA_PATH = os.path.join("data", "raw")
PROCESSED_JSON_PATH = os.path.join("data", "api_json")

# Build the default embeddings path relative to this settings file. This keeps
# the configuration portable across different environments.
# BASE_DIR should point to the project root. "settings.py" lives in
# leavebot/config/, so we need to go three directories up.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
default_doc_path = os.path.join(
    BASE_DIR, "data", "combined_doc_knowledge.json"
)
# Allow overriding the embeddings path via environment variable
DOC_EMBEDDINGS_PATH = os.getenv("DOC_EMBEDDINGS_PATH", default_doc_path)


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "leavebot.log")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

ENABLE_DOC_SEARCH = os.getenv("ENABLE_DOC_SEARCH", "True") == "True"
ENABLE_API_FETCH = os.getenv("ENABLE_API_FETCH", "True") == "True"

PROJECT_VERSION = "1.0.0"
PROJECT_AUTHOR = "Shahnawaz/ AI Team Anvin"
