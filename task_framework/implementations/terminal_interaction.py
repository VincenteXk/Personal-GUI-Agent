"""终端用户交互实现。"""

import json
from typing import Any, Optional

from ..interfaces import (
    UserInteractionInterface,
    InteractionType,
    Choice,
)


class TerminalUserInteraction(UserInteractionInterface):
    """基于终端的用户交互实现。"""

    # 交互类型对应的符号
    TYPE_SYMBOLS = {
        InteractionType.INFO: "ℹ️",
        InteractionType.WARNING: "⚠️",
        InteractionType.ERROR: "❌",
        InteractionType.SUCCESS: "✅",
        InteractionType.QUESTION: "❓",
        InteractionType.CHOICE: "🔘",
        InteractionType.CONFIRMATION: "❔",
        InteractionType.PREVIEW: "👀",
        InteractionType.PROGRESS: "⏳",
    }

    def show_message(
        self, message: str, interaction_type: InteractionType = InteractionType.INFO
    ) -> None:
        """向终端显示消息。"""
        symbol = self.TYPE_SYMBOLS.get(interaction_type, "•")
        print(f"\n{symbol} {message}")

    def get_choice(
        self,
        prompt: str,
        choices: list[Choice],
        allow_custom: bool = False,
    ) -> str:
        """让用户从选项中选择。"""
        print(f"\n🔘 {prompt}")
        print()

        for i, choice in enumerate(choices, 1):
            desc = f" - {choice.description}" if choice.description else ""
            print(f"  [{i}] {choice.label}{desc}")

        if allow_custom:
            print(f"  [0] 自定义输入")

        print()

        while True:
            try:
                user_input = input("请输入选项编号: ").strip()
                choice_num = int(user_input)

                if allow_custom and choice_num == 0:
                    custom = input("请输入自定义内容: ").strip()
                    return custom

                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1].id
                else:
                    print(f"❌ 请输入 1-{len(choices)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                raise

    def get_confirmation(
        self, prompt: str, default: bool = False, risk_warning: Optional[str] = None
    ) -> bool:
        """获取用户确认。"""
        if risk_warning:
            print(f"\n⚠️  {risk_warning}")

        default_str = "Y/n" if default else "y/N"
        user_input = input(f"\n❔ {prompt} [{default_str}]: ").strip().lower()

        if not user_input:
            return default

        return user_input in ["y", "yes", "是", "确认", "确定"]

    def show_preview(self, title: str, content: dict[str, Any]) -> None:
        """显示预览信息。"""
        print(f"\n{'='*60}")
        print(f"👀 {title}")
        print("=" * 60)

        for key, value in content.items():
            if isinstance(value, list):
                print(f"\n{key}:")
                for i, item in enumerate(value, 1):
                    print(f"  {i}. {item}")
            elif isinstance(value, dict):
                print(f"\n{key}:")
                print(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                print(f"{key}: {value}")

        print("=" * 60)

    def show_progress(
        self, current: int, total: int, message: Optional[str] = None
    ) -> None:
        """显示进度信息。"""
        percentage = int((current / total) * 100)
        bar_length = 30
        filled = int((current / total) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        msg = f" - {message}" if message else ""
        print(
            f"\r⏳ [{bar}] {percentage}% ({current}/{total}){msg}", end="", flush=True
        )

        if current == total:
            print()  # 完成后换行

    def show_result(self, title: str, result: dict[str, Any]) -> None:
        """显示结构化结果。"""
        print(f"\n{'='*60}")
        print(f"📊 {title}")
        print("=" * 60)

        for key, value in result.items():
            if isinstance(value, (dict, list)):
                print(f"\n{key}:")
                print(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                print(f"{key}: {value}")

        print("=" * 60)

    def request_missing_info(
        self,
        prompt: str,
        missing_fields: list[str],
        suggestions: Optional[dict[str, list[str]]] = None,
    ) -> dict[str, str]:
        """请求缺失的信息。"""
        print(f"\n❓ {prompt}")
        print()

        result = {}

        for field in missing_fields:
            # 显示建议（如果有）
            if suggestions and field in suggestions:
                print(f"\n建议的 {field}:")
                for i, suggestion in enumerate(suggestions[field], 1):
                    print(f"  [{i}] {suggestion}")
                print(f"  [0] 自定义输入")

                try:
                    choice = int(input(f"\n{field} (选择或输入): ").strip())
                    if 1 <= choice <= len(suggestions[field]):
                        result[field] = suggestions[field][choice - 1]
                        continue
                except (ValueError, IndexError):
                    pass

            # 直接输入
            value = input(f"{field}: ").strip()
            if value:
                result[field] = value

        return result
