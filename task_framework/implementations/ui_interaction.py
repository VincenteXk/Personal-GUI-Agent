from nicegui import ui
import json
from typing import Any, Optional, Dict, List
import asyncio

from ..interfaces import (
    UserInteractionInterface,
    InteractionType,
    Choice,
)


class WebUserInteraction(UserInteractionInterface):
    """
    UserInteractionInterface 的 Web 端完整实现 (基于 NiceGUI)。
    """

    def __init__(self):
        # 1. 定义完整的样式映射
        self.TYPE_MAPPING = {
            InteractionType.INFO:         {"color": "info",     "icon": "info",           "title": "提示"},
            InteractionType.WARNING:      {"color": "warning",  "icon": "warning",        "title": "警告"},
            InteractionType.ERROR:        {"color": "negative", "icon": "error",          "title": "错误"},
            InteractionType.SUCCESS:      {"color": "positive", "icon": "check_circle",   "title": "成功"},
            InteractionType.QUESTION:     {"color": "primary",  "icon": "help",           "title": "询问"},
            InteractionType.CHOICE:       {"color": "primary",  "icon": "list",           "title": "选择"},
            InteractionType.CONFIRMATION: {"color": "warning",  "icon": "help_outline",   "title": "确认"},
            InteractionType.PREVIEW:      {"color": "accent",   "icon": "preview",        "title": "预览"},
            InteractionType.PROGRESS:     {"color": "primary",  "icon": "hourglass_top",  "title": "进度"},
        }
        
        # 用于跟踪进度条对话框的实例，防止重复弹出
        self._progress_dialog = None
        self._progress_bar = None
        self._progress_label = None

    async def show_message(
        self, message: str, interaction_type: InteractionType = InteractionType.INFO
    ) -> None:
        """根据类型显示不同颜色的 Toast 通知。"""
        style = self.TYPE_MAPPING.get(interaction_type, self.TYPE_MAPPING[InteractionType.INFO])
        
        ui.notify(
            message,
            type=style["color"],
            icon=style["icon"],
            position="top-right",
            close_button=True,
            timeout=5000 if interaction_type in [InteractionType.ERROR, InteractionType.WARNING] else 3000
        )
        # 极短的延迟确保 UI 渲染刷新
        await asyncio.sleep(0.1)

    async def get_choice(
        self,
        prompt: str,
        choices: List[Choice],
        allow_custom: bool = False,
    ) -> str:
        """
        显示单选模态框。
        """
        result = asyncio.Future()
        
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-md'):
            ui.label(prompt).classes('text-h6 q-mb-md')
            
            # 构建选项映射 {ID: Label (Description)}
            options_map = {}
            for c in choices:
                desc = f" - {c.description}" if c.description else ""
                options_map[c.id] = f"{c.label}{desc}"
            
            # 默认选中第一个
            selected_value = choices[0].id if choices else None
            
            # 单选组件
            radio = ui.radio(options_map, value=selected_value).props('dense').classes('q-mb-md')
            
            # 自定义输入部分
            custom_input = ui.input(label="请输入自定义值").classes('w-full hidden')
            
            if allow_custom:
                def toggle_custom(e):
                    if e.value:
                        custom_input.classes(remove='hidden')
                        radio.disable()
                    else:
                        custom_input.classes(add='hidden')
                        radio.enable()
                
                ui.checkbox("手动输入", on_change=toggle_custom).classes('q-mb-sm')

            with ui.row().classes('w-full justify-end q-mt-md'):
                def on_confirm():
                    # 判断是取 input 的值还是 radio 的值
                    is_custom_mode = not "hidden" in custom_input.classes
                    final_value = custom_input.value if is_custom_mode else radio.value
                    
                    if not final_value:
                        ui.notify("请提供有效的选项", type="warning")
                        return
                    dialog.submit(final_value)

                ui.button('确定', on_click=on_confirm)

        dialog.open()
        return await dialog

    async def get_confirmation(
        self, prompt: str, default: bool = False, risk_warning: Optional[str] = None
    ) -> bool:
        """
        显示确认对话框，支持风险警告高亮。
        """
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-sm'):
            # 风险警告区域
            if risk_warning:
                with ui.row().classes('items-center text-negative q-mb-md bg-red-100 p-2 rounded'):
                    ui.icon('warning', size='md').classes('q-mr-sm')
                    ui.label(risk_warning).classes('font-bold')

            ui.label(prompt).classes('text-lg font-medium q-mb-lg')

            with ui.row().classes('w-full justify-end'):
                # 根据 default 值决定哪个按钮是主要样式
                cancel_props = 'outline' if default else ''
                confirm_props = '' if default else 'outline'
                
                ui.button('否', on_click=lambda: dialog.submit(False)).props(cancel_props).classes('q-mr-sm')
                ui.button('是', on_click=lambda: dialog.submit(True)).props(confirm_props)

        dialog.open()
        return await dialog

    async def show_preview(self, title: str, content: Dict[str, Any]) -> None:
        """
        使用 JSON 编辑器组件显示只读预览。
        """
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-3xl h-3/4'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(title).classes('text-h5')
                ui.icon('preview', size='sm').classes('text-grey')
            
            ui.separator().classes('q-my-md')
            
            # 使用 JSONEditor 展示结构化数据，设置为只读模式
            # content 需要包装在 dict 中以符合某些 editor 的预期，或者直接传
            ui.json_editor({'content': {'json': content}}, ).classes('h-full w-full')
            
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('关闭预览', on_click=dialog.submit).props('flat')
                
        dialog.open()
        await dialog

    async def show_progress(
        self, current: int, total: int, message: Optional[str] = None
    ) -> None:
        """
        显示或更新进度条。
        逻辑：如果是第一次调用，创建弹窗；后续调用更新数值；完成后自动关闭。
        """
        percentage = current / total if total > 0 else 0
        
        # 1. 如果对话框不存在，初始化它
        if not self._progress_dialog:
            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label('正在处理...').classes('text-h6 q-mb-sm')
                self._progress_label = ui.label(message or '').classes('text-grey-7 q-mb-sm text-sm')
                self._progress_bar = ui.linear_progress(value=0).props('show-value size="25px"')
            self._progress_dialog = dialog
            self._progress_dialog.open()
        
        # 2. 更新数值和文字
        if self._progress_bar:
            self._progress_bar.value = percentage
        if self._progress_label and message:
            self._progress_label.set_text(message)
            
        # 3. 如果完成，关闭并清理
        if current >= total:
            await asyncio.sleep(0.5) # 给用户一点时间看到 100%
            if self._progress_dialog:
                self._progress_dialog.close()
            self._progress_dialog = None
            self._progress_bar = None
        else:
            # 强制 UI 刷新
            await asyncio.sleep(0)

    async def show_result(self, title: str, result: Dict[str, Any]) -> None:
        """复用预览逻辑展示结果，但标题样式略有不同。"""
        await self.show_preview(f"📊 {title}", result)

    async def request_missing_info(
        self,
        prompt: str,
        missing_fields: List[str],
        suggestions: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, str]:
        """
        动态生成表单，要求用户补全缺失字段。
        """
        result_future = asyncio.Future()
        form_values = {}  # 存储控件对象

        with ui.dialog() as dialog, ui.card().classes('w-full max-w-md'):
            ui.label(prompt).classes('text-h6 q-mb-md text-primary')
            ui.label('请完善以下信息以继续：').classes('text-caption q-mb-md')

            # 动态生成输入控件
            for field in missing_fields:
                field_suggestions = suggestions.get(field) if suggestions else None
                
                if field_suggestions:
                    # 如果有建议值，使用下拉框 (允许输入新值)
                    control = ui.select(
                        options=field_suggestions, 
                        label=field, 
                        with_input=True,
                        new_value_mode='add-unique'
                    ).classes('w-full q-mb-sm')
                else:
                    # 否则使用普通文本框
                    control = ui.input(label=field).classes('w-full q-mb-sm')
                
                form_values[field] = control

            def submit_form():
                # 收集所有控件的值
                final_data = {}
                is_valid = True
                for f_name, f_control in form_values.items():
                    val = f_control.value
                    if not val:
                        f_control.props('error error-message="必填项"')
                        is_valid = False
                    else:
                        f_control.props(remove='error')
                        final_data[f_name] = val
                
                if is_valid:
                    dialog.submit(final_data)

            with ui.row().classes('w-full justify-end q-mt-lg'):
                ui.button('提交信息', on_click=submit_form)