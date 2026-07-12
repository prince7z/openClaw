"""Google Tasks tools implementation."""

from typing import Any
from langchain.tools import tool

from app.tools.calendar.executor import execute_calendar_request
from app.tools.calendar.schemas import Task, TaskResponse


def _api_list_tasks(
    service: Any,
    limit: int,
    tasklist_id: str
) -> dict[str, Any]:
    """Execute raw Tasks list query.

    Args:
        service: Authenticated Google Tasks client.
        limit: Limit of results.
        tasklist_id: The ID of the task list.

    Returns:
        A TaskResponse dictionary.
    """
    res = service.tasks().list(
        tasklist=tasklist_id,
        maxResults=limit
    ).execute()

    items = res.get("items") or []

    tasks = []
    for item in items:
        tasks.append(
            Task(
                id=item.get("id", ""),
                title=item.get("title") or "(No Title)",
                notes=item.get("notes"),
                status=item.get("status", "needsAction"),
                due=item.get("due"),
                completed=item.get("completed")
            )
        )

    response = TaskResponse(
        success=True,
        tasks=tasks
    )
    return response.model_dump()


def _api_create_task(
    service: Any,
    title: str,
    notes: str | None,
    due: str | None,
    tasklist_id: str
) -> dict[str, Any]:
    """Execute raw Tasks insert query.

    Args:
        service: Authenticated Google Tasks client.
        title: Task title.
        notes: Task notes/description.
        due: Task due date (RFC3339 string).
        tasklist_id: The ID of the task list.

    Returns:
        A TaskResponse dictionary.
    """
    body: dict[str, Any] = {"title": title}
    if notes is not None:
        body["notes"] = notes
    if due is not None:
        body["due"] = due

    created = service.tasks().insert(
        tasklist=tasklist_id,
        body=body
    ).execute()

    task = Task(
        id=created.get("id", ""),
        title=created.get("title") or "(No Title)",
        notes=created.get("notes"),
        status=created.get("status", "needsAction"),
        due=created.get("due"),
        completed=created.get("completed")
    )

    response = TaskResponse(
        success=True,
        task=task
    )
    return response.model_dump()


def _api_update_task(
    service: Any,
    task_id: str,
    title: str | None,
    notes: str | None,
    status: str | None,
    due: str | None,
    tasklist_id: str
) -> dict[str, Any]:
    """Execute raw Tasks patch query.

    Args:
        service: Authenticated Google Tasks client.
        task_id: The ID of the task to update.
        title: Optional updated title.
        notes: Optional updated notes.
        status: Optional updated status ('needsAction' or 'completed').
        due: Optional updated due date.
        tasklist_id: The ID of the task list.

    Returns:
        A TaskResponse dictionary.
    """
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if notes is not None:
        body["notes"] = notes
    if status is not None:
        body["status"] = status
    if due is not None:
        body["due"] = due

    patched = service.tasks().patch(
        tasklist=tasklist_id,
        task=task_id,
        body=body
    ).execute()

    task = Task(
        id=patched.get("id", ""),
        title=patched.get("title") or "(No Title)",
        notes=patched.get("notes"),
        status=patched.get("status", "needsAction"),
        due=patched.get("due"),
        completed=patched.get("completed")
    )

    response = TaskResponse(
        success=True,
        task=task
    )
    return response.model_dump()


def _api_delete_task(
    service: Any,
    task_id: str,
    tasklist_id: str
) -> dict[str, Any]:
    """Execute raw Tasks delete query.

    Args:
        service: Authenticated Google Tasks client.
        task_id: The ID of the task to delete.
        tasklist_id: The ID of the task list.

    Returns:
        A TaskResponse dictionary.
    """
    service.tasks().delete(
        tasklist=tasklist_id,
        task=task_id
    ).execute()

    response = TaskResponse(
        success=True
    )
    return response.model_dump()


@tool("calendar.list_tasks")
def calendar_list_tasks(
    limit: int = 15,
    tasklist_id: str = "@default"
) -> dict[str, Any]:
    """Retrieve lists of pending or completed tasks.

    Args:
        limit: Max results count. Defaults to 15.
        tasklist_id: The ID of the task list. Defaults to '@default' (the user's primary list).

    Returns:
        A dict containing success state and list of parsed Tasks.
    """
    details = {
        "Tasklist ID": tasklist_id,
        "Limit": limit
    }
    return execute_calendar_request(
        "Task",
        details,
        "tasks",
        _api_list_tasks,
        limit,
        tasklist_id
    )


@tool("calendar.create_task")
def calendar_create_task(
    title: str,
    notes: str | None = None,
    due: str | None = None,
    tasklist_id: str = "@default"
) -> dict[str, Any]:
    """Create a new task in a tasks list.

    Args:
        title: The title/subject of the task.
        notes: Optional details or notes for the task.
        due: Optional RFC3339 date-time string indicating when the task is due (e.g. '2026-07-13T12:00:00Z').
        tasklist_id: The ID of the task list. Defaults to '@default'.

    Returns:
        A dict containing success state and created Task details.
    """
    details = {
        "Task Title": title,
        "Tasklist ID": tasklist_id,
        "Due Date": due or "None"
    }
    return execute_calendar_request(
        "Task",
        details,
        "tasks",
        _api_create_task,
        title,
        notes,
        due,
        tasklist_id
    )


@tool("calendar.update_task")
def calendar_update_task(
    task_id: str,
    title: str | None = None,
    notes: str | None = None,
    status: str | None = None,
    due: str | None = None,
    tasklist_id: str = "@default"
) -> dict[str, Any]:
    """Update details or status of an existing task (e.g., mark as completed).

    Args:
        task_id: The unique ID of the task to update.
        title: Optional updated title/subject.
        notes: Optional updated details.
        status: Optional updated status ('needsAction' or 'completed').
        due: Optional updated due date in RFC3339 format.
        tasklist_id: The ID of the task list. Defaults to '@default'.

    Returns:
        A dict containing success state and updated Task details.
    """
    details = {
        "Task ID": task_id,
        "Tasklist ID": tasklist_id,
        "Update Title": title or "No Change",
        "Update Status": status or "No Change"
    }
    return execute_calendar_request(
        "Task",
        details,
        "tasks",
        _api_update_task,
        task_id,
        title,
        notes,
        status,
        due,
        tasklist_id
    )


@tool("calendar.delete_task")
def calendar_delete_task(
    task_id: str,
    tasklist_id: str = "@default"
) -> dict[str, Any]:
    """Delete a task from a tasks list.

    Args:
        task_id: The unique ID of the task to delete.
        tasklist_id: The ID of the task list. Defaults to '@default'.

    Returns:
        A dict containing success state.
    """
    details = {
        "Task ID": task_id,
        "Tasklist ID": tasklist_id
    }
    return execute_calendar_request(
        "Task",
        details,
        "tasks",
        _api_delete_task,
        task_id,
        tasklist_id
    )
