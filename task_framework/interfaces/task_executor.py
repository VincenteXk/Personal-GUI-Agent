"""任务执行器接口定义。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ExecutionResult:
    """执行结果数据类。"""

    success: bool  # 是否成功
    message: Optional[str] = None  # 结果消息
    data: Optional[dict[str, Any]] = None  # 结果数据
    should_retry: bool = False  # 是否应该重试
    require_takeover: bool = False  # 是否需要人工接管


class TaskExecutorInterface(ABC):
    """任务执行器接口 - 定义如何执行具体任务。"""

    @abstractmethod
    def execute_task(
        self,
        task_type: str,
        task_params: dict[str, Any],
        context: dict[str, Any],
    ) -> ExecutionResult:
        """
        执行具体任务。

        Args:
            task_type: 任务类型（如：phone_operation, web_search, etc.）
            task_params: 任务参数
            context: 执行上下文

        Returns:
            执行结果
        """
        pass

    @abstractmethod
    def can_handle(self, task_type: str) -> bool:
        """
        检查是否能处理特定类型的任务。

        Args:
            task_type: 任务类型

        Returns:
            True 如果能处理
        """
        pass

    @abstractmethod
    def get_supported_task_types(self) -> list[str]:
        """
        获取支持的任务类型列表。

        Returns:
            任务类型列表
        """
        pass
