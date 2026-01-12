"""ProfileInitAgent - 初始画像创建Agent。"""

import json
import re
from typing import Optional
from openai import OpenAI

from task_framework.interfaces import UserInputInterface, UserInteractionInterface, InteractionType


class ProfileInitAgent:
    """初始画像创建Agent。

    通过LLM与用户对话，创建初始用户画像：
    - 语言风格（正式/轻松/中立）
    - 常用APP（前3-5个）
    - 默认模式（快速/均衡/谨慎）
    """

    def __init__(
        self,
        user_input: UserInputInterface,
        user_interaction: UserInteractionInterface,
        model_client: OpenAI,
        model_name: str = "mimo-v2-flash",
        language: str = "zh",
    ):
        """初始化ProfileInitAgent。"""
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.model_client = model_client
        self.model_name = model_name
        self.language = language
        self.system_prompt = self._get_system_prompt()
        self.profile_data = {
            "language_style": None,
            "scene_preference": None,
            "default_mode": None,
        }

    def run(self) -> dict:
        """
        运行初始画像创建流程。

        Returns:
            用户画像字典
        """
        self.user_interaction.show_message(
            "👤 创建个人画像",
            InteractionType.INFO
        )

        conversation_history = []
        max_turns = 20

        for turn in range(max_turns):
            try:
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
                        {"role": "user", "content": f"当前已收集的画像数据: {json.dumps(self.profile_data, ensure_ascii=False)}"},
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
                    # 尝试从消息中提取JSON
                    json_match = re.search(r"```json\s*(\{.*?\})\s*```", assistant_message, re.DOTALL)
                    if not json_match:
                        json_match = re.search(r"\{.*\}", assistant_message, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(1) if json_match.lastindex == 1 else json_match.group()
                        
                        # 尝试修复常见的JSON格式错误
                        # 1. 修复缺少逗号的问题 - 在JSON对象字段之间
                        json_str = re.sub(r'"\s*\n\s*"', '",\n  "', json_str)  # 修复字段间缺少逗号
                        json_str = re.sub(r'"\s*\n\s*{', '",\n  {', json_str)  # 修复字段值与对象间缺少逗号
                        
                        # 2. 修复其他常见格式问题
                        json_str = re.sub(r'}\s*{\s*', '},{', json_str)
                        json_str = re.sub(r'}\s*"', '},"', json_str)
                        
                        # 3. 修复缺少引号的问题
                        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                        
                        try:
                            response_data = json.loads(json_str)
                        except json.JSONDecodeError as e:
                            # 如果仍然失败，尝试更激进的修复
                            try:
                                # 尝试在每个换行后的非特殊字符前添加逗号
                                lines = json_str.split('\n')
                                fixed_lines = []
                                for i, line in enumerate(lines):
                                    fixed_lines.append(line)
                                    # 如果不是最后一行，且当前行以引号或}结尾，下一行以引号或{开头
                                    if i < len(lines) - 1:
                                        current_line = line.strip()
                                        next_line = lines[i+1].strip()
                                        if (current_line.endswith('"') or current_line.endswith('}')) and \
                                           (next_line.startswith('"') or next_line.startswith('{')):
                                            # 检查当前行是否已经以逗号结尾
                                            if not current_line.endswith(','):
                                                fixed_lines[-1] = line.rstrip() + ','
                                
                                json_str = '\n'.join(fixed_lines)
                                response_data = json.loads(json_str)
                            except json.JSONDecodeError:
                                self.user_interaction.show_message(
                                    f"解析响应失败: {e}\n原始响应: {assistant_message[:200]}...",
                                    InteractionType.ERROR
                                )
                                continue
                    else:
                        # 如果没有找到JSON格式，显示原始消息
                        self.user_interaction.show_message(
                            assistant_message,
                            InteractionType.INFO
                        )
                        continue

                # 处理响应
                if response_data.get("type") == "question":
                    self._handle_question(response_data)
                elif response_data.get("type") == "update_profile":
                    self._handle_profile_update(response_data)
                    # 如果 continue_asking 为 false，表示所有信息收集完毕，结束流程
                    if not response_data.get("continue_asking", True):
                        return self.profile_data
                elif response_data.get("type") == "completed":
                    self.user_interaction.show_message(
                        "✅ 画像创建完成",
                        InteractionType.SUCCESS
                    )
                    return self.profile_data

            except Exception as e:
                self.user_interaction.show_message(
                    f"❌ 错误: {e}",
                    InteractionType.ERROR
                )
                continue

        self.user_interaction.show_message(
            "⏱️ 画像创建超时",
            InteractionType.WARNING
        )
        return self.profile_data

    def _handle_question(self, data: dict) -> None:
        """处理问题。"""
        message = data.get("message", "")
        if message:
            self.user_interaction.show_message(message, InteractionType.INFO)

    def _handle_profile_update(self, data: dict) -> None:
        """处理画像更新。"""
        field = data.get("field", "")
        value = data.get("value")
        message = data.get("message", "")

        if field in self.profile_data:
            self.profile_data[field] = value

        # 显示确认消息
        if message:
            self.user_interaction.show_message(message, InteractionType.SUCCESS)

        # 如果有下一个问题，直接显示
        next_question = data.get("next_question")
        if next_question:
            self.user_interaction.show_message(next_question, InteractionType.INFO)

    def _get_system_prompt(self) -> str:
        """获取系统提示词。"""
        if self.language == "en":
            return self._get_system_prompt_en()
        return self._get_system_prompt_zh()

    def _get_system_prompt_zh(self) -> str:
        """中文系统提示词。"""
        return """你是用户画像创建向导。你的任务是通过友好的对话，帮助用户创建初始的个人画像。

## 画像要素

1. **语言风格** (language_style)
   - 正式 (formal): 商务、工作相关
   - 轻松 (casual): 日常、随意
   - 中立 (neutral): 平衡

2. **场景偏好** (scene_preference)
   - 用户在日常选择中的倾向
   - 例如：品质 vs 性价比、价格 vs 速度等

3. **默认模式** (default_mode)
   - 快速 (fast): 快速完成，信息最少化确认
   - 均衡 (balanced): 平衡效率和安全，部分操作需确认
   - 谨慎 (careful): 详细确认，每步都需要用户确认

## 对话策略

1. 每次只问一个主题
2. 使用简洁、友好的语言
3. 提供具体例子帮助用户理解
4. 如果用户没有明确选择，给出建议
5. 适合语音对话：一次性收集一个主题的信息，减少交互次数

## 输出格式

### 询问：
```json
{
  "type": "question",
  "message": "你的问题"
}
```

### 更新画像（收集到信息后）：
```json
{
  "type": "update_profile",
  "field": "字段名",
  "value": 值,
  "message": "回复用户的消息，确认已收集的信息",
  "continue_asking": true或false（如果问题还没问完就继续问下一个，false表示所有信息都收集完了）
}
```
如果 continue_asking 为 true，还需要在同一个JSON中添加下一个问题：
```json
{
  "type": "update_profile",
  "field": "字段名",
  "value": 值,
  "message": "回复用户的消息",
  "continue_asking": true,
  "next_question": "下一个要问的问题"
}
```

### 完成：
```json
{
  "type": "completed",
  "message": "完成消息"
}
```

## 具体问题流程

按照以下顺序收集三个信息：

1. **第一个问题**：希望助手用什么样的风格讲话？
   - 可以让用户自由描述（如"幽默有趣"、"简洁专业"、"温暖友善"等）
   - 收集到后更新 language_style 字段

2. **第二个问题**：在日常选择中，你更看重什么？比如外卖你更看重品质还是性价比？打车更在意价格还是速度？
   - 这是开放问题，用来了解用户的场景偏好和决策倾向
   - 收集到后更新 scene_preference 字段

3. **第三个问题**：微信发消息前是否都默认询问你，等你确认再发？
   - "是" → 谨慎(careful)模式
   - "否" → 快速(fast)模式
   - "有时候" → 均衡(balanced)模式
   - 收集到后更新 default_mode 字段

三个问题都收集完后，LLM 会设置 `continue_asking` 为 false 来结束流程。

## 重要规则
- 理解用户的自然语言回答
- 如果用户说"随便"或"无所谓"，使用默认值
- 所有回应必须是有效的JSON格式
- 适合语音对话：尽量在一次交互中完成一个主题的收集
- 当返回 update_profile 时，必须包含 message 字段来回复用户
- 如果还有信息需要收集，设置 continue_asking 为 true，并包含 next_question 字段
- 如果所有信息都已收集完毕，设置 continue_asking 为 false（此时流程结束）
- 流程顺序：先问风格 → 再问场景偏好 → 最后问确认习惯 → 完成"""

    def _get_system_prompt_en(self) -> str:
        """English system prompt."""
        return """You are a user profile creation guide. Your task is to help users create their initial personal profile through friendly conversation.

## Profile Elements

1. **Language Style** (language_style)
   - Formal: Business, work-related
   - Casual: Daily, informal
   - Neutral: Balanced

2. **Common Apps** (common_apps)
   - Collect top 3-5 most frequently used apps
   - Example: ["WeChat", "Taobao", "Meituan"]

3. **Default Mode** (default_mode)
   - Fast: Quick completion, minimal confirmation
   - Balanced: Balance efficiency and safety, some operations need confirmation
   - Careful: Detailed confirmation, every step needs user approval

## Conversation Strategy

1. Ask one topic at a time
2. Use concise, friendly language
3. Provide concrete examples to help users understand
4. If user doesn't choose clearly, provide recommendations

## Output Format

### Ask:
```json
{
  "type": "question",
  "message": "Your question"
}
```

### Update profile:
```json
{
  "type": "update_profile",
  "field": "Field name",
  "value": Value
}
```

### Complete:
```json
{
  "type": "completed",
  "message": "Completion message"
}
```

## Important Rules
- Understand user's natural language responses
- If user says "whatever" or "doesn't matter", use default values
- For app lists, accept natural expressions like "WeChat, Alipay"
- All responses must be valid JSON format"""