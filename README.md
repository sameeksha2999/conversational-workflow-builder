

````markdown
# Conversational Workflow Builder

> **Digitomics AI Engineer Assignment**

An AI-powered conversational workflow builder that converts natural-language automation requests into structured, visual workflow representations through an intelligent clarification process.

---

## Overview

The **Conversational Workflow Builder** allows users to describe an automation requirement in natural language.

Instead of requiring the user to manually define every workflow parameter, the system:

1. Understands the user's automation request.
2. Identifies missing or ambiguous information.
3. Asks targeted clarification questions.
4. Collects and maintains the information provided by the user.
5. Determines when all required information has been collected.
6. Generates a structured workflow representation.
7. Visualizes the generated workflow as a node-based diagram.

The system is designed specifically for **workflow planning and representation**. It does not execute workflows or connect to external services.

---

## Problem Statement

Automation requests are often incomplete when expressed in natural language.

For example:

> "Whenever a new invoice arrives, notify my finance team."

The request describes the intended automation, but additional information is required before a complete workflow can be created.

The system therefore needs to determine:

- What platform or system provides the trigger?
- How should the user be notified?
- Who should receive the notification?
- Are there any additional conditions or requirements?

Rather than making assumptions, the application uses a conversational clarification process to collect the missing information.

---

## Solution

The application implements a conversational agent that maintains a structured workflow state throughout the interaction.

### Conversation Flow

```text
User Request
     │
     ▼
Understand Request
     │
     ▼
Identify Missing Information
     │
     ▼
Ask Clarification
     │
     ▼
Update Workflow State
     │
     ▼
Check Completeness
     │
     ├── Information Missing ──► Ask Next Question
     │
     ▼
All Required Information Collected
     │
     ▼
Generate Workflow
     │
     ▼
Visualize Workflow
````

The agent continues the clarification process until the required information has been collected.

---

## Key Features

### 1. Natural Language Workflow Input

Users can describe their automation requirement naturally.

Example:

```text
Whenever a new invoice arrives, notify my finance team.
```

---

### 2. Intelligent Clarification

The system identifies missing information and asks relevant questions instead of assuming values.

Example conversation:

```text
User:
Whenever a new invoice arrives, notify my finance team.

Assistant:
Which platform or system should provide or be monitored for this event?

User:
Gmail

Assistant:
How would you like to be notified?

User:
Email

Assistant:
Who should receive the notification?

User:
Finance team

Assistant:
I have collected the required information. Your workflow is ready.
```

---

### 3. Structured Workflow State

The application maintains the conversation as structured state rather than relying only on raw chat history.

The workflow state can contain:

* Goal
* Trigger
* Trigger source
* Monitoring location
* Actions
* Conditions
* Notifications
* Notification channel
* Notification recipient
* Duplicate handling
* Additional requirements
* Missing information
* Ambiguities
* Asked questions
* Workflow status

---

### 4. One Question at a Time

The clarification process is designed to ask one question at a time.

This makes each user response easier to associate with the corresponding missing workflow information and keeps the conversation focused.

---

### 5. Conditional Workflows

The system supports conditional automation requests with YES/NO branches.

Example:

```text
Whenever a new support ticket arrives.
If the ticket is high priority, notify the support team;
otherwise create a follow-up task.
```

The generated workflow is represented as:

```text
              New Support Ticket
                       │
                       ▼
                Priority Check
                 /           \
              YES             NO
               │               │
               ▼               ▼
        Email Notification   Follow-up Task
               \               /
                \             /
                     ▼
                    End
```

---

### 6. Workflow Visualization

Completed workflows are rendered as a visual node-based workflow using **React Flow**.

The visualization supports:

* Trigger nodes
* Action nodes
* Notification nodes
* Condition nodes
* YES/NO branches
* Workflow connections
* End node

---

## Architecture

```text
┌───────────────────────────┐
│           User            │
│                           │
│ Natural Language Request  │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│      React Frontend       │
│                           │
│ • Chat Interface          │
│ • Conversation State      │
│ • Workflow Visualization  │
└─────────────┬─────────────┘
              │
              │ HTTP / JSON
              ▼
