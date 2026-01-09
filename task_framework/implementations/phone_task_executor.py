"""PhoneAgent任务执行器 - 将AutoGLM集成到任务调度框架。"""

from dataclasses import dataclass
from typing import Any, Optional

from src.AutoGLM.agent import PhoneAgent, AgentConfig as PhoneAgentConfig
from src.AutoGLM.model import ModelClient, ModelConfig
from task_framework.interfaces import (
    TaskExecutorInterface,
    ExecutionResult,
    TaskCapability,
    TaskParameter,
)


@dataclass
class PhoneTaskConfig:
    """手机任务配置。"""

    device_id: Optional[str] = None
    max_steps: int = 50
    lang: str = "cn"
    verbose: bool = True


class PhoneTaskExecutor(TaskExecutorInterface):
    """
    手机任务执行器。

    将AutoGLM的PhoneAgent封装为TaskExecutor，供任务调度Agent使用。

    特点：
    - 执行设备层面的操作（打开app、点击、输入等）
    - 无修正、无选择、无外部交互的序列操作
    - 可以用作单元操作（打开某app）或简单序列（打开app并打开购物车）

    Example:
        >>> executor = PhoneTaskExecutor(model_config, phone_config)
        >>> result = executor.execute_task(
        ...     "phone_automation",
        ...     {"instruction": "打开微信并打开购物车"},
        ...     {}
        ... )
    """

    def __init__(
        self,
        model_config: Optional[ModelConfig] = None,
        phone_config: Optional[PhoneTaskConfig] = None,
    ):
        self.model_config = model_config or ModelConfig()
        self.phone_config = phone_config or PhoneTaskConfig()

        # 创建PhoneAgent实例（每次执行任务时可以复用）
        agent_config = PhoneAgentConfig(
            max_steps=self.phone_config.max_steps,
            device_id=self.phone_config.device_id,
            lang=self.phone_config.lang,
            verbose=self.phone_config.verbose,
        )

        self.phone_agent = PhoneAgent(
            model_config=self.model_config,
            agent_config=agent_config,
        )

    # can_handle 方法现在由父类 TaskExecutorInterface 提供默认实现

    def execute_task(
        self,
        task_type: str,
        task_params: dict[str, Any],
        context: dict[str, Any],
    ) -> ExecutionResult:
        """
        执行手机任务。

        Args:
            task_type: 任务类型
            task_params: 任务参数，必须包含 "instruction" 字段
            context: 执行上下文，可选 "device_id"

        Returns:
            ExecutionResult 执行结果

        Example task_params:
            {
                "instruction": "打开微信，找到测试联系人1",
                "max_steps": 30,  # 可选
            }
        """
        print(f"\n{'='*60}")
        print(f"📱 PhoneTaskExecutor 开始执行")
        print(f"任务类型: {task_type}")
        print(f"任务参数: {task_params}")
        print(f"上下文: {context}")
        print(f"{'='*60}\n")

        if not self.can_handle(task_type):
            return ExecutionResult(
                success=False,
                message=f"不支持的任务类型: {task_type}",
                data={},
            )

        # 提取指令
        instruction = task_params.get("instruction")
        if not instruction:
            return ExecutionResult(
                success=False,
                message="缺少必需的字段: instruction",
                data={},
            )

        # 更新配置
        if context and "device_id" in context:
            self.phone_agent.agent_config.device_id = context["device_id"]

        if "max_steps" in task_params:
            self.phone_agent.agent_config.max_steps = task_params["max_steps"]

        print(f"🎯 即将执行指令: {instruction}")
        print(f"📋 最大步数: {self.phone_agent.agent_config.max_steps}")
        if self.phone_agent.agent_config.device_id:
            print(f"📱 设备ID: {self.phone_agent.agent_config.device_id}")
        print()
        # 执行任务
        try:
            # 重置agent状态
            self.phone_agent.reset()

            print("🚀 开始执行PhoneAgent...")
            # 运行任务
            result_message = self.phone_agent.run(instruction)

            # 获取执行上下文和步骤
            agent_context = self.phone_agent.context
            step_count = self.phone_agent.step_count

            print(f"\n✅ PhoneAgent执行完成")
            print(f"   执行步数: {step_count}")
            print(f"   结果消息: {result_message}\n")

            return ExecutionResult(
                success=True,
                message=result_message,
                data={
                    "step_count": step_count,
                    "task_type": task_type,
                    "instruction": instruction,
                    "context_length": len(agent_context),
                },
            )

        except Exception as e:
            print(f"\n❌ PhoneAgent执行失败: {str(e)}\n")
            return ExecutionResult(
                success=False,
                message=f"执行失败: {str(e)}",
                data={
                    "error": str(e),
                    "task_type": task_type,
                    "instruction": instruction,
                },
            )

    def get_capabilities(self) -> list[TaskCapability]:
        """
        获取执行器的能力列表。

        Returns:
            TaskCapability 列表，描述每种可执行的任务类型
        """
        return [
            TaskCapability(
                task_type="phone_automation",
                name="手机自动化",
                description="执行手机上的简单自动化操作序列（3-10步内）",
                parameters=[
                    TaskParameter(
                        name="instruction",
                        description="要执行的任务指令，用自然语言清晰描述操作步骤",
                        required=True,
                        example="打开微信，找到张三，发送消息'你好'",
                        value_type="string",
                    ),
                    TaskParameter(
                        name="max_steps",
                        description="最大执行步骤数限制（建议10-30）",
                        required=False,
                        example="20",
                        value_type="number",
                    ),
                ],
                examples=[
                    {
                        "description": "打开应用",
                        "task_data": {"instruction": "打开微信"},
                    },
                    {
                        "description": "发送消息",
                        "task_data": {"instruction": "打开微信，找到张三，发送'你好'"},
                    },
                    {
                        "description": "浏览商品",
                        "task_data": {
                            "instruction": "打开淘宝，搜索iPhone 15，点击第一个"
                        },
                    },
                ],
                limitations=[
                    "仅适合3-10步的简单操作序列",
                    "需要设备通过ADB/HDC连接",
                    "执行过程无法暂停或修正",
                    "不支持需要生物认证的操作",
                    "不支持需要多轮交互确认的复杂任务",
                ],
            ),
        ]
