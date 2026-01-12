"""
语音助手模块

集成语音助手功能，提供语音输入/输出接口
支持语音识别 (ASR)、语言模型处理 (LLM) 和文本转语音 (TTS)
"""

import os
import time
import threading
import wave
import pyaudio
import webrtcvad
import asyncio
import edge_tts
from playsound import playsound
import io
import re
import tempfile
from funasr import AutoModel
from typing import Optional, Any, Dict, List
from openai import OpenAI

# 创建线程锁用于音频资源的线程安全访问
audio_lock = threading.Lock()


# 配置参数
AUDIO_RATE = 16000
CHUNK = 1024
VAD_MODE = 3

# API配置
API_KEY = ""#这个地方待处理，我想的是deepseek client其实可以在主程序创建，VoiceAssistant其实只需要“说->听”的功能就行了，llm过程完全可以删掉
BASE_URL = "https://api.deepseek.com"


class VoiceAssistant:
    """
    语音助手类，提供完整的语音交互功能

    支持：
    - 语音识别 (ASR)
    - 语言模型处理 (LLM)
    - 文本转语音 (TTS)
    - 对话历史管理
    - 实时录音与VAD检测
    """

    def __init__(
        self,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
        model: str = "deepseek-chat",
        system_prompt: str = "你是一个智能语音助手，能够帮助用户完成各种任务。请用简体中文回答用户的问题。",
    ):
        """
        初始化语音助手

        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 使用的模型名称
        """
        # 初始化状态变量
        self.recording_active = False
        self.tts_playing = False
        self.tts_stop_event = threading.Event()

        # 初始化对话记忆
        self.messages = [{"role": "system", "content": system_prompt}]

        # 初始化音频系统线程锁
        self.audio_lock = threading.Lock()

        # 初始化模型
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(VAD_MODE)
        print("加载 FunASR 模型...")
        self.asr_model = AutoModel(model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")

        print("连接 DeepSeek API...")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def __del__(self):
        """析构函数，清理资源"""
        pass

    def check_vad_activity(self, audio_data):
        """检测语音活动"""
        step = int(AUDIO_RATE * 0.02)
        flag_rate = round(0.4 * len(audio_data) // step)
        return (
            sum(
                1
                for i in range(0, len(audio_data), step)
                if len(chunk := audio_data[i : i + step]) == step
                and self.vad.is_speech(chunk, AUDIO_RATE)
            )
            > flag_rate
        )

    def single_record(
        self,
        max_duration: int = 10,
        min_duration: int = 1,
        silence_duration: float = 1.5,
    ):
        """单次录音功能，支持VAD检测，带自动停止功能
        Args:
            max_duration: 最大录音时长（秒）
            min_duration: 最短录音时长（秒）
            silence_duration: 检测到静音后停止录音的时长（秒）
        """
        with self.audio_lock:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=AUDIO_RATE,
                input=True,
                frames_per_buffer=CHUNK
            )

            audio_buffer = []
            accumulated_audio = []
            processing_started = False
            silence_start_time = None

            print("开始录音，请说话...")

            try:
                while True:
                    data = stream.read(CHUNK)
                    audio_buffer.append(data)
                    accumulated_audio.append(data)

                    current_duration = len(accumulated_audio) * CHUNK / AUDIO_RATE

                    # 每0.5秒进行一次VAD检测
                    if len(audio_buffer) * CHUNK / AUDIO_RATE >= 0.5:
                        raw_audio = b''.join(audio_buffer)
                        vad_result = self.check_vad_activity(raw_audio)

                        if vad_result:
                            print("检测语音")
                            if not processing_started:
                                processing_started = True
                            silence_start_time = None
                        elif processing_started and silence_start_time is None:
                            silence_start_time = time.time()
                            print("处理...")

                        audio_buffer = []

                        # 检查最大录音时长
                        if current_duration >= max_duration:
                            print(f"达到最大录音时长{max_duration}秒")
                            break

                    # 如果已达到最小时长且检测到足够的静音，则停止录音
                    if (processing_started and silence_start_time and
                        current_duration >= min_duration and
                        time.time() - silence_start_time > silence_duration):
                        print("重置")
                        break

                # 返回录音数据
                raw_audio = b''.join(accumulated_audio)
                if processing_started or len(raw_audio) > 0:
                    return raw_audio
                else:
                    print("未检测到语音活动")
                    return None

            except Exception as e:
                raise e
            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()

    def asr_transcribe(self, audio_data):
        """ASR语音转录"""
        if not audio_data:
            return None

        print(f"识别中...({len(audio_data)/AUDIO_RATE:.2f}秒)")
        start_time = time.time()

        try:
            # 将音频数据转换为 WAV 格式
            audio_stream = io.BytesIO()
            with wave.open(audio_stream, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(AUDIO_RATE)
                wf.writeframes(audio_data)

            # 保存临时音频文件（FunASR 需要文件路径）
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_stream.getvalue())
                temp_path = temp_audio.name

            # FunASR 识别
            result = self.asr_model.generate(input=temp_path, batch_size_s=300)

            # 清理临时文件
            os.remove(temp_path)

            asr_time = time.time() - start_time
            print(f"识别耗时: {asr_time:.2f}秒")

            # FunASR 返回列表格式的结果
            if result and len(result) > 0:
                text = result[0]["text"].strip() if isinstance(result[0], dict) else str(result[0]).strip()
                if text:
                    print(f"识别: {text}")
                    return text
            return None
        except Exception as e:
            print(f"语音识别出错: {e}")
            return None

    def llm_process(self, text):
        """LLM处理文本并生成回复"""
        if not text:
            return None

        # 添加用户消息到对话记忆
        self.messages.append({"role": "user", "content": text})

        print("处理中...")
        start_time = time.time()

        response = self.client.chat.completions.create(
            model="deepseek-chat", messages=self.messages, max_tokens=200
        )
        llm_time = time.time() - start_time

        # 使用正则表达式过滤掉中英字符和标点符号外的所有字符
        full_response = response.choices[0].message.content
        # 保留中英文字符、数字、空格、中英文标点符号
        filtered_response = re.sub(
            r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.,!?;:：，。！？；：""' "（）【】《》\\-\n]",
            "",
            full_response,
        )
        print(f"回复: {filtered_response}")
        print(f"LLM耗时: {llm_time:.2f}秒")

        # 添加助手回复到对话记忆
        self.messages.append({"role": "assistant", "content": filtered_response})

        # 限制对话记忆长度，避免上下文过长
        if len(self.messages) > 10:  # 保留最近5轮对话（系统消息+5轮用户/助手对话）
            self.messages = [self.messages[0]] + self.messages[-9:]

        return filtered_response

    def speak(self, text: str) -> None:
        """
        文本转语音并播放

        Args:
            text: 要播放的文本
        """
        if not text:
            return

        # 使用线程锁确保音频播放的线程安全
        with self.audio_lock:
            print("合成中...")
            start_time = time.time()
            
            # 使用临时文件而不是固定文件名，避免文件冲突
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name

            # 创建通信对象并保存音频
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
            asyncio.run(communicate.save(temp_path))
            tts_time = time.time() - start_time
            print(f"TTS耗时: {tts_time:.2f}秒")

            # 播放音频
            start_time = time.time()
            playsound(temp_path, block=True)
            play_time = time.time() - start_time
            print(f"播放耗时: {play_time:.2f}秒")

            # 删除临时文件
            os.remove(temp_path)

    def ask_question(self, question: str):
        """主动向用户提问并等待回答的完整流程"""
        print(f"助手: {question}")

        # 语音合成并播放问题
        self.speak(question)

        # 等待用户回答
        print("等待用户回答...")
        audio_data = self.single_record()

        # ASR转录用户回答
        user_response = self.asr_transcribe(audio_data)
        print(f"用户: {user_response}")
        return user_response

    def listen_and_transcribe(self):
        """录音并转写文本"""
        audio_data = self.single_record()
        if audio_data:
            return self.asr_transcribe(audio_data)
        return None

    def ask(self, question: str):
        """主动向用户提问并获取回答"""
        print(f"助手: {question}")

        # 语音合成并播放问题
        self.speak(question)

        # 等待用户回答
        print("等待用户回答...")
        user_response = self.listen_and_transcribe()
        print(f"用户: {user_response}")
        return user_response

    def get_conversation_history(self):
        """
        获取对话历史记录

        Returns:
            list: 对话消息列表
        """
        return self.messages

    def clear_conversation_history(self) -> None:
        """清空对话历史记录，仅保留系统消息"""
        if len(self.messages) > 1:
            system_message = self.messages[0]
            self.messages = [system_message]
            print("✅ 对话历史已清空")