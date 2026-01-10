#!/usr/bin/env python3
"""
将旧的会话数据结构迁移到新的会话文件组织系统

旧结构:
data/
├── raw/
│   ├── logcat_20260110_000917.log
│   ├── uiautomator_20260110_000917.log
│   └── window_20260110_000917.log
├── screenshots/
│   └── screenshot_20260110_000947_779.png
├── sessions/
│   └── session_2026-01-10T00-09-16.536000Z.json
└── processed/
    ├── session_*_llm.json
    └── analysis/
        └── session_*_analysis_*.json

新结构:
data/
├── sessions/
│   └── 20260110_000916_536a/
│       ├── metadata.json
│       ├── raw/
│       │   ├── logcat.log
│       │   ├── uiautomator.log
│       │   └── window.log
│       ├── screenshots/
│       │   └── 000947_779.png (相对时间命名)
│       ├── processed/
│       │   ├── events.json
│       │   └── session_summary.json
│       └── analysis/
│           └── vlm_analysis.json
└── master_index.json
"""

import os
import json
import shutil
import re
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.learning.utils import (
    generate_session_id, create_session_folder,
    create_session_metadata, update_master_index, save_json
)


class SessionMigrator:
    """会话数据迁移工具"""

    def __init__(self, data_dir: str = "data", archive_dir: str = "archive"):
        self.data_dir = data_dir
        self.archive_dir = os.path.join(data_dir, archive_dir)
        self.sessions_dir = os.path.join(data_dir, "sessions")
        self.old_processed_dir = os.path.join(data_dir, "processed")
        self.old_raw_dir = os.path.join(data_dir, "raw")
        self.old_screenshots_dir = os.path.join(data_dir, "screenshots")
        self.migration_report = {
            "total_sessions": 0,
            "successful_migrations": 0,
            "failed_migrations": 0,
            "skipped_sessions": [],
            "errors": []
        }

    def migrate_all(self):
        """执行完整迁移"""
        print("=" * 80)
        print("会话数据迁移工具")
        print("=" * 80)
        print()

        # 检查旧数据是否存在
        if not os.path.exists(self.old_processed_dir):
            print("错误：未找到 data/processed 目录，可能没有旧会话数据需要迁移")
            return False

        # 扫描旧的会话文件
        old_sessions = self._scan_old_sessions()
        if not old_sessions:
            print("未找到旧格式的会话数据")
            return True

        print(f"找到 {len(old_sessions)} 个旧格式会话")
        print()

        # 创建备份目录
        self._prepare_backup_dirs()

        # 迁移每个会话
        for i, session_file in enumerate(old_sessions, 1):
            print(f"[{i}/{len(old_sessions)}] 迁移: {os.path.basename(session_file)}")
            try:
                self._migrate_session(session_file)
                self.migration_report["successful_migrations"] += 1
            except Exception as e:
                print(f"  ✗ 失败: {e}")
                self.migration_report["failed_migrations"] += 1
                self.migration_report["errors"].append({
                    "session": os.path.basename(session_file),
                    "error": str(e)
                })

        self.migration_report["total_sessions"] = len(old_sessions)

        # 输出迁移报告
        self._print_report()

        # 备份旧数据
        self._backup_old_data()

        return True

    def _scan_old_sessions(self):
        """扫描旧的会话文件"""
        sessions = []
        if not os.path.exists(self.old_processed_dir):
            return sessions

        for filename in os.listdir(self.old_processed_dir):
            if filename.endswith("_llm.json"):
                file_path = os.path.join(self.old_processed_dir, filename)
                # 对应的原始会话文件
                session_id = filename.replace("_llm.json", "")
                original_session = os.path.join(self.sessions_dir, f"{session_id}.json")
                if os.path.exists(original_session):
                    sessions.append(original_session)

        return sorted(sessions)

    def _migrate_session(self, old_session_file: str):
        """迁移单个会话"""
        # 读取原始会话数据
        with open(old_session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # 提取会话ID和时间戳
        old_session_id = os.path.splitext(os.path.basename(old_session_file))[0]
        start_time = session_data.get("context_window", {}).get("start_time")

        if not start_time:
            raise ValueError(f"无法从会话数据中提取开始时间")

        # 生成新的会话ID
        new_session_id = generate_session_id(start_time)
        print(f"  新会话ID: {new_session_id}")

        # 创建新会话文件夹
        session_folder = create_session_folder(self.data_dir, new_session_id)

        # 迁移raw文件
        self._migrate_raw_files(old_session_id, session_folder, start_time)

        # 迁移截图
        self._migrate_screenshots(old_session_id, session_folder, start_time)

        # 迁移处理后的数据
        self._migrate_processed_data(old_session_id, session_folder, session_data)

        # 迁移分析数据
        self._migrate_analysis_data(old_session_id, session_folder)

        # 创建metadata.json
        end_time = session_data.get("context_window", {}).get("end_time")
        metadata = create_session_metadata(
            session_id=new_session_id,
            start_time=start_time,
            end_time=end_time,
            status="completed",
            statistics={
                "total_events": len(session_data.get("events", [])),
                "screenshot_count": len(session_data.get("search_content", [])),
                "app_sessions": len(session_data.get("app_sessions", []))
            }
        )

        metadata_file = os.path.join(session_folder, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 更新全局索引
        update_master_index(self.data_dir, new_session_id, metadata)

        print(f"  ✓ 迁移成功")

    def _migrate_raw_files(self, old_session_id: str, session_folder: str, start_time: str):
        """迁移raw数据文件"""
        raw_folder = os.path.join(session_folder, "raw")

        # 从旧时间戳推断logcat文件名
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            timestamp_pattern = start_dt.strftime('%Y%m%d_%H%M')  # 只匹配年月日小时分钟
        except (ValueError, TypeError):
            timestamp_pattern = None

        # 查找并复制raw文件
        for raw_file in ["logcat", "uiautomator", "window"]:
            src_pattern = f"{raw_file}_{timestamp_pattern}" if timestamp_pattern else None

            # 尝试从data/raw目录找文件
            found = False
            if os.path.exists(self.old_raw_dir):
                for filename in os.listdir(self.old_raw_dir):
                    if src_pattern and filename.startswith(src_pattern):
                        src_file = os.path.join(self.old_raw_dir, filename)
                        dst_file = os.path.join(raw_folder, f"{raw_file}.log")
                        shutil.copy2(src_file, dst_file)
                        found = True
                        break

            if not found:
                print(f"  ⚠ 未找到 {raw_file} 文件")

    def _migrate_screenshots(self, old_session_id: str, session_folder: str, start_time: str):
        """迁移截图文件并重命名为相对时间格式"""
        screenshots_folder = os.path.join(session_folder, "screenshots")

        if not os.path.exists(self.old_screenshots_dir):
            return

        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return

        # 查找属于这个会话时间范围内的截图
        for filename in os.listdir(self.old_screenshots_dir):
            if not filename.startswith("screenshot_") or not filename.endswith(".png"):
                continue

            # 提取时间戳
            match = re.search(r'screenshot_(\d{8}_\d{6}_\d{3})\.png', filename)
            if not match:
                continue

            try:
                timestamp_str = match.group(1)
                screenshot_dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S_%f")
                screenshot_time = screenshot_dt.replace(microsecond=screenshot_dt.microsecond * 1000)

                # 计算相对于会话开始的时间偏移
                time_offset = (screenshot_time - start_dt).total_seconds()

                # 只迁移属于本会话时间范围内的截图（允许±60秒的容差）
                if 0 <= time_offset <= 3600:  # 假设会话最多1小时
                    # 将文件名转换为相对时间格式
                    offset_hours = int(time_offset // 3600)
                    offset_minutes = int((time_offset % 3600) // 60)
                    offset_seconds = int(time_offset % 60)
                    offset_millis = int((time_offset % 1) * 1000)

                    new_filename = f"{offset_hours:02d}{offset_minutes:02d}{offset_seconds:02d}_{offset_millis:03d}.png"
                    src_file = os.path.join(self.old_screenshots_dir, filename)
                    dst_file = os.path.join(screenshots_folder, new_filename)

                    shutil.copy2(src_file, dst_file)
            except (ValueError, TypeError):
                continue

    def _migrate_processed_data(self, old_session_id: str, session_folder: str, session_data: dict):
        """迁移处理后的数据"""
        processed_folder = os.path.join(session_folder, "processed")

        # 保存事件数据
        events_file = os.path.join(processed_folder, "events.json")
        events_data = {
            "session_id": old_session_id,
            "events": session_data.get("events", [])
        }
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)

        # 保存会话摘要（LLM就绪格式）
        summary_file = os.path.join(processed_folder, "session_summary.json")
        summary_data = {
            "session_info": session_data.get("context_window", {}),
            "user_activities": session_data.get("app_sessions", []),
            "screenshots": session_data.get("screenshots", []),
            "search_content": session_data.get("search_content", [])
        }
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

    def _migrate_analysis_data(self, old_session_id: str, session_folder: str):
        """迁移分析数据"""
        analysis_folder = os.path.join(session_folder, "analysis")

        if not os.path.exists(self.old_processed_dir):
            return

        # 查找对应的分析文件
        analysis_dir = os.path.join(self.old_processed_dir, "analysis")
        if not os.path.exists(analysis_dir):
            return

        for filename in os.listdir(analysis_dir):
            if old_session_id in filename and "analysis" in filename:
                src_file = os.path.join(analysis_dir, filename)
                dst_file = os.path.join(analysis_folder, "vlm_analysis.json")
                shutil.copy2(src_file, dst_file)
                break

    def _prepare_backup_dirs(self):
        """准备备份目录"""
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir)

    def _backup_old_data(self):
        """备份旧数据结构"""
        print()
        print("备份旧数据...")

        backup_map = {
            self.old_raw_dir: os.path.join(self.archive_dir, "raw"),
            self.old_screenshots_dir: os.path.join(self.archive_dir, "screenshots"),
            self.old_processed_dir: os.path.join(self.archive_dir, "processed"),
        }

        for src, dst in backup_map.items():
            if os.path.exists(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)
                print(f"  已备份: {src} -> {dst}")

    def _print_report(self):
        """输出迁移报告"""
        print()
        print("=" * 80)
        print("迁移报告")
        print("=" * 80)
        print(f"总会话数: {self.migration_report['total_sessions']}")
        print(f"成功迁移: {self.migration_report['successful_migrations']}")
        print(f"失败迁移: {self.migration_report['failed_migrations']}")

        if self.migration_report["errors"]:
            print()
            print("错误详情:")
            for error in self.migration_report["errors"]:
                print(f"  - {error['session']}: {error['error']}")

        print()
        print("✓ 迁移完成!")
        print(f"新数据位置: {self.sessions_dir}")
        print(f"全局索引: {os.path.join(self.data_dir, 'master_index.json')}")
        print()


def main():
    """主函数"""
    data_dir = "data"

    # 检查参数
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]

    # 检查数据目录
    if not os.path.exists(data_dir):
        print(f"错误：数据目录 {data_dir} 不存在")
        sys.exit(1)

    # 执行迁移
    migrator = SessionMigrator(data_dir)

    # 提示用户确认
    print("此工具将迁移旧的会话数据结构到新格式。")
    print("旧数据将被备份到 data/archive 目录。")
    print()

    response = input("是否继续? (y/n): ").strip().lower()
    if response != 'y':
        print("已取消迁移")
        sys.exit(0)

    success = migrator.migrate_all()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
