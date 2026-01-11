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
import requests  # 添加requests用于API调用

# 导入AutoGLM
from src.AutoGLM.agent import PhoneAgent, AgentConfig
from src.AutoGLM.model import ModelConfig

# 导入语音模块
from src.AutoGLM.voice import VoiceAssistant

# 导入learning_mode相关模块
from src.learning.behavior_analyzer import BehaviorAnalyzer
from src.learning.vlm_analyzer import VLMAnalyzer

# 导入本地模块
from src.core.refiner import InstructionRefiner

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
        self.refiner = InstructionRefiner(model_config=self._get_model_config())
        self.phone_agent = None
        self.behavior_analyzer = BehaviorAnalyzer()
        self.vlm_analyzer = None
        self.graphrag_api_url = self.config["graphrag_config"]["api_url"]
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
                "max_concurrent_tasks": 3,
                "api_url": "http://localhost:8001"  # 添加GraphRAG API地址
            }
        }

        # 加载 JSON
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                self._deep_update(config, user_config)

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
        self.phone_agent = PhoneAgent(model_config=model_conf, agent_config=agent_conf)

        # 初始化 VLM (用于感知)
        learn_conf = self.config["learning_config"]
        if learn_conf["api_key"]:
            self.vlm_analyzer = VLMAnalyzer(
                api_key=learn_conf["api_key"],
                model=learn_conf["model"],
                api_url=learn_conf.get("api_url")
            )
            print("✅ VLM Analyzer 已配置")
        else:
            print("⚠️ VLM Analyzer 未配置，行为学习模式不可用")

        # 检查GraphRAG API是否可用
        if self._check_graphrag_api():
            print("✅ GraphRAG API连接成功")
        else:
            print("⚠️ 无法连接到GraphRAG API")
    
    def _check_graphrag_api(self) -> bool:
        """检查GraphRAG API是否可用"""
        try:
            response = requests.get(f"{self.graphrag_api_url}/health")
            return response.status_code == 200
        except Exception as e:
            print(f"GraphRAG API连接失败: {e}")
            return False

    def start_learning_mode(self, duration: Optional[int] = None):
        """启动学习模式"""
        print("🎓 启动学习模式...")
        
        session_id,data_for_vlm = self.behavior_analyzer.collect_and_process(duration_seconds=duration)

        if session_id and self.vlm_analyzer:
            # 生成和分析LLM数据（传递会话ID）
            print("使用VLM分析用户行为数据...")

            vlm_analysis = self.vlm_analyzer.analyze_session_with_screenshots(data_for_vlm)

            with open('data/sessions/{0}/analysis/{0}_vlm.json'.format(session_id), "w", encoding="utf-8") as f:
                json.dump(vlm_analysis, f, ensure_ascii=False, indent=2)

        elif not self.vlm_analyzer:
            print("⚠️ VLM Analyzer 未配置，跳过视觉分析")
        else:
            print("⚠️ 未收集到足够的会话数据")
    
    def _store_analysis_to_graphrag(self, analysis_result: Dict[str, Any]):
        """将分析结果存储到GraphRAG API"""
        # 检查是否有可用的GraphRAG API
        if not self._check_graphrag_api():
            print("⚠️ GraphRAG API不可用，跳过存储分析结果")
            return
        
        # 提取分析结果中的关键信息
        if "analysis" in analysis_result and "analysis" in analysis_result["analysis"]:
            analysis = analysis_result["analysis"]["analysis"]
            
            # 构建任务描述
            task_description = f"用户行为分析: {analysis.get('main_action', '未知行为')}"
            if "intent" in analysis:
                task_description += f", 意图: {analysis['intent']}"
            
            # 构建请求数据
            data = {
                "task_description": task_description,
                "analysis_result": analysis_result
            }
            
            try:
                # 提交到GraphRAG API
                response = requests.post(f"{self.graphrag_api_url}/tasks", json=data, timeout=30)
                
                if response.status_code == 200:
                    task_id = response.json().get("task_id", "unknown")
                    print(f"✅ 分析结果已提交到GraphRAG，任务ID: {task_id}")
                else:
                    print(f"❌ 提交到GraphRAG失败，状态码: {response.status_code}, 响应: {response.text}")
            except requests.exceptions.ConnectionError:
                print(f"❌ 无法连接到GraphRAG API服务器: {self.graphrag_api_url}")
            except requests.exceptions.Timeout:
                print(f"❌ 连接到GraphRAG API超时: {self.graphrag_api_url}")
            except Exception as e:
                print(f"❌ 提交到GraphRAG API时发生错误: {e}")
        else:
            print("⚠️ 无效的分析结果格式，跳过存储")
    
    def start_execution_mode(self, task: str, voice_mode: bool = False):
        """启动执行模式"""
        print(f"🚀 启动执行模式，任务: {task}")
        
        # 初始化语音模块
        voice_assistant = None
        if voice_mode:
            from src.AutoGLM.voice import VoiceAssistant
            voice_assistant = VoiceAssistant()
            print("🎤 语音模式已就绪！")

        # 1. 使用InstructionRefiner优化指令
        refined_task = self.refiner.refine_task(task)

        # 2. 使用PhoneAgent执行任务
        result = self.phone_agent.run(refined_task)
        print(f"任务执行结果: {result}")
        
        # 如果是语音模式，将结果转换为语音播放
        if voice_mode and voice_assistant and result:
            voice_assistant.speak(result)
        
        return result
    
    def start_interactive_mode(self, voice_mode: bool = False):
        """启动交互模式"""
        # 初始化语音模块
        voice_assistant = None
        if voice_mode:
            from src.AutoGLM.voice import VoiceAssistant
            voice_assistant = VoiceAssistant()
            print("🎤 语音模式已就绪！")
        
        print("\n进入交互模式。输入 'quit' 退出。\n")
    
        while True:
            # 判断是语音输入还是文字输入
            if voice_mode and voice_assistant:
                # 1. 语音模式逻辑
                user_input = input("\n[按回车键开始说话] (输入 'q' 退出) >> ").strip()
                
                if user_input.lower() in ("quit", "exit", "q"):
                    print("再见!")
                    break
                
                # 调用语音识别
                audio_data = voice_assistant.single_record()
                if not audio_data:
                    print("⚠️ 未检测到语音，请重试")
                    continue
                    
                task = voice_assistant.asr_transcribe(audio_data)
                
                if not task:
                    print("⚠️ 语音识别失败，请重试")
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
            try:
                refined_task = self.refiner.refine_task(task)
                result = self.phone_agent.run(refined_task)
                print(f"\n结果: {result}\n")
                
                # 如果是语音模式，将结果转换为语音播放
                if voice_mode and voice_assistant and result:
                    voice_assistant.speak(result)
                    
                self.phone_agent.reset()
            except Exception as e:
                print(f"❌ 执行任务时发生错误: {e}")
    


def main():
    """主入口函数"""
    import argparse

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="PersonalUI - 个性化GUI Agent系统")
    parser.add_argument("--base-url", type=str, default=None, help="Model API base URL")
    parser.add_argument("--model", type=str, default=None, help="Model name")
    parser.add_argument("--apikey", type=str, default=None, help="API key")
    parser.add_argument("--device-id", type=str, default=None, help="Device ID")
    parser.add_argument("--max-steps", type=int, default=100, help="Max steps")
    parser.add_argument("--lang", type=str, default="cn", help="Language (cn/en)")
    parser.add_argument("--mode", type=str, default="interactive",
                       choices=["interactive", "learning", "execution"],
                       help="Running mode")

    args = parser.parse_args()

    # 初始化 PersonalUI
    app = PersonalUI(args)

    # 根据模式运行
    if args.mode == "learning":
        app.start_learning_mode(duration=60)
    elif args.mode == "execution":
        app.start_execution_mode()
    else:
        # 运行交互模式
        app.start_interactive_mode()


if __name__ == "__main__":
    main()