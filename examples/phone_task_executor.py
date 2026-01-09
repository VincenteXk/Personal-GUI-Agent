"""Phone任务执行器示例 - 将PhoneAgent集成到任务框架。"""

import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from task_framework.interfaces import TaskExecutorInterface, ExecutionResult


class PhoneTaskExecutor(TaskExecutorInterface):
    """
    Phone任务执行器 - 使用PhoneAgent执行手机相关任务。

    这是一个示例实现，展示如何将底层Agent（PhoneAgent）
    集成到高层任务框架中。
    """

    def __init__(self, phone_agent=None):
        """
        初始化Phone任务执行器。

        Args:
            phone_agent: PhoneAgent实例（可选）
        """
        self.phone_agent = phone_agent
        self._supported_types = [
            "phone_operation",
            "app_launch",
            "send_message",
            "phone_call",
            "phone_general",
        ]

    def execute_task(
        self,
        task_type: str,
        task_params: dict[str, Any],
        context: dict[str, Any],
    ) -> ExecutionResult:
        """
        执行Phone相关任务。

        Args:
            task_type: 任务类型
            task_params: 任务参数（应包含'instruction'或可构建任务描述的数据）
            context: 执行上下文

        Returns:
            执行结果
        """
        print(f"\n📱 PhoneTaskExecutor (示例) 开始执行")
        print(f"   任务类型: {task_type}")
        print(f"   任务参数: {task_params}\n")

        if not self.can_handle(task_type):
            return ExecutionResult(
                success=False,
                message=f"不支持的任务类型: {task_type}",
            )

        # 如果有PhoneAgent实例，使用它执行
        if self.phone_agent:
            try:
                # 构建任务描述
                task_description = self._build_task_description(task_params)
                print(f"🎯 执行指令: {task_description}")

                # 执行任务
                result = self.phone_agent.run(task_description)

                print(f"✅ 执行成功: {result}\n")
                return ExecutionResult(
                    success=True,
                    message=result,
                    data={"type": "phone_task", "result": result},
                )
            except Exception as e:
                print(f"❌ 执行失败: {e}\n")
                return ExecutionResult(
                    success=False,
                    message=f"执行失败: {e}",
                    should_retry=True,
                )
        else:
            # 模拟执行（用于演示）
            print(f"⚠️ 模拟执行（未提供PhoneAgent实例）\n")
            return ExecutionResult(
                success=True,
                message=f"模拟执行 {task_type} 任务",
                data=task_params,
            )

    def can_handle(self, task_type: str) -> bool:
        """检查是否能处理特定类型的任务。"""
        return task_type in self._supported_types

    def get_supported_task_types(self) -> list[str]:
        """获取支持的任务类型列表。"""
        return self._supported_types.copy()

    def _build_task_description(self, task_params: dict[str, Any]) -> str:
        """
        从任务参数构建任务描述。

        Args:
            task_params: 任务参数

        Returns:
            任务描述字符串
        """
        # 优先使用instruction字段（标准方式）
        if "instruction" in task_params:
            return task_params["instruction"]

        # 兼容旧的task_info方式
        task_info = task_params.get("task_info")
        if task_info:
            return task_info.normalized_task or task_info.original_input

        # 从step构建
        step = task_params.get("step", {})
        return step.get("description", "执行Phone操作")


def main():
    """演示如何使用PhoneTaskExecutor。"""
    print("=" * 60)
    print("Phone任务执行器示例")
    print("=" * 60)

    # 创建执行器
    executor = PhoneTaskExecutor()

    # 测试执行
    test_tasks = [
        {
            "type": "app_launch",
            "params": {
                "step": {"description": "打开微信"},
                "task_info": type(
                    "obj",
                    (object,),
                    {
                        "original_input": "打开微信",
                        "normalized_task": "打开微信应用",
                    },
                )(),
            },
        },
        {
            "type": "send_message",
            "params": {
                "step": {"description": "发送消息"},
                "task_info": type(
                    "obj",
                    (object,),
                    {
                        "original_input": "给张三发消息说开会",
                        "normalized_task": "发送消息给张三",
                    },
                )(),
            },
        },
    ]

    for task in test_tasks:
        print(f"\n执行任务: {task['type']}")
        result = executor.execute_task(
            task["type"], task["params"], {"device_id": None}
        )
        print(f"结果: {result.success}")
        print(f"消息: {result.message}")


if __name__ == "__main__":
    main()
