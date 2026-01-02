"""
系统构建器，用于从例子中分析和构建类/属性系统配置
"""

import yaml
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path

from ..llm.client import LLMClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SystemBuilder:
    """系统构建器，用于分析和构建类/属性系统配置"""

    def __init__(
        self,
        llm_client: LLMClient,
        core_prompt_path: Path,
        rules_prompt_path: Path,
        build_prompt_path: Path,
        base_system: Optional[Dict] = None,
    ):
        """
        初始化系统构建器

        Args:
            llm_client: LLM客户端
            core_prompt_path: 核心系统提示词文件路径
            rules_prompt_path: 系统规则提示词文件路径
            build_prompt_path: 构建系统提示词文件路径
            base_system: 基础系统配置（如果为None，使用默认基础架构）
        """
        self.llm_client = llm_client

        # 加载提示词模板
        self.core_prompt = LLMClient.load_prompt_template(core_prompt_path)
        self.rules_prompt = LLMClient.load_prompt_template(rules_prompt_path)
        self.build_prompt_template = LLMClient.load_prompt_template(build_prompt_path)

        # 设置基础系统架构
        if base_system is None:
            # 默认基础架构：包含"用户"类
            self.base_system = {
                "classes": {
                    "用户": {
                        "description": "用户本人，执行操作的主体",
                        "properties": [],
                    }
                },
                "base_entities": [],
            }
        else:
            self.base_system = base_system

        # 确保 base_entities 存在
        if "base_entities" not in self.base_system:
            self.base_system["base_entities"] = []

        logger.debug("系统构建器初始化完成")
        logger.debug(
            f"基础系统架构包含 {len(self.base_system.get('classes', {}))} 个类"
        )
        logger.debug(
            f"基础实体包含 {len(self.base_system.get('base_entities', []))} 个实体"
        )

    def build_or_extend_system(
        self, example_text: str, existing_system: Optional[Dict] = None
    ) -> Dict:
        """
        构建或扩展系统配置（统一操作）
        基于基础架构，从例子文本中构建或扩展系统配置

        Args:
            example_text: 示例文本
            existing_system: 现有系统配置（可选，如果提供则进行扩展，否则构建新系统）

        Returns:
            系统配置字典，格式与config.yaml中的classes部分相同
            包含基础架构 + 从例子中提取的类
        """
        if existing_system:
            logger.info("基于现有系统扩展配置")
            logger.debug(f"现有系统包含 {len(existing_system.get('classes', {}))} 个类")
        else:
            logger.info("从例子构建新系统配置")

        logger.debug(f"例子文本长度: {len(example_text)} 字符")
        logger.debug(f"例子文本预览: {example_text[:200]}...")

        # 合并基础架构和现有系统
        current_system = self._merge_with_base(existing_system)

        # 将当前系统转换为YAML字符串
        current_system_yaml = yaml.dump(
            {"classes": current_system.get("classes", {})},
            allow_unicode=True,
            default_flow_style=False,
        )

        # 准备提示词（包含规则和基础架构）
        # 构建基础架构YAML（如果不存在现有系统，使用基础架构）
        if existing_system:
            base_system_yaml = current_system_yaml
        else:
            # 只包含类的部分（不包括base_entities，因为实体是在提取阶段处理的）
            base_classes = {"classes": self.base_system.get("classes", {})}
            base_system_yaml = yaml.dump(
                base_classes,
                allow_unicode=True,
                default_flow_style=False,
            )

        # 生成基础实体信息字符串
        base_entities_info = self._format_base_entities()

        # 格式化提示词
        # 构建参数字典，包含所有可能的变量
        format_kwargs = {
            "core_prompt": self.core_prompt,
            "rules_prompt": self.rules_prompt,
            "base_system_yaml": base_system_yaml,
            "base_entities_info": base_entities_info,
            "example_text": example_text,
            "is_extension": "扩展现有系统" if existing_system else "构建新系统",
        }

        # 如果模板不支持某些变量，尝试移除它们
        try:
            prompt = self.build_prompt_template.format(**format_kwargs)
        except KeyError as e:
            # 如果缺少变量，尝试不使用该变量
            missing_key = str(e).strip("'")
            logger.debug(f"提示词模板不支持变量 '{missing_key}'，尝试移除")
            format_kwargs.pop(missing_key, None)
            prompt = self.build_prompt_template.format(**format_kwargs)

        logger.debug("调用LLM构建/扩展系统配置...")
        logger.debug(f"提示词长度: {len(prompt)} 字符")

        # 调用LLM
        messages = [{"role": "user", "content": prompt}]
        response = self.llm_client.chat_completion(messages, temperature=0.3)

        logger.debug(f"LLM响应长度: {len(response)} 字符")
        logger.debug(f"LLM响应内容:\n{response}")

        # 解析YAML响应
        new_system_config = self._parse_yaml_response(response)

        # 合并基础架构
        final_system = self._merge_with_base(new_system_config)

        logger.info(
            f"系统配置构建/扩展完成，包含 {len(final_system.get('classes', {}))} 个类"
        )
        return final_system

    def _merge_with_base(self, system_config: Optional[Dict]) -> Dict:
        """
        将系统配置与基础架构合并

        Args:
            system_config: 系统配置（可选）

        Returns:
            合并后的系统配置
        """
        merged = {"classes": {}}

        # 先添加基础架构
        merged["classes"].update(self.base_system.get("classes", {}))

        # 再添加/覆盖系统配置中的类
        if system_config:
            merged["classes"].update(system_config.get("classes", {}))

        return merged

    def _format_base_entities(self) -> str:
        """
        格式化基础实体信息为字符串

        Returns:
            格式化的基础实体信息字符串
        """
        base_entities = self.base_system.get("base_entities", [])
        if not base_entities:
            return "无预定义基础实体"

        lines = ["预定义的基础实体（这些实体在系统中始终可用）："]
        for entity in base_entities:
            entity_name = entity.get("name", "")
            entity_desc = entity.get("description", "")
            entity_classes = entity.get("classes", [])
            classes_str = ", ".join(entity_classes) if entity_classes else "无类"
            lines.append(f"  - {entity_name}: {entity_desc} (类: {classes_str})")

        return "\n".join(lines)

    def build_system_from_example(self, example_text: str) -> Dict:
        """
        从例子文本中构建系统配置（向后兼容方法）

        Args:
            example_text: 示例文本

        Returns:
            系统配置字典
        """
        return self.build_or_extend_system(example_text, existing_system=None)

    def validate_and_extend_system(
        self, existing_system: Dict, example_text: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        验证现有系统是否能充分概括例子，如果不能则扩展系统（向后兼容方法）

        Args:
            existing_system: 现有系统配置（classes部分）
            example_text: 新的示例文本

        Returns:
            (is_adequate, updated_system, message) 元组
        """
        # 先尝试使用现有系统
        extended_system = self.build_or_extend_system(example_text, existing_system)

        # 检查是否有新增的类
        existing_classes = set(existing_system.get("classes", {}).keys())
        extended_classes = set(extended_system.get("classes", {}).keys())
        new_classes = extended_classes - existing_classes

        if new_classes:
            logger.info(f"系统需要扩展，新增类: {new_classes}")
            return (
                False,
                extended_system,
                f"系统需要扩展，新增了 {len(new_classes)} 个类",
            )
        else:
            logger.info("现有系统充分，无需扩展")
            return True, None, "系统充分，无需扩展"

    def _parse_yaml_response(self, response: str) -> Dict:
        """
        从LLM响应中解析YAML配置
        支持分步输出格式，提取Stage 5的YAML配置

        Args:
            response: LLM返回的文本

        Returns:
            解析后的系统配置字典
        """
        logger.debug("开始解析YAML响应...")

        # 尝试提取Stage 5的YAML代码块（分步输出格式）
        yaml_content = self._extract_stage5_yaml(response)

        if not yaml_content:
            # 如果没有找到Stage 5，尝试提取YAML代码块（向后兼容）
            yaml_content = self._extract_yaml_block(response)

        if not yaml_content:
            # 如果没有代码块，尝试直接解析整个响应
            yaml_content = response.strip()

        try:
            config = yaml.safe_load(yaml_content)
            if not config:
                raise ValueError("解析结果为空")

            # 确保有classes键
            if "classes" not in config:
                raise ValueError("响应中缺少'classes'键")

            # 合并基础架构（确保基础架构始终存在）
            config = self._merge_with_base(config)

            logger.debug(f"成功解析YAML，包含 {len(config['classes'])} 个类")
            return config
        except Exception as e:
            logger.error(f"解析YAML失败: {e}", exc_info=True)
            logger.error(f"响应内容:\n{response}")
            raise ValueError(f"无法解析YAML响应: {e}")

    def _parse_validation_response(self, response: str) -> Dict:
        """
        解析验证响应
        支持分步输出格式，提取Stage 5的YAML配置和文本信息

        Args:
            response: LLM返回的文本

        Returns:
            解析后的结果字典，包含status、message和可选的classes
        """
        logger.debug("开始解析验证响应...")

        # 尝试从Stage 5提取status和message（分步输出格式）
        stage5_info = self._extract_stage5_info(response)

        # 尝试提取Stage 5的YAML代码块（分步输出格式）
        yaml_content = self._extract_stage5_yaml(response)

        if not yaml_content:
            # 如果没有找到Stage 5，尝试提取YAML代码块（向后兼容）
            yaml_content = self._extract_yaml_block(response)

        if not yaml_content:
            yaml_content = response.strip()

        try:
            result = yaml.safe_load(yaml_content)
            if not result:
                raise ValueError("解析结果为空")

            # 如果YAML中没有status，尝试从Stage 5文本中提取
            if "status" not in result and stage5_info:
                result["status"] = stage5_info.get("status")
                if stage5_info.get("message"):
                    result["message"] = stage5_info["message"]

            # 如果仍然没有status，尝试从整个响应中提取
            if "status" not in result:
                # 尝试从响应文本中查找status
                status_match = self._extract_status_from_text(response)
                if status_match:
                    result["status"] = status_match["status"]
                    if status_match.get("message"):
                        result["message"] = status_match["message"]

            if "status" not in result:
                raise ValueError("响应中缺少'status'键")

            status = result["status"]
            if status not in ["adequate", "needs_extension"]:
                raise ValueError(f"无效的status值: {status}")

            # 如果系统需要扩展，确保包含"用户"类
            if status == "needs_extension" and "classes" in result:
                if "用户" not in result["classes"]:
                    logger.warning("扩展后的系统配置中缺少'用户'类，自动添加")
                    result["classes"]["用户"] = {
                        "description": "用户本人，执行操作的主体",
                        "properties": [],
                    }

            logger.debug(f"解析成功，status: {status}")
            return result
        except Exception as e:
            logger.error(f"解析验证响应失败: {e}", exc_info=True)
            logger.error(f"响应内容:\n{response}")
            raise ValueError(f"无法解析验证响应: {e}")

    def _extract_stage5_info(self, text: str) -> Optional[Dict]:
        """
        从Stage 5的文本部分提取status和message信息

        Args:
            text: 包含分步输出的文本

        Returns:
            包含status和message的字典，如果没有找到则返回None
        """
        import re

        # 尝试匹配 Stage 5 部分（匹配到YAML代码块之前）
        stage5_patterns = [
            r"\*\*Stage 5[^*]*?\*\*\s*\n(.*?)(?=\n```|$)",
            r"Stage 5[^:]*?:\s*\n(.*?)(?=\n```|$)",
            r"Stage 5.*?\n(.*?)(?=\n```|$)",
        ]

        stage5_text = None
        for pattern in stage5_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                stage5_text = match.group(1).strip()
                break

        # 如果没找到，尝试在整个文本中查找
        if not stage5_text:
            # 尝试查找包含Status的行及其上下文
            status_section = re.search(
                r"(Status|status):\s*(adequate|needs_extension).*?(?=\n```|$)",
                text,
                re.DOTALL | re.IGNORECASE,
            )
            if status_section:
                stage5_text = status_section.group(0)

        if not stage5_text:
            return None

        result = {}

        # 提取status（从stage5_text或整个文本）
        status_patterns = [
            r"Status:\s*(adequate|needs_extension)",
            r"status:\s*(adequate|needs_extension)",
            r"Status\s*=\s*(adequate|needs_extension)",
        ]

        search_text = stage5_text if stage5_text else text
        for pattern in status_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                status = match.group(1).lower()
                if status == "needs_extension":
                    result["status"] = "needs_extension"
                else:
                    result["status"] = "adequate"
                break

        # 提取message/reasoning
        message_patterns = [
            r"Reasoning:\s*(.+?)(?=\n\n|\n```|$)",
            r"message:\s*(.+?)(?=\n\n|\n```|$)",
            r"Message:\s*(.+?)(?=\n\n|\n```|$)",
        ]
        for pattern in message_patterns:
            match = re.search(pattern, search_text, re.DOTALL | re.IGNORECASE)
            if match:
                result["message"] = match.group(1).strip()
                break

        if result:
            logger.debug(f"成功提取Stage 5信息: {result}")
            return result

        return None

    def _extract_status_from_text(self, text: str) -> Optional[Dict]:
        """
        从整个响应文本中提取status和message（备用方法）

        Args:
            text: 响应文本

        Returns:
            包含status和message的字典，如果没有找到则返回None
        """
        import re

        result = {}

        # 尝试在整个文本中查找status
        status_patterns = [
            r"Status:\s*(adequate|needs_extension)",
            r"status:\s*(adequate|needs_extension)",
        ]
        for pattern in status_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                status = match.group(1).lower()
                if status == "needs_extension":
                    result["status"] = "needs_extension"
                else:
                    result["status"] = "adequate"
                break

        # 尝试提取reasoning/message
        message_patterns = [
            r"Reasoning:\s*(.+?)(?=\n\n|\n```|$)",
        ]
        for pattern in message_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                result["message"] = match.group(1).strip()
                break

        return result if result else None

    def _extract_stage5_yaml(self, text: str) -> Optional[str]:
        """
        从分步输出格式中提取Stage 5的YAML配置

        Args:
            text: 包含分步输出的文本

        Returns:
            提取的YAML内容，如果没有找到则返回None
        """
        import re

        # 尝试匹配 Stage 5 部分的YAML代码块
        patterns = [
            r"Stage 5.*?```yaml\s*\n(.*?)\n```",
            r"Stage 5.*?```\s*\n(.*?)\n```",
            r"\*\*Stage 5.*?\*\*.*?```yaml\s*\n(.*?)\n```",
            r"\*\*Stage 5.*?\*\*.*?```\s*\n(.*?)\n```",
            r"Stage 5:.*?```yaml\s*\n(.*?)\n```",
            r"Stage 5:.*?```\s*\n(.*?)\n```",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                yaml_content = match.group(1).strip()
                if yaml_content:
                    logger.debug("成功提取Stage 5的YAML配置")
                    return yaml_content

        return None

    def _extract_yaml_block(self, text: str) -> Optional[str]:
        """
        从文本中提取YAML代码块

        Args:
            text: 包含YAML的文本

        Returns:
            提取的YAML内容，如果没有找到则返回None
        """
        # 尝试匹配 ```yaml ... ``` 或 ``` ... ```
        import re

        patterns = [
            r"```yaml\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
            r"```yaml(.*?)```",
            r"```(.*?)```",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()

        return None
