"""Database migrations and table structures setup (Asynchronous)."""

import logging
from app.database.sqlite.database import get_db_connection

logger = logging.getLogger("openclaw-agent")


async def run_migrations() -> None:
    """Execute database creation queries to build active_conversation and chat_archive tables.

    Runs automatically during application initialization lifecycle.
    """
    logger.info("Running SQLite database migrations...")
    conn = await get_db_connection()
    try:
        # Create active_conversation table tracking active session state
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS active_conversation (
                chat_id INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create chat_archive table storing conversation summaries
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_archive (
                conversation_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL
            )
        """)

        # Custom Workflow Engine Tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_sessions (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                definition_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS session_tasks (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES execution_sessions(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS session_steps (
                id TEXT PRIMARY KEY,
                task_id TEXT REFERENCES session_tasks(id) ON DELETE CASCADE,
                session_id TEXT REFERENCES execution_sessions(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                step_type TEXT NOT NULL,
                status TEXT NOT NULL,
                tool_name TEXT,
                planner_prompt TEXT,
                reasoner_prompt TEXT,
                inputs_json TEXT,
                metadata_json TEXT,
                resources_json TEXT,
                output_key TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 0,
                timeout_seconds REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS step_dependencies (
                session_id TEXT REFERENCES execution_sessions(id) ON DELETE CASCADE,
                step_id TEXT REFERENCES session_steps(id) ON DELETE CASCADE,
                depends_on_step_id TEXT REFERENCES session_steps(id) ON DELETE CASCADE,
                PRIMARY KEY (session_id, step_id, depends_on_step_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS session_variables (
                session_id TEXT REFERENCES execution_sessions(id) ON DELETE CASCADE,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                producer_step_id TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (session_id, key)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS step_results (
                step_id TEXT PRIMARY KEY REFERENCES session_steps(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                output_reference TEXT,
                metrics_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT REFERENCES execution_sessions(id) ON DELETE CASCADE,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        # Create indexes to speed up lookups
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_session_tasks_session_id ON session_tasks(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_session_steps_task_id ON session_steps(task_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_session_steps_session_id ON session_steps(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_step_deps_step_id ON step_dependencies(step_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_step_deps_depends_on ON step_dependencies(depends_on_step_id)")

        # Add error_message column dynamically if the table existed before Phase 1 column update
        try:
            await conn.execute("ALTER TABLE session_steps ADD COLUMN error_message TEXT")
        except Exception:
            pass

        await conn.commit()
        logger.info("SQLite database migrations executed successfully.")
    except Exception as exc:
        logger.error(f"Failed to execute database migrations: {exc}")
        raise exc
    finally:
        await conn.close()
