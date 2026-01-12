"""语音用户输入实现 - 包装终端输入并添加ASR功能"""

from typing import Optional
from ..interfaces import UserInputInterface
from .terminal_input import TerminalUserInput


class VoiceUserInput(UserInputInterface):
    """支持语音输入的用户输入实现"""

    def __init__(self, terminal_input: TerminalUserInput, voice_assistant, voice_mode: bool = False):
        """
        初始化语音输入包装器

        Args:
            terminal_input: 终端输入实现（作为回退）
            voice_assistant: VoiceAssistant实例，用于ASR和TTS
            voice_mode: 是否启用语音模式
        """
        self.terminal_input = terminal_input
        self.voice_assistant = voice_assistant
        self.voice_mode = voice_mode
        self.max_retries = 3

    def get_input(self, prompt: Optional[str] = None) -> str:
        """
        获取用户输入 - 在语音模式下使用ASR，否则使用终端输入

        Args:
            prompt: 可选的提示信息

        Returns:
            用户输入的字符串
        """
        if not self.voice_mode:
            return self.terminal_input.get_input(prompt)

        # 在终端显示提示信息
        if prompt:
            print(f"\n{prompt}")

        # 直接尝试ASR，不处理失败
        text = self.voice_assistant.listen_and_transcribe()
        return text if text else ""

    def get_voice_input(self) -> Optional[str]:
        """
        获取语音输入（直接调用VoiceAssistant）

        Returns:
            转录的文本或None
        """
        if not self.voice_mode:
            return self.terminal_input.get_voice_input()

        try:
            return self.voice_assistant.listen_and_transcribe()
        except Exception as e:
            print(f"[错误] 语音输入失败: {e}")
            return None

    def is_voice_available(self) -> bool:
        """
        检查语音输入是否可用

        Returns:
            voice_mode的状态
        """
        return self.voice_mode