┌───────────────────────────┐
│      FastAPI Backend      │
│                           │
│ • API Handling            │
│ • Agent Processing        │
│ • State Management        │
│ • Workflow Generation     │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│       Gemini AI Layer     │
│                           │
│ • Request Understanding   │
│ • Information Extraction  │
│ • Missing Information     │
│ • Ambiguity Detection     │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│   Structured Workflow     │
│                           │
│ Trigger → Condition →     │
│ Actions → Notifications   │
└───────────────────────────┘
```

---

## Technology Stack

### Frontend

* React
* Vite
* React Flow
* JavaScript
* CSS

### Backend

* Python
* FastAPI
* Pydantic
* Uvicorn

### AI

* Google Gemini API

### Development & Deployment

* Git
* GitHub
* Render

---

## Project Structure

```text
conversational-workflow-builder/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── workflow.py
│   │
│   ├── tests/
│   │   └── test_workflow.py
│   │
│   ├── .env.example
│   ├── .gitignore
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
```

---

## Backend Design

### `agent.py`

The conversational agent is responsible for processing the user's request and managing the clarification process.

Main responsibilities:

* Understand natural-language requests
* Extract workflow information
* Identify missing information
* Detect ambiguities
* Generate clarification questions
* Process follow-up answers
* Maintain workflow state
* Determine when the workflow is complete

The implementation combines AI-based analysis with deterministic application logic for predictable state handling.

---

### `models.py`

Defines the structured data models used throughout the application.

Important models include:

* `WorkflowState`
* `WorkflowItem`
* `ConditionItem`
* `ChatRequest`
* `ChatResponse`
* `AIAnalysis`

Pydantic models are used to maintain consistent data structures between the frontend, backend, AI analysis, and workflow generation layers.

---

### `workflow.py`

Responsible for converting the collected workflow state into a structured workflow representation.

It handles:

* Workflow nodes
* Workflow edges
* Trigger nodes
* Action nodes
* Notification nodes
* Condition nodes
* YES/NO branches
* End nodes

The generated representation is then consumed by the frontend for visualization.

---

### `main.py`

Contains the FastAPI application and exposes the backend API.

The primary endpoint is:

```text
POST /chat
```

The endpoint receives:

* The user's current message
* The current workflow state

and returns:

* Assistant response
* Updated workflow state
* Generated workflow when the required information is complete

---

## Workflow State

The application maintains a structured state throughout the conversation.

A simplified example is:

```json
{
  "goal": "Notify finance team when a new invoice arrives",
  "trigger_source": "Gmail",
  "notification_channel": "Email",
  "notification_recipient": "Finance team",
  "status": "complete"
}
```

This state allows the application to determine:

* What information has already been collected
* What information is still missing
* Whether clarification is required
* Whether the workflow is ready for generation

---

## Clarification Strategy

A core design principle of the application is:

> **The system should not assume missing information.**

For example, if a user says:

```text
Whenever a new invoice arrives.
```

the system should not automatically assume:

* The source platform
* The notification method
* The recipient
* Any additional workflow requirements

Instead, it identifies what is missing and asks the user for the required information.

The clarification loop continues until the workflow contains enough information to generate a complete representation.

---

## Example 1 — Simple Notification Workflow

### User Request

```text
Whenever a new invoice arrives, notify my finance team.
```

### Clarification

```text
Trigger Source → Gmail
Notification Channel → Email
Notification Recipient → Finance team
```

### Generated Workflow

```text
New Invoice Arrives
        │
        ▼
Email Notification
        │
        ▼
       End
```

---

## Example 2 — Conditional Workflow

### User Request

```text
Whenever a new support ticket arrives.
If the ticket is high priority, notify the support team;
otherwise create a follow-up task.
```

### Clarification

```text
Trigger Source → Zendesk
Notification Channel → Email
```

### Generated Workflow

```text
                 New Support Ticket
                         │
                         ▼
                  Priority Check
                   /           \
                YES             NO
                 │               │
                 ▼               ▼
          Email Notification  Follow-up Task
                 \               /
                  \             /
                       ▼
                      End
```

---

## API

### `POST /chat`

Processes the current conversation message and workflow state.

#### Request

```json
{
  "message": "Gmail",
  "state": {
    "goal": "Notify finance team when a new invoice arrives"
  }
}
```

#### Response

```json
{
  "reply": "How would you like to be notified?",
  "state": {},
  "workflow": null
}
```

When all required information has been collected, the response contains the generated workflow representation.

---

## Local Setup

### Prerequisites

Make sure the following are installed:

* Python
* Node.js
* npm
* Git
* Google Gemini API key

---

### 1. Clone the Repository

```bash
git clone https://github.com/sameeksha2999/conversational-workflow-builder.git
cd conversational-workflow-builder
```

---

### 2. Backend Setup

Navigate to the backend:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` directory:

