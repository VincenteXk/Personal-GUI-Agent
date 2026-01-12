"""权限配置管理工具。"""

import json
import os
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class PermissionConfig:
    """权限配置数据类。"""

    user_id: str
    permissions: dict[str, Any]
    meta_preferences: dict[str, Any]


class PermissionManager:
    """权限配置管理器。"""

    def __init__(self, config_path: str = "config/permissions.json"):
        """
        初始化权限管理器。

        Args:
            config_path: 权限配置文件路径
        """
        self.config_path = config_path
        self._config: Optional[PermissionConfig] = None

    def load(self) -> PermissionConfig:
        """
        加载权限配置。

        Returns:
            权限配置对象
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"权限配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._config = PermissionConfig(
            user_id=data.get("user_id", "default_user"),
            permissions=data.get("permissions", {}),
            meta_preferences=data.get("meta_preferences", {}),
        )
        return self._config

    def save(self, config: PermissionConfig) -> None:
        """
        保存权限配置。

        Args:
            config: 权限配置对象
        """
        data = {
            "user_id": config.user_id,
            "permissions": config.permissions,
            "meta_preferences": config.meta_preferences,
            "last_updated": self._get_timestamp(),
        }

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._config = config

    def get_permission(self, permission_key: str) -> Optional[dict[str, Any]]:
        """
        获取特定权限配置。

        Args:
            permission_key: 权限键名

        Returns:
            权限配置，如果不存在则返回None
        """
        if self._config is None:
            self.load()

        return self._config.permissions.get(permission_key)

    def set_permission(self, permission_key: str, value: dict[str, Any]) -> None:
        """
        设置特定权限配置。

        Args:
            permission_key: 权限键名
            value: 权限值
        """
        if self._config is None:
            self.load()

        self._config.permissions[permission_key] = value
        self.save(self._config)

    def get_meta_preference(self, key: str) -> Optional[Any]:
        """
        获取元偏好。

        Args:
            key: 元偏好键名

        Returns:
            元偏好值，如果不存在则返回None
        """
        if self._config is None:
            self.load()

        return self._config.meta_preferences.get(key)

    def set_meta_preference(self, key: str, value: Any) -> None:
        """
        设置元偏好。

        Args:
            key: 元偏好键名
            value: 元偏好值
        """
        if self._config is None:
            self.load()

        self._config.meta_preferences[key] = value
        self.save(self._config)

    def check_permission_mode(self, permission_key: str) -> str:
        """
        检查权限模式。

        Args:
            permission_key: 权限键名

        Returns:
            权限模式: "auto" | "confirm" | "forbidden"
        """
        perm = self.get_permission(permission_key)
        if perm is None:
            return "confirm"  # 默认需要确认

        return perm.get("mode", "confirm")

    def is_permission_enabled(self, permission_key: str) -> bool:
        """
        检查权限是否启用。

        Args:
            permission_key: 权限键名

        Returns:
            是否启用
        """
        perm = self.get_permission(permission_key)
        if perm is None:
            return False

        return perm.get("enabled", False)

    @staticmethod
    def _get_timestamp() -> str:
        """获取当前时间戳。"""
        from datetime import datetime

        return datetime.now().isoformat()
