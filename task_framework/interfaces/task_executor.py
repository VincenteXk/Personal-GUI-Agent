"""任务执行器接口定义。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExecutionResult:
    """执行结果数据类。"""

    success: bool  # 是否成功
    message: Optional[str] = None  # 结果消息
    data: Optional[dict[str, Any]] = None  # 结果数据
    should_retry: bool = False  # 是否应该重试
    require_takeover: bool = False  # 是否需要人工接管


@dataclass
class TaskParameter:
    """任务参数定义。"""

    name: str  # 参数名
    description: str  # 参数描述（自然语言）
    required: bool = True  # 是否必需
    example: Optional[str] = None  # 示例值
    value_type: str = "string"  # 值类型提示（string/number/boolean/object/array）


@dataclass
class TaskCapability:
    """任务能力定义 - 描述执行器能执行的单个任务类型。"""

    task_type: str  # 任务类型标识符（如：phone_automation, graphrag_query）
    name: str  # 任务名称（如：手机自动化）
    description: str  # 任务描述
    parameters: list[TaskParameter] = field(default_factory=list)  # 参数定义
    examples: list[dict[str, Any]] = field(default_factory=list)  # 使用示例
    limitations: list[str] = field(default_factory=list)  # 限制说明


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
    def get_capabilities(self) -> list[TaskCapability]:
        """
        获取执行器的能力列表。

        Returns:
            TaskCapability 列表，每个描述一种可执行的任务类型
        """
        pass

    def can_handle(self, task_type: str) -> bool:
        """
        检查是否能处理特定类型的任务。

        默认实现：检查 task_type 是否在 capabilities 中。
        子类一般不需要重写此方法。

        Args:
            task_type: 任务类型

        Returns:
            True 如果能处理
        """
        return task_type in self.get_supported_task_types()

    def get_supported_task_types(self) -> list[str]:
        """
        获取支持的任务类型列表。

        默认实现：从 capabilities 中提取。
        子类一般不需要重写此方法。

        Returns:
            任务类型列表
        """
        return [cap.task_type for cap in self.get_capabilities()]

    def get_capability_by_type(self, task_type: str) -> Optional[TaskCapability]:
        """
        根据任务类型获取对应的能力定义。

        Args:
            task_type: 任务类型

        Returns:
            TaskCapability 或 None
        """
        for cap in self.get_capabilities():
            if cap.task_type == task_type:
                return cap
        return None