```text
backend/.env
```

Add:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Start the backend:

```bash
python -m uvicorn app.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

---

### 3. Frontend Setup

Open a new terminal and navigate to:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the local URL provided by Vite in the terminal.

---

## Environment Variables

The backend requires:

```env
GEMINI_API_KEY=your_gemini_api_key
```

The actual `.env` file is excluded from Git using `.gitignore`.

A template is provided:

```text
backend/.env.example
```

Never commit the actual Gemini API key to GitHub.

---

## Deployment

The application is deployed using Render as separate frontend and backend services.

### Frontend

[https://conversational-workflow-builder-1.onrender.com](https://conversational-workflow-builder-1.onrender.com)

### Backend

[https://conversational-workflow-builder-backend.onrender.com](https://conversational-workflow-builder-backend.onrender.com)

---

## Testing

Backend workflow tests are located in:

```text
backend/tests/test_workflow.py
```

The application has been tested with conversational workflows including:

* Simple trigger and notification workflows
* Multi-step clarification
* Notification recipient collection
* Conditional workflows
* YES/NO branching
* Workflow generation
* Frontend-backend communication
* Deployed application flow

---

## Engineering Decisions

### Structured State

Workflow information is maintained using Pydantic models rather than relying only on conversation history.

This provides a predictable structure for:

* Required information
* Missing information
* Conditions
* Notifications
* Actions
* Workflow status

### AI + Deterministic Logic

The AI layer is used for natural-language understanding and structured analysis.

Deterministic application logic is used for important workflow-state operations such as:

* Updating collected information
* Calculating missing information
* Handling clarification answers
* Preventing duplicate workflow information
* Generating the final workflow representation

This approach provides flexibility in understanding natural language while keeping workflow generation controlled and predictable.

### Separation of Responsibilities

The project separates:

```text
Agent Logic
     ↓
State Models
     ↓
Workflow Generation
     ↓
Frontend Visualization
```

This makes the codebase easier to understand, test, and extend.

---

## Scope

This project is focused on **conversational workflow planning**, as required by the assignment.

### Included

* Natural-language workflow understanding
* Clarification questions
* Missing-information detection
* Conversation state management
* Ambiguity handling
* Workflow completion detection
* Structured workflow generation
* Conditional workflow representation
* Visual workflow rendering

### Not Included

* Actual workflow execution
* Sending real emails or notifications
* Connecting to Gmail, Zendesk, Slack, or other external services
* Managing third-party credentials
* Executing generated automation

The generated workflow is a representation of the intended automation.

---

## Assignment Alignment

The implementation addresses the main requirements of the Digitomics assignment:

| Assignment Requirement                 | Implementation                               |
| -------------------------------------- | -------------------------------------------- |
| Understand automation requests         | Gemini-assisted request analysis             |
| Identify missing information           | Workflow state and missing-information logic |
| Ask clarification questions            | Conversational clarification agent           |
| Handle ambiguity                       | Ambiguity tracking and clarification         |
| Preserve collected information         | Structured `WorkflowState`                   |
| Continue until information is complete | Completion and missing-information checks    |
| Generate workflow representation       | `workflow.py`                                |
| Support conditional workflows          | Condition nodes with YES/NO branches         |
| Visualize workflow                     | React Flow                                   |
| Avoid workflow execution               | Representation-only architecture             |

---

## Live Demo

**Application:**

[https://conversational-workflow-builder-1.onrender.com](https://conversational-workflow-builder-1.onrender.com)

The deployed application can be used to enter a natural-language automation request, answer clarification questions, and view the resulting workflow representation.

---

## Repository

**GitHub:**

[https://github.com/sameeksha2999/conversational-workflow-builder](https://github.com/sameeksha2999/conversational-workflow-builder)

---

## Author

**Sameeksha**

B.E. — Artificial Intelligence & Data Science

---

## Assignment

**Digitomics — AI Engineer Selection Process**

**Project:** Conversational Workflow Builder

The project was developed as a submission for the AI Engineer technical assignment.

````

**This is the complete file.** Don't add anything before or after it.

After pasting it into `README.md`, save it and run:

```bash
git add README.md
git commit -m "Improve project submission README"
git push origin main
````

Then refresh your GitHub repository page.
