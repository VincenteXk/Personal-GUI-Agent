"""Configuration module for Phone Agent."""

from src.shared.config import APP_PACKAGE_MAPPINGS as APP_PACKAGES

from .apps import get_app_name, get_package_name, list_supported_apps
from .prompts import SYSTEM_PROMPT
from .timing import TIMING_CONFIG
from .i18n import get_message, get_messages
from .prompts_en import SYSTEM_PROMPT as SYSTEM_PROMPT_EN
from .prompts_zh import SYSTEM_PROMPT as SYSTEM_PROMPT_ZH
from .timing import (
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