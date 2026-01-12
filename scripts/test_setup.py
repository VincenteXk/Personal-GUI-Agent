#!/usr/bin/env python3
"""
脚本验证脚本
检查脚本的导入和基本功能
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "graphrag" / "simple_graphrag"))

try:
    # 检查导入
    print("检查导入...")
    from simplegraph import SimpleGraph
    print("  ✓ SimpleGraph 导入成功")

    # 检查配置文件
    config_path = project_root / "graphrag" / "simple_graphrag" / "config" / "config.yaml"
    if config_path.exists():
        print(f"  ✓ 配置文件存在: {config_path}")
    else:
        print(f"  ✗ 配置文件不存在: {config_path}")
        sys.exit(1)

    # 检查 VLM 文件
    from glob import glob
    vlm_files = glob(str(project_root / "data/eval/profile1/*/analysis/*_vlm.json"))
    print(f"  ✓ 找到 {len(vlm_files)} 个 VLM 文件")

    for vlm_file in sorted(vlm_files)[:3]:
        print(f"    - {Path(vlm_file).name}")

    if len(vlm_files) > 3:
        print(f"    ... 还有 {len(vlm_files) - 3} 个文件")

    print("\n✓ 所有检查通过，可以运行脚本")

except Exception as e:
    print(f"\n✗ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
