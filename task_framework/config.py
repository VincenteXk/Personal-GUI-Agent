"""任务Agent配置。"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskAgentConfig:
    """任务Agent配置类。

    支持基于"感知-思考-行动"循环的任务调度架构。
    """

    # 基础配置
    max_steps: int = 50  # 最大步骤数
    max_retries: int = 3  # 最大重试次数
    verbose: bool = True  # 是否输出详细信息

    # 语言配置
    language: str = "zh"  # 语言设置

    # 设备配置
    default_device_id: Optional[str] = None  # 默认设备ID

    # 安全配置
    require_confirmation_for_sensitive: bool = True  # 敏感操作需要确认
    auto_update_profile: bool = False  # 是否自动更新用户画像

    # 模式配置
    enable_onboarding: bool = True  # 是否启用首次引导
    enable_voice_input: bool = False  # 是否启用语音输入

    # 执行配置
    timeout_per_step: int = 300  # 每步超时时间（秒）

    # 大模型配置
    model_base_url: Optional[str] = None  # 模型API地址
    model_api_key: Optional[str] = None  # 模型API密钥
    model_name: Optional[str] = None  # 模型名称

    # 系统提示词配置
    system_prompt: Optional[str] = None  # 自定义系统提示词

    def __post_init__(self):
        """配置验证。"""
        if self.max_steps <= 0:
            raise ValueError("max_steps must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.timeout_per_step <= 0:
            raise ValueError("timeout_per_step must be positive")
