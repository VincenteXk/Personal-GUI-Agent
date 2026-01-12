"""任务调度框架 - 采用"感知-思考-行动"循环架构。

基于大模型驱动的任务调度系统，专注于：
- 用户交互和任务理解
- 系统调度和任务管理
- 动态路径规划
- 风险控制和决策
"""

from .agent import TaskAgent, StepResult
from .config import TaskAgentConfig
from .context import TaskContext, TaskInfo, TaskState, ExecutionPlan
from .interfaces import (
    UserInputInterface,
    UserInteractionInterface,
    DeviceCapabilityInterface,
    ProfileManagerInterface,
    TaskExecutorInterface,
    InteractionType,
    Choice,
)
from .actions import (
    SchedulerActionHandler,
    SchedulerActionResult,
    parse_scheduler_action,
    schedule_do,
    schedule_finish,
)
from .system_prompts import get_scheduler_system_prompt, get_messages

__all__ = [
    # 核心Agent
    "TaskAgent",
    "StepResult",
    # 配置
    "TaskAgentConfig",
    # 上下文
    "TaskContext",
    "TaskInfo",
    "TaskState",
    "ExecutionPlan",
    # 接口
    "UserInputInterface",
    "UserInteractionInterface",
    "DeviceCapabilityInterface",
    "ProfileManagerInterface",
    "TaskExecutorInterface",
    "InteractionType",
    "Choice",
    # 操作
    "SchedulerActionHandler",
    "SchedulerActionResult",
    "parse_scheduler_action",
    "schedule_do",
    "schedule_finish",
    # 提示词
    "get_scheduler_system_prompt",
    "get_messages",
]