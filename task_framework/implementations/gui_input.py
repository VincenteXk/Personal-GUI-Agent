"""图形界面用户输入实现。"""

import tkinter as tk
from tkinter import simpledialog, messagebox
from typing import Optional
from ..interfaces import UserInputInterface

class GUIUserInput(UserInputInterface):
    """基于tkinter的图形界面用户输入实现。"""

    def __init__(self, root: Optional[tk.Tk] = None):
        """
        初始化GUI输入实现。

        Args:
            root: tkinter根窗口。如果为None，会自动创建一个隐藏窗口。
        """
        self.root = root or self._create_hidden_root()
        self._is_owned_root = root is None

    @staticmethod
    def _create_hidden_root() -> tk.Tk:
        """创建一个隐藏的根窗口用于对话框。"""
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        return root

    def get_input(self, prompt: Optional[str] = None) -> str:
        """
        通过GUI对话框获取用户输入。

        Args:
            prompt: 可选的提示信息

        Returns:
            用户输入的字符串；如果用户取消则返回空字符串
        """
        display_prompt = prompt or "请输入:"

        # 使用simpledialog获取用户输入
        result = simpledialog.askstring(
            "输入对话框",
            display_prompt,
            parent=self.root,
        )

        # 如果用户点击取消，返回空字符串
        return result if result is not None else ""

    def get_voice_input(self) -> Optional[str]:
        """
        获取语音输入（当前不支持）。

        Returns:
            None（不支持语音输入）
        """
        messagebox.showwarning("提示", "语音输入当前不支持")
        return None

    def is_voice_available(self) -> bool:
        """
        检查语音输入是否可用。

        Returns:
            False（当前不支持语音输入）
        """
        return False

    def cleanup(self) -> None:
        """清理GUI资源。"""
        if self._is_owned_root and self.root:
            try:
                self.root.destroy()
            except tk.TclError:
                pass  # 窗口已关闭
