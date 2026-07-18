import os
import sys
import asyncio
import logging
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Configure sys.path to include workspace root
sys.path.append(".")

# Override database environment variable to use a test database before any DB modules are loaded
os.environ["SQLITE_DB_PATH"] = "test_openclaw.db"

from app.database.sqlite.migrations import run_migrations
from app.workflow.planner.compiler import WorkflowCompiler
from app.workflow.coordinator import ExecutionCoordinator
from app.workflow.engine.validator import ValidationError
from app.workflow.repository.db import WorkflowRepository
from app.workflow.repository.models import SessionStatus, StepStatus, TaskStatus
from app.workflow.context.store import VariableStore
from app.workflow.context.registry import ToolRegistry, WorkflowTool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("test-workflow-engine")

async def cleanup_test_db():
    """Removes the test database files."""
    for filename in ("test_openclaw.db", "test_openclaw.db-wal", "test_openclaw.db-shm"):
        p = Path(filename)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    # Clean up test directories
    scratch_dir = Path("scratch")
    if scratch_dir.exists():
        # Keep scratch, but clear test files
        for item in scratch_dir.glob("test_*"):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

async def setup_test_environment():
    """Runs database migrations for the test DB."""
    await cleanup_test_db()
    logger.info("Running database migrations on test_openclaw.db...")
    await run_migrations()

async def test_cycle_detection():
    logger.info("=== Running test_cycle_detection ===")
    cycle_workflow = {
        "name": "Cycle Test",
        "tasks": [
            {
                "id": "task_1",
                "name": "Cyclic Task",
                "steps": [
                    {
                        "id": "step_a",
                        "step_type": "TOOL",
                        "tool_name": "read_file",
                        "depends_on": ["step_b"]
                    },
                    {
                        "id": "step_b",
                        "step_type": "TOOL",
                        "tool_name": "read_file",
                        "depends_on": ["step_a"]
                    }
                ]
            }
        ]
    }
    
    try:
        await WorkflowCompiler.compile(cycle_workflow)
        raise AssertionError("Cycle was not detected!")
    except ValidationError as exc:
        logger.info(f"[OK] Cycle successfully detected: {exc}")
        assert "cycle" in str(exc).lower()

async def test_missing_dependency():
    logger.info("=== Running test_missing_dependency ===")
    missing_dep_workflow = {
        "name": "Missing Dependency Test",
        "tasks": [
            {
                "id": "task_1",
                "name": "Missing Task",
                "steps": [
                    {
                        "id": "step_a",
                        "step_type": "TOOL",
                        "tool_name": "read_file",
                        "depends_on": ["non_existent_step"]
                    }
                ]
            }
        ]
    }

    try:
        await WorkflowCompiler.compile(missing_dep_workflow)
        raise AssertionError("Missing dependency was not detected!")
    except ValidationError as exc:
        logger.info(f"[OK] Missing dependency successfully detected: {exc}")
        assert "missing" in str(exc).lower()

