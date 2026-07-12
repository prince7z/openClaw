# Google Calendar & Tasks Integration Tools Description

This document defines guidelines for the OpenClaw agent planner on when and how to use the Google Calendar & Tasks tool suite.

## Calendar Tools List

1. **`calendar.list_events`**
   - **When to use**: To check the schedule or get upcoming meetings.
   - **Common scenarios**:
     - Check today's schedule: Set `start` to today's start (e.g. `2026-07-12T00:00:00Z`) and `end` to today's end (e.g. `2026-07-12T23:59:59Z`).
     - What is my next meeting: Set `limit=1` without passing a start/end (defaults to upcoming events from now).
   - **Parameters**: `start`, `end`, `limit`, `calendar_id`.

2. **`calendar.search`**
   - **When to use**: To find specific meetings or appointments by matching keyword queries (e.g. "interview", "dentist", or participant names).
   - **Parameters**: `query`, `limit`, `calendar_id`.

3. **`calendar.free_busy`**
   - **When to use**: To check user availability (busy time intervals) across a time range before scheduling or updating a meeting.
   - **Parameters**: `start`, `end`, `calendar_ids`.

4. **`calendar.create_event`**
   - **When to use**: To schedule a standard new event with options for description, location, attendees, and custom reminder overrides (e.g. popups or emails).
   - **Parameters**: `summary`, `start`, `end`, `description`, `location`, `attendees`, `reminders`, `calendar_id`.

5. **`calendar.create_recurring_event`**
   - **When to use**: To schedule recurring events (e.g. daily, weekly, monthly, or yearly repeats) using a recurrence rule (RRULE).
   - **Parameters**: `summary`, `start`, `end`, `recurrence_rule`, `description`, `location`, `attendees`, `reminders`, `calendar_id`.

6. **`calendar.create_meet_event`**
   - **When to use**: To schedule a meeting that automatically generates a Google Meet video conference link.
   - **Parameters**: `summary`, `start`, `end`, `description`, `location`, `attendees`, `reminders`, `calendar_id`.

7. **`calendar.update_event`**
   - **When to use**: To update properties (time, title, description, reminders, etc.) of an existing calendar event (uses patch/partial updates).
   - **Parameters**: `event_id`, `summary`, `start`, `end`, `description`, `location`, `attendees`, `reminders`, `calendar_id`.

8. **`calendar.add_attendees` / `calendar.remove_attendees`**
   - **When to use**: To invite or remove participants from an existing meeting without overwriting other details.
   - **Parameters**: `event_id`, `emails`, `calendar_id`.

9. **`calendar.delete_event`**
   - **When to use**: To cancel or remove an event.
   - **Parameters**: `event_id`, `calendar_id`.

10. **`calendar.list_shared_calendars`**
    - **When to use**: To discover secondary or shared calendars the user has access to.
    - **Parameters**: None.

---

## Tasks Tools List

1. **`calendar.list_tasks`**
   - **When to use**: To check pending or completed tasks.
   - **Parameters**: `limit`, `tasklist_id`.

2. **`calendar.create_task`**
   - **When to use**: To add a new task with optional description/notes and due dates.
   - **Parameters**: `title`, `notes`, `due`, `tasklist_id`.

3. **`calendar.update_task`**
   - **When to use**: To modify a task's title, notes, due date, or mark it completed (by passing `status="completed"`).
   - **Parameters**: `task_id`, `title`, `notes`, `status`, `due`, `tasklist_id`.

4. **`calendar.delete_task`**
   - **When to use**: To delete a task.
   - **Parameters**: `task_id`, `tasklist_id`.
