"""用户交互接口定义。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class InteractionType(Enum):
    """交互类型枚举。"""

    INFO = "info"  # 纯信息展示
    WARNING = "warning"  # 警告信息
    ERROR = "error"  # 错误信息
    SUCCESS = "success"  # 成功信息
    QUESTION = "question"  # 询问
    CHOICE = "choice"  # 选择题
    CONFIRMATION = "confirmation"  # 确认（是/否）
    PREVIEW = "preview"  # 预览（计划/结果等）
    PROGRESS = "progress"  # 进度显示


@dataclass
class Choice:
    """选择项数据类。"""

    id: str  # 选项ID
    label: str  # 选项标签
    description: Optional[str] = None  # 选项描述
    metadata: Optional[dict[str, Any]] = None  # 额外元数据


class UserInteractionInterface(ABC):
    """用户交互接口 - 定义如何与用户交互。"""

    @abstractmethod
    def show_message(
        self, message: str, interaction_type: InteractionType = InteractionType.INFO
    ) -> None:
        """
        向用户显示消息。

        Args:
            message: 要显示的消息
            interaction_type: 交互类型
        """
        pass

    @abstractmethod
    def get_choice(
        self,
        prompt: str,
        choices: list[Choice],
        allow_custom: bool = False,
    ) -> str:
        """
        让用户从选项中选择。

        Args:
            prompt: 提示信息
            choices: 可选项列表
            allow_custom: 是否允许自定义输入

        Returns:
            选择的选项ID或自定义输入
        """
        pass

    @abstractmethod
    def get_confirmation(
        self, prompt: str, default: bool = False, risk_warning: Optional[str] = None
    ) -> bool:
        """
        获取用户确认。

        Args:
            prompt: 提示信息
            default: 默认值
            risk_warning: 可选的风险警告

        Returns:
            True 表示确认，False 表示拒绝
        """
        pass

    @abstractmethod
    def show_preview(self, title: str, content: dict[str, Any]) -> None:
        """
        显示预览信息（如任务计划）。

        Args:
            title: 预览标题
            content: 预览内容（结构化数据）
        """
        pass

    @abstractmethod
    def show_progress(
        self, current: int, total: int, message: Optional[str] = None
    ) -> None:
        """
        显示进度信息。

        Args:
            current: 当前进度
            total: 总进度
            message: 可选的进度消息
        """
        pass

    @abstractmethod
    def show_result(self, title: str, result: dict[str, Any]) -> None:
        """
        显示结构化结果。

        Args:
            title: 结果标题
            result: 结果数据
        """
        pass

    @abstractmethod
    def request_missing_info(
        self,
        prompt: str,
        missing_fields: list[str],
        suggestions: Optional[dict[str, list[str]]] = None,
    ) -> dict[str, str]:
        """
        请求缺失的信息。

        Args:
            prompt: 提示信息
            missing_fields: 缺失的字段列表
            suggestions: 可选的建议值

        Returns:
            字段名到值的映射
        """
        pass
