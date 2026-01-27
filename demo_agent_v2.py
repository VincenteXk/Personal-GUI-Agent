"""演示脚本 - 使用TaskAgentV2"""

from openai import OpenAI
from task_framework.agent_v2 import TaskAgentV2
from task_framework.config import TaskAgentConfig
from task_framework.implementations import (
    TerminalUserInput,
    TerminalUserInteraction,
    VoiceUserInput,
    VoiceUserInteraction,
)
from task_framework.implementations.profile_manager import GraphRAGProfileManager
from dotenv import load_dotenv
import os
import sys
import subprocess

load_dotenv()
subprocess.run(["adb", "shell", "settings", "put", "secure", "show_ime_with_hard_keyboard", "1"])
subprocess.run(["adb", "shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"])


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("个性化GUI助手 - TaskAgentV2演示")
    print("=" * 70 + "\n")

    # 初始化客户端
    client = OpenAI(
        base_url=os.getenv("MODEL_BASE_URL", "https://api.xiaomimimo.com/v1"),
        api_key=os.getenv("MODEL_API_KEY"),
    )

    # 配置Agent
    config = TaskAgentConfig(
        max_steps=20,
        max_retries=3,
        verbose=True,
        language="zh",
        voice_mode=True,  # 设置为True启用语音模式
        enable_onboarding=False,
        enable_minimal_ask=True,
        enable_plan_preview=True,
        enable_preference_update=True,
        cleanup_context_after_task=True,
        model_base_url=os.getenv("MODEL_BASE_URL"),
        model_api_key=os.getenv("MODEL_API_KEY"),
        model_name=os.getenv("MODEL_NAME", "mimo-v2-flash"),
    )

    # 初始化用户接口 - 支持语音模式
    if config.voice_mode:
        # 添加src目录到sys.path以导入VoiceAssistant
        src_path = os.path.join(os.path.dirname(__file__), "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from AutoGLM.voice import VoiceAssistant

        print("[信息] 正在初始化语音模式...")
        voice_assistant = VoiceAssistant()

        terminal_input = TerminalUserInput()
        terminal_interaction = TerminalUserInteraction()

        user_input = VoiceUserInput(
            terminal_input, voice_assistant, voice_mode=True
        )
        user_interaction = VoiceUserInteraction(
            terminal_interaction, voice_assistant, voice_mode=True
        )

        print("[成功] 语音模式已启用")
    else:
        user_input = TerminalUserInput()
        user_interaction = TerminalUserInteraction()

    # 初始化用户画像管理器
    profile_manager = GraphRAGProfileManager(
        graphrag_url=os.getenv("GRAPHRAG_URL", "http://localhost:8000"),
        user_id="default_user"
    )

    # 创建Agent
    agent = TaskAgentV2(
        user_input=user_input,
        user_interaction=user_interaction,
        profile_manager=profile_manager,
        model_client=client,
        config=config,
    )

    # 运行Agent
    agent.run()


if __name__ == "__main__":
    main()