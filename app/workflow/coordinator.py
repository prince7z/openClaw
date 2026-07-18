import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Set, Optional

from app.workflow.repository.models import (
    ExecutionSession, SessionTask, SessionStep,
    SessionStatus, TaskStatus, StepStatus, StepType
)
from app.workflow.repository.db import WorkflowRepository
from app.workflow.graph import ExecutionGraph
from app.workflow.engine.scheduler import TopologicalScheduler
from app.workflow.engine.state_machine import validate_step_transition, validate_task_transition, validate_session_transition
from app.workflow.context.store import VariableStore, ArtifactStore
from app.workflow.events.asyncio_bus import AsyncioEventBus

from app.workflow.engine.resource import ResourceLockManager

# Import basic Phase 1 executors
from app.workflow.executors.tool import ToolExecutor
from app.workflow.executors.reasoner import ReasonerExecutor

logger = logging.getLogger("openclaw-workflow-coordinator")

class ExecutionCoordinator:
    """The brain of the workflow engine.
    
    Coordinates Graph updates, execution locks, Event Bus wake-ups,
    state transition validations, and dispatches to step executors.
    """
    def __init__(self, event_bus: Optional[AsyncioEventBus] = None):
        self.event_bus = event_bus or AsyncioEventBus()
        self.resource_manager = ResourceLockManager()
        self._lock = asyncio.Lock()
        self._active_sessions: Set[str] = set()

    async def run_session(self, session_id: str) -> None:
        """Starts the run loop for an execution session. Blocks until complete or failed."""
        async with self._lock:
            if session_id in self._active_sessions:
                logger.warning(f"Session {session_id} is already running.")
                return
            self._active_sessions.add(session_id)

        # 1. Fetch Session from DB and validate transition PENDING -> RUNNING
        sess_data = await WorkflowRepository.get_session(session_id)
        if not sess_data:
            raise ValueError(f"Session '{session_id}' not found in database.")

        curr_status = SessionStatus(sess_data["status"])
        validate_session_transition(curr_status, SessionStatus.RUNNING)
        
        await WorkflowRepository.update_session_status(session_id, SessionStatus.RUNNING)
        await WorkflowRepository.add_trace(
            session_id=session_id,
            target_type="SESSION",
            target_id=session_id,
            event_type="STATE_TRANSITION",
            message=f"Session transitioned from PENDING to RUNNING."
        )

        logger.info(f"Starting workflow execution session: {session_id}")

        # 2. Setup event listener for tick wakeups
        wake_topic = f"session:{session_id}:wake"
        tick_task = None
        session_done_event = asyncio.Event()

        async def listen_for_ticks():
            try:
                async for event in self.event_bus.subscribe(wake_topic):
                    await self._tick(session_id, session_done_event)
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.error(f"Error in tick listener for session {session_id}: {exc}")

        tick_task = asyncio.create_task(listen_for_ticks())

        # Yield control briefly to ensure the background listener subscribes to the event bus
        await asyncio.sleep(0.01)

        # 3. Trigger initial tick directly
        await self._tick(session_id, session_done_event)

        # 4. Wait until the session completes or fails
        await session_done_event.wait()

        # 5. Clean up tick listener
        if tick_task:
            tick_task.cancel()
            try:
                await tick_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            self._active_sessions.discard(session_id)

        logger.info(f"Execution session {session_id} execution finished.")

    async def _tick(self, session_id: str, session_done_event: asyncio.Event) -> None:
        """Executes a single topological scheduling pass over the graph."""
        async with self._lock:
            graph = await WorkflowRepository.load_graph(session_id)
            if not graph:
                logger.error(f"Failed to load graph for session {session_id} in tick.")
                return

            # 1. Update task and session states first
            await self._update_container_states(session_id, graph, session_done_event)
            if session_done_event.is_set():
                return

            # 2. Get ready steps from Scheduler
            ready_steps = TopologicalScheduler.get_ready_steps(graph, self.resource_manager._active_locks)
            logger.debug(f"Tick found {len(ready_steps)} ready steps for session {session_id}.")

            for step in ready_steps:
                # Acquire locks
                if not self.resource_manager.acquire_all(step.resources):
                    logger.debug(f"Step '{step.name}' required capabilities {step.resources} are locked, deferring.")
                    continue
                
                # Transition step state: PENDING -> READY -> RUNNING
                validate_step_transition(step.status, StepStatus.READY)
                await WorkflowRepository.update_step_status(step.id, StepStatus.READY)
                
                validate_step_transition(StepStatus.READY, StepStatus.RUNNING)
                step.status = StepStatus.RUNNING
                await WorkflowRepository.update_step_status(step.id, StepStatus.RUNNING)
                await WorkflowRepository.add_trace(
                    session_id=session_id,
                    target_type="STEP",
                    target_id=step.id,
                    event_type="STATE_TRANSITION",
                    message=f"Step '{step.name}' transitioned to RUNNING."
                )

                # Dispatch execution asynchronously
                asyncio.create_task(self._execute_step(session_id, step))

    async def _execute_step(self, session_id: str, step: SessionStep) -> None:
        """Asynchronously executes a step, records metrics, updates variables, and publishes a tick event."""
        logger.info(f"Dispatching step '{step.name}' (ID: {step.id}, Type: {step.step_type.value})")
        start_time = datetime.utcnow()
        start_ts = start_time.isoformat()
        
        error_msg = None
        result = None
        status = StepStatus.COMPLETED

        try:
            # 1. Retrieve all current variables for input substitution
            variables = await VariableStore.get_all(session_id)

            # 2. Load the correct plugin executor
            executor = self._get_executor(step, session_id)
            
            # 3. Run execution (wrapping with optional timeout)
            timeout = step.timeout_seconds if step.timeout_seconds > 0 else None
            if timeout:
                result = await asyncio.wait_for(executor.execute(variables), timeout=timeout)
            else:
                result = await executor.execute(variables)

            # 4. Save output variable if configured
            if step.output_key and result is not None:
                # Save to Variable Store
                await VariableStore.put(session_id, step.output_key, result, producer_step_id=step.id)

            logger.info(f"Step '{step.name}' execution completed successfully.")
            
        except asyncio.TimeoutError:
            logger.error(f"Step '{step.name}' timed out after {step.timeout_seconds} seconds.")
            error_msg = f"TimeoutError: Execution exceeded limit of {step.timeout_seconds}s"
            status = StepStatus.FAILED
        except Exception as exc:
            logger.error(f"Step '{step.name}' execution failed with exception: {exc}")
            error_msg = str(exc)
            status = StepStatus.FAILED

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # 5. Handle failure, retries, or save result
        if status == StepStatus.FAILED:
            if step.retry_count < step.max_retries:
                # Retry path: transition back to READY (will execute on next tick)
                new_retry = step.retry_count + 1
                logger.info(f"Retrying step '{step.name}' (Attempt {new_retry}/{step.max_retries}) in 1s...")
                await WorkflowRepository.increment_step_retry(step.id, new_retry)
                validate_step_transition(StepStatus.RUNNING, StepStatus.READY)
                await WorkflowRepository.update_step_status(step.id, StepStatus.READY)
                await WorkflowRepository.add_trace(
                    session_id=session_id,
                    target_type="STEP",
                    target_id=step.id,
                    event_type="STATE_TRANSITION",
                    message=f"Step '{step.name}' failed. Transitioned to READY for retry {new_retry}."
                )
                await asyncio.sleep(1.0) # Wait retry backoff
            else:
                # Terminal Failure
                await WorkflowRepository.update_step_status(step.id, StepStatus.FAILED, error_message=error_msg)
                await WorkflowRepository.add_trace(
                    session_id=session_id,
                    target_type="STEP",
                    target_id=step.id,
                    event_type="STATE_TRANSITION",
                    message=f"Step '{step.name}' failed permanently: {error_msg}"
                )
                # Save step result
                metrics = {
                    "started_at": start_ts,
                    "ended_at": end_time.isoformat(),
                    "duration_ms": duration_ms,
                    "retry_count": step.retry_count
                }
                await WorkflowRepository.save_step_result(step.id, StepStatus.FAILED, None, metrics, error_msg)
                
                # Propagate Failure: skip downstream nodes
                await self._propagate_failure_or_skip(session_id, step.id)
        else:
            # Successful completion
            validate_step_transition(StepStatus.RUNNING, StepStatus.COMPLETED)
            await WorkflowRepository.update_step_status(step.id, StepStatus.COMPLETED)
            await WorkflowRepository.add_trace(
                session_id=session_id,
                target_type="STEP",
                target_id=step.id,
                event_type="STATE_TRANSITION",
                message=f"Step '{step.name}' completed."
            )
            
            output_ref = f"variable:{step.output_key}" if step.output_key else None
            # Retrieve metrics from metadata (like token usage)
            meta = step.metadata
            metrics = {
                "started_at": start_ts,
                "ended_at": end_time.isoformat(),
                "duration_ms": duration_ms,
                "retry_count": step.retry_count,
                "tokens_used": meta.get("tokens_used", 0)
            }
            await WorkflowRepository.save_step_result(step.id, StepStatus.COMPLETED, output_ref, metrics, None)

        # Release capability locks
        async with self._lock:
            self.resource_manager.release_all(step.resources)

        # Trigger tick wakeup
        await self.event_bus.publish(f"session:{session_id}:wake", {"action": "step_done", "step_id": step.id})

    def _get_executor(self, step: SessionStep, session_id: str):
        """Plugin factory maps StepType to its executor class."""
        if step.step_type == StepType.TOOL:
            return ToolExecutor(step, session_id)
        elif step.step_type == StepType.REASONER:
            return ReasonerExecutor(step, session_id)
        # Placeholder mapping for Phase 2 nodes (will be implemented in phase 2)
        elif step.step_type == StepType.CONDITION:
            from app.workflow.executors.condition import ConditionExecutor
            return ConditionExecutor(step, session_id)
        elif step.step_type == StepType.WAIT:
            from app.workflow.executors.wait import WaitExecutor
            return WaitExecutor(step, session_id)
        elif step.step_type == StepType.APPROVAL:
            from app.workflow.executors.approval import ApprovalExecutor
            return ApprovalExecutor(step, session_id)
        elif step.step_type == StepType.PLANNER:
            from app.workflow.executors.planner import PlannerExecutor
            return PlannerExecutor(step, session_id)
        else:
            raise NotImplementedError(f"Executor for type '{step.step_type}' is not implemented.")

    async def _propagate_failure_or_skip(self, session_id: str, failed_step_id: str) -> None:
        """Recursively transitions downstream steps to SKIPPED because parent step failed."""
        graph = await WorkflowRepository.load_graph(session_id)
        if not graph:
            return
            
        skipped_queue = []
        # Find immediate children of the failed step
        for child_id in graph.edges.get(failed_step_id, []):
            skipped_queue.append(child_id)

        # Transitive skip propagation
        visited = set()
        while skipped_queue:
            curr_id = skipped_queue.pop(0)
            if curr_id in visited:
                continue
            visited.add(curr_id)

            step = graph.nodes.get(curr_id)
            if step and step.status in (StepStatus.PENDING, StepStatus.READY):
                validate_step_transition(step.status, StepStatus.SKIPPED)
                step.status = StepStatus.SKIPPED
                await WorkflowRepository.update_step_status(curr_id, StepStatus.SKIPPED)
                await WorkflowRepository.add_trace(
                    session_id=session_id,
                    target_type="STEP",
                    target_id=curr_id,
                    event_type="STATE_TRANSITION",
                    message=f"Step '{step.name}' SKIPPED due to parent step failure."
                )
                
                # Queue children of this skipped step
                for child_id in graph.edges.get(curr_id, []):
                    skipped_queue.append(child_id)

    async def _update_container_states(self, session_id: str, graph: ExecutionGraph, session_done_event: asyncio.Event) -> None:
        """Analyzes active graph step statuses and sets container Task and Session states accordingly."""
        tasks_data = await WorkflowRepository.get_tasks(session_id)
        if not tasks_data:
            return

        # 1. Update Tasks statuses
        # Group steps by task
        steps_by_task: Dict[str, List[SessionStep]] = {}
        for step in graph.nodes.values():
            if step.task_id not in steps_by_task:
                steps_by_task[step.task_id] = []
            steps_by_task[step.task_id].append(step)

        all_tasks_completed = True
        any_task_failed = False

        for t_dict in tasks_data:
            t_id = t_dict["id"]
            curr_status = TaskStatus(t_dict["status"])
            t_steps = steps_by_task.get(t_id, [])

            if not t_steps:
                continue

            # Compute target status based on steps
            step_statuses = [s.status for s in t_steps]
            
            if all(s == StepStatus.PENDING for s in step_statuses):
                target_status = TaskStatus.PENDING
            elif all(s in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in step_statuses):
                target_status = TaskStatus.COMPLETED
            elif any(s == StepStatus.FAILED for s in step_statuses) and not any(s in (StepStatus.RUNNING, StepStatus.WAITING, StepStatus.READY) for s in step_statuses):
                target_status = TaskStatus.FAILED
            elif any(s == StepStatus.WAITING for s in step_statuses):
                target_status = TaskStatus.WAITING
            else:
                target_status = TaskStatus.RUNNING

            if target_status != curr_status:
                validate_task_transition(curr_status, target_status)
                await WorkflowRepository.update_task_status(t_id, target_status)
                await WorkflowRepository.add_trace(
                    session_id=session_id,
                    target_type="TASK",
                    target_id=t_id,
                    event_type="STATE_TRANSITION",
                    message=f"Task '{t_dict['name']}' transitioned to {target_status.value}."
                )
                curr_status = target_status

            if curr_status == TaskStatus.FAILED:
                any_task_failed = True
            if curr_status != TaskStatus.COMPLETED:
                all_tasks_completed = False

        # 2. Check Session completion
        if graph.is_terminal():
            session_status = SessionStatus.COMPLETED
            if any_task_failed or any(s.status == StepStatus.FAILED for s in graph.nodes.values()):
                session_status = SessionStatus.FAILED

            await WorkflowRepository.update_session_status(session_id, session_status)
            await WorkflowRepository.add_trace(
                session_id=session_id,
                target_type="SESSION",
                target_id=session_id,
                event_type="STATE_TRANSITION",
                message=f"Session transitioned to {session_status.value}."
            )
            session_done_event.set()
