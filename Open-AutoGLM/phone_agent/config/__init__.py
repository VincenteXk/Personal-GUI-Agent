"""Configuration module for Phone Agent."""

"""Configuration package for phone agent."""

import sys
import os

# 尝试使用相对导入，如果失败则使用绝对导入
try:
    from ...shared_config import APP_PACKAGE_MAPPINGS as APP_PACKAGES
except ImportError:
    # 如果相对导入失败，尝试从根目录导入
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from shared_config import APP_PACKAGE_MAPPINGS as APP_PACKAGES

from .apps import get_app_name, get_package_name, list_supported_apps
from .prompts import SYSTEM_PROMPT
from .timing import TIMING_CONFIG

__all__ = [
    'APP_PACKAGES',
    'get_app_name',
    'get_package_name',
    'list_supported_apps',
    'SYSTEM_PROMPT',
    'TIMING_CONFIG'
]
from phone_agent.config.i18n import get_message, get_messages
from phone_agent.config.prompts_en import SYSTEM_PROMPT as SYSTEM_PROMPT_EN
from phone_agent.config.prompts_zh import SYSTEM_PROMPT as SYSTEM_PROMPT_ZH
from phone_agent.config.timing import (
    TIMING_CONFIG,
    ActionTimingConfig,
    ConnectionTimingConfig,
    DeviceTimingConfig,
    TimingConfig,
    get_timing_config,
    update_timing_config,
)


def get_system_prompt(lang: str = "cn") -> str:
    """
    Get system prompt by language.

    Args:
        lang: Language code, 'cn' for Chinese, 'en' for English.

    Returns:
        System prompt string.
    """
    if lang == "en":
        return SYSTEM_PROMPT_EN
    return SYSTEM_PROMPT_ZH


# Default to Chinese for backward compatibility
SYSTEM_PROMPT = SYSTEM_PROMPT_ZH

__all__ = [
    "APP_PACKAGES",
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_ZH",
    "SYSTEM_PROMPT_EN",
    "get_system_prompt",
    "get_messages",
    "get_message",
    "TIMING_CONFIG",
    "TimingConfig",
    "ActionTimingConfig",
    "DeviceTimingConfig",
    "ConnectionTimingConfig",
    "get_timing_config",
    "update_timing_config",
]