"""终端用户输入实现。"""

from typing import Optional
from ..interfaces import UserInputInterface


class TerminalUserInput(UserInputInterface):
    """基于终端的用户输入实现。"""

    def get_input(self, prompt: Optional[str] = None) -> str:
        """
        从终端获取用户输入。

        Args:
            prompt: 可选的提示信息

        Returns:
            用户输入的字符串
        """
        if prompt:
            return input(f"\n{prompt}: ")
        else:
            return input("\n> ")

    def get_voice_input(self) -> Optional[str]:
        """
        获取语音输入（当前不支持）。

        Returns:
            None（不支持语音输入）
        """
        print("⚠️  语音输入当前不支持")
        return None

    def is_voice_available(self) -> bool:
        """
        检查语音输入是否可用。

        Returns:
            False（终端不支持语音输入）
        """
        return False
