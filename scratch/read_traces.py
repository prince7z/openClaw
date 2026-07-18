import sqlite3
import json

def read_latest_session_details():
    conn = sqlite3.connect("openclaw.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get latest session ID
    cursor.execute("SELECT id, status, created_at FROM execution_sessions ORDER BY created_at DESC LIMIT 1")
    session = cursor.fetchone()
    if not session:
        print("No execution sessions found.")
        return

    session_id = session["id"]
    print(f"=== Session: {session_id} ({session['status']}) ===")
    
    # Get definition_json
    cursor.execute("SELECT definition_json FROM execution_sessions WHERE id = ?", (session_id,))
    definition_json = cursor.fetchone()["definition_json"]
    print("\n--- Workflow Definition JSON ---")
    print(json.dumps(json.loads(definition_json), indent=2))

    # Get traces
    print("\n--- Traces ---")
    cursor.execute("SELECT timestamp, target_type, event_type, message FROM execution_traces WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    for row in cursor.fetchall():
        print(f"[{row['timestamp']}] {row['target_type']} ({row['event_type']}): {row['message']}")

    # Get steps that failed
    print("\n--- Failed/Uncompleted Steps ---")
    cursor.execute("SELECT name, step_type, status, tool_name, error_message FROM session_steps WHERE session_id = ? AND status != 'COMPLETED'", (session_id,))
    for row in cursor.fetchall():
        print(f"Step: {row['name']} | Type: {row['step_type']} | Status: {row['status']}")
        print(f"  Tool: {row['tool_name']}")
        print(f"  Error: {row['error_message']}")

    conn.close()

if __name__ == "__main__":
    read_latest_session_details()
