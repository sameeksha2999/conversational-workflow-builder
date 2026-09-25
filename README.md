# Conversational Workflow Builder

Digitomics AI Engineer assignment implementation.

## Scope

This project is a conversational workflow planner. It does not execute workflows or integrate with external services. The AI agent collects the information needed to represent a workflow, asks clarification questions when information is missing, and generates a visual workflow only after the state is complete.

## Architecture

- `backend/app/agent.py` — AI orchestration, state merge, missing-information validation, one-question-at-a-time clarification.
- `backend/app/models.py` — typed workflow and conversation state.
- `backend/app/workflow.py` — converts collected state into nodes and edges for visualization.
- `backend/app/main.py` — FastAPI API.
- `frontend/src/App.jsx` — chatbot, collected-state panel, and React Flow visualization.

## Backend

From `backend`:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```text
GEMINI_API_KEY=your_key_here
```

Start:

```bash
uvicorn app.main:app --reload
```

## Frontend

From `frontend`:

```bash
npm install
npm run dev
```

Open `http://localhost:5173`.

## Example conversation

1. `I want a workflow that monitors new support tickets.`
2. Assistant asks which platform/system should be monitored.
3. `Zendesk`
4. Assistant asks what should happen when a ticket is created.
5. `Send an email notification to the support team.`
6. The state preserves Email + support team and the workflow is generated.

## Important design decision

Gemini identifies missing information, but the backend validates the state and selects exactly one next clarification question. This prevents an LLM response from accidentally combining multiple questions and keeps the conversation state deterministic.
