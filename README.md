
# LeaveBot

LeaveBot is a proof‑of‑concept assistant that answers leave‑related questions for employees. It calls internal HR APIs to retrieve employee details, leave types, balances and history, and combines that data with OpenAI tools for conversational responses and policy search.

## Installation

1. Clone this repository and navigate into the project directory.
2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Configuration

The application expects a `.env` file with API endpoints and secrets. A template is provided as `.env.example`.

1. Copy the example file and edit it with your own values:

```bash
cp .env.example .env
# then edit .env
```

2. Fill in your OpenAI API key and the URLs / tokens for the HR APIs.

## Running the Batch Test

You can run a scripted batch of questions using:

```bash
python -m leavebot.scripts.test_chatbot_batch <emp_id>
```

Replace `<emp_id>` with the employee ID you want to test. The script at `leavebot/scripts/test_chatbot_batch.py` resets the chatbot state for that employee, reads questions from `questions.txt`, and prints each question with the bot’s answer. Expect verbose debugging output that shows any tool calls made to fetch API data or search policy documents.

## Dependencies

The project relies on several internal API endpoints for employee data. These URLs and an authentication token (`ERP_BEARER_TOKEN`) must be supplied via environment variables. In addition, an `OPENAI_API_KEY` is required for both chat completion and embedding search features.

