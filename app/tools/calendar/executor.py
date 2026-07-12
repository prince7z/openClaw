"""Calendar API request execution middleware with logging, retries, and error normalization."""

import json
import logging
import time
from typing import Any, Callable
from googleapiclient.errors import HttpError

from app.integrations.calendar.service import get_calendar_service, get_tasks_service
from app.tools.calendar.logger import log_calendar_stage

logger = logging.getLogger("openclaw-agent")


def execute_calendar_request(
    action_name: str,
    details: dict[str, Any],
    service_type: str,
    api_call_func: Callable[..., Any],
    *args: Any,
    **kwargs: Any
) -> dict[str, Any]:
    """Execute Calendar or Tasks API requests with logging, retries, and error mapping.

    Args:
        action_name: The action name (e.g. 'Search', 'List', 'Create').
        details: Metadata fields to display in Rich logging.
        service_type: Which client is required ('calendar' or 'tasks').
        api_call_func: The callable API request function.
        *args: Variable arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        A dictionary containing the parsed JSON result, or a structured error dictionary.
    """
    log_calendar_stage(action_name, details)
    start_time = time.time()
    max_retries = 2

    # Retrieve target client service resource
    try:
        if service_type.lower() == "tasks":
            service = get_tasks_service()
        else:
            service = get_calendar_service()
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Google service not connected: {exc}"
        logger.error(f"Google Calendar {action_name} failed after {duration_ms}ms: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            # Execute target API call passing the service object as first parameter
            result = api_call_func(service, *args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"Google Calendar {action_name} executed successfully in {duration_ms}ms.")
            return result
        except HttpError as exc:
            last_error = exc
            status_code = exc.resp.status
            # Auto-retry on rate limits (429) or temporary server errors (5xx)
            if status_code in [429, 500, 502, 503, 504] and attempt < max_retries:
                sleep_time = 1.0 * (attempt + 1)
                logger.warning(f"Google Calendar API error {status_code} during {action_name}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            break
        except Exception as exc:
            last_error = exc
            break

    duration_ms = int((time.time() - start_time) * 1000)
    error_msg = str(last_error)

    # Parse native error message if HttpError
    if isinstance(last_error, HttpError):
        try:
            content_decoded = last_error.content.decode("utf-8", errors="ignore")
            error_data = json.loads(content_decoded)
            error_msg = error_data.get("error", {}).get("message", error_msg)
        except Exception:
            pass

    logger.error(f"Google Calendar {action_name} failed after {duration_ms}ms: {error_msg}")
    return {
        "success": False,
        "error": error_msg
    }
