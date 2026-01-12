#!/usr/bin/env python3
"""
图数据库重新初始化与批量加载脚本

功能：
1. 重新初始化图数据库（备份现有数据）
2. 异步读取并加载 data/eval/profile1 下的7条 VLM 分析记录
3. 将 VLM 数据转换为自然语言，并提交到图数据库进行知识抽取

使用：
    python scripts/reinit_graph_with_profile.py
"""

import sys
import json
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from glob import glob
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
os.chdir(project_root / "graphrag" / "simple_graphrag")
sys.path.insert(0, str(project_root / "graphrag" / "simple_graphrag"))

from simplegraph import SimpleGraph
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VLMDataProcessor:
    """VLM 数据处理器"""

    @staticmethod
    def parse_session_time(session_id: str) -> str:
        """
        从 session_id 中提取时间信息

        session_id 格式: 20260112_112849_5cd5
        返回格式: 2026年1月12日11:28
        """
        try:
            # 例如: 20260112_112849_5cd5
            date_part = session_id[:8]  # 20260112
            time_part = session_id[9:15]  # 112849

            year = date_part[:4]  # 2026
            month = date_part[4:6]  # 01
            day = date_part[6:8]  # 12

            hour = time_part[:2]  # 11
            minute = time_part[2:4]  # 28

            # 去掉前导零并转换为中文格式
            year = int(year)
            month = int(month)
            day = int(day)
            hour = int(hour)
            minute = int(minute)

            return f"{year}年{month}月{day}日{hour}:{minute:02d}"
        except Exception as e:
            logger.warning(f"无法解析 session_id: {session_id}, 错误: {e}")
            return "未知时间"

    @staticmethod
    def vlm_to_text(vlm_data: Dict[str, Any], session_id: str) -> Optional[str]:
        """
        将 VLM 分析结果转换为自然语言（保留所有详细信息）

        Args:
            vlm_data: VLM JSON 数据
            session_id: 会话 ID

        Returns:
            转换后的自然语言文本，如果 VLM 分析失败返回 None
        """
        if not vlm_data.get("success"):
            logger.warning(f"VLM 分析失败: {vlm_data.get('error', 'unknown error')}")
            return None

        analysis = vlm_data.get("analysis", {})
        if not analysis:
            logger.warning("VLM 分析数据为空")
            return None

        # 提取时间信息
        date_str = VLMDataProcessor.parse_session_time(session_id)

        # 构建自然语言描述
        parts = [
            f"在{date_str}，我使用{analysis.get('app_name', '应用')}应用。",
            f"{analysis.get('main_action', '执行了某些操作')}。"
        ]

        # 详细操作序列
        if analysis.get('detailed_actions'):
            try:
                actions = []
                for action in analysis['detailed_actions']:
                    if isinstance(action, dict) and action.get('action'):
                        actions.append(action['action'])

                if actions:
                    actions_desc = "具体操作包括：" + "，".join(actions) + "。"
                    parts.append(actions_desc)
            except Exception as e:
                logger.debug(f"处理详细操作时出错: {e}")

        # 聊天详情（如果存在）
        if analysis.get('chat_details'):
            try:
                chat = analysis['chat_details']
                if isinstance(chat, dict) and chat.get('contact'):
                    chat_desc = f"我与{chat['contact']}在{analysis.get('app_name', '应用')}中交流"

                    if chat.get('messages') and isinstance(chat['messages'], list):
                        messages = []
                        for msg in chat['messages']:
                            if isinstance(msg, dict):
                                direction = "发送" if msg.get('direction') == 'sent' else "收到"
                                content = msg.get('content', '')
                                if content:
                                    messages.append(f"{direction}了消息\"{content}\"")

                        if messages:
                            chat_desc += "，" + "，".join(messages)

                    chat_desc += "。"
                    parts.append(chat_desc)
            except Exception as e:
                logger.debug(f"处理聊天详情时出错: {e}")

        # 购物详情（如果存在）
        if analysis.get('shopping_details'):
            try:
                shop = analysis['shopping_details']
                if isinstance(shop, dict) and (shop.get('product_name') or shop.get('product')):
                    product_name = shop.get('product_name') or shop.get('product')
                    shop_desc = f"我查看了\"{product_name}\""

                    if shop.get('price'):
                        shop_desc += f"，价格为{shop['price']}"
                    if shop.get('merchant'):
                        shop_desc += f"，来自\"{shop['merchant']}\""
                    if shop.get('action_type'):
                        shop_desc += f"，进行了{shop['action_type']}操作"

                    shop_desc += "。"
                    parts.append(shop_desc)
            except Exception as e:
                logger.debug(f"处理购物详情时出错: {e}")

        # 用户意图
        intent = analysis.get('intent', '执行某些操作')
        parts.append(f"我的意图是{intent}。")

        # 关键观察
        if analysis.get('key_observations'):
            parts.append(f"{analysis['key_observations']}。")

        return " ".join(parts)


