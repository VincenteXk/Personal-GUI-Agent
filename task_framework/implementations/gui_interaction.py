"""图形界面用户交互实现。"""

import json
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
from typing import Any, Optional

from ..interfaces import (
    UserInteractionInterface,
    InteractionType,
    Choice,
)


class GUIUserInteraction(UserInteractionInterface):
    """基于tkinter的图形界面用户交互实现。"""

    # 交互类型对应的图标和标题颜色
    TYPE_CONFIG = {
        InteractionType.INFO: {
            "icon": "ℹ️",
            "title": "信息",
            "icon_type": messagebox.INFO,
        },
        InteractionType.WARNING: {
            "icon": "⚠️",
            "title": "警告",
            "icon_type": messagebox.WARNING,
        },
        InteractionType.ERROR: {
            "icon": "❌",
            "title": "错误",
            "icon_type": messagebox.ERROR,
        },
        InteractionType.SUCCESS: {
            "icon": "✅",
            "title": "成功",
            "icon_type": messagebox.INFO,
        },
        InteractionType.QUESTION: {
            "icon": "❓",
            "title": "提问",
            "icon_type": messagebox.QUESTION,
        },
        InteractionType.CHOICE: {
            "icon": "🔘",
            "title": "选择",
            "icon_type": messagebox.QUESTION,
        },
        InteractionType.CONFIRMATION: {
            "icon": "❔",
            "title": "确认",
            "icon_type": messagebox.QUESTION,
        },
        InteractionType.PREVIEW: {
            "icon": "👀",
            "title": "预览",
            "icon_type": messagebox.INFO,
        },
        InteractionType.PROGRESS: {
            "icon": "⏳",
            "title": "进度",
            "icon_type": messagebox.INFO,
        },
    }

    def __init__(self, root: Optional[tk.Tk] = None):
        """
        初始化GUI交互实现。

        Args:
            root: tkinter根窗口。如果为None，会自动创建。
        """
        self.root = root or self._create_root()
        self._is_owned_root = root is None
        self._progress_window: Optional[tk.Toplevel] = None
        self._progress_label: Optional[tk.Label] = None

    @staticmethod
    def _create_root() -> tk.Tk:
        """创建根窗口。"""
        root = tk.Tk()
        root.withdraw()  # 初始隐藏
        return root

    def show_message(
        self, message: str, interaction_type: InteractionType = InteractionType.INFO
    ) -> None:
        """
        显示消息对话框。

        Args:
            message: 要显示的消息
            interaction_type: 交互类型
        """
        config = self.TYPE_CONFIG.get(interaction_type)
        if not config:
            config = self.TYPE_CONFIG[InteractionType.INFO]

        icon_type = config["icon_type"]
        title = config["title"]

        messagebox.showmessage(
            title,
            message,
            parent=self.root,
            icon=icon_type,
        ) if interaction_type != InteractionType.ERROR else messagebox.showerror(
            title, message, parent=self.root
        )

        # 对于不同类型的消息使用不同的对话框函数
        if interaction_type == InteractionType.ERROR:
            messagebox.showerror(title, message, parent=self.root)
        elif interaction_type == InteractionType.WARNING:
            messagebox.showwarning(title, message, parent=self.root)
        else:
            messagebox.showinfo(title, message, parent=self.root)

    def get_choice(
        self,
        prompt: str,
        choices: list[Choice],
        allow_custom: bool = False,
    ) -> str:
        """
        创建选择对话框让用户选择。

        Args:
            prompt: 提示信息
            choices: 选择项列表
            allow_custom: 是否允许自定义输入

        Returns:
            选中项的ID或自定义输入内容
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("选择")
        dialog.geometry("400x300")
        dialog.resizable(False, False)

        # 使当前窗口在最前面
        dialog.transient(self.root)
        dialog.grab_set()

        selected_value = tk.StringVar()
        custom_input = None

        # 标题
        title_label = tk.Label(
            dialog, text=prompt, font=("Arial", 11, "bold"), wraplength=350
        )
        title_label.pack(pady=10, padx=10)

        # 创建radiobutton框架
        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 添加选择项
        for choice in choices:
            desc = f" - {choice.description}" if choice.description else ""
            label_text = f"{choice.label}{desc}"

            rb = tk.Radiobutton(
                frame,
                text=label_text,
                variable=selected_value,
                value=choice.id,
                font=("Arial", 10),
                wraplength=320,
                justify=tk.LEFT,
            )
            rb.pack(anchor=tk.W, pady=5)

        # 自定义输入选项
        custom_frame = None
        custom_entry = None

        if allow_custom:

            def on_custom_selected():
                nonlocal custom_frame, custom_entry
                if custom_frame:
                    custom_frame.pack(fill=tk.X, padx=20, pady=10)
                    if custom_entry:
                        custom_entry.focus()

            custom_frame = tk.Frame(dialog)
            tk.Label(custom_frame, text="自定义:", font=("Arial", 10)).pack(
                side=tk.LEFT, padx=5
            )
            custom_entry = tk.Entry(custom_frame, width=30)
            custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            rb = tk.Radiobutton(
                frame,
                text="自定义输入",
                variable=selected_value,
                value="__custom__",
                font=("Arial", 10),
                command=on_custom_selected,
            )
            rb.pack(anchor=tk.W, pady=5)

        # 按钮框架
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def on_ok():
            if selected_value.get() == "__custom__":
                if custom_entry and custom_entry.get():
                    selected_value.set(custom_entry.get())
            if not selected_value.get():
                messagebox.showwarning("提示", "请选择一个选项", parent=dialog)
                return
            dialog.destroy()

        def on_cancel():
            selected_value.set("")
            dialog.destroy()

        tk.Button(
            button_frame, text="确定", command=on_ok, width=10, bg="#4CAF50", fg="white"
        ).pack(side=tk.RIGHT, padx=5)
        tk.Button(
            button_frame, text="取消", command=on_cancel, width=10, bg="#f44336", fg="white"
        ).pack(side=tk.RIGHT, padx=5)

        # 等待对话框关闭
        dialog.wait_window()

        return selected_value.get() or ""

    def get_confirmation(
        self,
        prompt: str,
        default: bool = False,
        risk_warning: Optional[str] = None,
    ) -> bool:
        """
        获取用户确认。

        Args:
            prompt: 提示信息
            default: 默认值（True/False）
            risk_warning: 风险警告信息

        Returns:
            用户是否确认
        """
        message = prompt
        if risk_warning:
            message = f"{risk_warning}\n\n{prompt}"

        icon_type = messagebox.WARNING if risk_warning else messagebox.QUESTION

        result = messagebox.askyesno(
            "确认",
            message,
            parent=self.root,
            default=messagebox.YES if default else messagebox.NO,
            icon=icon_type,
        )

        return result

    def show_preview(self, title: str, content: dict[str, Any]) -> None:
        """
        显示预览信息。

        Args:
            title: 预览标题
            content: 要预览的内容字典
        """
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"👀 {title}")
        preview_window.geometry("600x400")

        preview_window.transient(self.root)

        # 创建滚动文本框
        text_frame = tk.Frame(preview_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = scrolledtext.ScrolledText(
            text_frame,
            font=("Courier", 10),
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED,
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # 格式化内容
        formatted_content = self._format_preview_content(content)

        # 插入内容
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, formatted_content)
        text_widget.config(state=tk.DISABLED)

        # 关闭按钮
        button_frame = tk.Frame(preview_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(
            button_frame,
            text="关闭",
            command=preview_window.destroy,
            width=10,
            bg="#2196F3",
            fg="white",
        ).pack()

        preview_window.transient(self.root)
        preview_window.grab_set()

    @staticmethod
    def _format_preview_content(content: dict[str, Any]) -> str:
        """格式化预览内容为文本。"""
        lines = []

        for key, value in content.items():
            lines.append(f"\n{key}:")
            lines.append("-" * 60)

            if isinstance(value, list):
                for i, item in enumerate(value, 1):
                    lines.append(f"  {i}. {item}")
            elif isinstance(value, dict):
                formatted = json.dumps(
                    value, ensure_ascii=False, indent=2, default=str
                )
                lines.append(formatted)
            else:
                lines.append(f"  {value}")

        return "\n".join(lines)

    def show_progress(
        self, current: int, total: int, message: Optional[str] = None
    ) -> None:
        """
        显示进度。

        Args:
            current: 当前进度
            total: 总数
            message: 可选的进度信息
        """
        if self._progress_window is None or not self._progress_window.winfo_exists():
            self._progress_window = tk.Toplevel(self.root)
            self._progress_window.title("⏳ 进度")
            self._progress_window.geometry("400x120")
            self._progress_window.resizable(False, False)
            self._progress_window.transient(self.root)

            frame = tk.Frame(self._progress_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            self._progress_label = tk.Label(
                frame, text="", font=("Arial", 10), wraplength=350
            )
            self._progress_label.pack(pady=10)

            self._progress_bar = ttk.Progressbar(
                frame, mode="determinate", length=350
            )
            self._progress_bar.pack(pady=10, fill=tk.X)

        # 更新进度
        percentage = int((current / total) * 100) if total > 0 else 0
        progress_text = f"{percentage}% ({current}/{total})"

        if message:
            progress_text += f" - {message}"

        self._progress_label.config(text=progress_text)
        self._progress_bar["value"] = percentage

        self._progress_window.update()

        # 完成时关闭窗口
        if current >= total:
            self._progress_window.destroy()
            self._progress_window = None

    def show_result(self, title: str, result: dict[str, Any]) -> None:
        """
        显示结构化结果。

        Args:
            title: 结果标题
            result: 结果字典
        """
        result_window = tk.Toplevel(self.root)
        result_window.title(f"📊 {title}")
        result_window.geometry("600x400")

        result_window.transient(self.root)

        # 创建滚动文本框
        text_frame = tk.Frame(result_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = scrolledtext.ScrolledText(
            text_frame,
            font=("Courier", 10),
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED,
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # 格式化结果
        formatted_result = self._format_preview_content(result)

        # 插入内容
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, formatted_result)
        text_widget.config(state=tk.DISABLED)

        # 关闭按钮
        button_frame = tk.Frame(result_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(
            button_frame,
            text="关闭",
            command=result_window.destroy,
            width=10,
            bg="#2196F3",
            fg="white",
        ).pack()

        result_window.transient(self.root)
        result_window.grab_set()

    def request_missing_info(
        self,
        prompt: str,
        missing_fields: list[str],
        suggestions: Optional[dict[str, list[str]]] = None,
    ) -> dict[str, str]:
        """
        请求缺失的信息。

        Args:
            prompt: 提示信息
            missing_fields: 缺失字段列表
            suggestions: 可选的建议字典

        Returns:
            用户输入的字段值字典
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("信息补充")
        dialog.geometry("500x400")

        dialog.transient(self.root)
        dialog.grab_set()

        # 标题
        title_label = tk.Label(
            dialog, text=prompt, font=("Arial", 11, "bold"), wraplength=450
        )
        title_label.pack(pady=10, padx=10)

        # 创建滚动框架用于字段输入
        canvas = tk.Canvas(dialog, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        entries = {}

        for field in missing_fields:
            field_frame = tk.Frame(scrollable_frame, bg="white")
            field_frame.pack(fill=tk.X, padx=10, pady=10)

            tk.Label(field_frame, text=f"{field}:", font=("Arial", 10), bg="white").pack(
                anchor=tk.W
            )

            # 如果有建议，显示下拉列表；否则显示输入框
            if suggestions and field in suggestions:
                var = tk.StringVar()
                combo = ttk.Combobox(
                    field_frame,
                    textvariable=var,
                    values=suggestions[field],
                    width=40,
                    state="readonly",
                )
                combo.pack(fill=tk.X, pady=5)
                entries[field] = var
            else:
                entry = tk.Entry(field_frame, width=40)
                entry.pack(fill=tk.X, pady=5)
                entries[field] = entry

        # 按钮框架
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        result = {}

        def on_ok():
            # 收集输入值
            for field, widget in entries.items():
                if isinstance(widget, tk.StringVar):
                    result[field] = widget.get()
                else:
                    result[field] = widget.get()

            # 验证必填字段
            empty_fields = [f for f, v in result.items() if not v]
            if empty_fields:
                messagebox.showwarning(
                    "提示", f"请填写以下字段: {', '.join(empty_fields)}", parent=dialog
                )
                return

            dialog.destroy()

        def on_cancel():
            result.clear()
            dialog.destroy()

        tk.Button(
            button_frame,
            text="确定",
            command=on_ok,
            width=10,
            bg="#4CAF50",
            fg="white",
        ).pack(side=tk.RIGHT, padx=5)
        tk.Button(
            button_frame,
            text="取消",
            command=on_cancel,
            width=10,
            bg="#f44336",
            fg="white",
        ).pack(side=tk.RIGHT, padx=5)

        dialog.wait_window()

        return result

    def cleanup(self) -> None:
        """清理GUI资源。"""
        if self._progress_window and self._progress_window.winfo_exists():
            try:
                self._progress_window.destroy()
            except tk.TclError:
                pass

        if self._is_owned_root and self.root:
            try:
                self.root.destroy()
            except tk.TclError:
                pass  # 窗口已关闭
