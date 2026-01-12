"""任务框架接口定义。"""

from .user_input import UserInputInterface
from .user_interaction import UserInteractionInterface, InteractionType, Choice
from .device_capability import DeviceCapabilityInterface
from .profile_manager import ProfileManagerInterface, UserProfile, ScenePreference
from .task_executor import (
    TaskExecutorInterface,
    ExecutionResult,
    TaskCapability,
    TaskParameter,
)

__all__ = [
    "UserInputInterface",
    "UserInteractionInterface",
    "InteractionType",
    "Choice",
    "DeviceCapabilityInterface",
    "ProfileManagerInterface",
    "UserProfile",
    "ScenePreference",
    "TaskExecutorInterface",
    "ExecutionResult",
    "TaskCapability",
    "TaskParameter",
]
