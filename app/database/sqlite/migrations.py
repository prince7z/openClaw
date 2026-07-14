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
        await conn.commit()
        logger.info("SQLite database migrations executed successfully.")
    except Exception as exc:
        logger.error(f"Failed to execute database migrations: {exc}")
        raise exc
    finally:
        await conn.close()
