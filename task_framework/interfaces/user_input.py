"""用户输入接口定义。"""

from abc import ABC, abstractmethod
from typing import Optional


class UserInputInterface(ABC):
    """用户输入接口 - 定义如何获取用户输入。"""

    @abstractmethod
    def get_input(self, prompt: Optional[str] = None) -> str:
        """
        获取用户输入。

        Args:
            prompt: 可选的提示信息

        Returns:
            用户输入的字符串
        """
        pass

    @abstractmethod
    def get_voice_input(self) -> Optional[str]:
        """
        获取语音输入（如果支持）。

        Returns:
            转换后的文本，如果不支持或失败则返回 None
        """
        pass

    @abstractmethod
    def is_voice_available(self) -> bool:
        """
        检查语音输入是否可用。

        Returns:
            True 如果支持语音输入
        """
        pass
