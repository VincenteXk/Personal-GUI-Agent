#!/usr/bin/env python3
"""
测试新的会话文件组织系统

这个脚本测试：
1. 会话ID生成
2. 会话文件夹创建
3. 元数据创建和保存
4. 全局索引更新
5. 会话查询功能
6. 会话加载功能
"""

import os
import sys
import json
import shutil
import tempfile
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.learning.utils import (
    generate_session_id,
    create_session_folder,
    create_session_metadata,
    update_master_index,
    query_sessions_by_date_range,
    query_sessions_by_timestamp,
    get_recent_sessions,
    get_session_by_id,
    load_session_metadata,
    list_all_sessions,
    rebuild_master_index
)


class SessionOrganizationTestSuite:
    """会话文件组织系统测试套件"""

    def __init__(self):
        # 创建临时测试目录
        self.test_dir = tempfile.mkdtemp(prefix="session_test_")
        print(f"测试目录: {self.test_dir}")
        self.results = []

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("会话文件组织系统 - 测试套件")
        print("=" * 80)
        print()

        tests = [
            ("会话ID生成", self.test_session_id_generation),
            ("会话文件夹创建", self.test_create_session_folder),
            ("元数据创建", self.test_create_metadata),
            ("全局索引管理", self.test_master_index),
            ("会话查询 - 时间范围", self.test_query_by_date_range),
            ("会话查询 - 时间戳", self.test_query_by_timestamp),
            ("获取最近会话", self.test_get_recent_sessions),
            ("会话查询 - 按ID", self.test_get_session_by_id),
            ("会话加载", self.test_load_session_metadata),
            ("列出所有会话", self.test_list_all_sessions),
            ("重建索引", self.test_rebuild_index),
        ]

        for test_name, test_func in tests:
            try:
                print(f"[测试] {test_name}...", end=" ")
                test_func()
                print("✓ 通过")
                self.results.append((test_name, True, None))
            except AssertionError as e:
                print(f"✗ 失败: {e}")
                self.results.append((test_name, False, str(e)))
            except Exception as e:
                print(f"✗ 错误: {e}")
                self.results.append((test_name, False, str(e)))

        # 输出报告
        self._print_report()

        # 清理
        shutil.rmtree(self.test_dir)

    def test_session_id_generation(self):
        """测试会话ID生成"""
        # 测试默认生成
        sid1 = generate_session_id()
        assert sid1 is not None
        # YYYYMMDD_HHMMSS_xxxx 格式, 每个_分隔
        assert len(sid1) >= 16  # 至少16字符

        # 验证格式
        assert sid1[8] == '_'  # 日期和时间的分隔符
        assert '_' in sid1[9:]  # 时间和短ID之间有分隔符

        # 测试多个ID不同
        sid2 = generate_session_id()
        assert sid1 != sid2  # 由于随机ID，应该不同

        # 测试从时间戳生成
        timestamp = "2026-01-10T15:30:45.123000Z"
        sid3 = generate_session_id(timestamp)
        assert sid3.startswith("20260110_153045")

    def test_create_session_folder(self):
        """测试会话文件夹创建"""
        session_id = generate_session_id()
        folder = create_session_folder(self.test_dir, session_id)

        # 检查文件夹是否创建
        assert os.path.exists(folder)
        assert os.path.isdir(folder)

        # 检查子目录是否创建
        subdirs = ["raw", "screenshots", "processed", "analysis"]
        for subdir in subdirs:
            subdir_path = os.path.join(folder, subdir)
            assert os.path.exists(subdir_path), f"子目录 {subdir} 未创建"
            assert os.path.isdir(subdir_path)

    def test_create_metadata(self):
        """测试元数据创建"""
        session_id = generate_session_id()
        start_time = "2026-01-10T15:30:45.123000Z"
        end_time = "2026-01-10T15:45:12.456000Z"

        metadata = create_session_metadata(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            status="completed",
            statistics={
                "total_events": 100,
                "screenshot_count": 20,
                "app_sessions": 3
            }
        )

        # 验证metadata结构
        assert metadata["session_id"] == session_id
        assert metadata["start_time"] == start_time
        assert metadata["end_time"] == end_time
        assert metadata["status"] == "completed"
        assert metadata["duration_seconds"] > 0
        assert metadata["statistics"]["total_events"] == 100

    def test_master_index(self):
        """测试全局索引管理"""
        # 创建多个会话
        session_ids = []
        for i in range(3):
            session_id = generate_session_id()
            session_ids.append(session_id)

            metadata = create_session_metadata(
                session_id=session_id,
                start_time=f"2026-01-10T{10+i:02d}:00:00.000000Z",
                status="completed"
            )

            update_master_index(self.test_dir, session_id, metadata)

        # 检查索引文件是否创建
        index_file = os.path.join(self.test_dir, "master_index.json")
        assert os.path.exists(index_file)

        # 加载索引并验证
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)

        assert index["total_sessions"] == 3
        assert len(index["index_entries"]) == 3
        assert index["version"] == "2.0"

    def test_query_by_date_range(self):
        """测试按日期范围查询"""
        # 创建两个会话
        session_id1 = generate_session_id("2026-01-10T10:00:00Z")
        session_id2 = generate_session_id("2026-01-11T10:00:00Z")

        metadata1 = create_session_metadata(
            session_id=session_id1,
            start_time="2026-01-10T10:00:00Z",
            status="completed"
        )
        metadata2 = create_session_metadata(
            session_id=session_id2,
            start_time="2026-01-11T10:00:00Z",
            status="completed"
        )

        update_master_index(self.test_dir, session_id1, metadata1)
        update_master_index(self.test_dir, session_id2, metadata2)

        # 查询1月10日的会话
        results = query_sessions_by_date_range(
            self.test_dir,
            "2026-01-10T00:00:00Z",
            "2026-01-10T23:59:59Z"
        )

        assert len(results) == 1
        assert results[0]["session_id"] == session_id1

    def test_query_by_timestamp(self):
        """测试按时间戳查询"""
        session_id = generate_session_id("2026-01-10T10:00:00Z")
        metadata = create_session_metadata(
            session_id=session_id,
            start_time="2026-01-10T10:00:00Z",
            end_time="2026-01-10T10:30:00Z",
            status="completed"
        )

        update_master_index(self.test_dir, session_id, metadata)

        # 查询会话范围内的时间戳
        result = query_sessions_by_timestamp(
            self.test_dir,
            "2026-01-10T10:15:00Z"
        )

        assert result is not None
        assert result["session_id"] == session_id

    def test_get_recent_sessions(self):
        """测试获取最近会话"""
        # 创建3个会话
        for i in range(3):
            session_id = generate_session_id(f"2026-01-10T{10+i:02d}:00:00Z")
            metadata = create_session_metadata(
                session_id=session_id,
                start_time=f"2026-01-10T{10+i:02d}:00:00Z",
                status="completed"
            )
            update_master_index(self.test_dir, session_id, metadata)

        # 获取最近2个
        recent = get_recent_sessions(self.test_dir, n=2)

        assert len(recent) == 2
        # 验证按时间降序排列
        assert recent[0]["start_time"] > recent[1]["start_time"]

    def test_get_session_by_id(self):
        """测试按ID获取会话"""
        session_id = generate_session_id()
        metadata = create_session_metadata(
            session_id=session_id,
            start_time="2026-01-10T10:00:00Z",
            status="completed"
        )

        update_master_index(self.test_dir, session_id, metadata)

        # 按ID查询
        result = get_session_by_id(self.test_dir, session_id)

        assert result is not None
        assert result["session_id"] == session_id

    def test_load_session_metadata(self):
        """测试加载会话元数据"""
        session_id = generate_session_id()
        metadata = create_session_metadata(
            session_id=session_id,
            start_time="2026-01-10T10:00:00Z",
            status="completed"
        )

        # 创建会话文件夹并保存metadata
        session_folder = create_session_folder(self.test_dir, session_id)
        metadata_file = os.path.join(session_folder, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 加载元数据
        loaded = load_session_metadata(self.test_dir, session_id)

        assert loaded is not None
        assert loaded["session_id"] == session_id
        assert loaded["status"] == "completed"

    def test_list_all_sessions(self):
        """测试列出所有会话"""
        # 创建3个会话
        for i in range(3):
            session_id = generate_session_id(f"2026-01-10T{10+i:02d}:00:00Z")
            create_session_folder(self.test_dir, session_id)

            metadata = create_session_metadata(
                session_id=session_id,
                start_time=f"2026-01-10T{10+i:02d}:00:00Z",
                status="completed"
            )

            metadata_file = os.path.join(
                self.test_dir, "sessions", session_id, "metadata.json"
            )
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f)

        # 列出所有会话
        sessions = list_all_sessions(self.test_dir)

        assert len(sessions) == 3

    def test_rebuild_index(self):
        """测试重建索引"""
        # 创建两个会话，但不更新索引
        session_ids = []
        for i in range(2):
            session_id = generate_session_id(f"2026-01-10T{10+i:02d}:00:00Z")
            session_ids.append(session_id)

            session_folder = create_session_folder(self.test_dir, session_id)
            metadata = create_session_metadata(
                session_id=session_id,
                start_time=f"2026-01-10T{10+i:02d}:00:00Z",
                status="completed"
            )

            metadata_file = os.path.join(session_folder, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f)

        # 重建索引
        rebuild_master_index(self.test_dir)

        # 验证索引
        index_file = os.path.join(self.test_dir, "master_index.json")
        assert os.path.exists(index_file)

        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)

        assert index["total_sessions"] == 2
        assert len(index["index_entries"]) == 2

    def _print_report(self):
        """输出测试报告"""
        print()
        print("=" * 80)
        print("测试报告")
        print("=" * 80)

        passed = sum(1 for _, success, _ in self.results if success)
        failed = sum(1 for _, success, _ in self.results if not success)
        total = len(self.results)

        print(f"总计: {total} | 通过: {passed} | 失败: {failed}")
        print()

        if failed > 0:
            print("失败的测试:")
            for name, success, error in self.results:
                if not success:
                    print(f"  - {name}")
                    if error:
                        print(f"    {error}")
            print()
            return False

        print("✓ 所有测试通过!")
        print()
        return True


def main():
    """主函数"""
    suite = SessionOrganizationTestSuite()
    suite.run_all_tests()


if __name__ == "__main__":
    main()
