"""语音用户交互实现 - 包装终端交互并添加TTS功能"""

import re
from typing import Any, Optional

from ..interfaces import (
    UserInteractionInterface,
    InteractionType,
    Choice,
)
from .terminal_interaction import TerminalUserInteraction


class VoiceUserInteraction(UserInteractionInterface):
    """支持语音输出（TTS）的用户交互实现"""

    # 应该触发TTS的交互类型
    # INFO: 重要提示信息
    # QUESTION: 需要用户回答的问题
    # CONFIRMATION: 是/否确认
    # SUCCESS: 任务成功
    TTS_ENABLED_TYPES = {
        InteractionType.INFO,  # 关键提示信息也需要播放
        InteractionType.QUESTION,
        InteractionType.CONFIRMATION,
        InteractionType.SUCCESS,
    }

    def __init__(
        self,
        terminal_interaction: TerminalUserInteraction,
        voice_assistant,
        voice_mode: bool = False,
    ):
        """
        初始化语音交互包装器

        Args:
            terminal_interaction: 终端交互实现（作为回退）
            voice_assistant: VoiceAssistant实例，用于TTS和ASR
            voice_mode: 是否启用语音模式
        """
        self.terminal_interaction = terminal_interaction
        self.voice_assistant = voice_assistant
        self.voice_mode = voice_mode

    def show_message(
        self, message: str, interaction_type: InteractionType = InteractionType.INFO
    ) -> None:
        """
        显示消息 - 在语音模式下为关键信息播放TTS

        Args:
            message: 要显示的消息
            interaction_type: 交互类型
        """
        # 总是在终端显示
        self.terminal_interaction.show_message(message, interaction_type)

        # 有条件地播放TTS
        if self.voice_mode and interaction_type in self.TTS_ENABLED_TYPES:
            self._speak_safely(message)

    def get_choice(
        self,
        prompt: str,
        choices: list[Choice],
        allow_custom: bool = False,
    ) -> str:
        """
        让用户从选项中选择 - 在语音模式下使用TTS + ASR

        Args:
            prompt: 提示信息
            choices: 可选项列表
            allow_custom: 是否允许自定义输入

        Returns:
            选择的选项ID或自定义输入
        """
        # 总是在终端显示选项
        self.terminal_interaction.show_message(prompt, InteractionType.CHOICE)
        for i, choice in enumerate(choices, 1):
            print(f"  [{i}] {choice.label}")

        # 语音模式：播放提示和选项，等待语音响应
        if self.voice_mode:
            try:
                # 播放提示信息
                self._speak_safely(prompt)

                # 播放各选项
                for i, choice in enumerate(choices, 1):
                    self._speak_safely(f"选项{i}: {choice.label}")

                # 获取语音响应
                response = self.voice_assistant.listen_and_transcribe()
                if response:
                    # 尝试从响应中提取数字
                    match = re.search(r"\d+", response)
                    if match:
                        num = int(match.group())
                        if 1 <= num <= len(choices):
                            return choices[num - 1].id

                    # 如果没有数字，尝试关键词匹配
                    response_lower = response.lower()
                    for i, choice in enumerate(choices, 1):
                        if choice.label.lower() in response_lower:
                            return choice.id

            except Exception as e:
                print(f"[警告] 语音选择失败: {e}")

        # 回退到终端选择
        return self.terminal_interaction.get_choice(prompt, choices, allow_custom)

    def get_confirmation(
        self,
        prompt: str,
        default: bool = False,
        risk_warning: Optional[str] = None,
    ) -> bool:
        """
        获取用户确认 - 在语音模式下使用TTS问题 + ASR响应

        Args:
            prompt: 提示信息
            default: 默认值
            risk_warning: 可选的风险警告

        Returns:
            True表示确认，False表示拒绝
        """
        # 如果有风险警告，先显示并播放
        if risk_warning:
            self.terminal_interaction.show_message(
                risk_warning, InteractionType.WARNING
            )
            if self.voice_mode:
                self._speak_safely(risk_warning)

        # 在终端显示提示信息
        self.terminal_interaction.show_message(prompt, InteractionType.CONFIRMATION)

        # 语音模式：播放问题，等待语音响应
        if self.voice_mode:
            try:
                # 播放确认问题
                self._speak_safely(prompt)

                # 获取语音响应
                response = self.voice_assistant.listen_and_transcribe()
                if response:
                    # 解析是/否
                    response_lower = response.lower()
                    if any(
                        word in response_lower
                        for word in ["是", "确认", "确定", "yes", "好", "对"]
                    ):
                        return True
                    if any(
                        word in response_lower for word in ["否", "不", "no", "别"]
                    ):
                        return False

            except Exception as e:
                print(f"[警告] 语音确认失败: {e}")

        # 回退到终端确认
        return self.terminal_interaction.get_confirmation(
            prompt, default, risk_warning
        )

    def show_preview(self, title: str, content: dict[str, Any]) -> None:
        """
        显示预览信息（委托给终端，不播放TTS）

        Args:
            title: 预览标题
            content: 预览内容
        """
        self.terminal_interaction.show_preview(title, content)

    def show_progress(
        self, current: int, total: int, message: Optional[str] = None
    ) -> None:
        """
        显示进度信息（委托给终端，不播放TTS）

        Args:
            current: 当前进度
            total: 总进度
            message: 可选的进度消息
        """
        self.terminal_interaction.show_progress(current, total, message)

    def show_result(self, title: str, result: dict[str, Any]) -> None:
        """
        显示结构化结果（委托给终端）

        Args:
            title: 结果标题
            result: 结果数据
        """
        self.terminal_interaction.show_result(title, result)

    def request_missing_info(
        self,
        prompt: str,
        missing_fields: list[str],
        suggestions: Optional[dict[str, list[str]]] = None,
    ) -> dict[str, str]:
        """
        请求缺失的信息（委托给终端）

        Args:
            prompt: 提示信息
            missing_fields: 缺失的字段列表
            suggestions: 可选的建议值

        Returns:
            字段名到值的映射
        """
        return self.terminal_interaction.request_missing_info(
            prompt, missing_fields, suggestions
        )

    def _speak_safely(self, text: str) -> None:
        """
        安全地播放文本 - 捕获异常，静默失败

        Args:
            text: 要播放的文本
        """
        try:
            # 过滤掉表情符号和其他特殊Unicode字符
            # 保留中文、英文、数字、常见标点符号
            cleaned_text = ''.join(
                char for char in text
                if ord(char) < 0x2000 or (0x4E00 <= ord(char) <= 0x9FFF)  # ASCII或中文
                or char in ' \n\t.,!?;:()[]{}，。！？；：（）【】{}、'
            )

            if cleaned_text.strip():  # 只有非空时才播放
                self.voice_assistant.speak(cleaned_text)
        except Exception as e:
            # 静默失败 - 用户仍然可以在终端上读取
            pass