class GraphDatabaseManager:
    """图数据库管理器"""

    def __init__(self, config_path: Path):
        """初始化图数据库管理器"""
        self.config_path = config_path
        self.project_root = project_root
        self.simplegraph: Optional[SimpleGraph] = None
        self.task_results: Dict[str, Any] = {}

    def backup_existing_database(self) -> None:
        """备份现有的图数据库"""
        # 使用绝对路径
        graph_path = self.project_root / "graphrag/simple_graphrag/output/graph.pkl"
        backup_path = self.project_root / "graphrag/simple_graphrag/output/graph.pkl.backup"

        if graph_path.exists():
            if backup_path.exists():
                backup_path.unlink()
                logger.info("删除旧备份文件")

            graph_path.rename(backup_path)
            logger.info(f"✓ 已备份图数据库到: {backup_path}")
        else:
            logger.info("✓ 不存在现有图数据库，无需备份")

    def initialize_database(self) -> None:
        """初始化图数据库"""
        logger.info("创建新的 SimpleGraph 实例（最大并发数: 3）...")

        self.simplegraph = SimpleGraph(
            config_path=self.config_path,
            max_concurrent_tasks=3,
            enable_smart_merge=True,
            progress_callback=self._progress_callback
        )
        logger.info("✓ 图数据库初始化完成")

    def _progress_callback(self, task_id: str, step: str, progress_data: dict) -> None:
        """进度回调函数"""
        status = progress_data.get('status', 'unknown')
        if step == 'extraction':
            logger.debug(f"[{task_id[:8]}...] 提取阶段: {status}")
        elif step == 'merging':
            logger.debug(f"[{task_id[:8]}...] 合并阶段: {status}")
        elif step == 'completed':
            logger.info(f"✓ 任务完成: {task_id[:8]}...")
            self.task_results[task_id] = status

    def get_statistics(self) -> Dict[str, Any]:
        """获取图数据库统计信息"""
        if not self.simplegraph:
            return {}

        return self.simplegraph.get_statistics()


class ProfileDataLoader:
    """Profile 数据加载器"""

    def __init__(self, profile_path: str = "data/eval/profile1", project_root_path: Path = None):
        """
        初始化 Profile 数据加载器

        Args:
            profile_path: Profile 目录路径
            project_root_path: 项目根目录
        """
        if project_root_path is None:
            project_root_path = project_root

        # 如果是相对路径，使用项目根目录
        profile_full_path = Path(profile_path) if Path(profile_path).is_absolute() else project_root_path / profile_path
        self.profile_path = profile_full_path
        self.vlm_files: List[Path] = []

    def discover_vlm_files(self) -> List[Path]:
        """发现所有 VLM JSON 文件"""
        pattern = str(self.profile_path / "*" / "analysis" / "*_vlm.json")
        vlm_files = [Path(f) for f in glob(pattern)]
        vlm_files.sort()

        self.vlm_files = vlm_files
        logger.info(f"✓ 找到 {len(vlm_files)} 个 VLM 分析文件")

        for i, f in enumerate(vlm_files, 1):
            logger.debug(f"  {i}. {f.name}")

        return vlm_files

    def load_vlm_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        加载单个 VLM JSON 文件

        Args:
            file_path: 文件路径

        Returns:
            JSON 数据，如果加载失败返回 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"无法读取 VLM 文件 {file_path}: {e}")
            return None

    def extract_session_id(self, file_path: Path) -> str:
        """从文件路径中提取 session_id"""
        # 文件名格式: {session_id}_vlm.json
        # 例如: 20260112_112849_5cd5_vlm.json
        return file_path.stem.replace('_vlm', '')


async def process_all_vlm_files(
    db_manager: GraphDatabaseManager,
    loader: ProfileDataLoader
) -> Dict[str, Any]:
    """
    异步处理所有 VLM 文件

    Args:
        db_manager: 图数据库管理器
        loader: Profile 数据加载器

    Returns:
        处理结果统计
    """
    if not db_manager.simplegraph:
        raise RuntimeError("图数据库未初始化")

    vlm_files = loader.discover_vlm_files()

    if not vlm_files:
        logger.warning("未找到任何 VLM 文件")
        return {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'task_ids': []
        }

    logger.info(f"\n正在处理 {len(vlm_files)} 个 VLM 分析文件...")

    task_ids = []
    processor = VLMDataProcessor()

    for i, vlm_file in enumerate(vlm_files, 1):
        logger.info(f"\n[{i}/{len(vlm_files)}] 处理: {vlm_file.name}")

        # 读取 VLM 文件
        vlm_data = loader.load_vlm_file(vlm_file)
        if not vlm_data:
            logger.error(f"  ✗ 跳过（读取失败）")
            continue

        # 提取 session_id
        session_id = loader.extract_session_id(vlm_file)

        # 转换为自然语言
        text = processor.vlm_to_text(vlm_data, session_id)
        if not text:
            logger.error(f"  ✗ 跳过（转换失败）")
            continue

        # 显示转换后的文本长度
        logger.info(f"  ✓ 转换成功 (文本长度: {len(text)} 字符)")

        # 提交任务
        try:
            task_id = await db_manager.simplegraph.submit_task(text)
            task_ids.append(task_id)
            logger.info(f"  ✓ 任务已提交: {task_id[:8]}...")
        except Exception as e:
            logger.error(f"  ✗ 提交任务失败: {e}")
            continue

    logger.info(f"\n已提交所有任务，等待处理完成...")
    logger.info(f"已提交 {len(task_ids)} 个任务")

    # 等待所有任务完成
    if task_ids and db_manager.simplegraph:
        await wait_for_all_tasks(db_manager.simplegraph, task_ids)

    return {
        'total': len(vlm_files),
        'successful': len(task_ids),
        'failed': len(vlm_files) - len(task_ids),
        'task_ids': task_ids
    }


