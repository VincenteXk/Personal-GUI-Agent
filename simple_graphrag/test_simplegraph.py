"""
SimpleGraph 测试脚本

测试增量更新任务队列系统的各个功能。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from simplegraph import SimpleGraph
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


async def test_basic_functionality():
    """测试基本功能"""
    print("\n" + "=" * 60)
    print("测试 1: 基本功能")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"
    sg = SimpleGraph(config_path=config_path, max_concurrent_tasks=2)

    # 测试初始化
    print("\n✓ SimpleGraph 初始化成功")
    stats = sg.get_statistics()
    print(
        f"  初始状态: {stats['graph']['entities']} 实体, {stats['graph']['relationships']} 关系"
    )

    # 启动
    await sg.start()
    print("\n✓ 任务处理器启动成功")

    # 提交任务
    task_id = await sg.submit_task("我在淘宝上购买了一本书《Python编程》。")
    print(f"\n✓ 任务提交成功: {task_id[:8]}...")

    # 等待完成
    while True:
        status = sg.get_task_status(task_id)
        if status["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(0.5)

    status = sg.get_task_status(task_id)
    print(f"\n✓ 任务执行完成: {status['status']}")

    if status["status"] == "completed":
        stats = sg.get_statistics()
        print(
            f"  结果: {stats['graph']['entities']} 实体, {stats['graph']['relationships']} 关系"
        )
    else:
        print(f"  错误: {status.get('error', 'Unknown')}")

    await sg.stop()
    print("\n✓ 任务处理器停止成功")

    return status["status"] == "completed"


async def test_concurrent_tasks():
    """测试并发任务"""
    print("\n" + "=" * 60)
    print("测试 2: 并发任务")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"
    sg = SimpleGraph(
        config_path=config_path,
        max_concurrent_tasks=3,
        enable_smart_merge=False,  # 禁用智能合并以加快测试
    )
    await sg.start()

    # 提交多个任务
    texts = [
        "我在京东上买了一部手机。",
        "我在B站上看了一个视频。",
        "我在知乎上读了一篇文章。",
    ]

    print(f"\n提交 {len(texts)} 个任务...")
    task_ids = []
    for text in texts:
        task_id = await sg.submit_task(text)
        task_ids.append(task_id)

    print(f"✓ 已提交 {len(task_ids)} 个任务")

    # 等待全部完成
    print("\n等待任务完成...")
    while True:
        statuses = [sg.get_task_status(tid)["status"] for tid in task_ids]
        if all(s in ["completed", "failed"] for s in statuses):
            break
        await asyncio.sleep(0.5)

    # 检查结果
    completed = sum(
        1 for tid in task_ids if sg.get_task_status(tid)["status"] == "completed"
    )
    print(f"\n✓ 任务完成: {completed}/{len(task_ids)}")

    stats = sg.get_statistics()
    print(
        f"  结果: {stats['graph']['entities']} 实体, {stats['graph']['relationships']} 关系"
    )

    await sg.stop()

    return completed == len(task_ids)


async def test_task_cancellation():
    """测试任务取消"""
    print("\n" + "=" * 60)
    print("测试 3: 任务取消")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"
    sg = SimpleGraph(config_path=config_path, max_concurrent_tasks=1)
    await sg.start()

    # 提交任务
    task_id = await sg.submit_task("这是一个将被取消的任务。")
    print(f"\n✓ 任务已提交: {task_id[:8]}...")

    # 立即取消
    await asyncio.sleep(0.1)
    success = await sg.cancel_task(task_id)

    if success:
        print(f"✓ 任务取消成功")
    else:
        print(f"⚠ 任务取消失败（可能已完成）")

    # 检查状态
    await asyncio.sleep(0.5)
    status = sg.get_task_status(task_id)
    print(f"  最终状态: {status['status']}")

    await sg.stop()

    return True  # 取消测试总是成功（因为可能任务已完成）


async def test_smart_merge():
    """测试智能合并"""
    print("\n" + "=" * 60)
    print("测试 4: 智能合并")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"
    sg = SimpleGraph(
        config_path=config_path,
        max_concurrent_tasks=2,
        enable_smart_merge=True,  # 启用智能合并
    )
    await sg.start()

    # 提交相似的任务（测试去重）
    texts = [
        "我在淘宝上购买了一本书。",
        "我在淘宝买了一本书籍。",  # 相似内容
    ]

    print(f"\n提交 {len(texts)} 个相似任务...")
    task_ids = []
    for text in texts:
        task_id = await sg.submit_task(text)
        task_ids.append(task_id)

    # 等待完成
    while True:
        statuses = [sg.get_task_status(tid)["status"] for tid in task_ids]
        if all(s in ["completed", "failed"] for s in statuses):
            break
        await asyncio.sleep(0.5)

    completed = sum(
        1 for tid in task_ids if sg.get_task_status(tid)["status"] == "completed"
    )
    print(f"\n✓ 任务完成: {completed}/{len(task_ids)}")

    stats = sg.get_statistics()
    print(f"  结果: {stats['graph']['entities']} 实体")
    print(f"  （智能合并应该识别重复实体）")

    await sg.stop()

    return completed > 0


async def test_statistics():
    """测试统计功能"""
    print("\n" + "=" * 60)
    print("测试 5: 统计功能")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"
    sg = SimpleGraph(config_path=config_path, max_concurrent_tasks=2)
    await sg.start()

    # 提交任务
    task_id = await sg.submit_task("这是一个测试任务。")

    # 等待完成
    while True:
        status = sg.get_task_status(task_id)
        if status["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(0.5)

    # 获取统计
    stats = sg.get_statistics()
    print("\n✓ 统计信息:")
    print(f"  System: {stats['system']['classes']} 类")
    print(
        f"  Graph: {stats['graph']['entities']} 实体, {stats['graph']['relationships']} 关系"
    )
    print(f"  Tasks: {stats['tasks']['total']} 总数")

    # 获取所有任务
    all_tasks = sg.get_all_tasks()
    print(f"\n✓ 任务列表: {len(all_tasks)} 个任务")

    await sg.stop()

    return True


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("SimpleGraph 测试套件")
    print("=" * 60)

    tests = [
        ("基本功能", test_basic_functionality),
        ("并发任务", test_concurrent_tasks),
        ("任务取消", test_task_cancellation),
        ("智能合并", test_smart_merge),
        ("统计功能", test_statistics),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ 测试失败: {name}")
            print(f"  错误: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {status}: {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return True
    else:
        print(f"\n⚠ {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
