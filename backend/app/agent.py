import os
import re
from typing import List, Optional, Tuple

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from .models import (
    AIAnalysis,
    ConditionItem,
    WorkflowItem,
    WorkflowState,
)
from .workflow import generate_workflow


# ============================================================
# ENVIRONMENT / GEMINI
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from backend/.env"
    )

client = genai.Client(api_key=API_KEY) if genai else None

MODEL_NAME = "gemini-3.5-flash-lite"


# ============================================================
# GEMINI SYSTEM INSTRUCTIONS
# ============================================================

SYSTEM_INSTRUCTIONS = """
You are the AI analysis component of an intelligent
conversational workflow builder.

The user describes an automation workflow in natural language.
Your job is to understand the request and identify workflow
information that is explicitly present.

The backend is responsible for deciding which clarification
question should be asked next.

IMPORTANT RULES:

1. NEVER invent missing information.

2. Only extract information that is explicitly supported by the
   user's message.

3. Never assume a platform, source, monitoring location,
   notification channel, recipient, condition, action, duplicate
   handling preference, or additional requirement.

4. Preserve information that has already been collected.

5. Do not remove previously collected information.

6. Ask only one clarification question at a time. The backend
   controls the clarification question.

7. Short answers such as:
      Gmail
      Zendesk
      Email
      Finance team
   should be interpreted according to the previous clarification
   question.

8. Do not confuse substrings with recipients. For example,
   "customer" must never be interpreted as "me".

9. If the original request explicitly contains a recipient for a
   branch action, that recipient is already known for that branch.
   Do not claim that it is missing.

10. Do not execute workflows.

11. Do not integrate with external services.

12. The final output is only a workflow representation.

13. Preserve conditional TRUE and FALSE branches.

14. If information is ambiguous, report the ambiguity instead of
    inventing an interpretation.

15. The workflow should only be considered complete when all
    information required for the specific workflow has been
    collected.

Return only structured information matching the supplied schema.
"""


# ============================================================
# CLARIFICATION QUESTIONS
# ============================================================

QUESTIONS = {
    "goal": "What is the main goal of this workflow?",
    "trigger": "What should trigger this workflow?",
    "trigger_source": (
        "Which platform or system should provide or be "
        "monitored for this event?"
    ),
    "workflow_operation": (
        "What should happen after the workflow is triggered?"
    ),
    "notification_channel": (
        "How would you like to be notified?"
    ),
    "notification_recipient": (
        "Who should receive the notification?"
    ),
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean(value: Optional[str]) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )


def normalized(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.lower(),
    ).strip()


def unique(values: List[str]) -> List[str]:
    result = []

    for value in values:
        if value and value not in result:
            result.append(value)

    return result


# ============================================================
# PLATFORM EXTRACTION
# ============================================================

PLATFORMS = {
    "gmail": "Gmail",
    "zendesk": "Zendesk",
    "outlook": "Outlook",
    "salesforce": "Salesforce",
    "jira": "Jira",
    "servicenow": "ServiceNow",
    "freshdesk": "Freshdesk",
    "hubspot": "HubSpot",
    "shopify": "Shopify",
    "github": "GitHub",
    "gitlab": "GitLab",
    "slack": "Slack",
    "discord": "Discord",
    "airtable": "Airtable",
    "google sheets": "Google Sheets",
    "microsoft teams": "Microsoft Teams",
    "teams": "Microsoft Teams",
}


