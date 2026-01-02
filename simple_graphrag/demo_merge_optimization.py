"""
演示合并优化的效果

展示两阶段架构：
- 阶段1: 提取阶段（并行）
- 阶段2: 合并阶段（串行）
"""

import asyncio
from pathlib import Path
from simplegraph import SimpleGraph
from dotenv import load_dotenv
from datetime import datetime
import time

# 加载环境变量
load_dotenv()


# 详细进度回调
def detailed_progress_callback(task_id: str, step: str, data: dict):
    """详细进度回调，展示各个阶段"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    message = data.get("message", "")
    percentage = data.get("percentage", 0)

    # 阶段图标和颜色
    stage_info = {
        "started": ("▶️", "开始"),
        "system_update": ("🔧", "System更新"),
        "extraction": ("🔍", "实体提取"),
        "extraction_completed": ("📦", "提取完成，等待合并"),
        "merging": ("🔄", "正在合并"),
        "completed": ("✅", "完成"),
        "failed": ("❌", "失败"),
        "cancelled": ("⏹️", "取消"),
        "merge_failed": ("⚠️", "合并失败"),
    }

    icon, stage_name = stage_info.get(step, ("•", step))

    # 格式化输出
    print(
        f"[{timestamp}] {icon} 任务 {task_id[:8]} | {stage_name:12s} | {message:40s} | {percentage:3d}%"
    )

    # 如果是提取完成阶段，提示用户这是关键阶段
    if step == "extraction_completed":
        print(f"           └─ 💡 提示: 任务已完成提取，现在进入合并队列等待串行处理")

    # 如果是合并阶段，说明正在串行处理
    if step == "merging":
        print(f"           └─ 🔐 串行处理: 确保数据一致性和合并质量")


# 测试文本
TEST_TEXTS = [
    "我在小红书上看到一篇关于咖啡的文章，作者推荐了三家上海的咖啡店。",
    "我打开高德地图搜索离我最近的咖啡店，找到了星巴克和瑞幸咖啡。",
    "我在美团上订了一杯星巴克的拿铁，用支付宝付款了。",
    "我在抖音上刷到一个咖啡拉花的教学视频，觉得很有趣。",
    "我用微信把这个视频分享给了我的朋友小明。",
]


async def demo_merge_optimization():
    """演示合并优化"""
    print("=" * 80)
    print("SimpleGraphRAG 合并优化演示")
    print("=" * 80)
    print()
    print("架构说明:")
    print("  • 阶段1: 提取阶段 (可并行) - 多个 workers 同时处理不同任务")
    print("  • 阶段2: 合并阶段 (串行)   - 单个 worker 逐个合并，确保质量")
    print()
    print("=" * 80)
    print()

    # 配置路径
    config_path = Path(__file__).parent / "config" / "config.yaml"

    # 初始化 SimpleGraph
    print("1️⃣  初始化 SimpleGraph...")
    print("   • 提取 Workers: 3 个（并行）")
    print("   • 合并 Worker: 1 个（串行）")
    print()

    sg = SimpleGraph(
        config_path=config_path,
        max_concurrent_tasks=3,  # 3个提取workers
        enable_smart_merge=True,  # 启用智能合并
        progress_callback=detailed_progress_callback,
    )

    # 启动
    await sg.start()
    print("   ✓ 任务处理器启动完成")
    print()

    # 提交任务
    print("2️⃣  提交 5 个任务...")
    print()

    start_time = time.time()
    task_ids = []

    for i, text in enumerate(TEST_TEXTS, 1):
        task_id = await sg.submit_task(text)
        task_ids.append(task_id)
        print(f"   [{i}] 任务 {task_id[:8]} 已提交")
        print(f"       内容: {text[:50]}...")
        await asyncio.sleep(0.1)  # 稍微延迟，让进度更清晰

    print()
    print(f"   ✓ 共提交 {len(task_ids)} 个任务")
    print()
    print("=" * 80)
    print("3️⃣  任务执行中（观察两阶段处理）...")
    print("=" * 80)
    print()

    # 实时监控
    last_status_line = ""
    while True:
        # 获取所有任务状态
        statuses = {}
        for tid in task_ids:
            status = sg.get_task_status(tid)
            if status:
                statuses[status["status"]] = statuses.get(status["status"], 0) + 1

        # 检查队列状态
        merge_queue_size = sg.merge_queue.qsize()

        # 构建状态行
        status_parts = []
        for status_name in ["running", "pending", "completed", "failed"]:
            count = statuses.get(status_name, 0)
            if count > 0:
                status_parts.append(f"{status_name}: {count}")

        status_line = f"\r   📊 状态: {', '.join(status_parts)} | 🔄 合并队列: {merge_queue_size} 个等待"

        # 只在状态变化时打印
        if status_line != last_status_line:
            print(status_line, end="", flush=True)
            last_status_line = status_line

        # 检查是否全部完成
        all_statuses = [sg.get_task_status(tid)["status"] for tid in task_ids]
        if all(s in ["completed", "failed", "cancelled"] for s in all_statuses):
            print()  # 换行
            break

        await asyncio.sleep(0.1)

    elapsed_time = time.time() - start_time

    print()
    print("=" * 80)
    print("4️⃣  任务完成，查看结果...")
    print("=" * 80)
    print()

    # 统计结果
    completed = 0
    failed = 0
    total_duration = 0

    for i, task_id in enumerate(task_ids, 1):
        status = sg.get_task_status(task_id)
        if status["status"] == "completed":
            completed += 1
            duration = status.get("duration", 0)
            total_duration += duration
            print(f"   [{i}] ✅ {task_id[:8]} | 完成 | 耗时: {duration:.2f}s")
        elif status["status"] == "failed":
            failed += 1
            error = status.get("error", "Unknown")
            print(f"   [{i}] ❌ {task_id[:8]} | 失败 | 错误: {error}")

    print()
    print("=" * 80)
    print("5️⃣  性能统计")
    print("=" * 80)
    print()
    print(f"   总耗时: {elapsed_time:.2f} 秒")
    print(f"   完成任务: {completed}/{len(task_ids)}")
    print(f"   失败任务: {failed}/{len(task_ids)}")
    if completed > 0:
        print(f"   平均耗时: {total_duration/completed:.2f} 秒/任务")
    print()

    # 图谱统计
    stats = sg.get_statistics()
    print("=" * 80)
    print("6️⃣  图谱统计")
    print("=" * 80)
    print()
    print(f"   System:")
    print(f"      • 类定义: {stats['system']['classes']} 个")
    print(f"      • 预定义实体: {stats['system']['predefined_entities']} 个")
    print()
    print(f"   Graph:")
    print(f"      • 实体: {stats['graph']['entities']} 个")
    print(f"      • 关系: {stats['graph']['relationships']} 个")
    print()

    # 停止
    await sg.stop()

    print("=" * 80)
    print("✅ 演示完成！")
    print("=" * 80)
    print()
    print("💡 关键观察点:")
    print("   1. 多个任务的提取阶段可以并行进行（System更新和实体提取）")
    print("   2. 提取完成后进入合并队列，等待串行处理")
    print("   3. 合并阶段按顺序执行，确保数据一致性和合并质量")
    print("   4. 进度通知清晰展示了每个阶段的状态")
    print()


if __name__ == "__main__":
    asyncio.run(demo_merge_optimization())
