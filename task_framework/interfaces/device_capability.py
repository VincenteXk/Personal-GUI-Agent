"""设备能力接口定义。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceStatus:
    """设备状态数据类。"""

    is_connected: bool  # 是否连接
    is_unlocked: bool  # 是否解锁
    is_authorized: bool  # 是否授权
    device_id: Optional[str] = None  # 设备ID
    error_message: Optional[str] = None  # 错误信息


class DeviceCapabilityInterface(ABC):
    """设备能力接口 - 定义设备相关的能力。"""

    @abstractmethod
    def check_device_status(self, device_id: Optional[str] = None) -> DeviceStatus:
        """
        检查设备状态。

        Args:
            device_id: 可选的设备ID

        Returns:
            设备状态信息
        """
        pass

    @abstractmethod
    def list_available_devices(self) -> list[str]:
        """
        列出可用设备。

        Returns:
            设备ID列表
        """
        pass

    @abstractmethod
    def get_current_app(self, device_id: Optional[str] = None) -> Optional[str]:
        """
        获取当前运行的应用。

        Args:
            device_id: 可选的设备ID

        Returns:
            应用包名或None
        """
        pass

    @abstractmethod
    def get_installed_apps(self, device_id: Optional[str] = None) -> list[str]:
        """
        获取已安装的应用列表。

        Args:
            device_id: 可选的设备ID

        Returns:
            应用包名列表
        """
        pass
