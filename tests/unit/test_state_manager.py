"""
State management tests
"""

import os
import pytest
from src.state_manager import StateManager, TaskState


class TestStateManager:
    """Test state management and task lifecycle"""

    def test_create_task(self, tmp_path):
        """Should create a new task with IDLE state"""
        db_path = tmp_path / "state.db"
        manager = StateManager(str(db_path))

        task_id = manager.create_task("Test task description")

        assert task_id is not None
        assert isinstance(task_id, str)

        task = manager.get_task(task_id)
        assert task["description"] == "Test task description"
        assert task["state"] == TaskState.IDLE.value

    def test_update_task_state(self, tmp_path):
        """Should update task state correctly"""
        db_path = tmp_path / "state.db"
        manager = StateManager(str(db_path))

        task_id = manager.create_task("Test task")
        manager.update_state(task_id, TaskState.DISPATCHING)

        task = manager.get_task(task_id)
        assert task["state"] == TaskState.DISPATCHING.value

    def test_state_transitions(self, tmp_path):
        """Should handle all state transitions"""
        db_path = tmp_path / "state.db"
        manager = StateManager(str(db_path))

        task_id = manager.create_task("Test task")

        # IDLE -> DISPATCHING
        manager.update_state(task_id, TaskState.DISPATCHING)
        assert manager.get_task(task_id)["state"] == TaskState.DISPATCHING.value

        # DISPATCHING -> EXECUTING
        manager.update_state(task_id, TaskState.EXECUTING)
        assert manager.get_task(task_id)["state"] == TaskState.EXECUTING.value

        # EXECUTING -> COMPLETED
        manager.update_state(task_id, TaskState.COMPLETED)
        assert manager.get_task(task_id)["state"] == TaskState.COMPLETED.value

    def test_get_pending_tasks(self, tmp_path):
        """Should retrieve all non-completed tasks"""
        db_path = tmp_path / "state.db"
        manager = StateManager(str(db_path))

        # Create multiple tasks
        task1 = manager.create_task("Task 1")
        task2 = manager.create_task("Task 2")
        task3 = manager.create_task("Task 3")

        # Complete one task
        manager.update_state(task3, TaskState.COMPLETED)

        # Get pending tasks
        pending = manager.get_pending_tasks()

        assert len(pending) == 2
        assert task3 not in [t["task_id"] for t in pending]
