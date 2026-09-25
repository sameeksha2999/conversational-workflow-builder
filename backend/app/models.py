from typing import List, Optional

from pydantic import BaseModel, Field


class WorkflowItem(BaseModel):
    name: str
    details: str = ""


class ConditionItem(BaseModel):
    name: str
    details: str = ""
    if_true: List[WorkflowItem] = Field(default_factory=list)
    if_false: List[WorkflowItem] = Field(default_factory=list)


class WorkflowState(BaseModel):
    goal: Optional[str] = None
    trigger: Optional[WorkflowItem] = None
    trigger_source: Optional[str] = None
    monitoring_location: Optional[str] = None
    actions: List[WorkflowItem] = Field(default_factory=list)
    conditions: List[ConditionItem] = Field(default_factory=list)
    notifications: List[WorkflowItem] = Field(default_factory=list)
    notification_channel: Optional[str] = None
    notification_recipient: Optional[str] = None
    duplicate_handling: Optional[str] = None
    additional_requirements: List[str] = Field(default_factory=list)

    # AI planning state
    required_fields: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    asked_questions: List[str] = Field(default_factory=list)
    status: str = "collecting"


class ChatRequest(BaseModel):
    message: str
    state: WorkflowState


class ChatResponse(BaseModel):
    reply: str
    state: WorkflowState
    workflow: Optional[dict] = None


class AIAnalysis(BaseModel):
    goal: Optional[str] = None
    trigger: Optional[WorkflowItem] = None
    trigger_source: Optional[str] = None
    monitoring_location: Optional[str] = None
    actions: List[WorkflowItem] = Field(default_factory=list)
    conditions: List[ConditionItem] = Field(default_factory=list)
    notifications: List[WorkflowItem] = Field(default_factory=list)
    notification_channel: Optional[str] = None
    notification_recipient: Optional[str] = None
    duplicate_handling: Optional[str] = None
    additional_requirements: List[str] = Field(default_factory=list)

    # Canonical planning fields returned by the model
    required_fields: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    next_question: str = ""
    is_complete: bool = False
