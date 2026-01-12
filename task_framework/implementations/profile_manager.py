"""用户画像管理实现 - 基于 GraphRAG 的实现。"""

import json
from typing import Any, Optional
from datetime import datetime
import requests

from task_framework.interfaces import ProfileManagerInterface, UserProfile, ScenePreference


class GraphRAGProfileManager(ProfileManagerInterface):
    """基于 GraphRAG 的用户画像管理器。

    直接使用 GraphRAG 的"我"实体和"用户"类来管理用户画像。
    场景偏好存储为独立的实体和关系。
    """

    def __init__(self, graphrag_url: str = "http://localhost:8000", user_id: str = "default_user"):
        """
        初始化 ProfileManager。

        Args:
            graphrag_url: GraphRAG 后端服务地址
            user_id: 用户 ID（当前版本使用固定的"我"实体）
        """
        self.graphrag_url = graphrag_url
        self.user_id = user_id
        self.timeout = 10
        self.entity_name = "我"  # 使用固定的用户实体

        # 本地缓存
        self._profile_cache: Optional[UserProfile] = None
        self._scene_preferences_cache: dict[str, ScenePreference] = {}

    def get_profile(self) -> UserProfile:
        """获取用户画像。"""
        # 先从缓存返回
        if self._profile_cache:
            return self._profile_cache

        # 从 GraphRAG 查询
        try:
            profile_data = self._query_user_profile()
            if profile_data:
                self._profile_cache = UserProfile(
                    language_style=profile_data.get("language_style", "casual"),
                    common_apps=profile_data.get("common_apps", []),
                    default_mode=profile_data.get("default_mode", "balanced"),
                    preferences=profile_data.get("preferences", {}),
                )
                return self._profile_cache
        except Exception as e:
            print(f"⚠️ 从 GraphRAG 查询画像失败: {e}")

        # 返回默认画像
        self._profile_cache = UserProfile()
        return self._profile_cache

    def update_profile(self, profile: UserProfile) -> None:
        """更新用户画像。"""
        # 更新缓存
        self._profile_cache = profile

        # 写入 GraphRAG
        try:
            self._write_user_profile(profile)
            print(f"✅ 画像已更新到 GraphRAG")
        except Exception as e:
            print(f"⚠️ 写入 GraphRAG 失败: {e}")

    def get_scene_preference(self, scene_type: str) -> Optional[ScenePreference]:
        """获取特定场景的偏好。"""
        # 先从缓存返回
        if scene_type in self._scene_preferences_cache:
            return self._scene_preferences_cache[scene_type]

        # 从 GraphRAG 查询
        try:
            pref_data = self._query_scene_preference(scene_type)
            if pref_data:
                pref = ScenePreference(
                    scene_type=scene_type,
                    preferences=pref_data.get("preferences", {}),
                    confidence=pref_data.get("confidence", 0.5),
                    is_temporary=pref_data.get("is_temporary", False),
                )
                self._scene_preferences_cache[scene_type] = pref
                return pref
        except Exception as e:
            print(f"⚠️ 从 GraphRAG 查询场景偏好失败: {e}")

        return None

    def update_scene_preference(
        self, preference: ScenePreference, user_confirmed: bool = False
    ) -> None:
        """更新场景偏好。"""
        # 更新缓存
        self._scene_preferences_cache[preference.scene_type] = preference

        # 写入 GraphRAG
        try:
            self._write_scene_preference(preference, user_confirmed)
            print(f"✅ 场景偏好 [{preference.scene_type}] 已更新到 GraphRAG")
        except Exception as e:
            print(f"⚠️ 写入 GraphRAG 失败: {e}")

    def save(self) -> None:
        """保存画像到 GraphRAG。"""
        if self._profile_cache:
            self.update_profile(self._profile_cache)

        for pref in self._scene_preferences_cache.values():
            self.update_scene_preference(pref)

    def load(self) -> None:
        """从 GraphRAG 加载画像。"""
        # 清空缓存，重新加载
        self._profile_cache = None
        self._scene_preferences_cache = {}

        # 触发加载
        _ = self.get_profile()

    # ==================== 私有方法 ====================

    def _query_user_profile(self) -> Optional[dict[str, Any]]:
        """从 GraphRAG 查询用户画像。"""
        try:
            # 获取"我"实体的详情
            url = f"{self.graphrag_url}/api/entities/{self.entity_name}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            entity = response.json()

            # 从"用户"类中提取属性
            user_class = next(
                (c for c in entity.get("classes", []) if c["class_name"] == "用户"),
                None
            )

            if user_class:
                props = {p["name"]: p.get("value", "") for p in user_class.get("properties", [])}
                return {
                    "language_style": props.get("language_style", "casual"),
                    "common_apps": props.get("common_apps", "").split(",") if props.get("common_apps") else [],
                    "default_mode": props.get("default_mode", "balanced"),
                    "preferences": json.loads(props.get("preferences", "{}")),
                }
            return None
        except Exception as e:
            print(f"查询用户画像异常: {e}")
            return None

    def _write_user_profile(self, profile: UserProfile) -> None:
        """将用户画像写入 GraphRAG。"""
        try:
            # 更新"用户"类的属性
            properties_to_update = [
                {
                    "class_name": "用户",
                    "property_name": "language_style",
                    "value": profile.language_style
                },
                {
                    "class_name": "用户",
                    "property_name": "common_apps",
                    "value": ",".join(profile.common_apps)
                },
                {
                    "class_name": "用户",
                    "property_name": "default_mode",
                    "value": profile.default_mode
                },
                {
                    "class_name": "用户",
                    "property_name": "preferences",
                    "value": json.dumps(profile.preferences)
                }
            ]

            url = f"{self.graphrag_url}/api/entities/{self.entity_name}/properties"
            for prop_data in properties_to_update:
                response = requests.put(url, json=prop_data, timeout=self.timeout)
                response.raise_for_status()
        except Exception as e:
            print(f"写入用户画像异常: {e}")
            raise

    def _query_scene_preference(self, scene_type: str) -> Optional[dict[str, Any]]:
        """从 GraphRAG 查询场景偏好（从"我"实体的场景类节点）。"""
        try:
            # 获取"我"实体的详情
            url = f"{self.graphrag_url}/api/entities/{self.entity_name}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            entity = response.json()

            # 从"我"实体的类中查找对应场景类型
            for cls in entity.get("classes", []):
                if cls.get("class_name") == scene_type:
                    # 从该类的属性中提取"偏好"
                    for prop in cls.get("properties", []):
                        if prop.get("name") == "偏好":
                            value = prop.get("value", "{}")
                            pref_data = json.loads(value) if isinstance(value, str) else value
                            return {
                                "scene_type": scene_type,
                                "preferences": pref_data.get("preferences", pref_data),
                                "confidence": pref_data.get("confidence", 0.5),
                                "is_temporary": pref_data.get("is_temporary", False),
                            }
            return None
        except Exception as e:
            print(f"查询场景偏好异常: {e}")
            return None

    def _write_scene_preference(
        self, preference: ScenePreference, user_confirmed: bool = False
    ) -> None:
        """将场景偏好写入 GraphRAG（存储在"我"实体的场景类节点）。"""
        try:
            # 构建偏好数据
            pref_value = {
                "preferences": preference.preferences,
                "confidence": preference.confidence,
                "is_temporary": preference.is_temporary,
                "user_confirmed": user_confirmed,
                "updated_at": datetime.now().isoformat(),
            }

            # 为"我"实体添加或更新场景类
            class_data = {
                "class_name": preference.scene_type,
                "properties": {
                    "偏好": json.dumps(pref_value, ensure_ascii=False)
                }
            }

            url = f"{self.graphrag_url}/api/entities/{self.entity_name}/classes"
            response = requests.post(url, json=class_data, timeout=self.timeout)
            response.raise_for_status()
            print(f"✅ 场景偏好 [{preference.scene_type}] 已同步到 GraphRAG")
        except Exception as e:
            print(f"写入场景偏好异常: {e}")
            raise
