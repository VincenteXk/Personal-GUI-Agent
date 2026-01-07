#!/usr/bin/env python3
"""
PersonalUI - 个性化GUI Agent系统

基于AutoGLM框架的个性化GUI agent，使用GraphRAG存储用户习惯，
通过learning mode学习用户行为并更新到GraphRAG，支持语音指令操作。

Usage:
    python main.py [OPTIONS]
"""

import argparse
import os
import sys
import json
import time
import threading
import subprocess
import shutil
from typing import Dict, Any, Optional

# 添加子模块路径
project_root = os.path.dirname(os.path.abspath(__file__))
autoglm_path = os.path.join(project_root, 'Open-AutoGLM')
sys.path.insert(0, autoglm_path)
sys.path.insert(0, os.path.join(project_root, 'learning_mode'))
sys.path.insert(0, os.path.join(project_root, 'graphrag'))

# 导入AutoGLM相关模块
try:
    from phone_agent.agent import PhoneAgent
    from phone_agent.config import ModelConfig, AgentConfig
    from phone_agent.device_factory import DeviceType, set_device_type
except ImportError:
    # 备用导入路径
    from Open_AutoGLM.phone_agent.agent import PhoneAgent
    from Open_AutoGLM.phone_agent.config import ModelConfig, AgentConfig
    from Open_AutoGLM.phone_agent.device_factory import DeviceType, set_device_type

# 导入语音模块
try:
    from phone_agent.voice import VoiceManager
except ImportError:
    VoiceManager = None

# 导入learning_mode相关模块
from learning_mode.behavior_analyzer import BehaviorAnalyzer
from learning_mode.vlm_analyzer import VLMAnalyzer

# 导入graphrag相关模块
from graphrag.simple_graphrag.simplegraph import SimpleGraph

# 导入本地模块
from observer import UserObserver
from refiner import InstructionRefiner
from knowledge_base import KnowledgeBase


