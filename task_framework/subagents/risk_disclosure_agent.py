"""RiskDisclosureAgent - 能力边界和风险提示Agent。"""

import json
from typing import Optional
from openai import OpenAI

from task_framework.interfaces import UserInputInterface, UserInteractionInterface, InteractionType


class RiskDisclosureAgent:
    """风险提示Agent。

    通过LLM与用户对话，确保用户理解系统的能力边界和风险：
    - 不自动支付
    - 不自动删除
    - 不主动发送信息（任务前确认）
    """

    def __init__(
        self,
        user_input: UserInputInterface,
        user_interaction: UserInteractionInterface,
        model_client: OpenAI,
        model_name: str = "mimo-v2-flash",
        language: str = "zh",
    ):
        """初始化RiskDisclosureAgent。

        Args:
            user_input: 用户输入接口
            user_interaction: 用户交互接口
            model_client: OpenAI客户端
            model_name: 使用的模型名称
            language: 语言设置 ('zh' 或 'en')
        """
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.model_client = model_client
        self.model_name = model_name
        self.language = language
        self.system_prompt = self._get_system_prompt()

    def run(self) -> bool:
        """
        运行风险提示流程。

        通过LLM与用户进行自然语言对话，确保用户理解系统能力边界。

        Returns:
            用户是否同意继续（True = 同意，False = 拒绝）
        """
        self.user_interaction.show_message(
            "📋 系统能力边界说明",
            InteractionType.INFO
        )

        conversation_history = []
        max_turns = 10

        for turn in range(max_turns):
            try:
                # 第一轮：系统主动说明
                if turn == 0:
                    user_message = "请开始说明"
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
                        *conversation_history,
                    ],
                    model=self.model_name,
                    max_completion_tokens=512,
                    temperature=0.3,
                )

                assistant_message = response.choices[0].message.content
                conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                # 尝试解析JSON
                try:
                    response_data = json.loads(assistant_message)
                except json.JSONDecodeError:
                    # 提取JSON片段
                    import re
                    json_match = re.search(r"\{.*\}", assistant_message, re.DOTALL)
                    if json_match:
                        response_data = json.loads(json_match.group())
                    else:
                        # 如果没有JSON，直接显示文本消息
                        self.user_interaction.show_message(
                            assistant_message,
                            InteractionType.INFO
                        )
                        continue

                # 处理响应
                if response_data.get("type") == "explanation":
                    self._handle_explanation(response_data)
                elif response_data.get("type") == "confirmation_needed":
                    self._handle_confirmation_request(response_data)
                elif response_data.get("type") == "confirmed":
                    # 用户已确认理解
                    self.user_interaction.show_message(
                        "✅ 已确认，现在开始设置权限",
                        InteractionType.SUCCESS
                    )
                    return True
                elif response_data.get("type") == "rejected":
                    # 用户拒绝
                    self.user_interaction.show_message(
                        "⚠️ 已取消设置",
                        InteractionType.WARNING
                    )
                    return False

            except Exception as e:
                self.user_interaction.show_message(
                    f"❌ 错误: {e}",
                    InteractionType.ERROR
                )
                continue

        # 超时
        self.user_interaction.show_message(
            "⏱️ 说明超时，请稍后重试",
            InteractionType.WARNING
        )
        return False

    def _handle_explanation(self, data: dict) -> None:
        """处理说明文本。"""
        message = data.get("message", "")
        if message:
            self.user_interaction.show_message(
                message,
                InteractionType.INFO
            )

    def _handle_confirmation_request(self, data: dict) -> None:
        """处理确认请求。"""
        message = data.get("message", "")
        if message:
            self.user_interaction.show_message(
                message,
                InteractionType.INFO
            )

    def _get_system_prompt(self) -> str:
        """获取系统提示词。"""
        if self.language == "en":
            return self._get_system_prompt_en()
        return self._get_system_prompt_zh()

    def _get_system_prompt_zh(self) -> str:
        """中文系统提示词。"""
        return """你是个性化GUI助手的初始化向导。你的任务是通过自然语言对话，清晰说明系统的能力边界和安全保障，确保用户充分理解。

## 核心要点（必须包含）

### ✅ 系统能力
- 自动填表和输入信息
- 浏览和查询信息
- 屏幕点击和页面导航
- 语音和文本指令理解
- 自动化任务规划和执行

### ⛔ 系统限制（最重要）
- 不会未经用户确认自动支付（订单、转账、红包等）
- 不会未经用户确认自动删除文件或数据
- 不会未经用户确认发送信息（微信、邮件、短信等）
- 所有敏感操作前都会停下来请用户确认

### 🔒 数据安全
- 仅为用户本人服务，不共享数据给其他用户
- 用户画像和偏好存储在本地或用户指定位置
- 所有操作可撤销，有执行历史回放

## 对话流程

1. 第1轮（用户："请开始说明"）：你主动说明能力和限制，用友好的语气
2. 后续轮次：根据用户反馈继续解释，直到用户表示理解
3. 当用户表示理解和同意时，返回确认

## 输出格式

### 说明阶段：
```json
{
  "type": "explanation",
  "message": "你的说明文本（可以很长，包含多个段落和换行）"
}
```

### 需要确认时：
```json
{
  "type": "confirmation_needed",
  "message": "你的问题或确认请求"
}
```

### 用户已确认时：
```json
{
  "type": "confirmed",
  "message": "确认消息"
}
```

### 用户拒绝时：
```json
{
  "type": "rejected",
  "message": "拒绝原因"
}
```

## 重要规则
- 一次说明不要太长，留给用户提问的空间
- 用户表示理解后，立即确认并结束
- 检测用户的拒绝意图（比如说"我不同意"、"这太危险了"等），及时返回rejected
- 所有回应都必须是有效的JSON格式"""

    def _get_system_prompt_en(self) -> str:
        """English system prompt."""
        return """You are an initialization guide for the Personalized GUI Assistant. Your task is to clearly explain the system's capabilities and safety boundaries through natural language conversation, ensuring users fully understand.

## Core Points (Must Include)

### ✅ System Capabilities
- Auto-fill forms and input information
- Browse and query information
- Screen tapping and page navigation
- Voice and text instruction understanding
- Automated task planning and execution

### ⛔ System Limitations (Most Important)
- Will NOT auto-pay without user confirmation (orders, transfers, red envelopes, etc.)
- Will NOT auto-delete files or data without user confirmation
- Will NOT auto-send messages without user confirmation (WeChat, email, SMS, etc.)
- All sensitive operations will pause for user confirmation

### 🔒 Data Security
- Serves only the user, no data sharing with other users
- User profile and preferences stored locally or at user-specified location
- All operations can be undone with execution history replay

## Conversation Flow

1. First turn (user: "please start"): You proactively explain capabilities and limitations with a friendly tone
2. Subsequent turns: Continue explaining based on user feedback until they express understanding
3. When user agrees and understands: Return confirmation

## Output Format

### Explanation phase:
```json
{
  "type": "explanation",
  "message": "Your explanation text (can be long with multiple paragraphs)"
}
```

### When confirmation needed:
```json
{
  "type": "confirmation_needed",
  "message": "Your question or confirmation request"
}
```

### When user confirmed:
```json
{
  "type": "confirmed",
  "message": "Confirmation message"
}
```

### When user rejected:
```json
{
  "type": "rejected",
  "message": "Rejection reason"
}
```

## Important Rules
- Don't explain too much in one go, leave room for user questions
- Confirm and end immediately when user shows understanding
- Detect rejection intent (like "I disagree", "This is too risky", etc.) and return rejected promptly
- All responses must be valid JSON format"""
