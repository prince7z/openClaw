"""Google Tasks tools implementation."""

from typing import Any, Literal
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


# Internal helper function, not exposed as tool
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





@tool("calendar_manage_task")
def manage_task(
    action: Literal["create", "update", "delete"],
    task_id: str | None = None,
    task: dict | None = None,
) -> dict[str, Any]:
    """Create, update, or delete tasks."""
    try:
        if action == "create":
            if not task:
                return {"success": False, "error": "task dictionary is required for create action", "data": None}
            title = task.get("title")
            if not title:
                return {"success": False, "error": "title is required in task dictionary for create action", "data": None}
            
            notes = task.get("notes")
            due = task.get("due")
            
            details = {
                "Task Title": title,
                "Tasklist ID": "@default",
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
                "@default"
            )

        elif action == "update":
            if not task_id:
                return {"success": False, "error": "task_id is required for update action", "data": None}
            if not task:
                return {"success": False, "error": "task dictionary is required for update action", "data": None}
            
            title = task.get("title")
            notes = task.get("notes")
            status = task.get("status")
            due = task.get("due")
            
            details = {
                "Task ID": task_id,
                "Tasklist ID": "@default",
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
                "@default"
            )

        elif action == "delete":
            if not task_id:
                return {"success": False, "error": "task_id is required for delete action", "data": None}
            details = {
                "Task ID": task_id,
                "Tasklist ID": "@default"
            }
            return execute_calendar_request(
                "Task",
                details,
                "tasks",
                _api_delete_task,
                task_id,
                "@default"
            )

        else:
            return {"success": False, "error": f"Unsupported action: {action}", "data": None}
    except Exception as exc:
        return {"success": False, "error": str(exc), "data": None}
