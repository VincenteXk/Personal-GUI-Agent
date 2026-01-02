"""
日志配置模块
根据 SIMPLERAG_VERBOSE 环境变量控制日志详细程度
"""

import logging
import os
from typing import Optional

# 需要屏蔽的第三方库logger列表
THIRD_PARTY_LOGGERS = [
    "httpcore",
    "httpcore.connection",
    "httpcore.http11",
    "httpcore.http2",
    "httpx",
    "openai",
    "openai._base_client",
    "openai._client",
    "urllib3",
    "urllib3.connectionpool",
]


def setup_logging(verbose: Optional[bool] = None) -> None:
    """
    设置日志配置

    Args:
        verbose: 是否启用详细日志，如果为None则从环境变量读取
    """
    # 确定是否启用详细日志
    if verbose is None:
        verbose_env = os.environ.get("SIMPLERAG_VERBOSE", "").lower()
        verbose = verbose_env in ("1", "true", "yes", "on")

    # 设置日志级别
    if verbose:
        level = logging.DEBUG
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    else:
        level = logging.INFO
        format_str = "%(asctime)s - %(levelname)s - %(message)s"

    # 配置根日志记录器
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # 强制重新配置
    )

    # 屏蔽第三方库的日志输出（设置为WARNING级别，只显示警告和错误）
    for logger_name in THIRD_PARTY_LOGGERS:
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.setLevel(logging.WARNING)
        # 防止日志传播到父logger
        third_party_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称（通常是模块名）

    Returns:
        配置好的日志记录器
    """
    return logging.getLogger(name)
