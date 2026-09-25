import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import ConditionItem, WorkflowItem, WorkflowState
from app.workflow import generate_workflow


def test_linear_workflow():
    state = WorkflowState(
        goal="Process new tickets",
        trigger=WorkflowItem(name="New ticket"),
        actions=[WorkflowItem(name="Assign ticket")],
    )
    workflow = generate_workflow(state)
    assert [n["id"] for n in workflow["nodes"]] == ["trigger", "action_1", "end"]


def test_branching_workflow():
    state = WorkflowState(
        goal="Process invoices",
        trigger=WorkflowItem(name="New invoice"),
        conditions=[
            ConditionItem(
                name="Amount > 10000",
                details="If amount is greater than 10000",
                if_true=[WorkflowItem(name="Send alert")],
                if_false=[WorkflowItem(name="Archive")],
            )
        ],
    )
    workflow = generate_workflow(state)
    ids = {node["id"] for node in workflow["nodes"]}
    assert "condition_1" in ids
    assert "condition_1_yes_1" in ids
    assert "condition_1_no_1" in ids
    assert "end" in ids
    assert any(edge.get("label") == "YES" for edge in workflow["edges"])
    assert any(edge.get("label") == "NO" for edge in workflow["edges"])
