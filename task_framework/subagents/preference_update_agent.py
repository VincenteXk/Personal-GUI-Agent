"""PreferenceUpdateAgent - 偏好更新Agent。"""

import json
from typing import Any, Optional
from openai import OpenAI

from task_framework.prompts.preference_update_prompts import get_preference_update_system_prompt
from task_framework.utils import ContextManager
from task_framework.interfaces import UserInteractionInterface, InteractionType


class PreferenceUpdateAgent:
    """偏好更新Agent。

    任务完成后分析用户行为，询问是否更新偏好。
    """

    def __init__(
        self,
        user_interaction: UserInteractionInterface,
        model_client: OpenAI,
        model_name: str = "mimo-v2-flash",
        language: str = "zh",
        context_manager: Optional[ContextManager] = None,
    ):
        """
        初始化PreferenceUpdateAgent。

        Args:
            user_interaction: 用户交互接口
            model_client: OpenAI客户端
            model_name: 使用的模型名称
            language: 语言设置
            context_manager: Context管理器
        """
        self.user_interaction = user_interaction
        self.model_client = model_client
        self.model_name = model_name
        self.language = language
        self.context_manager = context_manager or ContextManager()
        self.system_prompt = get_preference_update_system_prompt(language)

    def analyze_and_update(
        self,
        task_id: str,
        user_profile: Optional[dict[str, Any]] = None,
        execution_history: Optional[list[dict[str, Any]]] = None,
    ) -> Optional[dict[str, Any]]:
        """
        分析任务执行结果并询问是否更新偏好。

        Args:
            task_id: 任务ID
            user_profile: 用户画像
            execution_history: 执行历史

        Returns:
            偏好更新建议，如果无需更新则返回None
        """
        if user_profile is None:
            user_profile = {}
        if execution_history is None:
            execution_history = []

        # 加载Context
        task_context = self.context_manager.load_context(task_id)
        if task_context is None:
            self.user_interaction.show_message(
                "无法加载任务Context", InteractionType.WARNING
            )
            return None

        # 构建分析请求
        analysis_request = {
            "task_context": task_context,
            "user_profile": user_profile,
            "execution_history": execution_history,
        }

        try:
            response = self.model_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(analysis_request, ensure_ascii=False),
                    },
                ],
                model=self.model_name,
                max_completion_tokens=512,
                temperature=0.3,
            )

            response_text = response.choices[0].message.content

            # 解析响应
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group())
                else:
                    return None

            # 检查是否需要更新
            if not response_data.get("should_update", False):
                return None

            # 显示更新建议
            question = response_data.get("question", "是否更新偏好？")
            self.user_interaction.show_message(f"\n💡 {question}", InteractionType.INFO)

            # 获取用户确认
            confirmed = self.user_interaction.get_confirmation("是否同意？", default=False)

            if confirmed:
                return response_data.get("preference_update")
            else:
                return None

        except Exception as e:
            self.user_interaction.show_message(
                f"分析偏好出错: {e}", InteractionType.ERROR
            )
            return None

    def apply_preference_update(
        self,
        preference_update: dict[str, Any],
        profile_manager: Any,  # ProfileManagerInterface
    ) -> bool:
        """
        应用偏好更新。

        Args:
            preference_update: 偏好更新数据
            profile_manager: 画像管理器

        Returns:
            是否更新成功
        """
        try:
            from task_framework.interfaces import ScenePreference

            scene = preference_update.get("scene", "")
            field = preference_update.get("field", "")
            value = preference_update.get("value")
            confidence = preference_update.get("confidence", 0.5)

            if not scene or not field:
                return False

            # 获取或创建场景偏好
            scene_pref = profile_manager.get_scene_preference(scene)
            if scene_pref is None:
                scene_pref = ScenePreference(
                    scene_type=scene,
                    preferences={field: value},
                    confidence=confidence,
                )
            else:
                # 更新现有偏好
                scene_pref.preferences[field] = value
                scene_pref.confidence = confidence

            # 保存更新
            profile_manager.update_scene_preference(scene_pref, user_confirmed=True)

            self.user_interaction.show_message(
                f"✅ 偏好已更新: {scene} - {field} = {value}",
                InteractionType.SUCCESS,
            )

            return True

        except Exception as e:
            self.user_interaction.show_message(
                f"应用偏好更新失败: {e}", InteractionType.ERROR
            )
            return False
