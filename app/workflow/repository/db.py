import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional
import aiosqlite

from app.database.sqlite.database import get_db_connection
from app.workflow.repository.models import (
    ExecutionSession, SessionTask, SessionStep,
    SessionStatus, TaskStatus, StepStatus, StepType
)
from app.workflow.graph import ExecutionGraph

logger = logging.getLogger("openclaw-workflow-db")

class WorkflowRepository:
    """Manages raw SQL operations for reading and writing workflow state tables in SQLite."""

    @staticmethod
    async def create_session(
        session: ExecutionSession,
        tasks: List[SessionTask],
        steps: List[SessionStep],
        dependencies: List[Tuple[str, str]]
    ) -> None:
        """Inserts a new execution session, its tasks, steps, and dependencies into SQLite."""
        now = datetime.utcnow().isoformat()
        conn = await get_db_connection()
        try:
            await conn.execute("BEGIN TRANSACTION")
            
            # 1. Insert Session
            await conn.execute(
                """
                INSERT INTO execution_sessions (id, status, version, definition_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session.id, session.status.value, session.version, session.definition_json, now, now)
            )

            # 2. Insert Tasks
            for t in tasks:
                await conn.execute(
                    """
                    INSERT INTO session_tasks (id, session_id, name, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (t.id, t.session_id, t.name, t.status.value, now, now)
                )

            # 3. Insert Steps
            for s in steps:
                await conn.execute(
                    """
                    INSERT INTO session_steps (
                        id, task_id, session_id, name, step_type, status,
                        tool_name, planner_prompt, reasoner_prompt, inputs_json,
                        metadata_json, resources_json, output_key, retry_count,
                        max_retries, timeout_seconds, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s.id, s.task_id, s.session_id, s.name, s.step_type.value, s.status.value,
                        s.tool_name, s.planner_prompt, s.reasoner_prompt, s.inputs_json,
                        s.metadata_json, s.resources_json, s.output_key, s.retry_count,
                        s.max_retries, s.timeout_seconds, now, now
                    )
                )

            # 4. Insert Dependencies
            for step_id, depends_on_id in dependencies:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO step_dependencies (session_id, step_id, depends_on_step_id)
                    VALUES (?, ?, ?)
                    """,
                    (session.id, step_id, depends_on_id)
                )

            await conn.commit()
            logger.info(f"Successfully initialized workflow session {session.id} in DB.")
        except Exception as exc:
            await conn.rollback()
            logger.error(f"Failed to create session transaction: {exc}")
            raise exc
        finally:
            await conn.close()

    @staticmethod
    async def load_graph(session_id: str) -> Optional[ExecutionGraph]:
        """Loads and rebuilds an ExecutionGraph from SQLite for a given session ID."""
        conn = await get_db_connection()
        try:
            conn.row_factory = aiosqlite.Row
            
            # 1. Fetch Session Version
            async with conn.execute(
                "SELECT version FROM execution_sessions WHERE id = ?",
                (session_id,)
            ) as cursor:
                sess_row = await cursor.fetchone()
                if not sess_row:
                    return None
                version = sess_row["version"]

            graph = ExecutionGraph(session_id=session_id, version=version)

            # 2. Fetch Steps
            async with conn.execute(
                "SELECT * FROM session_steps WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                step_rows = await cursor.fetchall()
                for r in step_rows:
                    step = SessionStep(
                        id=r["id"],
                        task_id=r["task_id"],
                        session_id=r["session_id"],
                        name=r["name"],
                        step_type=StepType(r["step_type"]),
                        status=StepStatus(r["status"]),
                        tool_name=r["tool_name"],
                        planner_prompt=r["planner_prompt"],
                        reasoner_prompt=r["reasoner_prompt"],
                        inputs_json=r["inputs_json"],
                        metadata_json=r["metadata_json"],
                        resources_json=r["resources_json"],
                        output_key=r["output_key"],
                        retry_count=r["retry_count"],
                        max_retries=r["max_retries"],
                        timeout_seconds=r["timeout_seconds"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"]
                    )
                    graph.add_node(step)

            # 3. Fetch Dependencies
            async with conn.execute(
                "SELECT step_id, depends_on_step_id FROM step_dependencies WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                dep_rows = await cursor.fetchall()
                for r in dep_rows:
                    graph.add_dependency(
                        step_id=r["step_id"],
                        depends_on_step_id=r["depends_on_step_id"]
                    )

            graph.build()
            return graph
        except Exception as exc:
            logger.error(f"Failed to load execution graph for session {session_id}: {exc}")
            raise exc
        finally:
            await conn.close()

    @staticmethod
    async def update_step_status(step_id: str, status: StepStatus, error_message: Optional[str] = None) -> None:
        now = datetime.utcnow().isoformat()
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                UPDATE session_steps
                SET status = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.value, error_message, now, step_id)
            )
            await conn.commit()
        finally:
            await conn.close()

    @staticmethod
    async def increment_step_retry(step_id: str, retry_count: int) -> None:
        now = datetime.utcnow().isoformat()
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                UPDATE session_steps
                SET retry_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (retry_count, now, step_id)
            )
            await conn.commit()
        finally:
            await conn.close()

    @staticmethod
    async def update_task_status(task_id: str, status: TaskStatus) -> None:
        now = datetime.utcnow().isoformat()
        conn = await get_db_connection()
        try:
            await conn.execute(
                "UPDATE session_tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now, task_id)
            )
            await conn.commit()
        finally:
            await conn.close()

    @staticmethod
    async def update_session_status(session_id: str, status: SessionStatus) -> None:
        now = datetime.utcnow().isoformat()
        conn = await get_db_connection()
        try:
            await conn.execute(
                "UPDATE execution_sessions SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now, session_id)
            )
            await conn.commit()
        finally:
            await conn.close()

    @staticmethod
    async def update_session_version(session_id: str, version: int) -> None:
        now = datetime.utcnow().isoformat()
        conn = await get_db_connection()
        try:
            await conn.execute(
                "UPDATE execution_sessions SET version = ?, updated_at = ? WHERE id = ?",
                (version, now, session_id)
            )
            await conn.commit()
        finally:
            await conn.close()

    @staticmethod
    async def save_step_result(
        step_id: str,
        status: StepStatus,
        output_reference: Optional[str],
        metrics: Dict[str, Any],
        error: Optional[str]
    ) -> None:
        now = datetime.utcnow().isoformat()
        metrics_json = json.dumps(metrics)
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                INSERT OR REPLACE INTO step_results (step_id, status, output_reference, metrics_json, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (step_id, status.value, output_reference, metrics_json, error, now)
            )
            await conn.commit()
        finally:
            await conn.close()

    @staticmethod
    async def add_trace(
        session_id: str,
        target_type: str,
        target_id: str,
        event_type: str,
        message: str
    ) -> None:
        now = datetime.utcnow().isoformat()
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                INSERT INTO execution_traces (session_id, target_type, target_id, event_type, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, target_type, target_id, event_type, message, now)
            )
            await conn.commit()
        finally:
            await conn.close()

    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        conn = await get_db_connection()
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM execution_sessions WHERE id = ?",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        finally:
            await conn.close()
        return None

    @staticmethod
    async def get_steps(session_id: str) -> List[Dict[str, Any]]:
        conn = await get_db_connection()
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM session_steps WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        finally:
            await conn.close()
        return []

    @staticmethod
    async def get_tasks(session_id: str) -> List[Dict[str, Any]]:
        conn = await get_db_connection()
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM session_tasks WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        finally:
            await conn.close()
        return []

    @staticmethod
    async def get_traces(session_id: str) -> List[Dict[str, Any]]:
        conn = await get_db_connection()
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM execution_traces WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        finally:
            await conn.close()
        return []