async def test_e2e_sequential_execution():
    logger.info("=== Running test_e2e_sequential_execution ===")
    
    # Pre-populate test inputs
    Path("scratch").mkdir(exist_ok=True)
    input_file = Path("scratch/test_input.txt")
    output_file = Path("scratch/test_output.txt")
    
    input_file.write_text("Hello from OpenClaw custom workflow engine test!", encoding="utf-8")
    
    workflow_def = {
        "name": "E2E Test Workflow",
        "tasks": [
            {
                "id": "task_e2e",
                "name": "Sequential Task",
                "steps": [
                    {
                        "id": "step_read",
                        "name": "Read Input",
                        "step_type": "TOOL",
                        "tool_name": "read_file",
                        "inputs": {
                            "path": "scratch/test_input.txt"
                        },
                        "output_key": "file_data",
                        "depends_on": [] # Empty means run first
                    },
                    {
                        "id": "step_reason",
                        "name": "Translate Text",
                        "step_type": "REASONER",
                        "reasoner_prompt": "Translate this: ${file_data}",
                        "output_key": "translated_data"
                        # Omitting depends_on defaults to sequential (depends on step_read)
                    },
                    {
                        "id": "step_write",
                        "name": "Write Output",
                        "step_type": "TOOL",
                        "tool_name": "write_file",
                        "inputs": {
                            "path": "scratch/test_output.txt",
                            "content": "${translated_data}"
                        }
                    }
                ]
            }
        ]
    }

    # Compile the workflow definition into a session
    session_id = await WorkflowCompiler.compile(workflow_def)
    logger.info(f"Compiled session ID: {session_id}")

    # Set up mock response for LLM ainvoke
    mock_llm_response = AsyncMock()
    mock_llm_response.content = "Bonjour de l'agent OpenClaw!"
    mock_llm_response.response_metadata = {"token_usage": {"total_tokens": 15}}

    mock_llm_instance = AsyncMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_llm_response)

    coordinator = ExecutionCoordinator()
    
    # Run session with LLM call patched
    with patch("app.workflow.executors.reasoner.llm", mock_llm_instance):
        await coordinator.run_session(session_id)

    # 1. Assert session completed successfully in DB
    sess = await WorkflowRepository.get_session(session_id)
    assert sess is not None
    assert sess["status"] == SessionStatus.COMPLETED.value
    logger.info("[OK] SQLite Session status validated as COMPLETED.")

    # 2. Assert task completed
    tasks = await WorkflowRepository.get_tasks(session_id)
    assert len(tasks) == 1
    assert tasks[0]["status"] == TaskStatus.COMPLETED.value
    logger.info("[OK] SQLite Task status validated as COMPLETED.")

    # 3. Assert step results exist
    steps = await WorkflowRepository.get_steps(session_id)
    assert len(steps) == 3
    for s in steps:
        assert s["status"] == StepStatus.COMPLETED.value
    logger.info("[OK] SQLite Steps statuses validated as COMPLETED.")

    # 4. Assert Variable Store has correct outputs
    variables = await VariableStore.get_all(session_id)
    assert "file_data" in variables
    assert "translated_data" in variables
    
    # OpenClaw filesystem tools return a structured result dictionary
    assert isinstance(variables["file_data"], dict)
    assert variables["file_data"]["success"] is True
    assert variables["file_data"]["data"]["content"] == "Hello from OpenClaw custom workflow engine test!"
    
    assert variables["translated_data"] == "Bonjour de l'agent OpenClaw!"
    logger.info("[OK] Context variable interpolation verified successfully.")

    # 5. Assert the tool output was written to filesystem
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == "Bonjour de l'agent OpenClaw!"
    logger.info("[OK] Filesystem output validated successfully.")

    # 6. Assert execution traces and step results metrics are saved
    traces = await WorkflowRepository.get_traces(session_id)
    assert len(traces) > 0
    logger.info(f"[OK] Traces verified ({len(traces)} events logged).")

async def test_concurrency_locking():
    logger.info("=== Running test_concurrency_locking ===")
    
    # Define a custom mock sleep tool inside the registry
    async def mock_sleep_tool(delay: float):
        import asyncio
        await asyncio.sleep(delay)
        return "slept"

    ToolRegistry._registry["mock_sleep"] = WorkflowTool(
        name="mock_sleep",
        description="sleeps for locking test",
        input_schema={"delay": {"type": "number"}},
        callable_fn=mock_sleep_tool,
        resources=["browser.default"] # requires capability lock
    )

    # Workflow has Task A and Task B running in parallel, but their steps claim the same lock
    lock_workflow = {
        "name": "Lock Concurrency Test",
        "tasks": [
            {
                "id": "task_a",
                "name": "Task A",
                "steps": [
                    {
                        "id": "step_a1",
                        "name": "Sleep Step A",
                        "step_type": "TOOL",
                        "tool_name": "mock_sleep",
                        "inputs": {"delay": 0.5},
                        "resources": ["browser.default"],
                        "depends_on": []
                    }
                ]
            },
            {
                "id": "task_b",
                "name": "Task B",
                "steps": [
                    {
                        "id": "step_b1",
                        "name": "Sleep Step B",
                        "step_type": "TOOL",
                        "tool_name": "mock_sleep",
                        "inputs": {"delay": 0.5},
                        "resources": ["browser.default"],
                        "depends_on": []
                    }
                ]
            }
        ]
    }

    session_id = await WorkflowCompiler.compile(lock_workflow)
    coordinator = ExecutionCoordinator()

    start_time = asyncio.get_event_loop().time()
    await coordinator.run_session(session_id)
    end_time = asyncio.get_event_loop().time()

    total_duration = end_time - start_time
    logger.info(f"Lock concurrency execution took {total_duration:.3f}s")

    # If they executed in parallel, total duration would be ~0.5s.
    # Because of the browser.default lock, they MUST execute sequentially, taking >= 1.0s.
    assert total_duration >= 1.0, "Steps were not executed sequentially despite claiming the same capability lock!"
    logger.info("[OK] Capability Lock Manager validated successfully.")

async def run_all_tests():
    logger.info("Initializing test environment...")
    await setup_test_environment()
    
    try:
        await test_cycle_detection()
        await test_missing_dependency()
        await test_e2e_sequential_execution()
        await test_concurrency_locking()
        logger.info("\nALL TESTS PASSED SUCCESSFULLY! [OK]")
    finally:
        await cleanup_test_db()

if __name__ == "__main__":
    asyncio.run(run_all_tests())
