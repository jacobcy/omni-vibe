"""
State management module

功能:
- SQLite 狀態存儲
- 任務狀態機 (IDLE → DISPATCHING → EXECUTING → COMPLETED/FAILED)
- 斷點恢復
"""

import sqlite3
import uuid
from enum import Enum
from typing import Dict, List, Optional


class TaskState(Enum):
    """任務狀態枚舉"""

    IDLE = "idle"  # 任務已創建，等待開始
    DISPATCHING = "dispatching"  # 正在選擇執行器和模型
    EXECUTING = "executing"  # 執行器正在處理
    WAITING_FOR_CLOUD = "waiting"  # 雲端故障，任務已掛起（腦幹模式）
    COMPLETED = "completed"  # 任務成功完成
    FAILED = "failed"  # 任務失敗


class StateManager:
    """狀態管理類"""

    def __init__(self, db_path: str = "state.db"):
        """
        初始化狀態管理器

        Args:
            db_path: SQLite 數據庫路徑
        """
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """初始化數據庫表"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.conn.commit()

    def create_task(self, description: str) -> str:
        """
        創建新任務

        Args:
            description: 任務描述

        Returns:
            task_id: 任務ID
        """
        task_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (task_id, description, state) VALUES (?, ?, ?)",
            (task_id, description, TaskState.IDLE.value),
        )
        self.conn.commit()
        return task_id

    def update_state(self, task_id: str, state: TaskState):
        """
        更新任務狀態

        Args:
            task_id: 任務ID
            state: 新狀態
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
            (state.value, task_id),
        )
        self.conn.commit()

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        獲取任務信息

        Args:
            task_id: 任務ID

        Returns:
            任務字典或 None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "task_id": row[0],
            "description": row[1],
            "state": row[2],
            "created_at": row[3],
            "updated_at": row[4],
        }

    def get_pending_tasks(self) -> List[Dict]:
        """
        獲取待處理的任務（非 COMPLETED 狀態）

        Returns:
            任務列表
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM tasks WHERE state != ? ORDER BY created_at DESC",
            (TaskState.COMPLETED.value,),
        )
        rows = cursor.fetchall()

        return [
            {
                "task_id": row[0],
                "description": row[1],
                "state": row[2],
                "created_at": row[3],
                "updated_at": row[4],
            }
            for row in rows
        ]
