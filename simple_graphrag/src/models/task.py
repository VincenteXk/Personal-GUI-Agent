"""
任务模型

定义任务的数据结构和生命周期管理。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import asyncio
import uuid

if TYPE_CHECKING:
    from .entity import System
    from .delta import GraphDelta


@dataclass
class Task:
    """
    任务模型

    Attributes:
        task_id: 任务唯一标识符
        input_text: 输入的自然语言文本
        status: 任务状态 ("pending", "running", "completed", "failed", "cancelled")
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
        system_snapshot: 任务创建时的system副本（用于任务隔离）
        result_delta: 任务输出的增量更新包
        error: 错误信息（如果失败）
        progress: 任务进度信息
    """

    task_id: str
    input_text: str
    status: str = "pending"  # "pending", "running", "completed", "failed", "cancelled"
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 任务隔离：副本system
    system_snapshot: Optional["System"] = None

    # 任务输出
    result_delta: Optional["GraphDelta"] = None
    error: Optional[str] = None

    # 任务进度
    progress: dict = field(default_factory=dict)

    # 阶段结果存储
    stage_results: dict = field(default_factory=dict)

    # 异步控制（不序列化）
    _task_handle: Optional[asyncio.Task] = field(
        default=None, repr=False, compare=False
    )
    _cancel_event: asyncio.Event = field(
        default_factory=asyncio.Event, repr=False, compare=False
    )

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def start(self):
        """标记任务开始"""
        self.status = "running"
        self.started_at = datetime.now()

    def complete(self, result_delta: "GraphDelta"):
        """标记任务完成"""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.result_delta = result_delta

    def fail(self, error: str):
        """标记任务失败"""
        self.status = "failed"
        self.completed_at = datetime.now()
        self.error = error

    def cancel(self):
        """请求取消任务"""
        self._cancel_event.set()
        self.status = "cancelled"
        self.completed_at = datetime.now()

    def is_cancelled(self) -> bool:
        """检查任务是否被取消"""
        return self._cancel_event.is_set()

    def is_finished(self) -> bool:
        """检查任务是否已结束（完成/失败/取消）"""
        return self.status in ["completed", "failed", "cancelled"]

    def update_progress(
        self,
        step: str,
        message: str,
        percentage: Optional[float] = None,
        result: Optional[dict] = None,
        input_data: Optional[dict] = None,
        output_data: Optional[dict] = None,
        llm_response: Optional[str] = None,
    ):
        """
        更新任务进度

        Args:
            step: 当前步骤名称
            message: 进度消息
            percentage: 完成百分比
            result: 该阶段的结果数据（摘要）
            input_data: 该阶段的输入数据（详细）
            output_data: 该阶段的输出数据（详细）
            llm_response: LLM 的原始响应（如果有）
        """
        self.progress = {
            "step": step,
            "message": message,
            "percentage": percentage,
            "updated_at": datetime.now().isoformat(),
        }

        # 存储阶段结果（包含更详细的信息）
        if result is not None or input_data is not None or output_data is not None:
            self.stage_results[step] = {
                "result": result,
                "input": input_data,
                "output": output_data,
                "llm_response": llm_response,
                "timestamp": datetime.now().isoformat(),
            }

    def get_stage_result(self, step: str) -> Optional[dict]:
        """获取指定阶段的结果"""
        stage_data = self.stage_results.get(step)
        if stage_data:
            return stage_data.get("result")
        return None

    def get_all_stage_results(self) -> dict:
        """获取所有阶段的结果"""
        return self.stage_results

    def get_duration(self) -> Optional[float]:
        """获取任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    def to_dict(self, include_snapshot: bool = False) -> dict:
        """
        转换为字典格式

        Args:
            include_snapshot: 是否包含system_snapshot（较大，默认不包含）
        """
        data = {
            "task_id": self.task_id,
            "input_text": self.input_text,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error": self.error,
            "progress": self.progress,
            "stage_results": self.stage_results,
            "duration": self.get_duration(),
        }

        if include_snapshot and self.system_snapshot:
            data["system_snapshot"] = self.system_snapshot.to_dict()

        if self.result_delta:
            data["result_delta"] = self.result_delta.to_dict()

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """从字典创建任务（不包含异步控制对象）"""
        created_at = None
        started_at = None
        completed_at = None

        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"])

        # 导入在需要时才加载，避免循环依赖
        result_delta = None
        if data.get("result_delta"):
            from .delta import GraphDelta

            result_delta = GraphDelta.from_dict(data["result_delta"])

        system_snapshot = None
        if data.get("system_snapshot"):
            from .entity import System

            system_snapshot = System.from_dict(data["system_snapshot"])

        return cls(
            task_id=data["task_id"],
            input_text=data["input_text"],
            status=data.get("status", "pending"),
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            system_snapshot=system_snapshot,
            result_delta=result_delta,
            error=data.get("error"),
            progress=data.get("progress", {}),
            stage_results=data.get("stage_results", {}),
        )

    def get_summary(self) -> str:
        """获取任务摘要"""
        duration_str = f"{self.get_duration():.2f}s" if self.get_duration() else "N/A"
        return (
            f"Task(id={self.task_id[:8]}..., status={self.status}, "
            f"duration={duration_str}, text={self.input_text[:30]}...)"
        )


def generate_task_id() -> str:
    """生成任务ID"""
    return str(uuid.uuid4())
