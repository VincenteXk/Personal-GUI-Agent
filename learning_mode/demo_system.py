#!/usr/bin/env python3
"""
GUI Agent用户行为学习与分析系统演示脚本
演示整个系统的工作流程：在线记录 -> 离线分析 -> 喂给图数据库
"""

import os
import sys
import time
import argparse
import subprocess

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_command(cmd, description):
    """运行命令并处理结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"错误: {result.stderr}")
    
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description="GUI Agent用户行为学习与分析系统演示")
    parser.add_argument("--duration", "-d", type=int, default=60,
                       help="数据收集持续时间（秒），默认为60秒")
    parser.add_argument("--skip-collection", "-s", action="store_true",
                       help="跳过数据收集，直接使用已有数据进行分析")
    parser.add_argument("--skip-analysis", "-a", action="store_true",
                       help="跳过VLM分析")
    
    args = parser.parse_args()
    
    print("GUI Agent用户行为学习与分析系统演示")
    print("=" * 60)
    print(f"数据收集持续时间: {args.duration}秒")
    
    # 步骤1: 数据收集
    if not args.skip_collection:
        success = run_command(
            f"python unified_cli.py collect --duration {args.duration}",
            "收集Android用户行为数据"
        )
        if not success:
            print("数据收集失败，退出")
            return
    else:
        print("跳过数据收集，使用已有数据")
    
    # 步骤2: VLM分析
    if not args.skip_analysis:
        success = run_command(
            "python unified_cli.py analyze",
            "使用VLM分析用户行为"
        )
        if not success:
            print("VLM分析失败，退出")
            return
    else:
        print("跳过VLM分析")
    
    print("\n演示完成!")
    print("\n其他可用命令:")
    print("1. 启动后台学习: python unified_cli.py collect --background")
    print("2. 停止后台学习: python unified_cli.py collect --stop-background")
    print("3. 查看最新会话: python unified_cli.py show")
    print("4. 分析最新会话: python unified_cli.py analyze")

if __name__ == "__main__":
    main()