"""
LLM客户端封装，支持OpenAI兼容的API（同步和异步）
"""

from typing import Optional, Dict, Any, Literal
from openai import OpenAI, AsyncOpenAI
import os
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)

# API提供商配置
API_PROVIDERS = {
    "mimo": {
        "env_key": "MIMO_API_KEY",
        "default_base_url": "https://api.xiaomimimo.com/v1",
        "default_model": "mimo-v2-flash",
    },
    "ark": {
        "env_key": "ARK_API_KEY",
        "default_base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "deepseek-v3-2-251201",
    },
}


class LLMClient:
    """LLM客户端，封装大模型调用"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        provider: Literal["mimo", "ark"] = "mimo",
        verbose: bool = False,
    ):
        """
        初始化LLM客户端

        Args:
            api_key: API密钥，如果为None则从环境变量读取
            base_url: API基础URL，如果为None则使用provider的默认值
            model: 模型名称，如果为None则使用provider的默认值
            max_retries: 最大重试次数
            provider: API提供商，可选 "mimo" 或 "ark"，默认为 "mimo"
            verbose: 是否打印详细的输入输出信息，默认为 False
        """
        self.provider = provider
        self.verbose = verbose
        provider_config = API_PROVIDERS.get(provider)
        if not provider_config:
            raise ValueError(
                f"不支持的API提供商: {provider}，支持: {list(API_PROVIDERS.keys())}"
            )

        # 从环境变量或参数获取API密钥
        self.api_key = api_key or os.environ.get(provider_config["env_key"])
        # 使用提供的base_url或provider的默认值
        self.base_url = base_url or provider_config["default_base_url"]
        # 使用提供的model或provider的默认值
        self.model = model or provider_config["default_model"]
        self.max_retries = max_retries

        if not self.api_key:
            raise ValueError(
                f"需要提供API密钥或设置{provider_config['env_key']}环境变量"
            )

        logger.debug(
            f"初始化LLM客户端: provider={provider}, "
            f"base_url={self.base_url}, model={self.model}, verbose={verbose}"
        )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            max_retries=max_retries,
        )

        # 异步客户端（延迟初始化）
        self._async_client = None

    def chat_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        调用聊天完成API

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            模型返回的文本内容
        """
        logger.debug(
            f"调用LLM API: model={self.model}, temperature={temperature}, max_tokens={max_tokens}"
        )
        logger.debug(f"消息数量: {len(messages)}")

        # 如果 verbose 模式，打印输入内容
        if self.verbose:
            for i, msg in enumerate(messages):
                logger.info(f"消息 {i+1} ({msg.get('role')}):")
                logger.info(
                    f"{msg.get('content')[:1000]}{'...' if len(msg.get('content', '')) > 1000 else ''}"
                )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            logger.debug(f"LLM响应成功，返回内容长度: {len(content)} 字符")

            # 如果 verbose 模式，打印输出内容
            if self.verbose:
                logger.info(f"LLM响应内容:")
                logger.info(f"{content[:1000]}{'...' if len(content) > 1000 else ''}")

            return content
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"LLM调用失败: {str(e)}")

    def extract_text(
        self,
        prompt_template: str,
        input_text: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        使用提示词模板提取文本

        Args:
            prompt_template: 提示词模板字符串
            input_text: 输入文本（可选，如果模板中不需要）
            temperature: 温度参数，默认0.7
            **kwargs: 其他模板变量

        Returns:
            模型返回的文本内容
        """
        logger.debug("准备调用LLM提取文本...")
        logger.debug(f"模板变量: {list(kwargs.keys())}")

        # 填充模板变量
        if input_text:
            formatted_prompt = prompt_template.format(input_text=input_text, **kwargs)
        else:
            formatted_prompt = prompt_template.format(**kwargs)

        logger.debug(f"格式化后的提示词长度: {len(formatted_prompt)} 字符")
        if not self.verbose:
            logger.debug(f"提示词内容:\n{formatted_prompt}")

        messages = [{"role": "user", "content": formatted_prompt}]

        logger.debug("发送请求到LLM...")
        response = self.chat_completion(messages, temperature=temperature)
        logger.debug("收到LLM响应")

        return response

    @property
    def async_client(self) -> AsyncOpenAI:
        """获取异步客户端（延迟初始化）"""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                max_retries=self.max_retries,
            )
        return self._async_client

    async def chat_completion_async(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        异步调用聊天完成API

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            模型返回的文本内容
        """
        logger.debug(
            f"异步调用LLM API: model={self.model}, temperature={temperature}, max_tokens={max_tokens}"
        )
        logger.debug(f"消息数量: {len(messages)}")

        # 如果 verbose 模式，打印输入内容
        if self.verbose:
            for i, msg in enumerate(messages):
                logger.info(f"消息 {i+1} ({msg.get('role')}):")
                logger.info(
                    f"{msg.get('content')[:1000]}{'...' if len(msg.get('content', '')) > 1000 else ''}"
                )

        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            logger.debug(f"LLM异步响应成功，返回内容长度: {len(content)} 字符")

            # 如果 verbose 模式，打印输出内容
            if self.verbose:
                logger.info(f"LLM响应内容:")
                logger.info(f"{content[:1000]}{'...' if len(content) > 1000 else ''}")

            return content
        except Exception as e:
            logger.error(f"LLM异步调用失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"LLM异步调用失败: {str(e)}")

    async def extract_text_async(
        self,
        prompt_template: str,
        input_text: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        异步使用提示词模板提取文本

        Args:
            prompt_template: 提示词模板字符串
            input_text: 输入文本（可选，如果模板中不需要）
            temperature: 温度参数，默认0.7
            **kwargs: 其他模板变量

        Returns:
            模型返回的文本内容
        """
        logger.debug("准备异步调用LLM提取文本...")
        logger.debug(f"模板变量: {list(kwargs.keys())}")

        # 填充模板变量
        if input_text:
            formatted_prompt = prompt_template.format(input_text=input_text, **kwargs)
        else:
            formatted_prompt = prompt_template.format(**kwargs)

        logger.debug(f"格式化后的提示词长度: {len(formatted_prompt)} 字符")
        if not self.verbose:
            logger.debug(f"提示词内容:\n{formatted_prompt}")

        messages = [{"role": "user", "content": formatted_prompt}]

        logger.debug("发送异步请求到LLM...")
        response = await self.chat_completion_async(messages, temperature=temperature)
        logger.debug("收到LLM异步响应")

        return response

    async def close_async(self):
        """关闭异步客户端"""
        if self._async_client is not None:
            await self._async_client.close()
            self._async_client = None

    @staticmethod
    def load_prompt_template(file_path: Path) -> str:
        """
        从文件加载提示词模板

        Args:
            file_path: 提示词文件路径

        Returns:
            提示词模板字符串
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
