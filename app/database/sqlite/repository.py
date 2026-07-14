"""SQLite Database Repository Pattern implementing single-responsibility queries."""

import aiosqlite
import logging
from datetime import datetime
from typing import Any
from app.database.sqlite.database import get_db_connection

logger = logging.getLogger("openclaw-agent")


async def get_active(chat_id: int) -> dict[str, Any] | None:
    """Retrieve the active conversation state row for the specified chat ID.

    Args:
        chat_id: The unique identifier of the chat.

    Returns:
        A dictionary of the row contents if present, else None.
    """
    conn = await get_db_connection()
    try:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT chat_id, state_json, created_at, updated_at FROM active_conversation WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    finally:
        await conn.close()
    return None


async def create_active(chat_id: int, state_json: str) -> None:
    """Insert a new active conversation state record.

    Args:
        chat_id: Chat identifier.
        state_json: Opaque serialized AgentState block.
    """
    now = datetime.utcnow().isoformat()
    conn = await get_db_connection()
    try:
        await conn.execute(
            "INSERT INTO active_conversation (chat_id, state_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (chat_id, state_json, now, now)
        )
        await conn.commit()
    finally:
        await conn.close()


async def update_active(chat_id: int, state_json: str) -> None:
    """Update the serialized state block of an existing active conversation.

    Args:
        chat_id: Chat identifier.
        state_json: Serialized state block.
    """
    now = datetime.utcnow().isoformat()
    conn = await get_db_connection()
    try:
        await conn.execute(
            "UPDATE active_conversation SET state_json = ?, updated_at = ? WHERE chat_id = ?",
            (state_json, now, chat_id)
        )
        await conn.commit()
    finally:
        await conn.close()


async def delete_active(chat_id: int) -> None:
    """Remove the active conversation state record.

    Args:
        chat_id: Chat identifier.
    """
    conn = await get_db_connection()
    try:
        await conn.execute(
            "DELETE FROM active_conversation WHERE chat_id = ?",
            (chat_id,)
        )
        await conn.commit()
    finally:
        await conn.close()


async def exists(chat_id: int) -> bool:
    """Check if an active conversation state record exists for this chat ID.

    Args:
        chat_id: Chat identifier.

    Returns:
        True if exists, else False.
    """
    conn = await get_db_connection()
    try:
        async with conn.execute(
            "SELECT 1 FROM active_conversation WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None
    finally:
        await conn.close()


async def list_archives(chat_id: int) -> list[dict[str, Any]]:
    """Retrieve all archived conversation summaries for the specified chat ID.

    Args:
        chat_id: Chat identifier.

    Returns:
        A list of archived row dictionaries.
    """
    conn = await get_db_connection()
    try:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT conversation_id, chat_id, title, summary, started_at, ended_at FROM chat_archive WHERE chat_id = ? ORDER BY ended_at DESC",
            (chat_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_archive(conversation_id: str) -> dict[str, Any] | None:
    """Retrieve an archived conversation summary by its UUID string.

    Args:
        conversation_id: Unique UUID string representation.

    Returns:
        A dictionary of the archived row if present, else None.
    """
    conn = await get_db_connection()
    try:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT conversation_id, chat_id, title, summary, started_at, ended_at FROM chat_archive WHERE conversation_id = ?",
            (conversation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    finally:
        await conn.close()
    return None


async def archive_and_delete_active(chat_id: int, archive_data: dict[str, Any]) -> None:
    """Archive a conversation summary and delete its active context within a single transaction.

    Args:
        chat_id: Chat identifier.
        archive_data: Dictionary context containing keys 'conversation_id', 'title', 'summary',
                      'started_at', and 'ended_at'.
    """
    conn = await get_db_connection()
    try:
        await conn.execute("BEGIN TRANSACTION")
        
        # 1. Insert archived summary
        await conn.execute(
            """
            INSERT INTO chat_archive (conversation_id, chat_id, title, summary, started_at, ended_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                archive_data["conversation_id"],
                chat_id,
                archive_data["title"],
                archive_data["summary"],
                archive_data["started_at"],
                archive_data["ended_at"]
            )
        )
        
        # 2. Delete active conversation context
        await conn.execute(
            "DELETE FROM active_conversation WHERE chat_id = ?",
            (chat_id,)
        )
        
        await conn.commit()
    except Exception as exc:
        await conn.rollback()
        logger.error(f"Transaction failed, changes rolled back: {exc}")
        raise exc
    finally:
        await conn.close()
