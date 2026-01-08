"""任务上下文和状态管理。

支持"感知-思考-行动"循环的上下文管理。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime


class TaskState(Enum):
    """任务状态枚举。"""

    IDLE = "idle"  # 空闲
    ONBOARDING = "onboarding"  # 首次引导
    RECEIVING_INPUT = "receiving_input"  # 接收输入
    NORMALIZING = "normalizing"  # 指令标准化
    REQUESTING_INFO = "requesting_info"  # 请求缺失信息
    CHECKING_DEVICE = "checking_device"  # 检查设备
    PLANNING = "planning"  # 规划任务
    PREVIEWING = "previewing"  # 预览计划
    EXECUTING = "executing"  # 执行中
    CONFIRMING = "confirming"  # 等待确认（HITL）
    RETRY = "retry"  # 重试中
    TAKEOVER = "takeover"  # 人工接管
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class TaskInfo:
    """任务信息数据类。"""

    original_input: str  # 原始输入
    task_type: Optional[str] = None  # 任务类型
    normalized_task: Optional[str] = None  # 标准化后的任务
    key_info: dict[str, Any] = field(default_factory=dict)  # 关键信息
    constraints: list[str] = field(default_factory=list)  # 约束条件
    missing_fields: list[str] = field(default_factory=list)  # 缺失字段
    target_app: Optional[str] = None  # 目标应用
    execution_mode: str = "default"  # 执行模式


@dataclass
class ExecutionPlan:
    """执行计划数据类。"""

    task_type: str  # 任务类型
    steps: list[dict[str, Any]] = field(default_factory=list)  # 执行步骤
    estimated_time: Optional[int] = None  # 预计时间（秒）
    required_apps: list[str] = field(default_factory=list)  # 需要的应用
    risk_level: str = "low"  # 风险等级: low, medium, high
    alternatives: list["ExecutionPlan"] = field(default_factory=list)  # 备选方案


@dataclass
class TaskContext:
    """任务上下文 - 保存任务执行过程中的所有状态。

    支持"感知-思考-行动"循环架构，记录：
    - 当前状态和任务信息
    - 已执行的操作步骤（execution_history）
    - 用户交互历史（interaction_history）
    - 对话上下文（conversation_history）
    - 全局任务记录（task_info, execution_plan）
    """

    state: TaskState = TaskState.IDLE
    task_info: Optional[TaskInfo] = None
    execution_plan: Optional[ExecutionPlan] = None

    current_step: int = 0
    retry_count: int = 0
    max_retries: int = 3

    device_id: Optional[str] = None

    # 执行历史 - 记录已执行的操作和结果
    execution_history: list[dict[str, Any]] = field(default_factory=list)

    # 用户交互历史 - 记录与用户的交互
    interaction_history: list[dict[str, Any]] = field(default_factory=list)

    # 对话历史 - 用于大模型的上下文（类似phone_agent的_context）
    conversation_history: list[dict[str, Any]] = field(default_factory=list)

    # 临时数据
    temp_data: dict[str, Any] = field(default_factory=dict)

    # 全局标记
    task_start_time: Optional[datetime] = None
    last_action_result: Optional[Any] = None

    def add_execution_record(self, action: str, result: Any, success: bool) -> None:
        """添加执行记录。"""
        record = {
            "step": self.current_step,
            "action": action,
            "result": str(result) if result is not None else None,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "state": self.state.value,
        }
        self.execution_history.append(record)
        self.last_action_result = result

    def add_interaction_record(self, interaction_type: str, data: Any) -> None:
        """添加交互记录。"""
        record = {
            "step": self.current_step,
            "type": interaction_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        self.interaction_history.append(record)

    def add_conversation_message(self, role: str, content: str | dict) -> None:
        """添加对话消息到上下文。"""
        message = {"role": role, "content": content}
        self.conversation_history.append(message)

    def get_recent_execution_summary(self, n: int = 5) -> str:
        """获取最近n条执行记录的摘要。"""
        recent = self.execution_history[-n:] if self.execution_history else []
        if not recent:
            return "暂无执行历史"

        lines = []
        for record in recent:
            status = "✓" if record["success"] else "✗"
            lines.append(
                f"{status} 步骤{record['step']}: {record['action']} - {record['state']}"
            )
        return "\n".join(lines)

    def get_context_summary(self) -> dict[str, Any]:
        """获取上下文摘要，用于提供给大模型。"""
        return {
            "current_state": self.state.value,
            "current_step": self.current_step,
            "retry_count": self.retry_count,
            "task_info": (
                {
                    "original_input": (
                        self.task_info.original_input if self.task_info else None
                    ),
                    "task_type": self.task_info.task_type if self.task_info else None,
                    "key_info": self.task_info.key_info if self.task_info else {},
                }
                if self.task_info
                else None
            ),
            "recent_execution": self.get_recent_execution_summary(),
            "last_action_result": (
                str(self.last_action_result) if self.last_action_result else None
            ),
        }

    def can_retry(self) -> bool:
        """检查是否可以重试。"""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """增加重试次数。"""
        self.retry_count += 1

    def reset_retry(self) -> None:
        """重置重试次数。"""
        self.retry_count = 0

    def next_step(self) -> None:
        """进入下一步。"""
        self.current_step += 1
        self.reset_retry()

    def reset_for_new_task(self) -> None:
        """为新任务重置上下文。"""
        self.state = TaskState.IDLE
        self.task_info = None
        self.execution_plan = None
        self.current_step = 0
        self.retry_count = 0
        self.execution_history = []
        self.interaction_history = []
        self.conversation_history = []
        self.temp_data = {}
        self.task_start_time = None
        self.last_action_result = None
