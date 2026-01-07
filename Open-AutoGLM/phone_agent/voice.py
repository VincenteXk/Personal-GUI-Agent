"""
语音管理模块

将 dialogue.py 的 VoiceAssistant 适配为 phone_agent 接口
"""

import os
import sys
import queue
import io
import wave
import time
import asyncio
import threading
from typing import Optional


# 导入 VoiceAssistant
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from dialogue import VoiceAssistant
except ImportError as e:
    print(f"警告: 无法导入 dialogue 模块: {e}")
    VoiceAssistant = None


class VoiceManager:
    """
    语音管理器，适配 dialogue.py 的 VoiceAssistant

    提供统一的语音输入/输出接口，支持：
    - 语音识别 (ASR)
    - 文本转语音 (TTS)
    - 后台监听线程
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "deepseek-chat"):
        """
        初始化语音管理器

        Args:
            api_key: API密钥（可选，默认使用dialogue.py中的配置）
            base_url: API基础URL（可选，默认使用dialogue.py配置）
            model: 使用的模型名称
        """
        if VoiceAssistant is None:
            raise RuntimeError("VoiceAssistant 未能正确导入，请检查 dialogue.py 文件")

        self.assistant = VoiceAssistant()
        self.is_listening = False
        self.listener_threads = []

        # 如果提供了自定义配置，覆盖默认配置
        if api_key:
            try:
                from openai import OpenAI
                self.assistant.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.deepseek.com"
                )
            except ImportError:
                print("警告: OpenAI 库未安装")

    def listen_and_transcribe(self, timeout: int = 5) -> Optional[str]:
        """
        监听语音并转录为文本

        Args:
            timeout: 等待音频数据的超时时间（秒）

        Returns:
            str: 识别出的文本，如果没有识别到则返回None
        """
        try:
            audio_data = self.assistant.audio_queue.get(timeout=timeout)

            # 使用ASR模型识别
            audio_stream = io.BytesIO()
            with wave.open(audio_stream, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_data)

            audio_stream.seek(0)
            print(f"识别中...({len(audio_data)/16000:.2f}秒)")

            res = self.assistant.asr_model.generate(
                input=audio_stream,
                cache={},
                language="auto",
                use_itn=False
            )

            if res:
                text = res[0]['text'].split(">")[-1].strip().replace(" ", "")
                return text if text else None
            return None

        except queue.Empty:
            print("未检测到语音")
            return None
        except Exception as e:
            print(f"语音识别错误: {e}")
            return None

    def speak(self, text: str) -> None:
        """
        文本转语音并播放

        Args:
            text: 要播放的文本
        """
        try:
            asyncio.run(self.assistant.edge_tts_sync(text))
        except Exception as e:
            print(f"语音合成和播放错误: {e}")

    def start_listening(self) -> None:
        """
        启动后台监听线程

        启动两个守护线程：
        - audio_recorder: 录制音频并进行VAD检测
        - process_audio: 处理识别和LLM回复
        """
        if self.is_listening:
            print("监听已在运行")
            return

        self.is_listening = True
        self.assistant.recording_active = True

        # 启动录音线程
        recorder_thread = threading.Thread(
            target=self.assistant.audio_recorder,
            daemon=True,
            name="VoiceRecorder"
        )
        recorder_thread.start()
        self.listener_threads.append(recorder_thread)

        # 启动处理线程
        processor_thread = threading.Thread(
            target=self.assistant.process_audio,
            daemon=True,
            name="VoiceProcessor"
        )
        processor_thread.start()
        self.listener_threads.append(processor_thread)

        print("🎤 语音监听已启动")

    def stop_listening(self) -> None:
        """停止后台监听线程"""
        if not self.is_listening:
            print("监听未运行")
            return

        self.is_listening = False
        self.assistant.recording_active = False

        # 等待线程结束（最多5秒）
        for thread in self.listener_threads:
            thread.join(timeout=5)

        self.listener_threads = []
        print("🎤 语音监听已停止")

    def is_running(self) -> bool:
        """
        检查监听是否正在运行

        Returns:
            bool: 是否正在运行
        """
        return self.is_listening and self.assistant.recording_active

    def get_conversation_history(self):
        """
        获取对话历史记录

        Returns:
            list: 对话消息列表
        """
        return self.assistant.messages

    def clear_conversation_history(self) -> None:
        """清空对话历史记录，仅保留系统消息"""
        if len(self.assistant.messages) > 1:
            system_message = self.assistant.messages[0]
            self.assistant.messages = [system_message]
            print("✅ 对话历史已清空")
