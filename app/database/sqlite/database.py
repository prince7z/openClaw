"""SQLite database connection pool management using aiosqlite."""

import aiosqlite
from app.config.settings import settings


async def get_db_connection() -> aiosqlite.Connection:
    """Acquire a threadsafe asynchronous connection to the configured SQLite database.

    Enables high-performance WAL (Write-Ahead Logging) mode and checks foreign keys.

    Returns:
        An active aiosqlite.Connection object.
    """
    db_path = settings.sqlite_db_path
    conn = await aiosqlite.connect(db_path)
    
    # Optimize SQLite for speed and concurrency
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA synchronous=NORMAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    
    return conn
