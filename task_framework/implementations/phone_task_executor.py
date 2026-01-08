"""PhoneAgent任务执行器 - 将AutoGLM集成到任务调度框架。"""

from dataclasses import dataclass
from typing import Any, Optional

from src.AutoGLM.agent import PhoneAgent, AgentConfig as PhoneAgentConfig
from src.AutoGLM.model import ModelClient, ModelConfig
from task_framework.interfaces import TaskExecutorInterface, ExecutionResult


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

    def can_handle(self, task_type: str) -> bool:
        """
        检查是否能处理指定类型的任务。

        支持的任务类型：
        - phone_automation: 通用手机自动化
        - app_launch: 启动应用
        - send_message: 发送消息
        - shopping: 购物相关
        - food_delivery: 外卖相关
        """
        supported_types = [
            "phone_automation",
            "app_launch",
            "send_message",
            "shopping",
            "food_delivery",
            "general",  # 通用任务
        ]
        return task_type in supported_types

    def execute_task(
        self,
        task_type: str,
        task_data: dict[str, Any],
        config: dict[str, Any],
    ) -> ExecutionResult:
        """
        执行手机任务。

        Args:
            task_type: 任务类型
            task_data: 任务数据，必须包含 "instruction" 字段
            config: 执行配置，可选 "device_id"

        Returns:
            ExecutionResult 执行结果

        Example task_data:
            {
                "instruction": "打开微信，找到测试联系人1",
                "max_steps": 30,  # 可选
            }
        """
        if not self.can_handle(task_type):
            return ExecutionResult(
                success=False,
                message=f"不支持的任务类型: {task_type}",
                data={},
            )

        # 提取指令
        instruction = task_data.get("instruction")
        if not instruction:
            return ExecutionResult(
                success=False,
                message="缺少必需的字段: instruction",
                data={},
            )

        # 更新配置
        if "device_id" in config:
            self.phone_agent.agent_config.device_id = config["device_id"]

        if "max_steps" in task_data:
            self.phone_agent.agent_config.max_steps = task_data["max_steps"]

        # 执行任务
        try:
            # 重置agent状态
            self.phone_agent.reset()

            # 运行任务
            result_message = self.phone_agent.run(instruction)

            # 获取执行上下文和步骤
            context = self.phone_agent.context
            step_count = self.phone_agent.step_count

            return ExecutionResult(
                success=True,
                message=result_message,
                data={
                    "step_count": step_count,
                    "task_type": task_type,
                    "instruction": instruction,
                    "context_length": len(context),
                },
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"执行失败: {str(e)}",
                data={
                    "error": str(e),
                    "task_type": task_type,
                    "instruction": instruction,
                },
            )

    def get_capabilities(self) -> dict[str, Any]:
        """
        获取执行器的能力描述。

        Returns:
            能力字典
        """
        return {
            "name": "PhoneTaskExecutor",
            "description": "手机自动化任务执行器，基于AutoGLM PhoneAgent",
            "supported_task_types": [
                "phone_automation",
                "app_launch",
                "send_message",
                "shopping",
                "food_delivery",
                "general",
            ],
            "features": [
                "设备操作自动化",
                "视觉语言模型驱动",
                "无需外部交互的序列操作",
                "支持多种应用场景",
            ],
            "limitations": [
                "需要设备连接（ADB/HDC）",
                "执行过程不支持人工干预",
                "每次执行需要完整的自然语言指令",
            ],
        }
