#!/usr/bin/env python3
"""
脚本测试 - 验证导入和基本功能
"""

import sys
import os
from pathlib import Path

# 设置路径
project_root = Path(__file__).parent.parent
os.chdir(project_root / "graphrag" / "simple_graphrag")
sys.path.insert(0, str(project_root / "graphrag" / "simple_graphrag"))

try:
    print("🔍 测试导入...")

    # 测试 SimpleGraph 导入
    from simplegraph import SimpleGraph
    print("  ✓ SimpleGraph 导入成功")

    # 测试配置文件
    config_path = Path("config/config.yaml")
    if config_path.exists():
        print(f"  ✓ 配置文件存在")
    else:
        print(f"  ✗ 配置文件不存在: {config_path.absolute()}")
        sys.exit(1)

    # 测试 VLM 文件扫描
    from glob import glob
    vlm_pattern = str(project_root / "data/eval/profile1/*/analysis/*_vlm.json")
    vlm_files = glob(vlm_pattern)
    print(f"  ✓ 找到 {len(vlm_files)} 个 VLM 文件")

    if len(vlm_files) != 7:
        print(f"  ⚠️  警告: 期望 7 个文件，找到 {len(vlm_files)} 个")
    else:
        print(f"  ✓ 确认找到 7 个文件")

    print("\n✅ 所有测试通过！可以运行脚本")
    print("\n使用方法:")
    print("  cd scripts")
    print("  python reinit_graph_with_profile.py")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
