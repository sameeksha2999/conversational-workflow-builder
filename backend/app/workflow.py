from typing import Any, Dict, List

from .models import WorkflowItem, WorkflowState


# ============================================================
# ITEM CONFIGURATION
# ============================================================

def item_config(
    item: WorkflowItem,
) -> Dict[str, Any]:
    """
    Convert a workflow item into a serializable configuration.
    """

    return {
        "name": item.name,
        "details": item.details,
    }


# ============================================================
# NODE HELPERS
# ============================================================

def add_node(
    nodes: List[Dict[str, Any]],
    node_id: str,
    node_type: str,
    name: str,
    config: Dict[str, Any],
    x: int,
    y: int,
    branch: str | None = None,
) -> None:
    """
    Add one workflow node to the graph.
    """

    node = {
        "id": node_id,
        "type": node_type,
        "name": name,
        "config": config,
        "position": {
            "x": x,
            "y": y,
        },
    }

    if branch:
        node["branch"] = branch

    nodes.append(node)


def add_edge(
    edges: List[Dict[str, Any]],
    source: str,
    target: str,
    label: str | None = None,
    source_handle: str | None = None,
) -> None:
    """
    Add a directed connection between two workflow nodes.

    source_handle is important for condition nodes because the
    frontend has separate YES and NO handles.
    """

    edge = {
        "id": f"edge_{source}_{target}",
        "source": source,
        "target": target,
    }

    if label:
        edge["label"] = label

    if source_handle:
        edge["sourceHandle"] = source_handle

    edges.append(edge)


# ============================================================
# NOTIFICATION DETECTION
# ============================================================

def is_notification_item(
    item: WorkflowItem,
) -> bool:
    """
    Determine whether a workflow item represents a
    notification rather than a generic action.
    """

    text = (
        f"{item.name} {item.details}"
        .lower()
    )

    notification_patterns = (
        "notification",
        "notify",
        "send email",
        "send an email",
        "send sms",
        "send a slack",
        "send a notification",
        "alert",
    )

    return any(
        pattern in text
        for pattern in notification_patterns
    )


# ============================================================
# BRANCH NODE CREATION
# ============================================================

def add_branch_nodes(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    condition_id: str,
    merge_id: str,
    actions: List[WorkflowItem],
    branch: str,
    x: int,
    branch_y: int,
    state: WorkflowState,
    condition_index: int,
) -> int:
    """
    Create one condition branch.

    Returns the Y position occupied by the last branch node.

    branch:
        "YES" or "NO"
    """

    branch_lower = branch.lower()

    previous_id = condition_id

    # --------------------------------------------------------
    # Create branch action/notification nodes
    # --------------------------------------------------------

    for action_index, action in enumerate(
        actions,
        start=1,
    ):

        node_id = (
            f"condition_{condition_index}"
            f"_{branch_lower}_{action_index}"
        )

        if is_notification_item(action):
            node_type = "notification"
        else:
            node_type = "action"

        config = item_config(action)

        if node_type == "notification":

            config.update(
                {
                    "channel":
                        state.notification_channel,

                    "recipient":
                        state.notification_recipient,
                }
            )

        node_y = (
            branch_y
            + (action_index - 1) * 120
        )

        add_node(
            nodes,
            node_id,
            node_type,
            action.name,
            config,
            x,
            node_y,
            branch,
        )

        # ----------------------------------------------------
        # Condition -> first branch action
        # ----------------------------------------------------
        #
        # For the first branch node, use the condition's
        # corresponding source handle.
        #
        # For later nodes, use the normal bottom handle.
        # ----------------------------------------------------

        if previous_id == condition_id:

            add_edge(
                edges,
                condition_id,
                node_id,
                branch,
                branch_lower,
            )

        else:

            add_edge(
                edges,
                previous_id,
                node_id,
            )

        previous_id = node_id

    # --------------------------------------------------------
    # Connect branch to merge
    # --------------------------------------------------------

    if previous_id == condition_id:

        # This handles an empty branch safely.
        add_edge(
            edges,
            condition_id,
            merge_id,
            branch,
            branch_lower,
        )

    else:

        add_edge(
            edges,
            previous_id,
            merge_id,
        )

    # --------------------------------------------------------
    # Return last branch Y position
    # --------------------------------------------------------

    if actions:
        return (
            branch_y
            + (len(actions) - 1) * 120
        )

    return branch_y


def branch_contains_same_notification(
    state: WorkflowState,
    notification: WorkflowItem,
) -> bool:
    """Return True when the notification is already represented in a YES/NO branch."""

    target = (
        f"{notification.name} {notification.details}"
    ).strip().lower()

    for condition in state.conditions:
        for branch in (condition.if_true, condition.if_false):
            for item in branch:
                if not is_notification_item(item):
                    continue

                candidate = (
                    f"{item.name} {item.details}"
                ).strip().lower()

                if candidate == target:
                    return True

    return False


# ============================================================
# WORKFLOW GENERATION
# ============================================================

