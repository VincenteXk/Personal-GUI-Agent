"""任务执行上下文管理工具。"""

import json
import os
import uuid
from typing import Any, Optional
from datetime import datetime


class ContextManager:
    """任务执行上下文管理器。"""

    def __init__(self, context_dir: str = "temp/contexts"):
        """
        初始化Context管理器。

        Args:
            context_dir: Context文件存储目录
        """
        self.context_dir = context_dir
        os.makedirs(context_dir, exist_ok=True)

    def create_context(self, task_id: Optional[str] = None) -> dict[str, Any]:
        """
        创建新的任务Context。

        Args:
            task_id: 任务ID，如果为None则自动生成

        Returns:
            Context字典
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        context = {
            "task_id": task_id,
            "created_at": datetime.now().isoformat(),
            "current_observations": {},
            "user_choices_in_session": {},
            "execution_notes": [],
        }

        return context

    def save_context(self, context: dict[str, Any]) -> str:
        """
        保存Context到文件。

        Args:
            context: Context字典

        Returns:
            Context文件路径
        """
        task_id = context.get("task_id", str(uuid.uuid4()))
        file_path = os.path.join(self.context_dir, f"task_context_{task_id}.json")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)

        return file_path

    def load_context(self, task_id: str) -> Optional[dict[str, Any]]:
        """
        加载Context从文件。

        Args:
            task_id: 任务ID

        Returns:
            Context字典，如果文件不存在则返回None
        """
        file_path = os.path.join(self.context_dir, f"task_context_{task_id}.json")

        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            context = json.load(f)

        return context

    def update_context(self, task_id: str, updates: dict[str, Any]) -> bool:
        """
        更新Context。

        Args:
            task_id: 任务ID
            updates: 更新内容

        Returns:
            是否更新成功
        """
        context = self.load_context(task_id)
        if context is None:
            return False

        # 递归更新嵌套字典
        for key, value in updates.items():
            if key in context and isinstance(context[key], dict) and isinstance(value, dict):
                context[key].update(value)
            else:
                context[key] = value

        context["updated_at"] = datetime.now().isoformat()
        self.save_context(context)
        return True

    def add_observation(self, task_id: str, key: str, value: Any) -> bool:
        """
        添加观察记录到Context。

        Args:
            task_id: 任务ID
            key: 观察键名
            value: 观察值

        Returns:
            是否添加成功
        """
        context = self.load_context(task_id)
        if context is None:
            return False

        if "current_observations" not in context:
            context["current_observations"] = {}

        context["current_observations"][key] = value
        context["updated_at"] = datetime.now().isoformat()
        self.save_context(context)
        return True

    def add_user_choice(self, task_id: str, key: str, value: Any) -> bool:
        """
        添加用户选择到Context。

        Args:
            task_id: 任务ID
            key: 选择键名
            value: 选择值

        Returns:
            是否添加成功
        """
        context = self.load_context(task_id)
        if context is None:
            return False

        if "user_choices_in_session" not in context:
            context["user_choices_in_session"] = {}

        context["user_choices_in_session"][key] = value
        context["updated_at"] = datetime.now().isoformat()
        self.save_context(context)
        return True

    def add_note(self, task_id: str, note: str) -> bool:
        """
        添加执行笔记到Context。

        Args:
            task_id: 任务ID
            note: 笔记内容

        Returns:
            是否添加成功
        """
        context = self.load_context(task_id)
        if context is None:
            return False

        if "execution_notes" not in context:
            context["execution_notes"] = []

        context["execution_notes"].append({
            "timestamp": datetime.now().isoformat(),
            "note": note,
        })

        context["updated_at"] = datetime.now().isoformat()
        self.save_context(context)
        return True

    def delete_context(self, task_id: str) -> bool:
        """
        删除Context文件。

        Args:
            task_id: 任务ID

        Returns:
            是否删除成功
        """
        file_path = os.path.join(self.context_dir, f"task_context_{task_id}.json")

        if not os.path.exists(file_path):
            return False

        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"删除Context文件失败: {e}")
            return False

    def cleanup_old_contexts(self, days: int = 7) -> int:
        """
        清理旧的Context文件。

        Args:
            days: 保留天数

        Returns:
            删除的文件数
        """
        import time

        current_time = time.time()
        deleted_count = 0

        for filename in os.listdir(self.context_dir):
            if not filename.startswith("task_context_"):
                continue

            file_path = os.path.join(self.context_dir, filename)
            file_time = os.path.getmtime(file_path)

            # 如果文件超过指定天数，删除
            if (current_time - file_time) > (days * 24 * 3600):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"删除文件失败 {filename}: {e}")

        return deleted_count

    def get_context_summary(self, task_id: str) -> Optional[dict[str, Any]]:
        """
        获取Context摘要。

        Args:
            task_id: 任务ID

        Returns:
            Context摘要
        """
        context = self.load_context(task_id)
        if context is None:
            return None

        return {
            "task_id": context.get("task_id"),
            "created_at": context.get("created_at"),
            "observations_count": len(context.get("current_observations", {})),
            "choices_count": len(context.get("user_choices_in_session", {})),
            "notes_count": len(context.get("execution_notes", [])),
        }
