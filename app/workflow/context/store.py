import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
import aiosqlite

from app.database.sqlite.database import get_db_connection

logger = logging.getLogger("openclaw-workflow-context")

class VariableStore:
    """Manages tiny persistent variables stored in the SQLite session_variables table."""

    @staticmethod
    async def put(session_id: str, key: str, value: Any, producer_step_id: Optional[str] = None) -> None:
        """Stores a serialized key-value variable associated with an execution session.
        
        Args:
            session_id: The ID of the current running execution session.
            key: Name of the variable.
            value: Variable value (will be serialized to JSON).
            producer_step_id: The optional ID of the step that produced this variable.
        """
        now = datetime.utcnow().isoformat()
        serialized_val = json.dumps(value)
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                INSERT OR REPLACE INTO session_variables (session_id, key, value, producer_step_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, key, serialized_val, producer_step_id, now)
            )
            await conn.commit()
            logger.debug(f"Stored variable {key} in session {session_id}")
        except Exception as exc:
            logger.error(f"Failed to store variable {key} in SQLite: {exc}")
            raise exc
        finally:
            await conn.close()

    @staticmethod
    async def get(session_id: str, key: str) -> Optional[Any]:
        """Retrieves and deserializes a variable value from the SQLite store.
        
        Args:
            session_id: The session ID.
            key: The variable name.
            
        Returns:
            The deserialized python object, or None if not found.
        """
        conn = await get_db_connection()
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT value FROM session_variables WHERE session_id = ? AND key = ?",
                (session_id, key)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row["value"])
        except Exception as exc:
            logger.error(f"Failed to retrieve variable {key} from SQLite: {exc}")
            raise exc
        finally:
            await conn.close()
        return None

    @staticmethod
    async def get_all(session_id: str) -> Dict[str, Any]:
        """Retrieves all variables for a given session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            A dictionary of all deserialized variables.
        """
        conn = await get_db_connection()
        variables = {}
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT key, value FROM session_variables WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    variables[row["key"]] = json.loads(row["value"])
        except Exception as exc:
            logger.error(f"Failed to retrieve all variables for session {session_id}: {exc}")
            raise exc
        finally:
            await conn.close()
        return variables


class ArtifactStore:
    """Manages large assets (screenshots, DOM dumps, raw outputs) stored in the filesystem."""
    
    BASE_DIR = Path("scratch/artifacts")

    @classmethod
    def store(cls, session_id: str, name: str, data: Any, artifact_type: str) -> Dict[str, Any]:
        """Saves data to a file on the filesystem and returns a lightweight reference map.
        
        Args:
            session_id: The session ID.
            name: The file name / identifier for the artifact.
            data: Data contents to store (bytes, string, or JSON-serializable object).
            artifact_type: The MIME or structural type descriptor of the artifact.
            
        Returns:
            A dictionary containing metadata reference to the saved artifact.
        """
        # Ensure target folder exists
        session_dir = cls.BASE_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = session_dir / name
        
        try:
            if isinstance(data, bytes):
                filepath.write_bytes(data)
            elif isinstance(data, str):
                filepath.write_text(data, encoding="utf-8")
            else:
                # Treat as JSON-serializable
                filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
                
            ref = {
                "artifact_id": f"{session_id}/{name}",
                "type": artifact_type,
                "path": str(filepath.resolve().as_posix()),
                "expires_at": None
            }
            logger.debug(f"Saved artifact to {filepath}")
            return ref
        except Exception as exc:
            logger.error(f"Failed to store artifact {name} to file: {exc}")
            raise exc

    @classmethod
    def load(cls, reference: Dict[str, Any]) -> Any:
        """Reads an artifact's file contents using its metadata reference.
        
        Args:
            reference: Metadata reference dictionary returned by `store()`.
            
        Returns:
            The read contents (bytes, str, or deserialized JSON object).
        """
        path_str = reference.get("path")
        if not path_str:
            raise ValueError("Invalid artifact reference: missing 'path'")
            
        filepath = Path(path_str)
        if not filepath.exists():
            raise FileNotFoundError(f"Artifact file not found at {filepath}")
            
        # Inspect extension/type to determine load style
        try:
            suffix = filepath.suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".pdf", ".bin"):
                return filepath.read_bytes()
            elif suffix == ".json":
                return json.loads(filepath.read_text(encoding="utf-8"))
            else:
                return filepath.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error(f"Failed to load artifact from path {filepath}: {exc}")
            raise exc
