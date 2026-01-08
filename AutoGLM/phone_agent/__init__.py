"""
Phone Agent - An AI-powered phone automation framework.

This package provides tools for automating Android phone interactions
using AI models for visual understanding and decision making.
"""

from phone_agent.agent import PhoneAgent

# Import additional classes
from phone_agent.agent import AgentConfig
from phone_agent.device_factory import get_device_factory
from phone_agent.model import ModelConfig
from phone_agent.model.client import MessageBuilder

__version__ = "0.1.0"
__all__ = ["PhoneAgent", "AgentConfig", "get_device_factory", "ModelConfig", "MessageBuilder"]