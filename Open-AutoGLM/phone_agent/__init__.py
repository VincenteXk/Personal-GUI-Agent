"""
Phone Agent - An AI-powered phone automation framework.

This package provides tools for automating Android and iOS phone interactions
using AI models for visual understanding and decision making.
"""

from phone_agent.agent import PhoneAgent
from phone_agent.agent_ios import IOSPhoneAgent

# Import additional classes
from phone_agent.agent import AgentConfig
from phone_agent.device_factory import DeviceType, get_device_factory, set_device_type
from phone_agent.model import ModelConfig
from phone_agent.model.client import MessageBuilder

__version__ = "0.1.0"
__all__ = ["PhoneAgent", "IOSPhoneAgent", "AgentConfig", "DeviceType", "get_device_factory", "set_device_type", "ModelConfig", "MessageBuilder"]