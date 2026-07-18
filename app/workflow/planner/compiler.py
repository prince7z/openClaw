import uuid
import json
import logging
import re
from typing import Dict, Any, List, Union, Tuple
from datetime import datetime

from app.workflow.repository.models import (
    ExecutionSession, SessionTask, SessionStep,
    SessionStatus, TaskStatus, StepStatus, StepType
)
from app.workflow.repository.db import WorkflowRepository
from app.workflow.graph import ExecutionGraph
from app.workflow.engine.validator import GraphValidator

logger = logging.getLogger("openclaw-workflow-compiler")

class WorkflowCompiler:
    """Compiles Workflow JSON definitions into validated ExecutionGraph sessions saved to SQLite."""

    @staticmethod
    async def compile(definition: Union[str, Dict[str, Any]]) -> str:
        """Parses, validates, and persists a workflow definition as an active Execution Session.
        
        Args:
            definition: A dict or raw JSON string representation of the workflow.
            
        Returns:
            The generated session_id.
            
        Raises:
            ValueError: If parsing or structure validation fails.
            ValidationError: If cycle or dependency check fails.
        """
        if isinstance(definition, str):
            try:
                data = json.loads(definition)
            except Exception as exc:
                raise ValueError(f"Failed to parse workflow JSON: {exc}")
        else:
            data = definition

        # Validate top-level schema
        name = data.get("name", "Generated Workflow")
        tasks_list = data.get("tasks")
        if not tasks_list or not isinstance(tasks_list, list):
            raise ValueError("Workflow definition must contain a non-empty list of 'tasks'.")

        session_id = str(uuid.uuid4())
        
        session = ExecutionSession(
            id=session_id,
            status=SessionStatus.PENDING,
            version=1,
            definition_json=json.dumps(data)
        )

        tasks: List[SessionTask] = []
        steps: List[SessionStep] = []
        dependencies: List[Tuple[str, str]] = []

        # Used for DFS cycle verification in-memory before writing to DB
        temp_graph = ExecutionGraph(session_id=session_id)

        # 1. Normalize step IDs to guarantee session-wide uniqueness
        step_id_map = {}
        seen_global_ids = set()
        
        for task_idx, t_data in enumerate(tasks_list):
            t_id_raw = t_data.get("id") or f"task_{task_idx}"
            steps_list = t_data.get("steps") or []
            for step_idx, s_data in enumerate(steps_list):
                s_id_raw = s_data.get("id")
                if not s_id_raw:
                    continue
                
                unique_id = s_id_raw
                counter = 1
                while unique_id in seen_global_ids:
                    unique_id = f"{s_id_raw}_{counter}"
                    counter += 1
                
                seen_global_ids.add(unique_id)
                step_id_map[(t_id_raw, s_id_raw)] = unique_id

        def resolve_dep_id(current_task_id_raw: str, dep_id_raw: str) -> str:
            if (current_task_id_raw, dep_id_raw) in step_id_map:
                return step_id_map[(current_task_id_raw, dep_id_raw)]
            # Check other tasks
            for (t_raw, s_raw), uniq_id in step_id_map.items():
                if s_raw == dep_id_raw:
                    return uniq_id
            return dep_id_raw

        for task_idx, t_data in enumerate(tasks_list):
            t_id_raw = t_data.get("id") or f"task_{task_idx}"
            t_id = f"{session_id}_{t_id_raw}"
            t_name = t_data.get("name") or f"Task {task_idx}"
            
            task = SessionTask(
                id=t_id,
                session_id=session_id,
                name=t_name,
                status=TaskStatus.PENDING
            )
            tasks.append(task)

            steps_list = t_data.get("steps")
            if not steps_list or not isinstance(steps_list, list):
                raise ValueError(f"Task '{t_name}' must contain a list of 'steps'.")

            prev_step_id = None

            for step_idx, s_data in enumerate(steps_list):
                s_id_raw = s_data.get("id")
                if not s_id_raw:
                    raise ValueError(f"Step in task '{t_name}' is missing required field 'id'.")
                
                unique_s_id_raw = step_id_map.get((t_id_raw, s_id_raw), s_id_raw)
                s_id = f"{session_id}_{unique_s_id_raw}"
                s_name = s_data.get("name") or f"Step {step_idx}"
                s_type_str = s_data.get("step_type")
                if not s_type_str:
                    raise ValueError(f"Step '{s_id_raw}' is missing required 'step_type'.")
                
                try:
                    s_type = StepType(s_type_str.upper())
                except ValueError:
                    raise ValueError(f"Invalid step_type '{s_type_str}' for step '{s_id_raw}'.")

                # Parse inputs, metadata, and resources
                inputs = s_data.get("inputs") or {}
                metadata = s_data.get("metadata") or {}
                resources = s_data.get("resources") or []
                
                # Setup retries and timeouts
                max_retries = s_data.get("max_retries", 0)
                timeout_seconds = s_data.get("timeout_seconds", 0.0)

                step = SessionStep(
                    id=s_id,
                    task_id=t_id,
                    session_id=session_id,
                    name=s_name,
                    step_type=s_type,
                    status=StepStatus.PENDING,
                    tool_name=s_data.get("tool_name"),
                    planner_prompt=s_data.get("planner_prompt"),
                    reasoner_prompt=s_data.get("reasoner_prompt"),
                    inputs_json=json.dumps(inputs),
                    metadata_json=json.dumps(metadata),
                    resources_json=json.dumps(resources),
                    output_key=s_data.get("output_key"),
                    retry_count=0,
                    max_retries=max_retries,
                    timeout_seconds=timeout_seconds
                )
                steps.append(step)
                temp_graph.add_node(step)

                # Dependencies handling
                # If explicit depends_on is declared (even if empty list), respect it.
                # If depends_on is omitted, auto-link to previous step in this task (sequential by default).
                if "depends_on" in s_data:
                    deps_list = s_data["depends_on"]
                    if not isinstance(deps_list, list):
                        raise ValueError(f"depends_on for step '{s_id_raw}' must be a list of step IDs.")
                    for dep_id_raw in deps_list:
                        uniq_dep_raw = resolve_dep_id(t_id_raw, dep_id_raw)
                        dep_id = f"{session_id}_{uniq_dep_raw}"
                        dependencies.append((s_id, dep_id))
                        temp_graph.add_dependency(s_id, dep_id)
                else:
                    # Sequential by default: link to preceding step in same task
                    if prev_step_id:
                        dependencies.append((s_id, prev_step_id))
                        temp_graph.add_dependency(s_id, prev_step_id)

                prev_step_id = s_id

        # 4.5 Auto-resolve Dataflow Dependencies (Cross-Task Variable Dependencies)
        output_key_to_step_id = {}
        for s in steps:
            if s.output_key:
                output_key_to_step_id[s.output_key] = s.id

        for s in steps:
            content_to_check = f"{s.inputs_json} {s.reasoner_prompt or ''} {s.planner_prompt or ''}"
            vars_referenced = re.findall(r'\$\{(\w+)\}', content_to_check)
            for ref_var in vars_referenced:
                if ref_var in output_key_to_step_id:
                    producer_id = output_key_to_step_id[ref_var]
                    if producer_id != s.id and (s.id, producer_id) not in dependencies:
                        dependencies.append((s.id, producer_id))
                        temp_graph.add_dependency(s.id, producer_id)

        # 5. Build and Validate the full in-memory graph
        temp_graph.build()
        GraphValidator.validate(temp_graph)

        # 6. Save validated structures to SQLite
        await WorkflowRepository.create_session(session, tasks, steps, dependencies)
        
        # 6.5 Pre-populate system environment variables in VariableStore
        from app.workflow.context.store import VariableStore
        import os
        import pathlib
        
        home = str(pathlib.Path.home())
        desktop = os.path.join(home, "Desktop")
        if not os.path.exists(desktop):
            desktop = os.path.join(home, "OneDrive", "Desktop")
            
        sys_vars = {
            "user_home": home,
            "desktop_path": desktop,
            "workspace_path": os.getcwd()
        }
        for k, v in sys_vars.items():
            await VariableStore.put(session_id, k, v, producer_step_id="SYSTEM")
        
        # Add initial trace
        await WorkflowRepository.add_trace(
            session_id=session_id,
            target_type="SESSION",
            target_id=session_id,
            event_type="MUTATION",
            message=f"Session compiled and initialized. Initial version v1 created."
        )

        return session_id
