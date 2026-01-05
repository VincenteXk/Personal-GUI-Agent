#!/usr/bin/env python3
"""
统一命令行工具
整合了数据收集、VLM分析和图数据库集成功能
"""

import argparse
import sys
import os
import time
import json
from typing import Dict, Any, Optional

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from behavior_analyzer import BehaviorAnalyzer
from vlm_analyzer import VLMAnalyzer


class ConfigManager:
    """统一配置管理"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "api_key": "",
            "model": "glm-4.1v-thinking-flash",
            "output_dir": "data",
            "background_check_interval": 60,
            "analysis_interval": 300
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}, 使用默认配置")
        
        return default_config
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)


class UnifiedCLI:
    """统一命令行工具"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
    
    def collect_data(self, duration: Optional[int] = None, background: bool = False, stop_background: bool = False):
        """数据收集功能"""
        output_dir = self.config_manager.get("output_dir")
        analyzer = BehaviorAnalyzer(output_dir)
        
        if stop_background:
            # 停止后台学习模式
            analyzer.stop_background_learning()
            print("后台学习模式已停止")
        elif background:
            # 启动后台学习模式
            analyzer.start_background_learning()
            print("后台学习模式已启动，按Ctrl+C停止或使用--stop-background参数停止")
            try:
                # 保持主线程运行
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n接收到停止信号，正在停止后台学习模式...")
                analyzer.stop_background_learning()
        else:
            # 收集并处理数据
            sessions = analyzer.collect_and_process(duration_seconds=duration)
            
            if sessions:
                # 获取最新会话用于LLM
                latest_session = analyzer.get_latest_session_for_llm()
                if latest_session:
                    print("\n最新会话数据（用于LLM分析）：")
                    print(json.dumps(latest_session, indent=2, ensure_ascii=False))
                    
                    # 指出喂给LLM的文件路径
                    sessions_dir = os.path.join(output_dir, "sessions")
                    if os.path.exists(sessions_dir):
                        session_files = [f for f in os.listdir(sessions_dir) if f.endswith(".json")]
                        if session_files:
                            session_files.sort(key=lambda x: os.path.getmtime(os.path.join(sessions_dir, x)))
                            latest_file = os.path.join(sessions_dir, session_files[-1])
                            print(f"\n可以将以下文件喂给LLM进行分析：")
                            print(f"文件路径: {latest_file}")
            else:
                print("未收集到会话数据")
    
    def analyze_data(self):
        """VLM分析功能"""
        api_key = self.config_manager.get("api_key")
        model = self.config_manager.get("model")
        output_dir = self.config_manager.get("output_dir")
        sessions_dir = os.path.join(output_dir, "processed")
        
        if not api_key:
            print("错误: 未找到API密钥")
            print(f"请在config.json文件中设置api_key字段")
            return
        
        # 创建VLM分析器
        analyzer = VLMAnalyzer(api_key=api_key, model=model)
        
        # 检查会话目录
        if not os.path.exists(sessions_dir):
            print(f"错误: 目录 {sessions_dir} 不存在")
            return
        
        print("开始分析最新会话...")
        result = analyzer.analyze_latest_session(sessions_dir)
        
        if "error" in result:
            print(f"分析失败: {result['error']}")
        else:
            print(f"分析成功，结果已保存到: {result['output_file']}")
            
            # 打印分析结果
            if "analysis" in result and "analysis" in result["analysis"]:
                analysis = result["analysis"]["analysis"]
                if "app_name" in analysis:
                    print(f"应用名称: {analysis['app_name']}")
                if "main_action" in analysis:
                    print(f"主要行为: {analysis['main_action']}")
                if "detailed_actions" in analysis:
                    print("详细行为:")
                    for action in analysis["detailed_actions"]:
                        print(f"  - {action}")
                if "intent" in analysis:
                    print(f"用户意图: {analysis['intent']}")
                if "confidence" in analysis:
                    print(f"分析置信度: {analysis['confidence']}")
    
    def show_latest_session(self):
        """显示最新会话数据"""
        output_dir = self.config_manager.get("output_dir")
        analyzer = BehaviorAnalyzer(output_dir)
        
        latest_session = analyzer.get_latest_session_for_llm()
        if latest_session:
            print("最新会话数据（用于LLM分析）：")
            print(json.dumps(latest_session, indent=2, ensure_ascii=False))
            
            # 指出喂给LLM的文件路径
            sessions_dir = os.path.join(output_dir, "sessions")
            if os.path.exists(sessions_dir):
                session_files = [f for f in os.listdir(sessions_dir) if f.endswith(".json")]
                if session_files:
                    session_files.sort(key=lambda x: os.path.getmtime(os.path.join(sessions_dir, x)))
                    latest_file = os.path.join(sessions_dir, session_files[-1])
                    print(f"\n可以将以下文件喂给LLM进行分析：")
                    print(f"文件路径: {latest_file}")
        else:
            print("没有找到会话数据，请先运行数据收集")


def main():
    parser = argparse.ArgumentParser(description="GUI Agent用户行为学习与分析系统统一命令行工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 数据收集命令
    collect_parser = subparsers.add_parser("collect", help="收集用户行为数据")
    collect_parser.add_argument("--duration", "-d", type=int, default=300, 
                               help="数据收集持续时间（秒），默认为300秒（5分钟）")
    collect_parser.add_argument("--background", "-b", action="store_true",
                               help="启动后台学习模式，通过全局变量控制结束时机")
    collect_parser.add_argument("--stop-background", "-s", action="store_true",
                               help="停止后台学习模式")
    
    # 数据分析命令
    analyze_parser = subparsers.add_parser("analyze", help="分析用户行为数据")
    
    # 显示最新会话命令
    show_parser = subparsers.add_parser("show", help="显示最新会话数据")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = UnifiedCLI()
    
    if args.command == "collect":
        cli.collect_data(
            duration=args.duration,
            background=args.background,
            stop_background=args.stop_background
        )
    elif args.command == "analyze":
        cli.analyze_data()
    elif args.command == "show":
        cli.show_latest_session()


if __name__ == "__main__":
    main()