def check_system_requirements(
    device_type: DeviceType = DeviceType.ADB
) -> bool:
    """
    Check system requirements before running the agent.

    Checks:
    1. ADB tool installed
    2. At least one Android device connected
    3. ADB Keyboard installed on the device

    Args:
        device_type: Type of device tool (currently only ADB supported).

    Returns:
        True if all checks pass, False otherwise.
    """
    print("🔍 Checking system requirements...")
    print("-" * 50)

    all_passed = True

    # Only support ADB for Android devices
    tool_name = "ADB"
    tool_cmd = "adb"

    # Check 1: Tool installed
    print(f"1. Checking {tool_name} installation...", end=" ")
    if shutil.which(tool_cmd) is None:
        print("❌ FAILED")
        print(f"   Error: {tool_name} is not installed or not in PATH.")
        print(f"   Solution: Install {tool_name}:")
        print("     - macOS: brew install android-platform-tools")
        print("     - Linux: sudo apt install android-tools-adb")
        print(
            "     - Windows: Download from https://developer.android.com/studio/releases/platform-tools"
        )
        all_passed = False
    else:
        # Double check by running version command
        try:
            version_cmd = [tool_cmd, "version"]
            result = subprocess.run(
                version_cmd, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version_line = result.stdout.strip().split("\n")[0]
                print(f"✅ OK ({version_line if version_line else 'installed'})")
            else:
                print("❌ FAILED")
                print(f"   Error: {tool_name} command failed to run.")
                all_passed = False
        except FileNotFoundError:
            print("❌ FAILED")
            print(f"   Error: {tool_name} command not found.")
            all_passed = False
        except subprocess.TimeoutExpired:
            print("❌ FAILED")
            print(f"   Error: {tool_name} command timed out.")
            all_passed = False

    # If tool is not installed, skip remaining checks
    if not all_passed:
        print("-" * 50)
        print("❌ System check failed. Please fix the issues above.")
        return False

    # Check 2: Device connected
    print("2. Checking connected devices...", end=" ")
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")
        # Filter out header and empty lines, look for 'device' status
        devices = [
            line for line in lines[1:] if line.strip() and "\tdevice" in line
        ]

        if not devices:
            print("❌ FAILED")
            print("   Error: No devices connected.")
            print("   Solution:")
            print("     1. Enable USB debugging on your Android device")
            print("     2. Connect via USB and authorize the connection")
            print(
                "     3. Or connect remotely: python main.py --connect <ip>:<port>"
            )
            all_passed = False
        else:
            device_ids = [d.split("\t")[0] for d in devices]
            print(
                f"✅ OK ({len(devices)} device(s): {', '.join(device_ids[:2])}{'...' if len(device_ids) > 2 else ''})"
            )
    except subprocess.TimeoutExpired:
        print("❌ FAILED")
        print(f"   Error: {tool_name} command timed out.")
        all_passed = False
    except Exception as e:
        print("❌ FAILED")
        print(f"   Error: {e}")
        all_passed = False

    # If no device connected, skip remaining checks
    if not all_passed:
        print("-" * 50)
        print("❌ System check failed. Please fix the issues above.")
        return False

    # Check 3: ADB Keyboard installed
    print("3. Checking ADB Keyboard...", end=" ")
    try:
        result = subprocess.run(
            ["adb", "shell", "ime", "list", "-s"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        ime_list = result.stdout.strip()

        if "com.android.adbkeyboard/.AdbIME" in ime_list:
            print("✅ OK")
        else:
            print("❌ FAILED")
            print("   Error: ADB Keyboard is not installed on the device.")
            print("   Solution:")
            print("     1. Download ADB Keyboard APK from:")
            print(
                "        https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk"
            )
            print("     2. Install it on your device: adb install ADBKeyboard.apk")
            print(
                "     3. Enable it in Settings > System > Languages & Input > Virtual Keyboard"
            )
            all_passed = False
    except subprocess.TimeoutExpired:
        print("❌ FAILED")
        print("   Error: ADB command timed out.")
        all_passed = False
    except Exception as e:
        print("❌ FAILED")
        print(f"   Error: {e}")
        all_passed = False

    print("-" * 50)

    if all_passed:
        print("✅ All system checks passed!\n")
    else:
        print("❌ System check failed. Please fix the issues above.")

    return all_passed


def check_model_api(base_url: str, model_name: str, api_key: str = "EMPTY") -> bool:
    """
    Check if the model API is accessible and the specified model exists.

    Checks:
    1. Network connectivity to the API endpoint
    2. Model exists in the available models list

    Args:
        base_url: The API base URL
        model_name: The model name to check
        api_key: The API key for authentication

    Returns:
        True if all checks pass, False otherwise.
    """
    # Try to import OpenAI
    try:
        from openai import OpenAI
    except ImportError:
        print("❌ OpenAI library not installed. Cannot check model API.")
        print("   Solution: pip install openai")
        return False
        
    print("🔍 Checking model API...")
    print("-" * 50)

    all_passed = True

    # Check 1: Network connectivity using chat API
    print(f"1. Checking API connectivity ({base_url})...", end=" ")
    try:
        # Create OpenAI client
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0)

        # Use chat completion to test connectivity (more universally supported than /models)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            temperature=0.0,
            stream=False,
        )

        # Check if we got a valid response
        if response.choices and len(response.choices) > 0:
            print("✅ OK")
        else:
            print("❌ FAILED")
            print("   Error: Received empty response from API")
            all_passed = False

    except Exception as e:
        print("❌ FAILED")
        error_msg = str(e)

        # Provide more specific error messages
        if "Connection refused" in error_msg or "Connection error" in error_msg:
            print(f"   Error: Cannot connect to {base_url}")
            print("   Solution:")
            print("     1. Check if the model server is running")
            print("     2. Verify the base URL is correct")
            print(f"     3. Try: curl {base_url}/chat/completions")
        elif "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            print(f"   Error: Connection to {base_url} timed out")
            print("   Solution:")
            print("     1. Check your network connection")
            print("     2. Verify the server is responding")
        elif (
            "Name or service not known" in error_msg
            or "nodename nor servname" in error_msg
        ):
            print(f"   Error: Cannot resolve hostname")
            print("   Solution:")
            print("     1. Check the URL is correct")
            print("     2. Verify DNS settings")
        else:
            print(f"   Error: {error_msg}")

        all_passed = False

    print("-" * 50)

    if all_passed:
        print("✅ Model API checks passed!\n")
    else:
        print("❌ Model API check failed. Please fix the issues above.")

    return all_passed


class PersonalUI:
    """PersonalUI系统主类，整合所有功能模块"""

    def __init__(self, args, config_path: str = "config.json"):
        """
        初始化PersonalUI系统

        Args:
            args: 命令行参数对象
            config_path: 配置文件路径
        """
        self.args = args
        # 加载配置并合并命令行参数
        self.config = self._load_and_merge_config(config_path)
        self.knowledge_base = KnowledgeBase()
        self.refiner = InstructionRefiner(model_config=self._get_model_config())
        self.observer = UserObserver()
        self.phone_agent = None
        self.behavior_analyzer = BehaviorAnalyzer()
        self.vlm_analyzer = None
        self.graphrag = None
        self._init_modules()

    def _load_and_merge_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件并使用命令行参数覆盖"""
        # 默认配置
        config = {
            "model_config": {
                "base_url": "http://localhost:8000/v1",
                "model": "autoglm-phone-9b",
                "api_key": "EMPTY"
            },
            "agent_config": {
                "max_steps": 100,
                "device_id": None,
                "lang": "cn"
            },
            "learning_config": {
                "api_key": "",
                "model": "glm-4.1v-thinking-flash",
                "output_dir": "data"
            },
            "graphrag_config": {
                "config_path": "graphrag/config.yaml",
                "max_concurrent_tasks": 3
            }
        }

        # 加载 JSON
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    self._deep_update(config, user_config)
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}, 使用默认配置")

        # 命令行参数覆盖 (CLI Args > Config File > Defaults)
        if hasattr(self.args, 'base_url') and self.args.base_url:
            config["model_config"]["base_url"] = self.args.base_url
        if hasattr(self.args, 'model') and self.args.model:
            config["model_config"]["model"] = self.args.model
        if hasattr(self.args, 'apikey') and self.args.apikey and self.args.apikey != "EMPTY":
            config["model_config"]["api_key"] = self.args.apikey

        # 设备ID覆盖
        if hasattr(self.args, 'device_id') and self.args.device_id:
            config["agent_config"]["device_id"] = self.args.device_id

        # Max steps覆盖
        if hasattr(self.args, 'max_steps') and self.args.max_steps != 100:
            config["agent_config"]["max_steps"] = self.args.max_steps

        # 语言覆盖
        if hasattr(self.args, 'lang') and self.args.lang:
            config["agent_config"]["lang"] = self.args.lang

        return config
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """递归更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def _get_model_config(self) -> ModelConfig:
        """获取模型配置对象"""
        return ModelConfig(
            base_url=self.config["model_config"]["base_url"],
            model_name=self.config["model_config"]["model"],
            api_key=self.config["model_config"]["api_key"],
            lang=self.config["agent_config"]["lang"]
        )

    def _init_modules(self):
        """初始化各个模块"""
        print("🚀 初始化核心模块...")
        model_conf = self._get_model_config()

        # 初始化 PhoneAgent
        agent_conf = AgentConfig(
            max_steps=self.config["agent_config"]["max_steps"],
            device_id=self.config["agent_config"]["device_id"],
            lang=self.config["agent_config"]["lang"]
        )
        try:
            self.phone_agent = PhoneAgent(model_config=model_conf, agent_config=agent_conf)
        except Exception as e:
            print(f"⚠️ PhoneAgent 初始化警告: {e}")

        # 初始化 VLM (用于感知)
        learn_conf = self.config["learning_config"]
        if learn_conf["api_key"]:
            self.vlm_analyzer = VLMAnalyzer(
                api_key=learn_conf["api_key"],
                model=learn_conf["model"]
            )

        # 初始化 GraphRAG
        try:
            rag_conf_path = self.config["graphrag_config"]["config_path"]
            if os.path.exists(rag_conf_path):
                self.graphrag = SimpleGraph(
                    config_path=rag_conf_path,
                    max_concurrent_tasks=self.config["graphrag_config"]["max_concurrent_tasks"]
                )
        except Exception as e:
            print(f"⚠️ GraphRAG 初始化跳过: {e}")
    
    def start_learning_mode(self, duration: Optional[int] = None, background: bool = False):
        """启动学习模式"""
        print("🎓 启动学习模式...")
        
        if background:
            # 后台学习模式
            self.behavior_analyzer.start_background_learning()
            print("后台学习模式已启动，按Ctrl+C停止")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n接收到停止信号，正在停止后台学习模式...")
                self.behavior_analyzer.stop_background_learning()
        else:
            # 前台学习模式
            sessions = self.behavior_analyzer.collect_and_process(duration_seconds=duration)
            
            if sessions and self.vlm_analyzer:
                # 分析收集到的数据
                print("🔍 分析用户行为数据...")
                output_dir = self.config["learning_config"]["output_dir"]
                sessions_dir = os.path.join(output_dir, "processed")
                
                result = self.vlm_analyzer.analyze_latest_session(sessions_dir)
                
                if "error" not in result and self.graphrag:
                    # 将分析结果存储到GraphRAG
                    self._store_analysis_to_graphrag(result)
    
    def _store_analysis_to_graphrag(self, analysis_result: Dict[str, Any]):
        """将分析结果存储到GraphRAG"""
        if not self.graphrag:
            print("GraphRAG未初始化，跳过存储")
            return
        
        try:
            # 提取分析结果中的关键信息
            if "analysis" in analysis_result and "analysis" in analysis_result["analysis"]:
                analysis = analysis_result["analysis"]["analysis"]
                
                # 构建任务描述
                task_description = f"用户行为分析: {analysis.get('main_action', '未知行为')}"
                if "intent" in analysis:
                    task_description += f", 意图: {analysis['intent']}"
                
                # 提交到GraphRAG
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                task_id = loop.run_until_complete(self.graphrag.submit_task(task_description))
                print(f"分析结果已提交到GraphRAG，任务ID: {task_id}")
                loop.close()
        except Exception as e:
            print(f"存储分析结果到GraphRAG失败: {e}")
    
    def start_execution_mode(self, task: str, voice_mode: bool = False):
        """启动执行模式"""
        print(f"🚀 启动执行模式，任务: {task}")
        
        # 初始化语音模块
        voice_manager = None
        if voice_mode:
            try:
                from Open_AutoGLM.phone_agent.voice import VoiceManager
                voice_manager = VoiceManager()
                print("🎤 语音模式已就绪！")
            except ImportError:
                print("❌ 错误: 未找到 Open_AutoGLM.phone_agent.voice 模块，无法启动语音模式。")
                return
        
        # 1. 使用InstructionRefiner优化指令
        refined_task = self.refiner.refine_task(task)
        
        # 2. 使用PhoneAgent执行任务
        result = self.phone_agent.run(refined_task)
        print(f"任务执行结果: {result}")
        
        return result
    
    def start_interactive_mode(self, voice_mode: bool = False):
        """启动交互模式"""
        # 初始化语音模块
        voice_manager = None
        if voice_mode:
            try:
                from Open_AutoGLM.phone_agent.voice import VoiceManager
                voice_manager = VoiceManager()
                print("🎤 语音模式已就绪！")
            except ImportError:
                print("❌ 错误: 未找到 Open_AutoGLM.phone_agent.voice 模块，无法启动语音模式。")
                return
        
        print("\n进入交互模式。输入 'quit' 退出。\n")
    
        while True:
            try:
                # 判断是语音输入还是文字输入
                if voice_mode and voice_manager:
                    # 1. 语音模式逻辑
                    user_input = input("\n[按回车键开始说话] (输入 'q' 退出) >> ").strip()
                    
                    if user_input.lower() in ("quit", "exit", "q"):
                        print("再见!")
                        break
                    
                    # 调用语音识别
                    task = voice_manager.listen_and_transcribe()
                    
                    if not task:
                        print("⚠️ 未检测到语音，请重试")
                        continue
                        
                    print(f"🗣️ 识别到指令: {task}")
                    
                    # (可选) 让用户确认一下识别是否准确
                    confirm = input("确认执行? [Y/n]: ").strip().lower()
                    if confirm == 'n':
                        print("已取消，请重新录入。")
                        continue

                else:
                    # 2. 原有的文字输入逻辑
                    task = input("输入您的任务: ").strip()
                    
                if task.lower() in ("quit", "exit", "q"):
                    print("再见!")
                    break

                if not task:
                    continue

                print()
                refined_task = self.refiner.refine_task(task)
                result = self.phone_agent.run(refined_task)
                print(f"\n结果: {result}\n")
                self.phone_agent.reset()

            except KeyboardInterrupt:
                print("\n\n已中断。再见!")
                break
            except Exception as e:
                print(f"\n错误: {e}\n")
    
    def start_observer_mode(self):
        """启动观察模式"""
        print("👁️ 启动观察模式...")
        self.observer.start_learning_loop()
    
    def check_system_requirements(self, device_type: DeviceType = DeviceType.ADB) -> bool:
        """检查系统要求"""
        return check_system_requirements(device_type)


def handle_device_commands(args) -> bool:
    """
    处理纯设备管理命令

    Returns:
        bool: 如果处理了设备命令则返回True，否则返回False
    """
    # 列出设备
    if hasattr(args, 'list_devices') and args.list_devices:
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            print(result.stdout)
            return True
        except Exception as e:
            print(f"列出设备失败: {e}")
            return True

    # 连接设备
    if hasattr(args, 'connect') and args.connect:
        try:
            result = subprocess.run(['adb', 'connect', args.connect], capture_output=True, text=True)
            print(result.stdout)
            return True
        except Exception as e:
            print(f"连接设备失败: {e}")
            return True

    # 断开设备
    if hasattr(args, 'disconnect') and args.disconnect:
        try:
            result = subprocess.run(['adb', 'disconnect', args.disconnect], capture_output=True, text=True)
            print(result.stdout)
            return True
        except Exception as e:
            print(f"断开设备失败: {e}")
            return True

    # 启用TCP/IP
    if hasattr(args, 'enable_tcpip') and args.enable_tcpip:
        try:
            result = subprocess.run(['adb', 'tcpip', str(args.enable_tcpip)], capture_output=True, text=True)
            print(result.stdout)
            return True
        except Exception as e:
            print(f"启用TCP/IP失败: {e}")
            return True

    return False


def parse_merged_args():
    """合并后的参数解析器"""
    parser = argparse.ArgumentParser(description="PersonalUI - 个性化智能手机 Agent")

    # --- 全局配置参数 ---
    parser.add_argument("--device-id", "-d", help="指定设备 ID")
    parser.add_argument("--connect", "-c", help="连接远程设备 (ip:port)")
    parser.add_argument("--disconnect", help="断开设备")
    parser.add_argument("--list-devices", action="store_true", help="列出设备并退出")
    parser.add_argument("--enable-tcpip", type=int, metavar="PORT", help="开启TCP调试端口")

    parser.add_argument("--base-url", help="模型 API Base URL")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--apikey", help="模型 API Key")
    parser.add_argument("--max-steps", type=int, default=100, help="最大步数")
    parser.add_argument("--lang", choices=["cn", "en"], default="cn", help="语言")

    # --- 子命令结构 ---
    subparsers = parser.add_subparsers(dest="command", help="操作模式")

    # 1. 运行模式
    run_parser = subparsers.add_parser("run", help="执行自动化任务")
    run_parser.add_argument("task", nargs="?", help="要执行的任务指令")
    run_parser.add_argument("--voice", action="store_true", help="开启语音输入")

    # 2. 学习模式
    learn_parser = subparsers.add_parser("learn", help="学习用户习惯")
    learn_parser.add_argument("--duration", type=int, default=300, help="学习时长(秒)")
    learn_parser.add_argument("--background", "-b", action="store_true", help="后台静默学习")

    # 3. 检查模式
    subparsers.add_parser("check", help="检查系统环境")

    # 4. 辅助命令
    subparsers.add_parser("list-apps", help="列出支持的应用")

    return parser.parse_args()


def main():
    """主入口函数"""
    args = parse_merged_args()

    # 1. 设置全局设备类型（仅支持 ADB）
    set_device_type(DeviceType.ADB)

    # 2. 处理纯设备命令 (无需初始化Agent)
    if handle_device_commands(args):
        return

    # 3. 系统检查命令
    if hasattr(args, 'command') and args.command == "check":
        check_system_requirements()
        check_model_api(
            args.base_url or "http://localhost:8000/v1",
            args.model or "autoglm-phone-9b"
        )
        return

    # 4. 列出应用命令
    if hasattr(args, 'command') and args.command == "list-apps":
        print("支持的应用列表:")
        print("  - WeChat")
        print("  - Alipay")
        print("  - Others...")
        return

    # 5. 初始化 PersonalUI (注入 args)
    app = PersonalUI(args)

    # 6. 命令分发
    if hasattr(args, 'command'):
        if args.command == "learn":
            # 确保设备连接
            if not check_system_requirements():
                sys.exit(1)
            app.start_learning_mode(args.duration, args.background)

        elif args.command == "run":
            # 确保系统就绪
            if not check_system_requirements():
                sys.exit(1)
            app.start_execution_mode(args.task, args.voice)

    else:
        # 默认行为：显示帮助
        print("请指定命令: run, learn, check, list-apps")
        print("使用 --help 查看完整帮助")



if __name__ == "__main__":
    main()