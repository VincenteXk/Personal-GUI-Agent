"""
Descripttion:
Author: Sion's pota
version:
Date: 2026-01-08 16:26:25
LastEditors: Sion's pota
LastEditTime: 2026-01-08 16:27:08
"""

"""用户画像管理接口定义。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class UserProfile:
    """用户画像数据类。"""

    language_style: str = "casual"  # 语言风格
    common_apps: list[str] = None  # 常用APP
    default_mode: str = "balanced"  # 默认模式
    preferences: dict[str, Any] = None  # 用户偏好

    def __post_init__(self):
        if self.common_apps is None:
            self.common_apps = []
        if self.preferences is None:
            self.preferences = {}


@dataclass
class ScenePreference:
    """场景偏好数据类。"""

    scene_type: str  # 场景类型（如：shopping, social, etc.）
    preferences: dict[str, Any]  # 偏好设置
    confidence: float = 0.5  # 置信度
    is_temporary: bool = False  # 是否仅本次有效


class ProfileManagerInterface(ABC):
    """用户画像管理接口。"""

    @abstractmethod
    def get_profile(self) -> UserProfile:
        """
        获取用户画像。

        Returns:
            用户画像对象
        """
        pass

    @abstractmethod
    def update_profile(self, profile: UserProfile) -> None:
        """
        更新用户画像。

        Args:
            profile: 新的用户画像
        """
        pass

    @abstractmethod
    def get_scene_preference(self, scene_type: str) -> Optional[ScenePreference]:
        """
        获取特定场景的偏好。

        Args:
            scene_type: 场景类型

        Returns:
            场景偏好，如果不存在则返回 None
        """
        pass

    @abstractmethod
    def update_scene_preference(
        self, preference: ScenePreference, user_confirmed: bool = False
    ) -> None:
        """
        更新场景偏好。

        Args:
            preference: 场景偏好
            user_confirmed: 用户是否确认更新
        """
        pass

    @abstractmethod
    def save(self) -> None:
        """保存画像到持久化存储。"""
        pass

    @abstractmethod
    def load(self) -> None:
        """从持久化存储加载画像。"""
        pass