def extract_source(message: str) -> Optional[str]:
    text = clean(message)
    lower = text.lower()

    # Direct short answers.
    if lower in PLATFORMS:
        return PLATFORMS[lower]

    # Explicit platform phrases.
    patterns = [
        r"\bfrom\s+(.+?)(?:[,.!?]|$)",
        r"\busing\s+(.+?)(?:[,.!?]|$)",
        r"\bthrough\s+(.+?)(?:[,.!?]|$)",
        r"\bon\s+(.+?)(?:[,.!?]|$)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        candidate = clean(match.group(1))

        if candidate.lower() in PLATFORMS:
            return PLATFORMS[candidate.lower()]

    return None


# ============================================================
# TRIGGER EXTRACTION
# ============================================================

def extract_trigger(message: str) -> Optional[str]:
    text = clean(message)
    lower = text.lower()

    if "new invoice" in lower:
        return "New invoice arrives"

    if "new support ticket" in lower:
        return "New support ticket arrives"

    patterns = [
        r"\bnew\s+(.+?)\s+(?:arrives|arrive|is received|received)",
        r"\bwhen\s+(?:a\s+)?(.+?)\s+(?:arrives|arrive|is created|created|is received|received)",
        r"\bwhenever\s+(?:a\s+)?(.+?)\s+(?:arrives|arrive|is created|created|is received|received)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            value = clean(match.group(1))

            if value:
                if value.lower().startswith("new "):
                    return value

                return f"New {value}"

    return None


# ============================================================
# GOAL EXTRACTION
# ============================================================

def extract_goal(message: str) -> str:
    text = clean(message)
    lower = text.lower()

    if (
        "invoice" in lower
        and (
            "notify" in lower
            or "notification" in lower
            or "alert" in lower
        )
    ):
        return "Notify finance team when a new invoice arrives"

    if (
        "support ticket" in lower
        and "priority" in lower
    ):
        return "Handle support tickets based on priority"

    return text


# ============================================================
# NOTIFICATION CHANNELS
# ============================================================

CHANNELS = {
    "email": "Email",
    "e-mail": "Email",
    "slack": "Slack",
    "sms": "SMS",
    "discord": "Discord",
    "teams": "Microsoft Teams",
    "microsoft teams": "Microsoft Teams",
}


def normalize_channel(value: str) -> str:
    value = clean(value)

    return CHANNELS.get(
        value.lower(),
        value,
    )


# ============================================================
# NOTIFICATION EXTRACTION
# ============================================================

def extract_notification_details(
    message: str,
) -> Tuple[Optional[str], Optional[str]]:

    text = clean(message)
    lower = text.lower()

    channel = None
    recipient = None

    # --------------------------------------------------------
    # CHANNEL
    # --------------------------------------------------------

    for keyword, value in CHANNELS.items():

        if re.search(
            r"\b" + re.escape(keyword) + r"\b",
            lower,
        ):
            channel = value
            break

    # --------------------------------------------------------
    # KNOWN RECIPIENTS
    # --------------------------------------------------------

    known_recipients = [
        "support team",
        "support staff",
        "support group",
        "finance team",
        "finance department",
        "admin team",
        "administrator",
        "operations team",
        "engineering team",
        "customer service team",
        "sales team",
        "hr team",
        "management team",
    ]

    for item in known_recipients:

        if re.search(
            r"\b" + re.escape(item) + r"\b",
            lower,
        ):
            recipient = item.title()
            break

    # --------------------------------------------------------
    # EXPLICIT "NOTIFY X" / "SEND TO X"
    # --------------------------------------------------------

    if recipient is None:

        patterns = [
            r"\bnotify\s+(?:the\s+)?(.+?)(?:[,.!?]|$)",
            r"\bsend\s+(?:it\s+)?to\s+(?:the\s+)?(.+?)(?:[,.!?]|$)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if not match:
                continue

            candidate = clean(
                match.group(1)
            )

            if candidate.lower() not in {
                "email",
                "an email",
                "a notification",
                "notification",
                "sms",
                "slack",
                "teams",
            }:
                recipient = candidate
                break

    return channel, recipient


# ============================================================
# NOTIFICATION IDENTIFICATION
# ============================================================

def is_notification(
    item: WorkflowItem,
) -> bool:

    text = (
        f"{item.name} {item.details}"
    ).lower()

    return any(
        word in text
        for word in [
            "notification",
            "notify",
            "alert",
            "send email",
            "send an email",
            "send sms",
            "send slack",
        ]
    )


def notification_has_recipient(
    item: WorkflowItem,
) -> bool:

    _, recipient = extract_notification_details(
        item.details
    )

    if recipient:
        return True

    details_lower = item.details.lower()

    return bool(
        re.search(
            r"\brecipient\s*:",
            details_lower,
        )
    )


def get_branch_notification_recipient(
    state: WorkflowState,
) -> Optional[str]:
    """Return the first explicit recipient found on a branch notification."""

    for condition in state.conditions:
        for branch in (condition.if_true, condition.if_false):
            for item in branch:
                if not is_notification(item):
                    continue

                _, recipient = extract_notification_details(item.details)
                if recipient:
                    return recipient

                match = re.search(
                    r"\\brecipient\\s*:\\s*(.+)$",
                    item.details,
                    re.IGNORECASE,
                )
                if match:
                    return clean(match.group(1))

    return None


def branch_has_notification_recipient(
    state: WorkflowState,
) -> bool:

    for condition in state.conditions:

        for item in condition.if_true:
            if (
                is_notification(item)
                and notification_has_recipient(item)
            ):
                return True

        for item in condition.if_false:
            if (
                is_notification(item)
                and notification_has_recipient(item)
            ):
                return True

    return False


# ============================================================
# BRANCH ACTION PARSER
# ============================================================

def parse_branch_action(
    message: str,
) -> Optional[WorkflowItem]:

    text = clean(message)

    if not text:
        return None

    lower = text.lower()

    if lower in {
        "do nothing",
        "nothing",
        "no action",
        "ignore",
        "ignore it",
    }:

        return WorkflowItem(
            name="Do nothing",
            details=text,
        )

    channel, recipient = (
        extract_notification_details(text)
    )

    # If the channel is already explicitly stated.
    if channel:

        details = text

        if recipient:
            details += (
                f" | Recipient: {recipient}"
            )

        return WorkflowItem(
            name=f"{channel} notification",
            details=details,
        )

    # Notification without channel.
    # This must be checked before generic action parsing so that
    # "Notify my finance team" is treated as a notification
    # requiring a notification channel, not as a generic action.
    if re.search(
        r"\bnotify\b|\balert\b",
        lower,
    ):

        details = text

        if recipient:
            details += f" | Recipient: {recipient}"

        return WorkflowItem(
            name="Notification",
            details=details,
        )

    # Normal actions.
    patterns = [
        r"\bcreate\s+([^,.!?]+)",
        r"\bmark\s+([^,.!?]+)",
        r"\bupdate\s+([^,.!?]+)",
        r"\bassign\s+([^,.!?]+)",
        r"\bsave\s+([^,.!?]+)",
        r"\bforward\s+([^,.!?]+)",
        r"\bescalate\s+([^,.!?]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            return WorkflowItem(
                name=clean(
                    match.group(0)
                ).capitalize(),
                details=text,
            )

    return WorkflowItem(
        name=text,
        details=text,
    )


# ============================================================
# CONDITION EXTRACTION
# ============================================================

def extract_condition(
    message: str,
) -> Optional[ConditionItem]:

    text = clean(message)
    lower = text.lower()

    if (
        " if " not in f" {lower} "
        and "otherwise" not in lower
        and " else " not in f" {lower} "
    ):
        return None

    # Assignment/reference condition.
    priority_match = re.search(
        r"\bif\s+(?:the\s+)?ticket\s+is\s+high\s+priority",
        text,
        re.IGNORECASE,
    )

    if priority_match:

        condition = ConditionItem(
            name="Ticket priority check",
            details=(
                "Check whether the ticket is high priority."
            ),
        )

        otherwise = re.search(
            r"\botherwise\b",
            text,
            re.IGNORECASE,
        )

        if otherwise:

            yes_text = text[
                priority_match.end():
                otherwise.start()
            ].strip(
                " ,;:."
            )

            no_text = text[
                otherwise.end():
            ].strip(
                " ,;:."
            )

            yes_action = parse_branch_action(
                yes_text
            )

            no_action = parse_branch_action(
                no_text
            )

            if yes_action:
                condition.if_true = [
                    yes_action
                ]

            if no_action:
                condition.if_false = [
                    no_action
                ]

        return condition

    return ConditionItem(
        name="Condition",
        details=text,
        if_true=[],
        if_false=[],
    )


# ============================================================
# BRANCH HELPERS
# ============================================================

def branch_items(
    state: WorkflowState,
) -> List[WorkflowItem]:

    result = []

    for condition in state.conditions:

        result.extend(
            condition.if_true
        )

        result.extend(
            condition.if_false
        )

    return result


def has_branch_notification(
    state: WorkflowState,
) -> bool:

    return any(
        is_notification(item)
        for item in branch_items(state)
    )


def update_branch_notification_channel(
    state: WorkflowState,
    channel: str,
) -> None:

    for condition in state.conditions:

        for branch in (
            condition.if_true,
            condition.if_false,
        ):

            for item in branch:

                if not is_notification(item):
                    continue

                recipient = extract_notification_details(
                    item.details
                )[1]

                if recipient:

                    item.name = (
                        f"{channel} notification"
                    )

                else:

                    item.name = (
                        f"{channel} notification"
                    )


def remove_branch_duplicates(
    state: WorkflowState,
) -> None:

    branches = branch_items(state)

    if not branches:
        return

    filtered_actions = []

    for action in state.actions:

        action_text = normalized(
            f"{action.name} {action.details}"
        )

        duplicate = False

        for branch in branches:

            branch_text = normalized(
                f"{branch.name} {branch.details}"
            )

            if (
                action_text == branch_text
                or action_text in branch_text
                or branch_text in action_text
            ):
                duplicate = True
                break

        if not duplicate:
            filtered_actions.append(action)

    state.actions = filtered_actions


# ============================================================
# INITIAL REQUEST PARSER
# ============================================================

def parse_initial_request(
    message: str,
    state: WorkflowState,
) -> None:

    text = clean(message)

    # --------------------------------------------------------
    # GOAL
    # --------------------------------------------------------

    if not state.goal:
        state.goal = extract_goal(text)

    # --------------------------------------------------------
    # TRIGGER
    # --------------------------------------------------------

    trigger = extract_trigger(text)

    if trigger and not state.trigger:

        state.trigger = WorkflowItem(
            name=trigger,
            details=text,
        )

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    source = extract_source(text)

    if source:
        state.trigger_source = source

    # --------------------------------------------------------
    # CONDITION
    # --------------------------------------------------------

    condition = extract_condition(text)

    if condition:

        state.conditions = [
            condition
        ]

    # --------------------------------------------------------
    # NOTIFICATION
    # --------------------------------------------------------

    channel, recipient = (
        extract_notification_details(text)
    )

    # If a notification is already inside a condition,
    # DO NOT create a separate global notification.
    if has_branch_notification(state):

        if channel:
            state.notification_channel = channel

        # Preserve an explicitly stated branch recipient.
        branch_recipient = get_branch_notification_recipient(state)
        state.notification_recipient = branch_recipient

    elif channel:

        state.notification_channel = channel

        state.notifications = [
            WorkflowItem(
                name=f"{channel} notification",
                details=text,
            )
        ]

        # IMPORTANT:
        # The invoice-style initial request deliberately
        # does NOT collect the recipient.
        state.notification_recipient = None

    elif any(
        word in text.lower()
        for word in [
            "notify",
            "notification",
            "alert",
        ]
    ):

        state.notifications = [
            WorkflowItem(
                name="Notification",
                details=text,
            )
        ]

        # Initial request recipient is deliberately not
        # considered collected.
        state.notification_recipient = None

    # Keep the planning-state notification count meaningful for
    # conditional workflows. Branch notifications belong to their
    # YES/NO branch in the graph, but the state panel should still
    # report that a notification exists.
    if (
        has_branch_notification(state)
        and not state.notifications
    ):
        branch_notification = next(
            (
                item
                for item in branch_items(state)
                if is_notification(item)
            ),
            None,
        )

        if branch_notification:
            state.notifications = [branch_notification]

    remove_branch_duplicates(state)


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_with_ai(
    message: str,
    state: WorkflowState,
) -> AIAnalysis:

    if client is None or types is None:
        return AIAnalysis()

    prompt = f"""
{SYSTEM_INSTRUCTIONS}

CURRENT WORKFLOW STATE:

{state.model_dump_json(indent=2)}

NEW USER MESSAGE:

{message}

Analyze only the new information contained in the message.

Do not invent missing values.

Return only structured JSON matching AIAnalysis.
"""

    try:

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIAnalysis,
                max_output_tokens=900,
                thinking_config=types.ThinkingConfig(
                    thinking_level="minimal"
                ),
            ),
        )

        if not response.text:
            return AIAnalysis()

        return AIAnalysis.model_validate_json(
            response.text
        )

    except Exception as error:

        print(
            "Gemini analysis failed. "
            "Using deterministic processing.",
            error,
        )

        return AIAnalysis()


# ============================================================
# MERGE GEMINI RESULT
# ============================================================

def merge_ai_result(
    state: WorkflowState,
    analysis: AIAnalysis,
    message: str,
) -> None:

    # --------------------------------------------------------
    # GOAL
    # --------------------------------------------------------

    if not state.goal and analysis.goal:

        state.goal = clean(
            analysis.goal
        )

    # --------------------------------------------------------
    # TRIGGER
    # --------------------------------------------------------

    if (
        analysis.trigger
        and not state.trigger
    ):

        state.trigger = analysis.trigger

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    explicit_source = extract_source(
        message
    )

    if explicit_source:

        state.trigger_source = (
            explicit_source
        )

    # --------------------------------------------------------
    # MONITORING LOCATION
    # --------------------------------------------------------

    if analysis.monitoring_location:

        state.monitoring_location = (
            analysis.monitoring_location
        )

    # --------------------------------------------------------
    # CONDITIONS
    # --------------------------------------------------------

    if analysis.conditions:

        if not state.conditions:

            state.conditions = list(
                analysis.conditions
            )

        else:

            current = state.conditions[0]
            incoming = analysis.conditions[0]

            if incoming.name:
                current.name = incoming.name

            if incoming.details:
                current.details = (
                    incoming.details
                )

            # Do not overwrite deterministic branch
            # information with empty AI branches.
            if (
                incoming.if_true
                and not current.if_true
            ):
                current.if_true = (
                    incoming.if_true
                )

            if (
                incoming.if_false
                and not current.if_false
            ):
                current.if_false = (
                    incoming.if_false
                )

    # --------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------

    for action in analysis.actions:

        action_key = normalized(
            f"{action.name} {action.details}"
        )

        exists = any(
            normalized(
                f"{existing.name} "
                f"{existing.details}"
            ) == action_key
            for existing in state.actions
        )

        if not exists:
            state.actions.append(action)

    # --------------------------------------------------------
    # NOTIFICATIONS
    # --------------------------------------------------------

    # If deterministic parsing already found a global notification,
    # keep that single notification instead of adding a second,
    # semantically equivalent notification returned by Gemini.
    # Gemini enriches the state but must not duplicate deterministic
    # workflow items.
    if not has_branch_notification(state) and not state.notifications:

        for notification in analysis.notifications:

            notification_key = normalized(
                f"{notification.name} "
                f"{notification.details}"
            )

            exists = any(
                normalized(
                    f"{existing.name} "
                    f"{existing.details}"
                ) == notification_key
                for existing in state.notifications
            )

            if not exists:
                state.notifications.append(
                    notification
                )

    # --------------------------------------------------------
    # CHANNEL
    # --------------------------------------------------------

    if analysis.notification_channel:

        state.notification_channel = (
            normalize_channel(
                analysis.notification_channel
            )
        )

        update_branch_notification_channel(
            state,
            state.notification_channel,
        )

    # --------------------------------------------------------
    # RECIPIENT
    # --------------------------------------------------------

    # A recipient explicitly written in a conditional branch is
    # already collected and should be reflected in the planning state.
    branch_recipient = get_branch_notification_recipient(state)

    if branch_recipient:
        state.notification_recipient = branch_recipient

    # Gemini can populate the recipient after the recipient
    # clarification has been asked.
    elif (
        state.asked_questions
        and "who should receive"
        in state.asked_questions[-1].lower()
        and analysis.notification_recipient
    ):
        state.notification_recipient = clean(
            analysis.notification_recipient
        )

    # --------------------------------------------------------
    # DUPLICATE HANDLING
    # --------------------------------------------------------

    if analysis.duplicate_handling:

        state.duplicate_handling = (
            analysis.duplicate_handling
        )

    # --------------------------------------------------------
    # ADDITIONAL REQUIREMENTS
    # --------------------------------------------------------

    if analysis.additional_requirements:

        state.additional_requirements = unique(
            [
                *state.additional_requirements,
                *analysis.additional_requirements,
            ]
        )

    # --------------------------------------------------------
    # AMBIGUITIES
    # --------------------------------------------------------

    if analysis.ambiguities:

        state.ambiguities = unique(
            [
                *state.ambiguities,
                *analysis.ambiguities,
            ]
        )

    remove_branch_duplicates(state)


# ============================================================
# MISSING INFORMATION
# ============================================================

def calculate_missing_information(
    state: WorkflowState,
) -> List[str]:

    missing = []

    # --------------------------------------------------------
    # BASIC INFORMATION
    # --------------------------------------------------------

    if not state.goal:
        missing.append("goal")

    if not state.trigger:
        missing.append("trigger")

    if (
        state.trigger
        and not state.trigger_source
    ):
        missing.append(
            "trigger_source"
        )

    # --------------------------------------------------------
    # WORKFLOW OPERATION
    # --------------------------------------------------------

    if not (
        state.actions
        or state.conditions
        or state.notifications
    ):

        missing.append(
            "workflow_operation"
        )

    # --------------------------------------------------------
    # CONDITIONAL BRANCHES
    # --------------------------------------------------------

    for condition in state.conditions:

        if not condition.if_true:

            missing.append(
                "condition_branch_actions"
            )

            break

        if not condition.if_false:

            missing.append(
                "condition_branch_actions"
            )

            break

    # --------------------------------------------------------
    # NOTIFICATIONS
    # --------------------------------------------------------

    has_global_notification = bool(
        state.notifications
    )

    has_branch_notification_value = (
        has_branch_notification(state)
    )

    has_notification = (
        has_global_notification
        or has_branch_notification_value
        or bool(state.notification_channel)
    )

    if has_notification:

        # Channel is always required when a notification
        # exists and has not been explicitly provided.
        if not state.notification_channel:

            missing.append(
                "notification_channel"
            )

        # ----------------------------------------------------
        # RECIPIENT RULE
        #
        # Global notification:
        #     recipient must be explicitly clarified.
        #
        # Branch notification:
        #     if recipient was already written in the
        #     original request, it is already known.
        # ----------------------------------------------------

        if (
            has_global_notification
            and not state.notification_recipient
        ):

            missing.append(
                "notification_recipient"
            )

        elif (
            has_branch_notification_value
            and not branch_has_notification_recipient(
                state
            )
        ):

            # Branch notification exists but no recipient
            # was supplied in the original request.
            missing.append(
                "notification_recipient"
            )

    return unique(missing)


# ============================================================
# NEXT QUESTION
# ============================================================

def next_question(
    state: WorkflowState,
) -> str:

    missing = calculate_missing_information(
        state
    )

    if not missing:
        return ""

    # --------------------------------------------------------
    # CONDITIONAL BRANCHES
    # --------------------------------------------------------

    if "condition_branch_actions" in missing:

        for condition in state.conditions:

            if not condition.if_true:

                return (
                    "What should happen when the "
                    "condition is true?"
                )

            if not condition.if_false:

                return (
                    "What should happen when the "
                    "condition is false?"
                )

    # --------------------------------------------------------
    # NORMAL QUESTIONS
    # --------------------------------------------------------

    return QUESTIONS.get(
        missing[0],
        "Could you provide the missing workflow information?",
    )


# ============================================================
# FOLLOW-UP ANSWER HANDLER
# ============================================================

def handle_followup_answer(
    message: str,
    state: WorkflowState,
) -> bool:

    text = clean(message)

    if not text:
        return False

    previous_question = ""

    if state.asked_questions:

        previous_question = (
            state.asked_questions[-1]
            .lower()
        )

    # --------------------------------------------------------
    # PLATFORM
    # --------------------------------------------------------

    if (
        "which platform" in previous_question
        or "which system" in previous_question
    ):

        source = extract_source(text)

        state.trigger_source = (
            source or text
        )

        return True

    # --------------------------------------------------------
    # NOTIFICATION CHANNEL
    # --------------------------------------------------------

    if (
        "how would you like to be notified"
        in previous_question
    ):

        channel = normalize_channel(text)

        state.notification_channel = channel

        # Update global notification.
        for notification in state.notifications:

            if (
                notification.name
                in {
                    "Notification",
                    "Email notification",
                    "Slack notification",
                    "SMS notification",
                    "Microsoft Teams notification",
                }
            ):

                notification.name = (
                    f"{channel} notification"
                )

        # If notification is in a condition,
        # update that branch instead.
        update_branch_notification_channel(
            state,
            channel,
        )

        # If nothing existed, create a global notification.
        if (
            not state.notifications
            and not has_branch_notification(state)
        ):

            state.notifications = [
                WorkflowItem(
                    name=f"{channel} notification",
                    details=(
                        "Notification requested by user."
                    ),
                )
            ]

        return True

    # --------------------------------------------------------
    # RECIPIENT
    # --------------------------------------------------------

    if (
        "who should receive"
        in previous_question
    ):

        # Store the exact answer.
        state.notification_recipient = text

        return True

    # --------------------------------------------------------
    # TRIGGER
    # --------------------------------------------------------

    if (
        "what should trigger"
        in previous_question
    ):

        state.trigger = WorkflowItem(
            name=text,
            details=text,
        )

        return True

    # --------------------------------------------------------
    # NORMAL ACTION
    # --------------------------------------------------------

    if (
        "what should happen after"
        in previous_question
    ):

        action = parse_branch_action(
            text
        )

        if action:
            if is_notification(action):
                exists = any(
                    normalized(
                        f"{item.name} {item.details}"
                    )
                    == normalized(
                        f"{action.name} {action.details}"
                    )
                    for item in state.notifications
                )

                if not exists:
                    state.notifications.append(action)

                _, recipient = extract_notification_details(
                    action.details
                )

                if recipient:
                    state.notification_recipient = recipient

            else:
                state.actions.append(action)

        return True

    # --------------------------------------------------------
    # TRUE BRANCH
    # --------------------------------------------------------

    if (
        "what should happen when the "
        "condition is true"
        in previous_question
    ):

        action = parse_branch_action(
            text
        )

        if action:

            if not state.conditions:

                state.conditions = [
                    ConditionItem(
                        name="Condition",
                        details="Condition",
                    )
                ]

            state.conditions[0].if_true = [
                action
            ]

        return True

    # --------------------------------------------------------
    # FALSE BRANCH
    # --------------------------------------------------------

    if (
        "what should happen when the "
        "condition is false"
        in previous_question
    ):

        action = parse_branch_action(
            text
        )

        if action:

            if not state.conditions:

                state.conditions = [
                    ConditionItem(
                        name="Condition",
                        details="Condition",
                    )
                ]

            state.conditions[0].if_false = [
                action
            ]

        return True

    return False


# ============================================================
# MAIN AGENT
# ============================================================

def process_message(
    message: str,
    state: WorkflowState,
):

    message = clean(message)

    if not message:

        return (
            "Please describe the workflow you want to create.",
            state,
            None,
        )

    # ========================================================
    # FIRST MESSAGE
    # ========================================================

    first_message = (
        not state.goal
        and not state.trigger
        and not state.asked_questions
    )

    if first_message:

        parse_initial_request(
            message,
            state,
        )

        # Gemini enriches understanding but deterministic
        # parsing remains responsible for clarification logic.
        analysis = analyze_with_ai(
            message,
            state,
        )

        merge_ai_result(
            state,
            analysis,
            message,
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # For a global notification such as:
        #
        # "notify my finance team"
        #
        # recipient is deliberately NOT considered collected.
        #
        # For a branch notification such as:
        #
        # "notify the support team; otherwise..."
        #
        # the branch already contains its explicit recipient,
        # so that recipient is preserved.
        # ----------------------------------------------------

        if not has_branch_notification(state):

            state.notification_recipient = None
        else:
            state.notification_recipient = (
                get_branch_notification_recipient(state)
            )

    # ========================================================
    # FOLLOW-UP MESSAGE
    # ========================================================

    else:

        answered = handle_followup_answer(
            message,
            state,
        )

        if not answered:

            parse_initial_request(
                message,
                state,
            )

            analysis = analyze_with_ai(
                message,
                state,
            )

            merge_ai_result(
                state,
                analysis,
                message,
            )

    # ========================================================
    # CLEAR RESOLVED PLATFORM AMBIGUITIES
    # ========================================================

    if state.trigger_source:

        state.ambiguities = [
            item
            for item in state.ambiguities
            if (
                "platform"
                not in item.lower()
                and "source"
                not in item.lower()
            )
        ]

    # ========================================================
    # CALCULATE MISSING INFORMATION
    # ========================================================

    missing = calculate_missing_information(
        state
    )

    state.missing_information = missing

    # ========================================================
    # COMPLETE
    # ========================================================

    if (
        not missing
        and not state.ambiguities
    ):

        state.status = "complete"

        workflow = generate_workflow(
            state
        )

        return (
            "I have collected the required information. "
            "Your workflow is ready.",
            state,
            workflow,
        )

    # ========================================================
    # CONTINUE COLLECTING
    # ========================================================

    state.status = "collecting"

    question = next_question(
        state
    )

    # ========================================================
    # RECORD QUESTION
    # ========================================================

    if question:

        if (
            not state.asked_questions
            or state.asked_questions[-1]
            != question
        ):

            state.asked_questions.append(
                question
            )

        state.asked_questions = (
            state.asked_questions[-20:]
        )

    return (
        question,
        state,
        None,
    )