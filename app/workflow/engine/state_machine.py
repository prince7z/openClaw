from typing import Dict, Set
from app.workflow.repository.models import StepStatus, TaskStatus, SessionStatus

class InvalidStateTransition(ValueError):
    """Raised when an invalid state transition is attempted in the workflow engine."""
    pass

# Transition tables mapping a status to its set of legal next statuses
STEP_TRANSITIONS: Dict[StepStatus, Set[StepStatus]] = {
    StepStatus.PENDING: {StepStatus.READY, StepStatus.SKIPPED},
    StepStatus.READY: {StepStatus.RUNNING, StepStatus.SKIPPED},
    StepStatus.RUNNING: {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.WAITING, StepStatus.READY},
    StepStatus.WAITING: {StepStatus.READY, StepStatus.RUNNING, StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED},
    StepStatus.FAILED: {StepStatus.READY},  # Allowed for retries
    StepStatus.COMPLETED: set(),           # Terminal
    StepStatus.SKIPPED: set(),             # Terminal
}

TASK_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.WAITING},
    TaskStatus.WAITING: {TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),           # Terminal
    TaskStatus.FAILED: set(),              # Terminal
}

SESSION_TRANSITIONS: Dict[SessionStatus, Set[SessionStatus]] = {
    SessionStatus.PENDING: {SessionStatus.RUNNING, SessionStatus.COMPLETED, SessionStatus.FAILED},
    SessionStatus.RUNNING: {SessionStatus.COMPLETED, SessionStatus.FAILED},
    SessionStatus.COMPLETED: set(),        # Terminal
    SessionStatus.FAILED: set(),           # Terminal
}

def validate_step_transition(current: StepStatus, target: StepStatus) -> None:
    """Enforce step state transition table constraints.
    
    Raises:
        InvalidStateTransition: If the transition is illegal.
    """
    if current == target:
        return
    allowed = STEP_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"Step transition from '{current.value}' to '{target.value}' is illegal."
        )

def validate_task_transition(current: TaskStatus, target: TaskStatus) -> None:
    """Enforce task state transition table constraints.
    
    Raises:
        InvalidStateTransition: If the transition is illegal.
    """
    if current == target:
        return
    allowed = TASK_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"Task transition from '{current.value}' to '{target.value}' is illegal."
        )

def validate_session_transition(current: SessionStatus, target: SessionStatus) -> None:
    """Enforce session state transition table constraints.
    
    Raises:
        InvalidStateTransition: If the transition is illegal.
    """
    if current == target:
        return
    allowed = SESSION_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"Session transition from '{current.value}' to '{target.value}' is illegal."
        )
