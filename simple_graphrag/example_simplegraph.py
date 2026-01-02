"""
SimpleGraph 使用示例

演示如何使用 SimpleGraph 进行异步任务处理和智能合并。
包括：
- 基本的任务提交和执行
- 进度追踪和回调
- 阶段结果获取
- 任务取消
- 并发处理
"""

import asyncio
from pathlib import Path
from simplegraph import SimpleGraph
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()


# 进度回调函数
def progress_callback(task_id: str, step: str, data: dict):
    """
    进度回调函数

    Args:
        task_id: 任务ID
        step: 当前步骤
        data: 进度数据
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    message = data.get("message", "")
    percentage = data.get("percentage", 0)

    # 使用图标
    icons = {
        "started": "▶️",
        "system_update": "🔧",
        "extraction": "🔍",
        "extraction_completed": "📦",
        "merging": "🔄",
        "completed": "✅",
        "failed": "❌",
        "cancelled": "⏹️",
        "merge_failed": "⚠️",
    }
    icon = icons.get(step, "•")

    print(
        f"[{timestamp}] {icon} 任务 {task_id[:8]} | {step}: {message} ({percentage}%)"
    )

    # 如果有阶段结果，打印详细摘要
    if "result" in data:
        result = data["result"]
        if step == "system_update":
            added = result.get("added_classes", [])
            enhanced = result.get("enhanced_classes", [])
            added_detail = result.get("added_classes_detail", [])
            enhanced_detail = result.get("enhanced_classes_detail", [])

            if added or enhanced:
                print(f"           └─ 新增类: {len(added)}, 增强类: {len(enhanced)}")
                # 显示详细信息
                for cls in added_detail[:2]:  # 只显示前2个
                    props_str = (
                        ", ".join(cls["properties"])
                        if cls["properties"]
                        else "(无属性)"
                    )
                    print(f"              • {cls['name']}: {props_str}")
                if len(added_detail) > 2:
                    print(f"              ... 还有 {len(added_detail) - 2} 个")

        elif step == "extraction":
            entities_count = result.get("entities_count", 0)
            relationships_count = result.get("relationships_count", 0)
            entities = result.get("entities", [])
            relationships = result.get("relationships", [])

            print(
                f"           └─ 提取: {entities_count} 个实体, {relationships_count} 个关系"
            )
            # 显示前几个实体
            for entity in entities[:3]:
                classes_str = ", ".join(entity["classes"])
                print(f"              • {entity['name']} [{classes_str}]")
            if len(entities) > 3:
                print(f"              ... 还有 {len(entities) - 3} 个实体")

            # 显示前几个关系
            if relationships:
                for rel in relationships[:2]:
                    print(f"              • {rel['source']} → {rel['target']}")
                if len(relationships) > 2:
                    print(f"              ... 还有 {len(relationships) - 2} 个关系")


# 示例文本
EXAMPLE_TEXTS = [
    "我在抖音上刷到一家网红餐厅，名叫“张三的店”，于是打开美团外卖订了他们家的招牌套餐。",
    "我用高德地图查找了“张三的店”的位置，到达后用大众点评写了一条好评。",
    "我在小红书上看到一个很有趣的关于AI绘图的视频，然后用微信分享给了小明。",
    "我在Bilibili上看到了一本《相爱一场》的书籍介绍，便在淘宝上购买了一本。",
]


async def main():
    """主函数"""
    print("=" * 60)
    print("SimpleGraph 使用示例")
    print("=" * 60)

    # 配置路径
    config_path = Path(__file__).parent / "config" / "config.yaml"
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # 初始化 SimpleGraph（带进度回调）
    print("\n1. 初始化 SimpleGraph...")
    sg = SimpleGraph(
        config_path=config_path,
        max_concurrent_tasks=3,  # 最多3个并发任务
        enable_smart_merge=True,  # 启用智能合并
        progress_callback=progress_callback,  # 设置进度回调
    )

    # 启动任务处理器
    print("\n2. 启动任务处理器...")
    await sg.start()

    # 提交多个任务（并行执行）
    print("\n3. 提交任务...")
    task_ids = []
    for i, text in enumerate(EXAMPLE_TEXTS, 1):
        task_id = await sg.submit_task(text)
        task_ids.append(task_id)
        print(f"   任务 {i} 已提交: {task_id[:8]}...")
        print(f"   内容: {text[:50]}...")

    print(f"\n共提交 {len(task_ids)} 个任务")

    # 等待所有任务完成
    print("\n4. 等待任务完成...")
    while True:
        statuses = [sg.get_task_status(tid)["status"] for tid in task_ids]

        # 打印进度
        completed = sum(1 for s in statuses if s == "completed")
        failed = sum(1 for s in statuses if s == "failed")
        running = sum(1 for s in statuses if s == "running")
        pending = sum(1 for s in statuses if s == "pending")

        print(
            f"\r   进度: {completed}/{len(task_ids)} 完成, {running} 运行中, {pending} 等待中, {failed} 失败",
            end="",
        )

        if all(s in ["completed", "failed", "cancelled"] for s in statuses):
            print()  # 换行
            break

        await asyncio.sleep(0.5)

    # 查看任务结果
    print("\n5. 任务结果:")
    for i, task_id in enumerate(task_ids, 1):
        status = sg.get_task_status(task_id)
        print(f"   任务 {i} ({task_id[:8]}...): {status['status']}")
        if status["status"] == "failed":
            print(f"      错误: {status.get('error', 'Unknown')}")
        elif status["status"] == "completed":
            duration = status.get("duration", 0)
            print(f"      耗时: {duration:.2f}s")

            # 获取阶段结果
            stage_results = sg.get_task_stage_results(task_id)
            if stage_results:
                print(f"      阶段结果:")
                for stage, stage_data in stage_results.items():
                    result = stage_data.get("result", {})
                    if stage == "system_update":
                        added = len(result.get("added_classes", []))
                        enhanced = len(result.get("enhanced_classes", []))
                        print(f"        - {stage}: 新增 {added} 类, 增强 {enhanced} 类")
                    elif stage == "extraction":
                        entities = result.get("entities_count", 0)
                        relations = result.get("relationships_count", 0)
                        print(
                            f"        - {stage}: 提取 {entities} 实体, {relations} 关系"
                        )

    # 查看统计信息
    print("\n6. 统计信息:")
    stats = sg.get_statistics()
    print(f"   System:")
    print(f"      类: {stats['system']['classes']} 个")
    print(f"      预定义实体: {stats['system']['predefined_entities']} 个")
    print(f"   Graph:")
    print(f"      实体: {stats['graph']['entities']} 个")
    print(f"      关系: {stats['graph']['relationships']} 个")
    print(f"   Tasks:")
    print(f"      总数: {stats['tasks']['total']}")
    print(f"      完成: {stats['tasks']['by_status']['completed']}")
    print(f"      失败: {stats['tasks']['by_status']['failed']}")

    # 保存和可视化
    print("\n7. 保存和可视化...")
    graph_path = output_dir / "simplegraph.pkl"
    viz_path = output_dir / "simplegraph_visualization.html"

    sg.save(graph_path)
    print(f"   Graph 已保存到: {graph_path}")

    sg.visualize(viz_path)
    print(f"   可视化已生成: {viz_path}")

    # 停止任务处理器
    print("\n8. 停止任务处理器...")
    await sg.stop()

    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)


async def demo_cancel_task():
    """演示任务取消功能"""
    print("\n" + "=" * 60)
    print("任务取消演示")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"
    sg = SimpleGraph(config_path=config_path, max_concurrent_tasks=2)
    await sg.start()

    # 提交任务
    print("\n1. 提交任务...")
    task_id = await sg.submit_task("这是一个测试任务，用于演示取消功能。")
    print(f"   任务已提交: {task_id[:8]}...")

    # 等待一小段时间
    await asyncio.sleep(0.5)

    # 取消任务
    print("\n2. 取消任务...")
    success = await sg.cancel_task(task_id)
    if success:
        print(f"   任务已取消: {task_id[:8]}...")
    else:
        print(f"   任务取消失败（可能已完成）: {task_id[:8]}...")

    # 检查状态
    await asyncio.sleep(0.5)
    status = sg.get_task_status(task_id)
    print(f"\n3. 任务状态: {status['status']}")

    await sg.stop()
    print("\n取消演示完成")


async def demo_progress_tracking():
    """演示进度追踪功能"""
    print("\n" + "=" * 60)
    print("进度追踪演示")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"

    # 定义详细的进度回调
    def detailed_progress_callback(task_id: str, step: str, data: dict):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        message = data.get("message", "")
        percentage = data.get("percentage", 0)

        # 使用不同的符号表示不同阶段
        symbols = {
            "started": "▶",
            "system_update": "🔧",
            "extraction": "🔍",
            "extraction_completed": "📦",
            "merging": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "⏹",
            "merge_failed": "⚠️",
        }
        symbol = symbols.get(step, "•")

        print(
            f"[{timestamp}] {symbol} {task_id[:8]} | {step}: {message} ({percentage}%)"
        )

        # 打印详细结果
        if "result" in data:
            result = data["result"]
            if step == "system_update":
                added = result.get("added_classes", [])
                enhanced = result.get("enhanced_classes", [])
                if added:
                    print(f"           新增类: {', '.join(added)}")
                if enhanced:
                    print(f"           增强类: {', '.join(enhanced)}")
            elif step == "extraction":
                entities = result.get("entities", [])
                relationships = result.get("relationships", [])
                print(f"           提取实体: {len(entities)} 个")
                for entity in entities[:3]:  # 只显示前3个
                    print(
                        f"             - {entity['name']}: {', '.join(entity['classes'])}"
                    )
                if len(entities) > 3:
                    print(f"             ... 还有 {len(entities) - 3} 个")
                print(f"           提取关系: {len(relationships)} 个")

    sg = SimpleGraph(
        config_path=config_path,
        max_concurrent_tasks=2,
        enable_smart_merge=True,
        progress_callback=detailed_progress_callback,
    )
    await sg.start()

    # 提交任务
    print("\n1. 提交任务并追踪进度...")
    task_id = await sg.submit_task(
        "小明在知乎上看到一篇关于人工智能的文章，觉得很有意思，于是用微信分享给了同事小红。"
        "小红看完后，在GitHub上找到了相关的开源项目，并star了这个项目。"
    )

    # 实时查询进度
    print("\n2. 实时查询任务进度...")
    while True:
        status = sg.get_task_status(task_id)
        if status["status"] in ["completed", "failed", "cancelled"]:
            break
        await asyncio.sleep(0.5)

    # 查看最终结果
    print("\n3. 查看阶段结果详情:")
    stage_results = sg.get_task_stage_results(task_id)
    for stage, stage_data in stage_results.items():
        timestamp = stage_data.get("timestamp", "")
        result = stage_data.get("result", {})
        print(f"\n   阶段: {stage} (时间: {timestamp})")
        print(f"   结果: {result}")

    await sg.stop()
    print("\n进度追踪演示完成")


async def demo_concurrent_tasks():
    """演示并发任务处理"""
    print("\n" + "=" * 60)
    print("并发任务演示")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"
    sg = SimpleGraph(
        config_path=config_path,
        max_concurrent_tasks=5,  # 5个并发任务
        enable_smart_merge=False,  # 禁用智能合并以加快速度
        progress_callback=progress_callback,  # 使用进度回调
    )
    await sg.start()

    # 提交大量任务
    print("\n1. 提交10个任务...")
    task_ids = []
    for i in EXAMPLE_TEXTS:
        task_id = await sg.submit_task(i)
        task_ids.append(task_id)

    print(f"   已提交 {len(task_ids)} 个任务")

    # 等待完成
    print("\n2. 等待任务完成...")
    start_time = asyncio.get_event_loop().time()

    while True:
        statuses = [sg.get_task_status(tid)["status"] for tid in task_ids]
        if all(s in ["completed", "failed", "cancelled"] for s in statuses):
            break
        await asyncio.sleep(0.1)

    elapsed = asyncio.get_event_loop().time() - start_time

    # 统计
    stats = sg.get_statistics()
    print(f"\n3. 完成!")
    print(f"   总耗时: {elapsed:.2f}s")
    print(f"   平均每任务: {elapsed/len(task_ids):.2f}s")
    print(f"   完成任务: {stats['tasks']['by_status']['completed']}")
    # 可视化最后的图谱
    sg.visualize(
        Path(__file__).parent / "output" / "simplegraph_visualization.html", False
    )

    await sg.stop()
    print("\n并发演示完成")


if __name__ == "__main__":
    # 运行主示例
    # asyncio.run(main())

    # 可选：运行其他演示
    # asyncio.run(demo_progress_tracking())  # 详细进度追踪演示
    # asyncio.run(demo_cancel_task())  # 任务取消演示
    asyncio.run(demo_concurrent_tasks())  # 并发任务演示