def generate_workflow(
    state: WorkflowState,
) -> Dict[str, Any]:
    """
    Build a representation-only workflow graph.

    This function DOES NOT execute anything.

    It only creates:
        - nodes
        - edges
        - branch relationships
        - collected information

    Conditional operations remain inside their YES/NO
    branches and are not duplicated as normal actions.
    """

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # --------------------------------------------------------
    # Layout constants
    # --------------------------------------------------------

    x_center = 350

    yes_x = 100
    no_x = 600

    start_y = 60

    node_gap = 150

    y = start_y

    # --------------------------------------------------------
    # TRIGGER
    # --------------------------------------------------------

    if state.trigger:

        trigger_config = item_config(
            state.trigger
        )

        trigger_config.update(
            {
                "source":
                    state.trigger_source,

                "monitoring_location":
                    state.monitoring_location,
            }
        )

        add_node(
            nodes,
            "trigger",
            "trigger",
            state.trigger.name,
            trigger_config,
            x_center,
            y,
        )

        current = "trigger"

        y += node_gap

    else:

        current = None

    # --------------------------------------------------------
    # NORMAL ACTIONS
    # --------------------------------------------------------

    for index, action in enumerate(
        state.actions,
        start=1,
    ):

        node_id = f"action_{index}"

        add_node(
            nodes,
            node_id,
            "action",
            action.name,
            item_config(action),
            x_center,
            y,
        )

        if current:

            add_edge(
                edges,
                current,
                node_id,
            )

        current = node_id

        y += 130

    # --------------------------------------------------------
    # CONDITIONS
    # --------------------------------------------------------

    for condition_index, condition in enumerate(
        state.conditions,
        start=1,
    ):

        condition_id = (
            f"condition_{condition_index}"
        )

        # ----------------------------------------------------
        # CONDITION NODE
        # ----------------------------------------------------

        add_node(
            nodes,
            condition_id,
            "condition",
            condition.name,
            {
                "name":
                    condition.name,

                "details":
                    condition.details,
            },
            x_center,
            y,
        )

        # Connect previous workflow node to condition.
        if current:

            add_edge(
                edges,
                current,
                condition_id,
            )

        # ----------------------------------------------------
        # Branch starting position
        # ----------------------------------------------------

        branch_y = y + 150

        merge_id = (
            f"condition_{condition_index}_merge"
        )

        # ----------------------------------------------------
        # Calculate branch height BEFORE creating merge.
        #
        # This prevents the merge node from overlapping a
        # second/third branch action.
        # ----------------------------------------------------

        yes_count = len(
            condition.if_true
        )

        no_count = len(
            condition.if_false
        )

        largest_branch_count = max(
            yes_count,
            no_count,
            1,
        )

        last_branch_y = (
            branch_y
            + (largest_branch_count - 1) * 120
        )

        merge_y = last_branch_y + 150

        # ----------------------------------------------------
        # YES BRANCH
        # ----------------------------------------------------

        add_branch_nodes(
            nodes,
            edges,
            condition_id,
            merge_id,
            condition.if_true,
            "YES",
            yes_x,
            branch_y,
            state,
            condition_index,
        )

        # ----------------------------------------------------
        # NO BRANCH
        # ----------------------------------------------------

        add_branch_nodes(
            nodes,
            edges,
            condition_id,
            merge_id,
            condition.if_false,
            "NO",
            no_x,
            branch_y,
            state,
            condition_index,
        )

        # ----------------------------------------------------
        # MERGE NODE
        # ----------------------------------------------------

        add_node(
            nodes,
            merge_id,
            "merge",
            "Continue",
            {
                "details":
                    "Continue after the condition branches"
            },
            x_center,
            merge_y,
        )

        # Everything after this condition connects from the
        # merge node.
        current = merge_id

        # Leave enough space before the next workflow section.
        y = merge_y + 150

    # --------------------------------------------------------
    # GLOBAL NOTIFICATIONS
    # --------------------------------------------------------
    #
    # These notifications are only notifications that are
    # outside conditional branches.
    #
    # Branch notifications are represented directly inside
    # their YES/NO branches.
    # --------------------------------------------------------

    global_notification_index = 0

    for notification in state.notifications:

        # A branch notification may be mirrored in state.notifications
        # only so the collected-information panel can report that a
        # notification exists. It must not become a second graph node.
        if branch_contains_same_notification(
            state,
            notification,
        ):
            continue

        global_notification_index += 1

        node_id = (
            f"notification_{global_notification_index}"
        )

        config = item_config(
            notification
        )

        config.update(
            {
                "channel":
                    state.notification_channel,

                "recipient":
                    state.notification_recipient,
            }
        )

        add_node(
            nodes,
            node_id,
            "notification",
            notification.name,
            config,
            x_center,
            y,
        )

        if current:

            add_edge(
                edges,
                current,
                node_id,
            )

        current = node_id

        y += 140

    # --------------------------------------------------------
    # END
    # --------------------------------------------------------

    if current:

        add_node(
            nodes,
            "end",
            "end",
            "End",
            {},
            x_center,
            y,
        )

        add_edge(
            edges,
            current,
            "end",
        )

    # --------------------------------------------------------
    # RETURN WORKFLOW REPRESENTATION
    # --------------------------------------------------------

    return {
        "workflow_name":
            state.goal
            or "Generated Workflow",

        "status":
            "ready",

        "nodes":
            nodes,

        "edges":
            edges,

        "collected_information":
            {
                "trigger_source":
                    state.trigger_source,

                "monitoring_location":
                    state.monitoring_location,

                "notification_channel":
                    state.notification_channel,

                "notification_recipient":
                    state.notification_recipient,

                "duplicate_handling":
                    state.duplicate_handling,

                "additional_requirements":
                    state.additional_requirements,
            },
    }