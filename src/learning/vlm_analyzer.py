"""
VLM分析模块 - 使用GLM-4.1V-Thinking-Flash模型分析用户行为
"""
import os
import json
import re
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
from string import Template
import requests
from PIL import Image
import io
from .utils import extract_json_from_llm_response


class VLMAnalyzer:
    """VLM分析器，用于分析截图和文本，推理用户行为链"""

    def __init__(self, api_key: str, model: str = "glm-4v", api_url: str = None):
        """
        初始化VLM分析器

        Args:
            api_key: 智谱AI API密钥
            model: 使用的模型名称，默认为glm-4v
            api_url: API端点URL，如果为None则使用默认智谱AI端点
        """
        self.api_key = api_key
        self.model = model
        self.api_url = api_url or "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _safe_format_template(self, template: str, **kwargs) -> str:
        # 使用正则表达式只替换明确的占位符
        result = template
        for key, value in kwargs.items():
            # 只替换 {key} 这样的占位符，不要贪心匹配
            result = re.sub(
                r'\{' + re.escape(key) + r'\}',
                str(value).replace('\\', '\\\\'),  # 转义反斜杠
                result
            )
        return result

    def encode_image_to_base64(self, image_path: str, base_dir: str = None) -> str:
        """
        将图片编码为base64格式

        Args:
            image_path: 图片文件路径（可以是绝对路径或相对于base_dir的相对路径）
            base_dir: 基础目录，用于解析相对路径（适用于新的会话结构）

        Returns:
            base64编码的图片字符串
        """
        try:
            # 处理相对路径
            actual_path = image_path
            if base_dir and not os.path.isabs(image_path):
                actual_path = os.path.join(base_dir, image_path)

            # 检查文件是否存在
            if not os.path.exists(actual_path):
                print(f"图片文件不存在: {actual_path}")
                return None

            # 尝试直接读取文件并编码为base64
            with open(actual_path, "rb") as image_file:
                image_data = image_file.read()

                # 如果文件太小，可能不是有效的图片
                if len(image_data) < 100:
                    print(f"图片文件太小，可能已损坏: {actual_path}")
                    return None

                # 尝试使用PIL验证图片
                try:
                    with Image.open(io.BytesIO(image_data)) as img:
                        # 如果图片过大，进行压缩
                        if len(image_data) > 5 * 1024 * 1024:  # 5MB
                            img.thumbnail((2048, 2048), Image.LANCZOS)

                            # 保存到内存
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='JPEG', quality=85)
                            img_byte_arr = img_byte_arr.getvalue()
                            return base64.b64encode(img_byte_arr).decode('utf-8')
                        else:
                            # 直接编码原始数据
                            return base64.b64encode(image_data).decode('utf-8')
                except Exception as img_error:
                    print(f"PIL无法处理图片，但尝试直接编码: {img_error}")
                    # 即使PIL无法处理，也尝试直接编码
                    return base64.b64encode(image_data).decode('utf-8')

        except Exception as e:
            print(f"图片编码失败: {e}")
            return None

    def get_app_specific_prompt(self, app_package: str) -> str:
        """
        根据应用类型返回定制化prompt模板（包含占位符）

        注意: JSON示例中的{{}}需要双重转义为{{{{}}}}：
        - 第一次format(app_name)后变为{{}}
        - 第二次format(user_activities, screenshots_info)后变为{}

        Returns:
            包含{user_activities}和{screenshots_info}占位符的prompt模板
        """
        base_template = """你是一个Android应用行为分析专家。请分析用户在{app_name}中的操作序列。

用户活动信息：
{user_activities}

截图信息：
{screenshots_info}

请提取标准化的action chain，使用以下action类型：
- search: 搜索内容
- browse: 浏览/滚动
- click: 点击操作
- input: 输入文本
- view_detail: 查看详情
- add_to_cart: 加入购物车
- order: 下单
- pay: 支付
- share: 分享
- other: 其他操作

输出JSON格式：
{{{{
  "actions": [
    {{"type": "...", "target": "具体对象", "timestamp_offset": 秒数, "details": "..."}},
    ...
  ],
  "summary": "一句话总结用户意图"
}}}}

优化提示（P1改进）：
- 活动停留时长：已在括号中标注，用于判断用户关注度
- UI坐标信息：已在交互中提供，可定位屏幕位置
- 合并输入：连续输入已合并为单个序列，保留最终文本"""

        # 应用特定增强
        if "chrome" in app_package.lower() or "browser" in app_package.lower():
            enhanced = base_template + "\n\n重点关注：搜索关键词、访问的URL、停留时长、页面切换"
        elif "taobao" in app_package.lower() or "jd" in app_package.lower() or "amazon" in app_package.lower():
            enhanced = base_template + "\n\n重点关注：浏览的商品名称、价格、是否加购/支付、商品名称"
        elif "wechat" in app_package.lower() or "qq" in app_package.lower():
            enhanced = base_template + "\n\n重点关注：发送消息的文本内容、互动的联系人或群组名称、分享的内容"
        elif "meituan" in app_package.lower() or "eleme" in app_package.lower():
            enhanced = base_template + "\n\n重点关注：最后下单商品的准确名称、搜索的餐厅名称、浏览的菜品名称、价格、下单操作"
        else:
            enhanced = base_template

        # 第一次format: 填充app_name，{{{{ 变为 {{
        return enhanced.format(app_name=self._get_app_display_name(app_package))

    def _get_app_display_name(self, app_package: str) -> str:
        """
        从包名获取应用显示名称

        Args:
            app_package: 应用包名，如com.sankuai.meituan

        Returns:
            应用显示名称，如"美团"
        """
        from src.shared.config import get_app_name_from_package

        app_name = get_app_name_from_package(app_package)
        return app_name if app_name else "应用"

    def analyze_session_with_screenshots(self, session_data: Dict[str, Any], prompt_template: str = None) -> Dict[str, Any]:
        """
        分析会话数据中的截图和文本，推理用户行为链

        Args:
            session_data: 会话数据，包含截图和交互信息
            prompt_template: 自定义提示模板，如果为None则使用默认模板

        Returns:
            包含行为链分析结果的字典
        """
        if not session_data or "screenshots" not in session_data:
            return {"error": "会话数据或截图信息缺失"}

        # ===== P0 修复：添加数据质量验证 =====
        # 检查user_activities数据
        user_activities = session_data.get("user_activities", [])
        has_meaningful_activities = False
        total_interactions = 0

        for app in user_activities:
            activities = app.get("activities", [])
            if activities:
                has_meaningful_activities = True
                for activity in activities:
                    interactions = activity.get("interactions", [])
                    total_interactions += len(interactions)

        # 检查截图数据
        screenshots = session_data.get("screenshots", [])
        has_screenshots = len(screenshots) > 0

        # 如果数据为空或非常稀疏，返回警告而非虚假分析
        if not has_meaningful_activities and not has_screenshots:
            return {
                "error": "数据质量过低：没有有意义的用户活动和截图信息",
                "warning": "无法进行可靠的行为分析，请检查数据采集和处理过程",
                "data_summary": {
                    "app_count": len(user_activities),
                    "activities_count": sum(len(app.get("activities", [])) for app in user_activities),
                    "interactions_count": total_interactions,
                    "screenshots_count": len(screenshots)
                }
            }

        # 记录数据质量信息（用于调试）
        print(f"数据质量检查：")
        print(f"  应用数量: {len(user_activities)}")
        print(f"  活动数量: {sum(len(app.get('activities', [])) for app in user_activities)}")
        print(f"  交互数量: {total_interactions}")
        print(f"  截图数量: {len(screenshots)}")
        print(f"  是否有意义的活动: {has_meaningful_activities}")
        print(f"  是否有截图: {has_screenshots}")
        
        # 准备提示词
        if prompt_template is None:
            prompt_template = """
请仔细分析以下用户行为数据和截图，推理用户的行为过程。

用户活动信息：
{user_activities}

用户输入的文本内容：
{text_inputs}

请基于截图内容、交互日志和用户输入的文本，详细分析用户行为。特别注意：
- 聊天类应用：提取聊天对象名称、群名、发送的具体消息内容（包括用户输入的文本）
- 购物类应用：提取商品名称、价格、下单金额、搜索内容
- 浏览类应用：提取访问内容、搜索内容和操作流程

请严格按照以下JSON格式返回结果（确保输出是有效JSON）：

{
  "app_name": "应用名称",
  "main_action": "主要行为总结",
  "detailed_actions": [
    {
      "time": "时间戳",
      "action": "具体行为描述，包含所有可见的文本和细节（如有的话）"
    }
  ],
  "chat_details": "如是聊天应用，描述：和谁聊天（名称/群名）、发了什么消息、使用的输入法等。如非聊天应用，写null",
  "shopping_details": "如是购物应用，描述：浏览/购买了什么商品（名称、价格）、下单金额、支付方式等。如非购物应用，写null",
  "intent": "用户的最终目的和意图",
  "confidence": 0.9,
  "key_observations": "其他关键发现和观察（如输入内容、涉及的联系人/商家等）"
}

重要：必须返回有效的JSON，chat_details和shopping_details如果不适用请直接写null。
"""
        
        # 格式化用户活动信息
        user_activities_text = ""
        if "user_activities" in session_data:
            for app in session_data["user_activities"]:
                app_name = app.get("app_name", "未知应用")
                activities = app.get("activities", [])
                user_activities_text += f"应用: {app_name}\n"

                for activity in activities:
                    activity_name = activity.get("activity_name", "未知活动")
                    start_time = activity.get("start_time", "未知时间")
                    interactions = activity.get("interactions", [])

                    user_activities_text += f"  活动: {activity_name}\n"
                    user_activities_text += f"  开始时间: {start_time}\n"
                    user_activities_text += f"  交互次数: {len(interactions)}\n"

        # 格式化用户输入的文本内容
        text_inputs_text = ""
        text_inputs = session_data.get("text_inputs", [])
        if text_inputs:
            for i, text_input in enumerate(text_inputs):
                content = text_input.get("content", "")
                app_package = text_input.get("app_package", "")
                timestamp = text_input.get("timestamp", "未知时间")
                text_inputs_text += f"输入 {i+1}: \"{content}\" (应用: {app_package}, 时间: {timestamp})\n"
        else:
            text_inputs_text = "无文本输入\n"

        prompt = self._safe_format_template(
            prompt_template,
            user_activities=user_activities_text,
            text_inputs=text_inputs_text,
        )

        # 准备消息内容
        content = [{"type": "text", "text": prompt}]

        # 获取会话的基础目录（用于解析相对路径）
        # 尝试从session_data中推断会话目录
        session_base_dir = None
        if "session_id" in session_data:
            # 新格式：从session_id推断会话目录
            session_id = session_data["session_id"]
            session_base_dir = os.path.join("data", "sessions", session_id)
            #session_base_dir = os.path.join('data','eval','profile3', session_id)

        # 添加截图（均匀添加前5张，避免token过多）
        for i, screenshot in enumerate(screenshots[::len(screenshots)//5]):
            filepath = screenshot.get("filepath", "")
            # 标准化路径，处理Windows路径分隔符
            if filepath:
                filepath = os.path.normpath(filepath)

                # 如果是绝对路径，直接使用；如果是相对路径且有session_base_dir，则相对解析
                if os.path.isabs(filepath):
                    full_path = filepath
                elif session_base_dir:
                    full_path = os.path.join(session_base_dir, filepath)
                else:
                    full_path = filepath

                if os.path.exists(full_path):
                    base64_image = self.encode_image_to_base64(full_path)
                    if base64_image:
                        # 根据文件扩展名判断MIME类型
                        ext = os.path.splitext(full_path)[1].lower()
                        mime_type = "image/png" if ext == ".png" else "image/jpeg"

                        # 构建proper data URL
                        data_url = f"data:{mime_type};base64,{base64_image}"
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        })
        
        # 构建请求
        request_data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }
        
        try:
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=request_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 提取模型回答
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0].get("message", {})
                    content = message.get("content", "")
                    reasoning_content = message.get("reasoning_content", "")
                    
                    # 尝试解析JSON格式的回答（使用改进的解析器）
                    try:
                        analysis_result = extract_json_from_llm_response(content)
                    except ValueError:
                        # 如果解析失败，返回原始文本
                        analysis_result = {
                            "raw_response": content,
                            "reasoning": reasoning_content,
                            "error": "无法解析JSON格式的回答"
                        }
                    
                    return {
                        "success": True,
                        "analysis": analysis_result,
                        "reasoning": reasoning_content,
                        "usage": result.get("usage", {}),
                        "model": result.get("model", self.model)
                    }
                else:
                    return {"error": "API响应格式异常", "response": result}
            else:
                return {
                    "error": f"API请求失败，状态码: {response.status_code}",
                    "response": response.text
                }
                
        except Exception as e:
            return {"error": f"请求异常: {str(e)}"}