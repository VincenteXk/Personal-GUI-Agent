"""
SystemUpdater：增量扩展 System

职责：
1. 接收现有 System 和自然语言文本
2. 调用 LLM 判断现有 System 是否能囊括文本中的概念
3. 如果不能，以指定格式（YAML）增量扩展 System
4. 返回扩展后的 System + 变更说明
"""

import yaml
import re
from typing import Tuple, Dict, List, Optional
from pathlib import Path

from ..models.entity import System, ClassDefinition, PropertyDefinition
from ..llm.client import LLMClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SystemUpdater:
    """
    SystemUpdater：增量扩展 System

    工作流程：
    1. 分析自然语言文本中的概念
    2. 对比现有 System 的类定义
    3. 调用 LLM 判断是否需要扩展
    4. 如果需要，返回增量类定义（YAML 格式）
    5. 应用到 System（调用 System.add_class_definition）
    """

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_path: Optional[Path] = None,
    ):
        """
        初始化 SystemUpdater

        Args:
            llm_client: LLM 客户端
            prompt_path: 提示词模板路径（可选）
        """
        self.llm_client = llm_client

        # 加载提示词模板（如果提供）
        if prompt_path:
            self.prompt_template = LLMClient.load_prompt_template(prompt_path)
        else:
            # 使用默认模板
            self.prompt_template = self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """获取默认的提示词"""
        return """# 任务：检查并生成系统扩展配置

## 现有系统定义

{system_yaml}

## 输入文本

{text}

## 要求

请分析输入文本中提到的概念、实体类型和属性，判断现有系统是否能完整表达这些内容。

### 回答格式

**如果现有系统足够**，只需回复：
```
SUFFICIENT
```

**如果需要扩展**，直接输出增量扩展的YAML配置（不要任何说明文字）：
```yaml
classes:
  类名1:
    description: "类的描述"
    properties:
      - name: "属性名"
        required: false
        value_required: false
        description: "属性描述"
  类名2:
    description: "另一个类"
    properties: []
```

### 重要规则

1. 只输出**新增或需要增强**的类，不要重复输出现有类
2. 如果需要给现有类添加属性，只输出该类的新增属性
3. 类名和属性名要精炼、语义清晰
4. 每个类和属性必须有 description
5. 合理设置 required 和 value_required
6. 严格按照 YAML 格式输出，不要 markdown 代码块标记

仅回答 SUFFICIENT 或 YAML 配置，不要其他内容。
"""

    def check_and_update(
        self, system: System, text: str, auto_apply: bool = True
    ) -> Tuple[System, Dict]:
        """
        检查并更新 System（一次LLM调用完成）

        Args:
            system: 现有 System
            text: 输入的自然语言文本
            auto_apply: 是否自动应用更新（默认 True）

        Returns:
            (更新后的 System, 变更信息字典)
            变更信息格式: {
                "needed": bool,
                "added_classes": List[str],
                "enhanced_classes": List[str],
                "details": str
            }
        """
        logger.info("检查 System 是否需要扩展")
        logger.debug(f"输入文本长度: {len(text)} 字符")

        # 一次性完成检查和配置生成
        need_update, incremental_config = self._check_and_generate(system, text)

        if not need_update:
            logger.info("现有 System 足够，无需扩展")
            return system, {
                "needed": False,
                "added_classes": [],
                "enhanced_classes": [],
                "details": "现有系统足够",
            }

        if not incremental_config or "classes" not in incremental_config:
            logger.warning("LLM 未返回有效的增量配置")
            return system, {
                "needed": True,
                "added_classes": [],
                "enhanced_classes": [],
                "details": "LLM 未返回有效配置",
            }

        logger.info(f"需要扩展 System，涉及 {len(incremental_config['classes'])} 个类")

        # 应用更新
        if auto_apply:
            added, enhanced = self._apply_update(system, incremental_config)
            logger.info(
                f"System 扩展完成: 新增 {len(added)} 个类, 增强 {len(enhanced)} 个类"
            )

            return system, {
                "needed": True,
                "added_classes": added,
                "enhanced_classes": enhanced,
                "details": f"新增 {len(added)} 个类, 增强 {len(enhanced)} 个类",
            }
        else:
            # 不自动应用，只返回配置
            return system, {
                "needed": True,
                "added_classes": [],
                "enhanced_classes": [],
                "details": "需要扩展（未自动应用）",
                "config": incremental_config,
            }

    def _check_and_generate(self, system: System, text: str) -> Tuple[bool, Dict]:
        """
        一次性完成检查和配置生成

        Returns:
            (是否需要更新, 增量配置字典)
        """
        system_yaml = yaml.dump(
            {
                "classes": {
                    name: system.get_class_definition(name).to_dict()
                    for name in system.get_all_classes()
                }
            },
            allow_unicode=True,
            default_flow_style=False,
        )

        logger.debug("调用 LLM 检查并生成配置...")
        response = self.llm_client.extract_text(
            prompt_template=self.prompt_template,
            temperature=0.3,
            system_yaml=system_yaml,
            text=text,
        )

        logger.debug(f"LLM 响应长度: {len(response)} 字符")

        # 解析响应
        if "SUFFICIENT" in response.upper():
            logger.debug("LLM 判断：系统足够")
            return False, {}

        # 尝试解析为 YAML 配置
        try:
            config = self._parse_yaml_response(response)
            if config and "classes" in config and config["classes"]:
                logger.debug(f"解析到增量配置: {list(config['classes'].keys())}")
                return True, config
            else:
                logger.warning("LLM 响应不包含有效的类定义")
                return False, {}
        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            logger.debug(f"原始响应: {response[:500]}")
            return False, {}

    def _parse_yaml_response(self, response: str) -> Dict:
        """解析 LLM 返回的 YAML 配置"""
        # 移除可能的 markdown 代码块标记
        response = re.sub(r"```ya?ml\s*\n", "", response)
        response = re.sub(r"```\s*$", "", response)
        response = response.strip()

        try:
            config = yaml.safe_load(response)
            if not isinstance(config, dict):
                raise ValueError("解析结果不是字典")
            return config
        except Exception as e:
            logger.error(f"YAML 解析失败: {e}")
            logger.debug(f"原始响应:\n{response}")
            return {}

    def _apply_update(
        self, system: System, config: Dict
    ) -> Tuple[List[str], List[str]]:
        """
        应用增量配置到 System

        Returns:
            (新增的类列表, 增强的类列表)
        """
        added_classes = []
        enhanced_classes = []

        for class_name, class_config in config.get("classes", {}).items():
            # 检查类是否已存在
            existing = system.get_class_definition(class_name)

            # 构造 ClassDefinition
            properties = []
            for prop_data in class_config.get("properties", []):
                properties.append(
                    PropertyDefinition(
                        name=prop_data["name"],
                        required=prop_data.get("required", False),
                        value_required=prop_data.get("value_required", False),
                        description=prop_data.get("description"),
                    )
                )

            class_def = ClassDefinition(
                name=class_name,
                description=class_config.get("description"),
                properties=properties,
            )

            # 应用（System.add_class_definition 会自动判断是新增还是增强）
            system.add_class_definition(class_def)

            if existing:
                enhanced_classes.append(class_name)
                logger.debug(f"增强类: {class_name}")
            else:
                added_classes.append(class_name)
                logger.debug(f"新增类: {class_name}")

        return added_classes, enhanced_classes
