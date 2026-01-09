#!/usr/bin/env python3
"""最小化语音测试：直接测试 ASR + TTS"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.AutoGLM.voice import VoiceAssistant, AUDIO_RATE

# 初始化（加载模型）
print("初始化语音助手...")
va = VoiceAssistant()

print("\n=== 测试 1: 识别能力 ===")
print("请准备录音...")
input("按回车开始录音（说话5秒后会自动停止）: ")

try:
    # 录音（修改超时参数简化流程）
    audio = va.single_record(max_duration=5, silence_duration=2)

    if audio:
        print(f"✅ 录音成功，长度: {len(audio)/AUDIO_RATE/2:.2f}秒")

        # 识别
        print("\n=== 测试 2: ASR 识别 ===")
        text = va.asr_transcribe(audio)

        if text:
            print(f"✅ 识别成功: {text}")

            # 播放识别结果
            print("\n=== 测试 3: TTS 合成播放 ===")
            print(f"播放: {text}")
            va.speak(text)
            print("✅ 播放完成")
        else:
            print("❌ 识别失败")
    else:
        print("❌ 录音失败或未检测到语音")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
