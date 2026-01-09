from nicegui import ui
import asyncio
from typing import Optional

from ..interfaces import UserInputInterface

class WebUserInput(UserInputInterface):
    """
    UserInputInterface 的 Web 端实现。
    """

    async def get_input(self, prompt: Optional[str] = None) -> str:
        """
        弹出一个包含输入框的对话框。
        """
        result = asyncio.Future()
        
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-sm'):
            if prompt:
                ui.label(prompt).classes('text-lg font-medium q-mb-sm')
            
            # 输入框，绑定回车键提交
            inp = ui.input(placeholder='请输入...').classes('w-full').props('autofocus')
            inp.on('keydown.enter', lambda: dialog.submit(inp.value))
            
            with ui.row().classes('w-full justify-end q-mt-md'):
                # 只有点击确定才返回文本，取消或者点遮罩层返回 None (处理为空串)
                ui.button('确定', on_click=lambda: dialog.submit(inp.value))
        
        dialog.open()
        val = await dialog
        return val if val else ""

    async def get_voice_input(self) -> Optional[str]:
        """
        Web 端语音输入模拟。
        """
        ui.notify("🎙️ 请开始说话... (模拟)", type="info", icon="mic")
        await asyncio.sleep(2) # 模拟录音
        return "这是模拟的语音输入内容"

    def is_voice_available(self) -> bool:
        return True