async def wait_for_all_tasks(simplegraph: SimpleGraph, task_ids: List[str]) -> None:
    """
    等待所有任务完成

    Args:
        simplegraph: SimpleGraph 实例
        task_ids: 任务ID列表
    """
    while True:
        statuses = [simplegraph.get_task_status(tid) for tid in task_ids]

        if not all(statuses):
            logger.warning("某些任务不存在")
            break

        statuses = [s["status"] for s in statuses]

        # 统计各状态的任务数
        completed = sum(1 for s in statuses if s == "completed")
        failed = sum(1 for s in statuses if s == "failed")
        running = sum(1 for s in statuses if s == "running")
        pending = sum(1 for s in statuses if s == "pending")

        logger.debug(
            f"进度: {completed}/{len(task_ids)} 完成, {running} 运行中, "
            f"{pending} 等待中, {failed} 失败"
        )

        # 检查是否所有任务都完成或失败
        if all(s in ["completed", "failed", "cancelled"] for s in statuses):
            logger.info(f"✓ 所有任务处理完成! (完成: {completed}, 失败: {failed})")
            break

        await asyncio.sleep(1)


async def save_and_summarize(
    db_manager: GraphDatabaseManager,
    process_result: Dict[str, Any]
) -> None:
    """
    保存图数据库并输出总结

    Args:
        db_manager: 图数据库管理器
        process_result: 处理结果
    """
    if not db_manager.simplegraph:
        return

    # 保存图数据库
    output_path = db_manager.project_root / "graphrag/simple_graphrag/output/graph.pkl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"\n保存图数据库...")
    db_manager.simplegraph.save(output_path)
    logger.info(f"✓ 图数据库已保存到: {output_path}")

    # 获取统计信息
    stats = db_manager.get_statistics()

    logger.info("\n" + "="*60)
    logger.info("处理完成总结")
    logger.info("="*60)
    logger.info(f"总处理文件数: {process_result['total']}")
    logger.info(f"成功提交任务数: {process_result['successful']}")
    logger.info(f"失败数: {process_result['failed']}")

    if stats:
        logger.info(f"\n图数据库统计信息:")
        # 统计信息格式可能不同，尝试多种键
        entities = stats.get('graph', {}).get('entities', stats.get('entity_count', 'N/A'))
        relationships = stats.get('graph', {}).get('relationships', stats.get('relationship_count', 'N/A'))
        classes = stats.get('system', {}).get('classes', stats.get('class_count', 'N/A'))

        logger.info(f"  - 实体数: {entities}")
        logger.info(f"  - 关系数: {relationships}")
        logger.info(f"  - 类数: {classes}")

    logger.info(f"\n文件位置:")
    logger.info(f"  - 图数据库: {output_path}")
    logger.info(f"  - 可视化: {db_manager.project_root}/graphrag/simple_graphrag/output/graph_visualization.html")
    logger.info(f"  - 备份: {db_manager.project_root}/graphrag/simple_graphrag/output/graph.pkl.backup")
    logger.info("="*60)


async def main():
    """主函数"""
    logger.info("="*60)
    logger.info("图数据库重新初始化与批量加载")
    logger.info("="*60)

    # 检查配置文件（使用相对于 simple_graphrag 目录的路径）
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path.absolute()}")
        return

    # 步骤 1: 备份数据库
    logger.info("\n[步骤 1/5] 备份现有数据库...")
    db_manager = GraphDatabaseManager(config_path)
    db_manager.backup_existing_database()

    # 步骤 2: 初始化数据库
    logger.info("\n[步骤 2/5] 初始化图数据库...")
    db_manager.initialize_database()

    # 步骤 3: 启动任务处理器
    logger.info("\n[步骤 3/5] 启动任务处理器...")
    if db_manager.simplegraph:
        await db_manager.simplegraph.start()

    # 步骤 4: 加载并处理数据
    logger.info("\n[步骤 4/5] 加载并处理 VLM 数据...")
    loader = ProfileDataLoader()
    process_result = await process_all_vlm_files(db_manager, loader)

    # 步骤 5: 保存并总结
    logger.info("\n[步骤 5/5] 保存数据库并输出总结...")
    await save_and_summarize(db_manager, process_result)

    # 停止任务处理器
    logger.info("\n停止任务处理器...")
    if db_manager.simplegraph:
        await db_manager.simplegraph.stop()


if __name__ == "__main__":
    asyncio.run(main())
