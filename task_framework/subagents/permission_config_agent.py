"""PermissionConfigAgent - 权限与连接引导Agent。"""

import json
import re
from typing import Optional
from openai import OpenAI

from task_framework.interfaces import UserInputInterface, UserInteractionInterface, InteractionType


class PermissionConfigAgent:
    """权限配置Agent。

    通过LLM与用户对话，配置：
    - APP信息获取/屏幕录制（可跳过）
    - 截屏、直接操控、输入、麦克风（必须有）
    - 可选：位置信息
    """

    def __init__(
        self,
        user_input: UserInputInterface,
        user_interaction: UserInteractionInterface,
        model_client: OpenAI,
        model_name: str = "mimo-v2-flash",
        language: str = "zh",
    ):
        """初始化PermissionConfigAgent。"""
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.model_client = model_client
        self.model_name = model_name
        self.language = language
        self.system_prompt = self._get_system_prompt()
        self.collected_permissions = {}

    def run(self) -> dict:
        """
        运行权限配置流程。

        Returns:
            权限配置字典
        """
        self.user_interaction.show_message(
            "🔐 权限与连接设置",
            InteractionType.INFO
        )

        conversation_history = []
        max_turns = 20

        for turn in range(max_turns):
            try:
                # 第一轮：启动
                if turn == 0:
                    user_message = "请开始"
                else:
                    user_message = self.user_input.get_input("你的回应")

                conversation_history.append({
                    "role": "user",
                    "content": user_message
                })

                # 请求LLM
                response = self.model_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": f"当前已收集的权限配置: {json.dumps(self.collected_permissions, ensure_ascii=False)}"},
                        *conversation_history,
                    ],
                    model=self.model_name,
                    max_completion_tokens=1024,
                    temperature=0.3,
                )

                assistant_message = response.choices[0].message.content
                conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                # 解析JSON
                try:
                    response_data = json.loads(assistant_message)
                except json.JSONDecodeError:
                    json_match = re.search(r"\{.*\}", assistant_message, re.DOTALL)
                    if json_match:
                        response_data = json.loads(json_match.group())
                    else:
                        self.user_interaction.show_message(
                            assistant_message,
                            InteractionType.INFO
                        )
                        continue

                # 处理响应
                if response_data.get("type") == "question":
                    self._handle_question(response_data)
                elif response_data.get("type") == "update_permission":
                    self._handle_permission_update(response_data)
                elif response_data.get("type") == "completed":
                    self.user_interaction.show_message(
                        "✅ 权限配置完成",
                        InteractionType.SUCCESS
                    )
                    return self.collected_permissions

            except Exception as e:
                self.user_interaction.show_message(
                    f"❌ 错误: {e}",
                    InteractionType.ERROR
                )
                continue

        self.user_interaction.show_message(
            "⏱️ 配置超时",
            InteractionType.WARNING
        )
        return self.collected_permissions

    def _handle_question(self, data: dict) -> None:
        """处理问题。"""
        message = data.get("message", "")
        if message:
            self.user_interaction.show_message(message, InteractionType.INFO)

    def _handle_permission_update(self, data: dict) -> None:
        """处理权限更新。"""
        permission_name = data.get("permission_name", "")
        value = data.get("value", "")

        if permission_name and value is not None:
            self.collected_permissions[permission_name] = value
            self.user_interaction.show_message(
                f"✓ {permission_name}: {value}",
                InteractionType.SUCCESS
            )

    def _get_system_prompt(self) -> str:
        """获取系统提示词。"""
        if self.language == "en":
            return self._get_system_prompt_en()
        return self._get_system_prompt_zh()

    def _get_system_prompt_zh(self) -> str:
        """中文系统提示词。"""
        return """你是权限配置向导。你的任务是通过友好的对话，引导用户配置系统所需的各项权限。

## 必须配置的权限

1. **截屏权限** (screenshot): 必须有
2. **直接操控权限** (direct_control): 必须有，允许系统点击屏幕和执行操作
3. **输入权限** (input): 必须有，允许系统输入文字
4. **麦克风权限** (microphone): 必须有，用于语音指令

## 可选权限

1. **APP信息获取** (app_info): 可选，允许系统获取已安装APP列表
2. **屏幕录制** (screen_recording): 可选，用于记录执行过程
3. **位置信息** (location): 可选，默认同意或每次使用时选择

## 对话策略

1. 每次只问一个权限
2. 先问必须权限，再问可选权限
3. 使用友好的语言解释为什么需要这个权限
4. 记录用户的选择

## 输出格式

### 询问权限：
```json
{
  "type": "question",
  "message": "你的问题或说明"
}
```

### 更新权限：
```json
{
  "type": "update_permission",
  "permission_name": "权限名称",
  "value": true 或 false 或 "select_each_time"
}
```

### 完成配置：
```json
{
  "type": "completed",
  "message": "配置完成"
}
```

## 重要规则
- 检测用户的明确同意和拒绝
- 必须权限不能拒绝，可以重新询问或提示其重要性
- 用户拒绝可选权限后，直接跳过
- 所有回应必须是有效的JSON格式"""

    def _get_system_prompt_en(self) -> str:
        """English system prompt."""
        return """You are a permission configuration guide. Your task is to guide users through configuring system permissions with friendly conversation.

## Required Permissions

1. **Screenshot** (screenshot): Required
2. **Direct Control** (direct_control): Required, allows system to tap and execute operations
3. **Input** (input): Required, allows system to type text
4. **Microphone** (microphone): Required, for voice commands

## Optional Permissions

1. **App Info** (app_info): Optional, allows system to get installed app list
2. **Screen Recording** (screen_recording): Optional, for recording execution process
3. **Location** (location): Optional, default agree or select each time

## Conversation Strategy

1. Ask one permission at a time
2. Ask required permissions first, then optional ones
3. Use friendly language to explain why each permission is needed
4. Record user choices

## Output Format

### Ask permission:
```json
{
  "type": "question",
  "message": "Your question or explanation"
}
```

### Update permission:
```json
{
  "type": "update_permission",
  "permission_name": "Permission name",
  "value": true or false or "select_each_time"
}
```

### Complete configuration:
```json
{
  "type": "completed",
  "message": "Configuration complete"
}
```

## Important Rules
- Detect clear user agreement and rejection
- Required permissions cannot be rejected, can re-ask or highlight importance
- Skip optional permissions if user rejects them
- All responses must be valid JSON format"""
