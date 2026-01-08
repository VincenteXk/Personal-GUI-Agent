"""AutoGLM - AI-powered phone automation framework."""

from .agent import PhoneAgent, AgentConfig
from .device_factory import get_device_factory
from .model import ModelConfig
from .model.client import MessageBuilder
from .voice import VoiceAssistant

__version__ = "0.1.0"
__all__ = [
    "PhoneAgent",
    "AgentConfig",
    "get_device_factory",
    "ModelConfig",
    "MessageBuilder",
    "VoiceAssistant",
]
