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
import pygame
import io
import re
from typing import Optional, Any, Dict, List
from openai import OpenAI
from funasr import AutoModel

# 创建线程锁用于PyAudio资源的线程安全访问
pyaudio_lock = threading.Lock()


# 配置参数
AUDIO_RATE = 16000
CHUNK = 1024
VAD_MODE = 3

# API配置
API_KEY = "sk-cd1cfeb5f1874d4cb89b2430a7c8ca5b"
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

    def __init__(self, api_key: str = API_KEY, base_url: str = BASE_URL, model: str = "deepseek-chat", system_prompt: str = "你是一个智能语音助手，能够帮助用户完成各种任务。请用简体中文回答用户的问题。"):
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
        self.messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 初始化音频系统
        self.pyaudio_instance = pyaudio.PyAudio()
        self.pyaudio_lock = threading.Lock()
        
        # 初始化模型
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(VAD_MODE)
        print("加载ASR模型...")
        self.asr_model = AutoModel(model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
        
        print("连接DeepSeek API...")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        
        # 初始化pygame mixer
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
    
    def __del__(self):
        """析构函数，清理资源"""
        try:
            if hasattr(self, 'pyaudio_instance') and self.pyaudio_instance:
                self.pyaudio_instance.terminate()
        except:
            pass
        
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except:
            pass
    
    def check_vad_activity(self, audio_data):
        """检测语音活动"""
        step = int(AUDIO_RATE * 0.02)
        flag_rate = round(0.4 * len(audio_data) // step)
        return sum(1 for i in range(0, len(audio_data), step)
                   if len(chunk := audio_data[i:i + step]) == step and self.vad.is_speech(chunk, AUDIO_RATE)) > flag_rate
    
    def single_record(self, max_duration: int = 10, min_duration: int = 1, silence_duration: float = 1.0):
        """单次录音功能，支持VAD检测，带自动停止功能
        Args:
            max_duration: 最大录音时长（秒）
            min_duration: 最短录音时长（秒）
            silence_duration: 检测到静音后停止录音的时长（秒）
        """
        with self.pyaudio_lock:
            stream = self.pyaudio_instance.open(format=pyaudio.paInt16, channels=1, rate=AUDIO_RATE, input=True, frames_per_buffer=CHUNK)
            
            audio_buffer = []
            print("开始录音，请说话...")
            
            # 计算参数
            max_chunks = int(AUDIO_RATE / CHUNK * max_duration)
            min_chunks = int(AUDIO_RATE / CHUNK * min_duration)
            silence_chunks = int(silence_duration * AUDIO_RATE / CHUNK)
            
            chunks_recorded = 0
            silence_chunks_count = 0
            speech_started = False
            
            try:
                while chunks_recorded < max_chunks:
                    data = stream.read(CHUNK)
                    chunks_recorded += 1
                    
                    # 将字节数据转换为适合VAD检测的格式
                    # VAD需要16位PCM数据，采样率为8000、16000或32000Hz
                    # 我们需要确保数据长度符合要求（10ms、20ms或30ms的音频块）
                    if len(data) == CHUNK * 2:  # 确保是16位音频
                        # 检查当前块是否有语音
                        is_speech = self.vad.is_speech(data, AUDIO_RATE)
                        
                        if is_speech:
                            # 检测到语音，添加到缓冲区
                            audio_buffer.append(data)
                            speech_started = True
                            silence_chunks_count = 0  # 重置静音计数
                        else:
                            # 检测到静音
                            if speech_started:
                                # 如果已经开始录音，则添加静音块
                                audio_buffer.append(data)
                            
                            silence_chunks_count += 1
                    else:
                        # 数据长度不符合要求，添加到缓冲区
                        audio_buffer.append(data)
                    
                    # 如果已达到最小录音时长，且连续静音超过阈值，则停止录音
                    if chunks_recorded >= min_chunks and silence_chunks_count >= silence_chunks:
                        print(f"检测到{silence_duration}秒静音，停止录音")
                        break
            
                stream.stop_stream()
                stream.close()
            
                # 检查录音是否包含语音
                raw_audio = b''.join(audio_buffer)
                if speech_started:
                    print("检测到语音")
                    return raw_audio
                else:
                    print("未检测到语音活动")
                    return None
            except Exception as e:
                stream.stop_stream()
                stream.close()
                raise e
    
    def asr_transcribe(self, audio_data):
        """ASR语音转录"""
        if not audio_data:
            return None
            
        # 使用内存中的音频数据，避免创建临时文件
        audio_stream = io.BytesIO()
        with wave.open(audio_stream, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(AUDIO_RATE)
            wf.writeframes(audio_data)
        
        audio_stream.seek(0)
        print(f"识别中...({len(audio_data)/AUDIO_RATE:.2f}秒)")
        start_time = time.time()
        
        res = self.asr_model.generate(input=audio_stream, cache={}, language="auto", use_itn=False)
        asr_time = time.time() - start_time
        print(f"识别耗时: {asr_time:.2f}秒")
        
        if res and (text := res[0]['text'].split(">")[-1].strip().replace(" ", "")):
            print(f"识别: {text}")
            return text
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
            model="deepseek-chat",
            messages=self.messages,
            max_tokens=200
        )
        llm_time = time.time() - start_time
        
        # 使用正则表达式过滤掉中英字符和标点符号外的所有字符
        full_response = response.choices[0].message.content
        # 保留中英文字符、数字、空格、中英文标点符号
        filtered_response = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.,!?;:：，。！？；：""''（）【】《》\\-\n]', '', full_response)
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
            
        print("合成中...")
        start_time = time.time()
        temp_file = "temp_tts.mp3"
        
        # 创建通信对象并保存音频
        communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
        asyncio.run(communicate.save(temp_file))
        tts_time = time.time() - start_time
        print(f"TTS耗时: {tts_time:.2f}秒")
        
        # 播放音频
        start_time = time.time()
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        play_time = time.time() - start_time
        print(f"播放耗时: {play_time:.2f}秒")
        
        # 删除临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
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