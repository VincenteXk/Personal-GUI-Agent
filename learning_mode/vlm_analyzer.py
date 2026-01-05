"""
VLM分析模块 - 使用GLM-4.1V-Thinking-Flash模型分析用户行为
"""
import os
import json
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from PIL import Image
import io


class VLMAnalyzer:
    """VLM分析器，用于分析截图和文本，推理用户行为链"""
    
    def __init__(self, api_key: str, model: str = "glm-4v"):
        """
        初始化VLM分析器
        
        Args:
            api_key: 智谱AI API密钥
            model: 使用的模型名称，默认为glm-4v
        """
        self.api_key = api_key
        self.model = model
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """
        将图片编码为base64格式
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64编码的图片字符串
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(image_path):
                print(f"图片文件不存在: {image_path}")
                return None
                
            # 尝试直接读取文件并编码为base64
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                
                # 如果文件太小，可能不是有效的图片
                if len(image_data) < 100:
                    print(f"图片文件太小，可能已损坏: {image_path}")
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
        
        # 准备提示词
        if prompt_template is None:
            prompt_template = """
请分析以下用户行为数据，包括截图和交互信息，推理出用户的行为链。

用户活动信息：
{user_activities}

截图信息：
{screenshots_info}

请分析并回答：
1. 用户在使用什么应用？
2. 用户的主要行为是什么？
3. 如果是购物/外卖/支付类应用，请详细说明：
   - 何时进行的操作
   - 在什么平台/商家
   - 选择了什么商品/服务
   - 支付了多少金额（如果可见）
4. 用户的行为意图可能是什么？

请以JSON格式返回你的分析结果，包含以下字段：
- app_name: 应用名称
- main_action: 主要行为
- detailed_actions: 详细行为列表
- intent: 用户意图
- confidence: 分析的置信度（0-1）
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
        
        # 格式化截图信息
        screenshots_text = ""
        screenshots = session_data.get("screenshots", [])
        for i, screenshot in enumerate(screenshots):
            timestamp = screenshot.get("timestamp", "未知时间")
            filepath = screenshot.get("filepath", "")
            screenshots_text += f"截图 {i+1}: {timestamp}\n"
            screenshots_text += f"  文件路径: {filepath}\n"
        
        # 填充提示模板
        prompt = prompt_template.format(
            user_activities=user_activities_text,
            screenshots_info=screenshots_text
        )
        
        # 准备消息内容
        content = [{"type": "text", "text": prompt}]
        
        # 添加截图（最多添加前5张，避免token过多）
        for i, screenshot in enumerate(screenshots[:5]):
            filepath = screenshot.get("filepath", "")
            # 标准化路径，处理Windows路径分隔符
            if filepath:
                filepath = os.path.normpath(filepath)
                if os.path.exists(filepath):
                    base64_image = self.encode_image_to_base64(filepath)
                    if base64_image:
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": base64_image
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
                    
                    # 尝试解析JSON格式的回答
                    try:
                        analysis_result = json.loads(content)
                    except json.JSONDecodeError:
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
    
    def analyze_latest_session(self, sessions_dir: str, output_dir: str = None) -> Dict[str, Any]:
        """
        分析最新的会话数据
        
        Args:
            sessions_dir: 会话数据目录
            output_dir: 输出目录，如果为None则使用sessions_dir下的analysis子目录
            
        Returns:
            分析结果
        """
        # 获取最新的会话文件
        session_files = [f for f in os.listdir(sessions_dir) if f.endswith("_llm.json")]
        if not session_files:
            return {"error": "没有找到会话数据文件"}
        
        # 按修改时间排序，获取最新的
        session_files.sort(key=lambda x: os.path.getmtime(os.path.join(sessions_dir, x)))
        latest_session_file = os.path.join(sessions_dir, session_files[-1])
        
        # 读取会话数据
        with open(latest_session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        
        # 分析会话数据
        analysis_result = self.analyze_session_with_screenshots(session_data)
        
        # 保存分析结果
        if output_dir is None:
            output_dir = os.path.join(sessions_dir, "analysis")
            os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名
        session_name = os.path.splitext(os.path.basename(latest_session_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"{session_name}_analysis_{timestamp}.json")
        
        # 准备保存的数据
        save_data = {
            "session_file": latest_session_file,
            "analysis_time": datetime.now().isoformat(),
            "model": self.model,
            "result": analysis_result
        }
        
        # 保存到文件
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        print(f"分析结果已保存到: {output_file}")
        
        return {
            "output_file": output_file,
            "analysis": analysis_result
        }


# 示例使用
if __name__ == "__main__":
    # 需要替换为实际的API密钥
    API_KEY = "your_api_key_here"
    
    # 创建分析器
    analyzer = VLMAnalyzer(api_key=API_KEY)
    
    # 分析最新会话
    sessions_dir = "data/processed"
    result = analyzer.analyze_latest_session(sessions_dir)
    
    if "error" in result:
        print(f"分析失败: {result['error']}")
    else:
        print(f"分析成功，结果已保存到: {result['output_file']}")
        
        # 打印分析结果
        if "analysis" in result and "analysis" in result["analysis"]:
            analysis = result["analysis"]["analysis"]
            if "app_name" in analysis:
                print(f"应用名称: {analysis['app_name']}")
            if "main_action" in analysis:
                print(f"主要行为: {analysis['main_action']}")
            if "intent" in analysis:
                print(f"用户意图: {analysis['intent']}")