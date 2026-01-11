import json
import re
import subprocess
import time
import os
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Tuple, Optional, Any
import shutil

from src.shared.config import APP_PACKAGE_MAPPINGS

# 全局变量用于学习模式
learning_active = False
learning_thread = None


class ScreenshotCollector:
    """截图收集器，负责在特定事件触发时捕获屏幕截图"""

    def __init__(self, output_dir: str = "data/screenshots", session_id: str = None):
        """
        Args:
            output_dir: 输出目录，可以是 'data/screenshots' (旧格式) 或 'data/sessions/<session_id>/screenshots' (新格式)
            session_id: 会话ID，如果提供则使用新的会话结构
        """
        self.output_dir = output_dir
        self.session_id = session_id
        self.session_start_time = None  # 用于计算相对时间
        self.ensure_output_dir()
        self.stop_event = threading.Event()
        self.screenshot_thread = None
        self.last_screenshot_time = 0
        self.last_interaction_time = 0
        self.screenshot_interval = 30  # 默认30秒无交互时截图
        self.min_screenshot_interval = 2  # 最小截图间隔2秒，避免频繁截图
        
    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def take_screenshot(self, trigger_type="event", timestamp=None):
        """捕获屏幕截图

        Args:
            trigger_type: 触发类型，"event"表示事件触发，"timer"表示定时触发
            timestamp: 时间戳，如果为None则使用当前时间

        Returns:
            截图文件路径（相对于output_dir的相对路径或绝对路径）
        """
        if timestamp is None:
            timestamp = datetime.now()

        # 初始化会话开始时间（用于计算相对时间）
        if self.session_start_time is None and isinstance(timestamp, datetime):
            self.session_start_time = timestamp

        # 检查最小截图间隔
        current_time = time.time()
        if current_time - self.last_screenshot_time < self.min_screenshot_interval:
            return None  # 跳过截图，防止过于频繁

        # 生成截图文件名
        if self.session_id:
            # 新格式：使用相对时间 HHmmSS_mmm.png
            if isinstance(timestamp, datetime):
                time_offset = (timestamp - self.session_start_time).total_seconds()
                offset_hours = int(time_offset // 3600)
                offset_minutes = int((time_offset % 3600) // 60)
                offset_seconds = int(time_offset % 60)
                offset_millis = int((time_offset % 1) * 1000)
                filename = f"{offset_hours:02d}{offset_minutes:02d}{offset_seconds:02d}_{offset_millis:03d}.png"
            else:
                # 如果是字符串时间戳，转换并计算
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if self.session_start_time is None:
                    self.session_start_time = dt
                time_offset = (dt - self.session_start_time).total_seconds()
                offset_hours = int(time_offset // 3600)
                offset_minutes = int((time_offset % 3600) // 60)
                offset_seconds = int(time_offset % 60)
                offset_millis = int((time_offset % 1) * 1000)
                filename = f"{offset_hours:02d}{offset_minutes:02d}{offset_seconds:02d}_{offset_millis:03d}.png"
            full_path = os.path.join(self.output_dir, filename)
        else:
            # 旧格式：使用绝对时间戳 YYYYMMDD_HHMMSS_mmm.png
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            filename = f"screenshot_{dt.strftime('%Y%m%d_%H%M%S_%f')[:-3]}.png"
            full_path = os.path.join(self.output_dir, filename)

        try:
            # 使用adb pull方式截图，避免Windows系统下PNG文件头损坏问题
            # 首先在设备上截图
            device_screenshot_path = "/sdcard/screenshot_temp.png"
            cmd_capture = ['adb', 'shell', 'screencap', '-p', device_screenshot_path]
            subprocess.run(cmd_capture, capture_output=True, check=True)

            # 然后从设备拉取截图到本地
            cmd_pull = ['adb', 'pull', device_screenshot_path, full_path]
            subprocess.run(cmd_pull, capture_output=True, check=True)

            # 删除设备上的临时截图文件
            cmd_remove = ['adb', 'shell', 'rm', device_screenshot_path]
            subprocess.run(cmd_remove, capture_output=True, check=True)

            self.last_screenshot_time = current_time
            # 返回相对于output_dir的相对文件名（用于新格式）或绝对路径（用于旧格式）
            return filename if self.session_id else full_path
        except subprocess.CalledProcessError as e:
            print(f"截图失败: {e}")
            return None
    
    def start_monitoring(self, duration_seconds: int = 60):
        """启动截图监控线程
        
        Args:
            duration_seconds: 监控持续时间（秒）
        """
        # 确保之前的线程已经结束
        if self.screenshot_thread and self.screenshot_thread.is_alive():
            self.stop_monitoring()
        
        self.stop_event.clear()
        self.last_interaction_time = time.time()
        
        def monitor():
            start_time = time.time()
            while not self.stop_event.is_set() and (time.time() - start_time) < duration_seconds:
                current_time = time.time()
                
                # 如果超过30秒没有交互，则触发截图
                if current_time - self.last_interaction_time >= self.screenshot_interval:
                    self.take_screenshot(trigger_type="timer")
                
                # 每5秒检查一次
                time.sleep(5)
        
        # 每次都创建新的线程对象
        self.screenshot_thread = threading.Thread(target=monitor)
        self.screenshot_thread.start()
        return self.screenshot_thread
    
    def stop_monitoring(self):
        """停止截图监控"""
        self.stop_event.set()
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=5)
        self.screenshot_thread = None
    
    def trigger_screenshot(self, event_type="ui_event"):
        """由事件触发截图
        
        Args:
            event_type: 触发截图的事件类型
        """
        current_time = time.time()
        self.last_interaction_time = current_time
        
        # 只对特定类型的事件触发截图
        if event_type in ["click", "text_input", "swipe"]:
            self.take_screenshot(trigger_type="event")


class DataCollector:
    """数据收集器，负责从三个adb命令收集原始数据"""

    def __init__(self, output_dir: str = "data/raw", session_id: str = None):
        """
        Args:
            output_dir: 输出目录，可以是 'data/raw' (旧格式) 或 'data/sessions/<session_id>/raw' (新格式)
            session_id: 会话ID，用于标识会话特定的输出
        """
        self.output_dir = output_dir
        self.session_id = session_id
        self.ensure_output_dir()
        self.stop_event = threading.Event()
        self.threads = []
        self.screenshot_collector = ScreenshotCollector(
            os.path.join(os.path.dirname(output_dir), "screenshots") if session_id else "data/screenshots",
            session_id=session_id
        )  # 添加截图收集器
        
    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def collect_logcat(self, duration_seconds: int = 60):
        """收集logcat数据"""
        # 新格式使用简单的 logcat.log，旧格式保留时间戳
        if self.session_id:
            filename = os.path.join(self.output_dir, "logcat.log")
        else:
            filename = os.path.join(self.output_dir, f"logcat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        with open(filename, 'w', encoding='utf-8') as f:
            # Windows下使用PowerShell命令
            cmd = ['adb', 'shell', 'logcat', '-v', 'time']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

            start_time = time.time()
            while not self.stop_event.is_set() and (time.time() - start_time) < duration_seconds:
                line = process.stdout.readline()
                if line:
                    f.write(line)
                else:
                    time.sleep(0.1)

            process.terminate()
            return filename
    
    def _extract_event_type_from_line(self, line: str) -> str:
        """从UIAutomator事件行提取事件类型

        Args:
            line: UIAutomator事件行

        Returns:
            事件类型字符串，如 'click', 'swipe', 'text_input' 等
        """
        try:
            # 查找 EventType: 字段
            event_type_match = re.search(r'EventType: (\w+)', line)
            if not event_type_match:
                return None

            event_type = event_type_match.group(1)

            # 将UIAutomator事件类型映射到我们的事件类型
            if "CLICKED" in event_type or "CLICK" in event_type or "VIEW_CLICKED" in event_type:
                return "click"
            elif "TEXT_CHANGED" in event_type or "TEXT" in event_type or "VIEW_TEXT_CHANGED" in event_type:
                return "text_input"
            elif "SCROLLED" in event_type or "SCROLL" in event_type or "VIEW_SCROLLED" in event_type:
                return "swipe"

            return None
        except Exception:
            return None

    def collect_uiautomator(self, duration_seconds: int = 60):
        """收集uiautomator事件数据"""
        # 新格式使用简单的 uiautomator.log，旧格式保留时间戳
        if self.session_id:
            filename = os.path.join(self.output_dir, "uiautomator.log")
        else:
            filename = os.path.join(self.output_dir, f"uiautomator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        with open(filename, 'w', encoding='utf-8') as f:
            # Windows下使用PowerShell命令
            cmd = ['adb', 'shell', 'uiautomator', 'events']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

            start_time = time.time()
            while not self.stop_event.is_set() and (time.time() - start_time) < duration_seconds:
                line = process.stdout.readline()
                if line:
                    f.write(line)

                    # 新增：实时解析事件并触发截图
                    if 'EventType:' in line:
                        event_type = self._extract_event_type_from_line(line)
                        if event_type in ['click', 'swipe', 'text_input']:
                            self.screenshot_collector.trigger_screenshot(event_type=event_type)
                else:
                    time.sleep(0.1)

            process.terminate()
            return filename
    
    def collect_window(self, duration_seconds: int = 60, interval_seconds: int = 2):
        """收集window状态数据"""
        # 新格式使用简单的 window.log，旧格式保留时间戳
        if self.session_id:
            filename = os.path.join(self.output_dir, "window.log")
        else:
            filename = os.path.join(self.output_dir, f"window_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        with open(filename, 'w', encoding='utf-8') as f:
            start_time = time.time()
            while not self.stop_event.is_set() and (time.time() - start_time) < duration_seconds:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                try:
                    # Windows下使用PowerShell命令
                    cmd = ['adb', 'shell', 'dumpsys', 'window']
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
                    
                    # 使用正则表达式查找当前焦点窗口
                    match = re.search(r'mCurrentFocus=Window\{[^}]+\s+u0\s+([^/]+)/([^}]+)\}', result.stdout)
                    if match:
                        app_package, activity = match.groups()
                        f.write(f"{timestamp}: mCurrentFocus=Window{{xxx u0 {app_package}/{activity}}}\n")
                except subprocess.TimeoutExpired:
                    f.write(f"{timestamp}: ERROR: Timeout\n")
                except Exception as e:
                    f.write(f"{timestamp}: ERROR: {str(e)}\n")
                
                time.sleep(interval_seconds)
            
            return filename
    
    def start_collection(self, duration_seconds: int = 60):
        """启动所有数据收集线程
        
        Args:
            duration_seconds: 收集持续时间（秒），0表示无限期运行
            
        Returns:
            线程列表
        """
        self.stop_event.clear()
        
        # 创建并启动线程
        logcat_thread = threading.Thread(target=self.collect_logcat, args=(duration_seconds,))
        uiautomator_thread = threading.Thread(target=self.collect_uiautomator, args=(duration_seconds,))
        window_thread = threading.Thread(target=self.collect_window, args=(duration_seconds,))
        
        # 每次都创建新的截图监控线程
        screenshot_thread = self.screenshot_collector.start_monitoring(duration_seconds)
        
        self.threads = [logcat_thread, uiautomator_thread, window_thread]
        
        # 只启动 ourselves创建的线程，screenshot_thread已经在start_monitoring中启动了
        for thread in self.threads:
            thread.start()
        
        # 返回所有线程，包括截图线程
        return self.threads + [screenshot_thread]
    
    def stop_collection(self):
        """停止数据收集"""
        # 停止截图收集
        if self.screenshot_collector:
            self.screenshot_collector.stop_monitoring()
        
        # 停止logcat收集
        if hasattr(self, 'logcat_thread') and self.logcat_thread and self.logcat_thread.is_alive():
            self.logcat_active = False
            self.logcat_thread.join(timeout=5)
        
        # 停止uiautomator收集
        if hasattr(self, 'uiautomator_thread') and self.uiautomator_thread and self.uiautomator_thread.is_alive():
            self.uiautomator_active = False
            self.uiautomator_thread.join(timeout=5)
        
        # 停止window状态收集
        if hasattr(self, 'window_thread') and self.window_thread and self.window_thread.is_alive():
            self.window_active = False
            self.window_thread.join(timeout=5)
        
        # 停止所有线程
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=5)
        
        self.threads = []
        print("所有数据收集已停止")


class DataParser:
    """数据解析器，负责解析原始数据"""
    
    @staticmethod
    def parse_logcat_data(filename: str) -> List[Dict[str, Any]]:
        """解析logcat数据"""
        events = []
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # 解析时间戳
                timestamp_match = re.match(r'(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)', line)
                if not timestamp_match:
                    continue
                
                timestamp_str = timestamp_match.group(1)
                try:
                    # 将logcat时间戳转换为ISO格式
                    current_year = datetime.now().year
                    timestamp = datetime.strptime(f"{current_year}-{timestamp_str}", "%Y-%m-%d %H:%M:%S.%f")
                    timestamp_iso = timestamp.isoformat() + "Z"
                except ValueError:
                    continue
                
                # 解析ActivityTaskManager事件
                if "ActivityTaskManager" in line and ("Displayed" in line or "START u0" in line):
                    if "Displayed" in line:
                        # 示例: Displayed com.dianping.v1/.NovaMainActivity: +850ms
                        match = re.search(r'Displayed ([^/]+)/([^:]+):', line)
                        if match:
                            app_package, activity = match.groups()
                            duration_match = re.search(r'\+(\d+)ms', line)
                            duration = int(duration_match.group(1)) if duration_match else 0
                            
                            events.append({
                                "timestamp": timestamp_iso,
                                "source": "logcat",
                                "event_type": "app_start",
                                "app_package": app_package,
                                "activity": f"{app_package}/{activity}",
                                "duration": duration
                            })
                    elif "START u0" in line:
                        # 示例: START u0 {act=android.intent.action.MAIN ... pkg=com.tencent.mm cmp=com.tencent.mm/.ui.LauncherUI ...}
                        # 优先尝试从cmp=包名/活动 提取
                        match = re.search(r'cmp=([^/]+)/([^ }]+)', line)
                        if not match:
                            # 如果没有cmp=，尝试从pkg=包名和活动名提取
                            pkg_match = re.search(r'pkg=([^ ]+)', line)
                            if pkg_match:
                                app_package = pkg_match.group(1)
                                # 从cmp或活动信息中提取活动名
                                activity_match = re.search(r'cmp=([^/]+)/([^ }]+)', line)
                                if activity_match:
                                    activity = activity_match.group(2)
                                else:
                                    # 如果找不到，使用包名作为活动名
                                    activity = "Unknown"
                                match = (app_package, activity)

                        if match:
                            app_package, activity = match if isinstance(match, tuple) else match.groups()
                            # 确保app_package只包含有效的包名字符
                            if re.match(r'^[a-zA-Z][a-zA-Z0-9.]*$', app_package):
                                events.append({
                                    "timestamp": timestamp_iso,
                                    "source": "logcat",
                                    "event_type": "activity_change",
                                    "app_package": app_package,
                                    "activity": f"{app_package}/{activity}"
                                })
        
        return events
    
    @staticmethod
    def parse_uiautomator_data(filename: str) -> List[Dict[str, Any]]:
        """解析uiautomator数据，增强事件类型处理"""
        events = []
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # 解析时间戳
                    timestamp_match = re.match(r'(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)', line)
                    if not timestamp_match:
                        continue
                    
                    timestamp_str = timestamp_match.group(1)
                    # 添加年份
                    current_year = datetime.now().year
                    full_timestamp_str = f"{current_year}-{timestamp_str}"
                    
                    try:
                        timestamp = datetime.strptime(full_timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                        timestamp_iso = timestamp.isoformat() + "Z"
                    except ValueError:
                        continue
                    
                    # 解析事件类型
                    event_type_match = re.search(r'EventType: (\w+)', line)
                    if not event_type_match:
                        continue
                    
                    event_type = event_type_match.group(1)
                    action = ""
                    
                    # 扩展事件类型匹配
                    if "CLICKED" in event_type or "CLICK" in event_type:
                        action = "click"
                    elif "TEXT_CHANGED" in event_type or "TEXT" in event_type:
                        action = "text_input"
                    elif "LONG_CLICKED" in event_type or "LONG_CLICK" in event_type:
                        action = "long_click"
                    elif "SCROLLED" in event_type or "SCROLL" in event_type:
                        action = "swipe"
                    elif "WINDOW_STATE_CHANGED" in event_type:
                        action = "window_change"
                    elif "VIEW_CLICKED" in event_type:
                        action = "click"
                    elif "VIEW_TEXT_CHANGED" in event_type:
                        action = "text_input"
                    elif "VIEW_LONG_CLICKED" in event_type:
                        action = "long_click"
                    elif "VIEW_SCROLLED" in event_type:
                        action = "swipe"
                    elif "FOCUSED" in event_type:
                        action = "focus"
                    elif "SELECTED" in event_type:
                        action = "select"
                    elif "CHECKED" in event_type:
                        action = "check"
                    elif "PRESSED" in event_type:
                        action = "press"
                    elif "TOUCHED" in event_type:
                        action = "touch"
                    elif "NAVIGATED" in event_type:
                        action = "navigate"
                    else:
                        # 对于WINDOW_CONTENT_CHANGED等事件，我们将其视为内容变化
                        action = "content_change"
                    
                    # 解析包名
                    package_match = re.search(r'PackageName: (\S+)', line)
                    app_package = package_match.group(1) if package_match else ""
                    # 移除包名末尾的分号
                    if app_package and app_package.endswith(';'):
                        app_package = app_package[:-1]
                    
                    # 解析类名
                    class_match = re.search(r'ClassName: (\S+)', line)
                    class_name = class_match.group(1) if class_match else ""
                    
                    # 解析文本内容
                    text_match = re.search(r'Text: \[(.*?)\]', line)
                    text = text_match.group(1) if text_match else ""
                    
                    # 解析资源ID
                    resource_id_match = re.search(r'ResourceId: (\S+)', line)
                    resource_id = resource_id_match.group(1) if resource_id_match else ""
                    
                    # 解析内容描述
                    content_desc_match = re.search(r'ContentDescription: (\S+)', line)
                    content_desc = content_desc_match.group(1) if content_desc_match else ""
                    
                    # 解析坐标
                    coordinates = None
                    coord_match = re.search(r'bounds=\[(\d+),(\d+)\]\[(\d+),(\d+)\]', line)
                    if coord_match:
                        x1, y1, x2, y2 = int(coord_match.group(1)), int(coord_match.group(2)), int(coord_match.group(3)), int(coord_match.group(4))
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        coordinates = {
                            "center": {"x": center_x, "y": center_y},
                            "bounds": {"top_left": [x1, y1], "bottom_right": [x2, y2]}
                        }
                    
                    # 创建目标描述（P1优化：改进优先级）
                    # 优先级：1. text 2. resource_id 3. content_desc 4. class_name
                    target_description = "未知元素"

                    if text:
                        # 优先使用text
                        target_description = text
                        if resource_id:
                            # 简化resource_id，只保留最后部分
                            simplified_id = resource_id.split("/")[-1] if "/" in resource_id else resource_id
                            target_description = f"{text} ({simplified_id})"
                    elif resource_id:
                        # 其次使用resource_id
                        simplified_id = resource_id.split("/")[-1] if "/" in resource_id else resource_id
                        target_description = simplified_id
                    elif content_desc:
                        # 然后使用content_desc
                        target_description = content_desc
                    elif class_name:
                        # 最后使用class_name
                        simplified_class = class_name.split(".")[-1] if "." in class_name else class_name
                        target_description = simplified_class

                    target = target_description
                    
                    # 构建事件对象
                    event = {
                        "timestamp": timestamp_iso,
                        "source": "uiautomator",
                        "event_type": "ui_event",
                        "action": action,
                        "target": target,
                        "app_package": app_package,
                        "class": class_name
                    }
                    
                    # 添加可选字段
                    if coordinates:
                        event["coordinates"] = coordinates
                    
                    # 对于文本输入事件，提取输入的内容
                    if action == "text_input" and text:
                        event["content"] = text
                    
                    events.append(event)
                except Exception as e:
                    # 忽略无法解析的行
                    continue
        
        return events
    
    @staticmethod
    def parse_window_data(filename: str) -> List[Dict[str, Any]]:
        """解析window数据"""
        events = []
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or "mCurrentFocus" not in line:
                    continue
                
                try:
                    # 解析时间戳
                    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)', line)
                    if not timestamp_match:
                        continue
                    
                    timestamp_str = timestamp_match.group(1)
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                        timestamp_iso = timestamp.isoformat() + "Z"
                    except ValueError:
                        continue
                    
                    # 解析当前焦点窗口
                    focus_match = re.search(r'mCurrentFocus=Window\{[^}]+\s+u0\s+([^/]+)/([^}]+)\}', line)
                    if not focus_match:
                        continue
                    
                    app_package, activity = focus_match.groups()
                    
                    events.append({
                        "timestamp": timestamp_iso,
                        "source": "window",
                        "event_type": "current_focus",
                        "app_package": app_package,
                        "activity": f"{app_package}/{activity}"
                    })
                except Exception as e:
                    # 忽略无法解析的行
                    continue
        
        return events


class DataProcessor:
    """数据处理器，负责处理和融合数据"""
    
    def __init__(self):
        # 使用共享配置中的应用名称映射
        self.app_name_mapping = APP_PACKAGE_MAPPINGS
    
    def merge_and_sort_events(self, logcat_events, uiautomator_events, window_events, screenshot_events=None):
        """合并并排序所有事件，增强事件过滤和合并逻辑"""
        all_events = logcat_events + uiautomator_events + window_events
        
        # 添加截图事件
        if screenshot_events:
            all_events.extend(screenshot_events)
        
        # 按时间戳排序
        all_events.sort(key=lambda x: x.get("timestamp", 0))
        
        # 过滤无效事件
        filtered_events = []
        for event in all_events:
            # 过滤掉没有时间戳的事件
            if "timestamp" not in event:
                continue
                
            # 过滤掉没有事件类型的事件
            if "event_type" not in event:
                continue
                
            # 过滤掉无效的current_focus事件
            if event["event_type"] == "current_focus":
                if "app_package" not in event or not event["app_package"]:
                    continue
            
            filtered_events.append(event)
        
        # 合并连续的相同current_focus事件
        merged_events = []
        last_current_focus = None
        
        for event in filtered_events:
            if event["event_type"] == "current_focus":
                current_app = event.get("app_package", "")
                current_activity = event.get("activity", "")
                
                # 如果与上一个current_focus相同，跳过
                if last_current_focus:
                    last_app = last_current_focus.get("app_package", "")
                    last_activity = last_current_focus.get("activity", "")
                    
                    if current_app == last_app and current_activity == last_activity:
                        # 更新时间戳为最新的事件
                        last_current_focus["timestamp"] = event["timestamp"]
                        continue
                
                # 这是一个新的current_focus事件
                merged_events.append(event)
                last_current_focus = event
            else:
                merged_events.append(event)
                last_current_focus = None  # 重置，因为中间有其他事件
        
        return merged_events

    def segment_into_sessions(self, events, session_timeout_seconds=300):
        """将事件分割为会话"""
        from src.learning.utils import generate_session_id

        sessions = []
        current_session = None

        for event in events:
            # 规范化时间戳格式：统一转换为 ISO + 'Z' 格式
            timestamp_str = event["timestamp"]
            # 移除多余的时区信息（如 +00:00Z 或 +00:00+00:00）
            timestamp_str = timestamp_str.replace('+00:00', '')
            timestamp_str = timestamp_str.rstrip('Z') + 'Z'  # 确保以单个Z结尾

            event_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # 检查是否需要新会话
            if (current_session is None or
                (event_time - current_session["last_event_time"]).total_seconds() > session_timeout_seconds):

                if current_session:
                    sessions.append(current_session)

                # 使用新的session_id格式：YYYYMMDD_HHMMSS_<short-id>
                session_id = generate_session_id(event["timestamp"])

                current_session = {
                    "session_id": session_id,
                    "start_time": event["timestamp"],
                    "last_event_time": event_time,
                    "events": [event]
                }
            else:
                current_session["events"].append(event)
                current_session["last_event_time"] = event_time

        if current_session:
            sessions.append(current_session)

        return sessions
    
    def _should_filter_content_change(self, event: Dict[str, Any]) -> bool:
        """判断content_change事件是否应该被过滤

        过滤规则：
        1. target为空或仅含通用class名（FrameLayout、ProgressBar等）的content_change
        2. 保留含text/desc的content_change（可能是有意义的内容更新）

        Args:
            event: UIAutomator事件

        Returns:
            True表示应该过滤，False表示应该保留
        """
        if event.get("action") != "content_change":
            return False

        target = event.get("target", "")

        # 过滤掉空target
        if not target:
            return True

        # 过滤掉只有class信息的target（通用UI框架类）
        generic_classes = [
            "android.widget.FrameLayout",
            "android.widget.ProgressBar",
            "android.widget.LinearLayout",
            "android.view.View",
            "androidx.appcompat.widget.ActionBarOverlayLayout"
        ]

        has_text_or_desc = "text=" in target or ("desc=" in target and "desc=null;" not in target)
        if not has_text_or_desc:
            # 检查是否只含有通用class
            for generic_class in generic_classes:
                if generic_class in target and not any(attr in target for attr in ["text=", "id="] if attr != "text="):
                    return True

        return False

    def _should_filter_window_change(self, event: Dict[str, Any], last_interaction: Optional[Dict[str, Any]]) -> bool:
        """判断window_change事件是否应该被过滤

        过滤规则：
        1. 连续window_change事件的target相同且间隔<1秒时，过滤后续事件

        Args:
            event: 当前window_change事件
            last_interaction: 上一个交互事件

        Returns:
            True表示应该过滤，False表示应该保留
        """
        if event.get("action") != "window_change":
            return False

        if last_interaction is None or last_interaction.get("action") != "window_change":
            return False

        # 检查target是否相同
        if last_interaction.get("target") != event.get("target"):
            return False

        # 检查时间间隔（目标小于1秒）
        current_offset = event.get("time_offset", 0)
        last_offset = last_interaction.get("time_offset", 0)
        time_diff = current_offset - last_offset

        return 0 < time_diff < 1.0

    def _merge_consecutive_text_inputs(self, interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并连续的text_input事件为输入序列

        策略：
        1. 识别连续的text_input事件（同一target，时间间隔<2秒）
        2. 合并为单个interaction，保留完整的input_sequence
        3. 主要content为final_text

        Args:
            interactions: 原始交互列表

        Returns:
            合并后的交互列表
        """
        if not interactions:
            return interactions

        merged = []
        i = 0

        while i < len(interactions):
            interaction = interactions[i]

            # 如果不是text_input，直接添加
            if interaction.get("action") != "text_input":
                merged.append(interaction)
                i += 1
                continue

            # 开始收集连续的text_input事件
            text_input_sequence = [interaction]
            target = interaction.get("target", "")
            start_offset = interaction.get("time_offset", 0)

            j = i + 1
            while j < len(interactions):
                next_interaction = interactions[j]

                # 检查是否是同一目标的text_input且时间间隔<2秒
                if (next_interaction.get("action") == "text_input" and
                    next_interaction.get("target") == target and
                    next_interaction.get("time_offset", 0) - start_offset < 2.0):
                    text_input_sequence.append(next_interaction)
                    j += 1
                else:
                    break

            # 如果收集到多个text_input，进行合并
            if len(text_input_sequence) > 1:
                # 提取所有的content值
                input_sequence = [x.get("content", "") for x in text_input_sequence if x.get("content")]
                final_text = text_input_sequence[-1].get("content", "")

                merged_interaction = {
                    "action": "text_input",
                    "target": target,
                    "final_text": final_text,
                    "time_offset": text_input_sequence[-1].get("time_offset", 0)
                }

                # 仅当输入序列长度>1时才保留sequence
                if len(input_sequence) > 1:
                    merged_interaction["input_sequence"] = input_sequence
                else:
                    # 否则使用content字段（兼容旧格式）
                    merged_interaction["content"] = final_text

                merged.append(merged_interaction)
                i = j
            else:
                # 单个text_input，保持原样
                merged.append(interaction)
                i += 1

        return merged

    def build_app_sessions(self, events):
        """构建应用会话，优化交互事件处理

        核心修复：改进事件处理逻辑，使其对事件顺序更加鲁棒。
        当ui_event到达时，如果还没有activity，创建默认activity来接收交互。
        """
        app_sessions = []
        current_app = None
        current_activities = []
        current_app_package = None
        current_activity_name = None
        last_focus_time = None

        for event in events:
            event_type = event.get("event_type")

            if event_type == "current_focus":
                app_package = event.get("app_package", "")
                activity = event.get("activity", "")
                timestamp = event.get("timestamp", "")

                # 如果应用包名不为空
                if app_package:
                    # 如果是新应用，保存当前应用会话
                    if current_app_package != app_package:
                        # 保存当前应用会话
                        if current_app is not None:
                            # 计算最后一个活动的持续时间
                            if current_activities:
                                last_activity = current_activities[-1]
                                if "duration" not in last_activity:
                                    last_activity["duration"] = 0

                            current_app["activities"] = current_activities
                            app_sessions.append(current_app)

                        # 创建新应用会话
                        app_name = self.app_name_mapping.get(app_package, app_package)
                        current_app = {
                            "app_package": app_package,
                            "app_name": app_name,
                            "activities": []
                        }
                        current_activities = []
                        current_app_package = app_package

                    # 检查是否是新活动
                    if current_activity_name != activity:
                        # 计算上一个活动的持续时间
                        if current_activities:
                            prev_activity = current_activities[-1]
                            if "duration" not in prev_activity and last_focus_time:
                                try:
                                    prev_dt = datetime.fromisoformat(prev_activity["start_time"].replace('Z', '+00:00'))
                                    focus_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    prev_activity["duration"] = (focus_dt - prev_dt).total_seconds()
                                except:
                                    prev_activity["duration"] = 0

                        # 添加新活动
                        current_activities.append({
                            "name": activity,
                            "start_time": timestamp,
                            "interactions": []
                        })
                        current_activity_name = activity

                    last_focus_time = timestamp

            elif event_type == "ui_event" or event_type == "screenshot":
                # 确保有活动来接收交互事件
                # 如果没有current_activities，创建一个默认activity
                if not current_activities and current_app_package:
                    current_activities.append({
                        "name": "默认活动",
                        "start_time": event.get("timestamp", ""),
                        "interactions": []
                    })
                    current_activity_name = "默认活动"

                if current_activities:
                    current_activity = current_activities[-1]

                    # 计算时间偏移量
                    activity_start_time = current_activity["start_time"]
                    try:
                        event_dt = datetime.fromisoformat(event.get("timestamp", "").replace('Z', '+00:00'))
                        activity_dt = datetime.fromisoformat(activity_start_time.replace('Z', '+00:00'))
                        time_offset = (event_dt - activity_dt).total_seconds()
                    except:
                        time_offset = 0

                    if event_type == "ui_event":
                        # P0 优化：过滤content_change噪音事件
                        if self._should_filter_content_change(event):
                            continue

                        # 创建交互事件
                        interaction = {
                            "action": event["action"],
                            "target": event.get("target", ""),
                            "time_offset": time_offset
                        }

                        # 如果有内容，添加内容字段
                        if "content" in event:
                            interaction["content"] = event["content"]

                        # P0 优化：过滤重复的window_change事件
                        last_interaction = current_activity["interactions"][-1] if current_activity["interactions"] else None
                        if self._should_filter_window_change(event, last_interaction):
                            # 更新最后一个window_change事件的时间偏移
                            if last_interaction and last_interaction.get("action") == "window_change":
                                last_interaction["time_offset"] = time_offset
                            continue

                        # 合并连续的相同window_change事件（保留兼容性）
                        if (event["action"] == "window_change" and
                            current_activity["interactions"] and
                            current_activity["interactions"][-1]["action"] == "window_change" and
                            current_activity["interactions"][-1]["target"] == event.get("target", "")):
                            # 更新最后一个window_change事件的时间偏移
                            current_activity["interactions"][-1]["time_offset"] = time_offset
                        else:
                            # 添加新交互事件
                            current_activity["interactions"].append(interaction)

                    elif event_type == "screenshot":
                        # 创建截图交互事件
                        interaction = {
                            "action": "screenshot",
                            "filepath": event.get("filepath", ""),
                            "time_offset": time_offset
                        }
                        current_activity["interactions"].append(interaction)

        # 添加最后一个应用会话
        if current_app is not None:
            # 计算最后一个活动的持续时间
            if current_activities:
                last_activity = current_activities[-1]
                if "duration" not in last_activity:
                    last_activity["duration"] = 0

            current_app["activities"] = current_activities
            app_sessions.append(current_app)

        # P0 优化：合并所有应用会话中的连续text_input事件
        for app_session in app_sessions:
            for activity in app_session.get("activities", []):
                if "interactions" in activity:
                    activity["interactions"] = self._merge_consecutive_text_inputs(activity["interactions"])

        return app_sessions
    
    def get_ui_element_description(self, target):
        """将UI元素转换为可读描述，简化规则，保留原始数据供LLM分析"""
        # 优先使用文本内容
        if target.get("text"):
            return target["text"]
        
        # 其次使用内容描述
        if target.get("content_desc"):
            return target["content_desc"]
        
        # 最后使用资源ID，但简化处理，保留更多原始信息
        if target.get("resource_id"):
            # 只提取ID的最后部分，去除包名前缀
            resource_id = target["resource_id"]
            if ":" in resource_id:
                resource_id = resource_id.split(":")[-1]
            if "/" in resource_id:
                resource_id = resource_id.split("/")[-1]
            return resource_id
        
        # 如果都没有，返回类名的简化版本
        if target.get("class"):
            class_name = target["class"]
            # 提取类名的最后部分
            if "." in class_name:
                class_name = class_name.split(".")[-1]
            return class_name
        
        return "未知元素"
    
    def generate_summary_text(self, app_sessions):
        """生成简化的自然语言摘要，保留更多结构化数据供LLM分析"""
        # P1 优化：包含时长信息
        summary_parts = []

        for app_session in app_sessions:
            app_name = app_session["app_name"]
            activities = app_session["activities"]

            if not activities:
                continue

            # 计算总时长
            total_duration = sum(activity.get("duration", 0) for activity in activities)

            # 记录应用打开和停留时长
            if total_duration > 0:
                duration_text = f"({int(total_duration)}秒)"
                summary_parts.append(f"打开{app_name}{duration_text}")
            else:
                summary_parts.append(f"打开{app_name}")

            # 统计交互次数，不详细描述
            total_interactions = sum(len(activity.get("interactions", [])) for activity in activities)
            if total_interactions > 0:
                summary_parts.append(f"进行了{total_interactions}次交互")

        return "，".join(summary_parts) + "。" if summary_parts else ""
    
    def prepare_for_llm(self, session):
        """为LLM准备结构化数据，包含详细的交互信息

        修复：从raw_events中提取所有截图，不仅仅依赖于interactions中的screenshot
        """
        if not session:
            return None

        # 提取基本会话信息
        context_window = session.get("context_window", {})
        app_sessions = session.get("app_sessions", [])
        search_content = session.get("search_content", [])
        all_events = session.get("events", [])

        # 构建LLM友好的数据结构
        llm_data = {
            "session_info": {
                "start_time": context_window.get("start_time"),
                "end_time": context_window.get("end_time"),
                "duration_minutes": context_window.get("duration_minutes")
            },
            "user_activities": [],
            "screenshots": [],  # 单独的截图列表
            "search_content": search_content,  # 添加搜索内容
            "text_inputs": []  # 用户输入的文本内容
        }

        # 处理每个应用的会话
        for app_session in app_sessions:
            app_name = app_session.get("app_name", "未知应用")
            activities = app_session.get("activities", [])

            app_data = {
                "app_name": app_name,
                "activities": []
            }

            # 处理每个活动
            for activity in activities:
                activity_name = activity.get("name", "未知活动")
                start_time = activity.get("start_time")
                duration = activity.get("duration", 0)
                interactions = activity.get("interactions", [])

                activity_data = {
                    "activity_name": activity_name,
                    "start_time": start_time,
                    "duration_seconds": duration,
                    "interactions": []
                }

                # 处理每个交互，保留原始数据
                for interaction in interactions:
                    # 过滤掉无意义的content_change事件（target为空）
                    if interaction.get("action") == "content_change" and not interaction.get("target"):
                        continue

                    interaction_data = {
                        "action": interaction.get("action"),
                        "target": interaction.get("target"),
                        "time_offset": interaction.get("time_offset", 0)
                    }

                    # 处理截图事件
                    if interaction.get("action") == "screenshot":
                        # 添加到截图列表
                        screenshot_timestamp = start_time
                        if screenshot_timestamp and interaction.get("time_offset"):
                            try:
                                from datetime import datetime, timedelta
                                dt = datetime.fromisoformat(screenshot_timestamp.replace('Z', '+00:00'))
                                dt += timedelta(seconds=interaction.get("time_offset", 0))
                                screenshot_timestamp = dt.isoformat() + "Z"
                            except:
                                pass

                        llm_data["screenshots"].append({
                            "timestamp": screenshot_timestamp,
                            "filepath": interaction.get("filepath", "")
                        })

                        # 在interactions中也保留截图信息
                        interaction_data["filepath"] = interaction.get("filepath", "")

                    # 添加内容字段（如果有）
                    if "content" in interaction:
                        interaction_data["content"] = interaction["content"]

                    activity_data["interactions"].append(interaction_data)

                app_data["activities"].append(activity_data)

            llm_data["user_activities"].append(app_data)

        # 从raw_events中提取截图（作为备选方案，确保没有遗漏）
        if not llm_data["screenshots"] and all_events:
            for event in all_events:
                if event.get("event_type") == "screenshot":
                    llm_data["screenshots"].append({
                        "timestamp": event.get("timestamp", ""),
                        "filepath": event.get("filepath", "")
                    })

        # 按时间戳排序截图
        llm_data["screenshots"].sort(key=lambda x: x.get("timestamp", ""))

        # 从raw_events中提取文本输入内容，确保VLM能看到用户输入的文本
        if all_events:
            seen_contents = set()  # 去重，避免重复的相同输入
            for event in all_events:
                if (event.get("event_type") == "ui_event" and
                    event.get("action") == "text_input" and
                    "content" in event and event["content"]):

                    content = event["content"].strip()
                    if content and content not in seen_contents:
                        seen_contents.add(content)
                        llm_data["text_inputs"].append({
                            "timestamp": event.get("timestamp", ""),
                            "app_package": event.get("app_package", ""),
                            "content": content
                        })

        # 添加原始事件数据（可选，用于更详细的分析）
        if "events" in session:
            llm_data["raw_events"] = session["events"]

        return llm_data
    
    def build_context_window(self, session, window_size_minutes=None):
        """构建上下文窗口
        
        Args:
            session: 会话数据
            window_size_minutes: 时间窗口大小（分钟），如果为None则使用整个会话
        """
        start_time = session["start_time"]
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            # 如果没有指定窗口大小，使用整个会话
            if window_size_minutes is None:
                # 获取会话中所有事件的时间范围
                all_timestamps = []
                for e in session["events"]:
                    try:
                        event_dt = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
                        all_timestamps.append(event_dt)
                    except ValueError:
                        continue
                
                if all_timestamps:
                    end_time = max(all_timestamps)
                    duration = (end_time - start_dt).total_seconds() / 60
                else:
                    end_time = start_dt
                    duration = 0
                
                # 使用所有事件
                window_events = session["events"]
            else:
                # 使用指定的时间窗口
                end_time = start_dt + timedelta(minutes=window_size_minutes)
                duration = window_size_minutes
                
                # 过滤时间窗口内的事件
                window_events = []
                for event in session["events"]:
                    try:
                        event_dt = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                        if start_dt <= event_dt < end_time:
                            window_events.append(event)
                    except ValueError:
                        continue
            
            # 构建应用会话
            app_sessions = self.build_app_sessions(window_events)

            # P1 优化：修复所有activities的duration字段
            for app_session in app_sessions:
                if "activities" in app_session:
                    app_session["activities"] = self.fix_activity_durations(app_session["activities"])

            # 生成摘要文本
            summary_text = self.generate_summary_text(app_sessions)

            # 提取搜索内容
            search_content = self.extract_search_content(window_events)
            
            return {
                "context_window": {
                    "start_time": start_time,
                    "end_time": end_time.isoformat() + "+00:00Z",
                    "duration_minutes": duration
                },
                "app_sessions": app_sessions,
                "summary_text": summary_text,
                "search_content": search_content
            }
        except ValueError:
            return None
    
    def extract_search_content(self, events):
        """从事件列表中提取搜索内容
        
        Args:
            events: 事件列表
            
        Returns:
            搜索内容列表，每个元素包含时间戳、应用包名和搜索内容
        """
        search_events = []
        current_search = None
        
        for event in events:
            # 只处理uiautomator的文本输入事件
            if (event.get("source") == "uiautomator" and 
                event.get("action") == "text_input" and 
                "content" in event and event["content"]):
                
                app_package = event.get("app_package", "")
                content = event["content"]
                timestamp = event["timestamp"]
                
                # 如果是新的搜索序列，或者与上一个输入间隔时间较长，则开始新的搜索
                if current_search is None or app_package != current_search["app_package"]:
                    # 保存上一个搜索序列（如果有）
                    if current_search is not None:
                        search_events.append(current_search)
                    
                    # 开始新的搜索序列
                    current_search = {
                        "timestamp": timestamp,
                        "app_package": app_package,
                        "input_sequence": [content],
                        "final_text": content
                    }
                else:
                    # 继续当前搜索序列
                    current_search["input_sequence"].append(content)
                    current_search["final_text"] = content
                    current_search["timestamp"] = timestamp  # 更新为最后输入的时间
        
        # 添加最后一个搜索序列（如果有）
        if current_search is not None:
            search_events.append(current_search)

        return search_events

    def segment_into_app_sessions(self, session):
        """
        将Session分割为多个Application Session

        分割规则:
        1. 应用切换 → 新AppSession
        2. 同一应用前后间隔>5分钟 → 新AppSession

        返回: List[Application Session]
        """
        app_sessions = []

        # 遍历当前Session中已经按应用分组的app_sessions
        for app_data in session.get('app_sessions', []):
            app_package = app_data.get('app_package', '')
            app_name = app_data.get('app_name', '')
            activities = app_data.get('activities', [])

            if not activities:
                continue

            # 检查是否需要分割（同一应用的多次使用）
            # 策略：如果activities之间有大于5分钟的间隔，则分割
            sub_sessions = self.split_activities_by_gap(activities, gap_threshold_seconds=300)

            for i, activity_group in enumerate(sub_sessions):
                if not activity_group:
                    continue

                start_time = activity_group[0].get('start_time', '')
                end_time = self._calculate_app_end_time(activity_group)

                app_session = {
                    "app_session_id": f"{app_package}_{start_time.replace(':', '-').replace('+', '_')}",
                    "app_name": app_name,
                    "app_package": app_package,
                    "start_time": start_time,
                    "end_time": end_time,
                    "activities": activity_group,
                    "screenshots": self._extract_screenshots_in_timerange(
                        session, start_time, end_time
                    )
                }

                # 计算时长
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    app_session['duration'] = (end_dt - start_dt).total_seconds()
                except:
                    app_session['duration'] = 0

                # 计算交互次数
                app_session['interactions_count'] = sum(
                    len(act.get('interactions', [])) for act in activity_group
                )

                app_sessions.append(app_session)

        return app_sessions

    def split_activities_by_gap(self, activities, gap_threshold_seconds=300):
        """
        按时间间隔分割Activity列表

        示例:
        输入: [微信Activity 10:00, 微信Activity 10:02, 微信Activity 11:00]
        输出: [[微信Activity 10:00, 微信Activity 10:02], [微信Activity 11:00]]
        """
        if not activities:
            return []

        groups = []
        current_group = [activities[0]]

        for i in range(1, len(activities)):
            try:
                prev_time = datetime.fromisoformat(activities[i-1].get('start_time', '').replace('Z', '+00:00'))
                curr_time = datetime.fromisoformat(activities[i].get('start_time', '').replace('Z', '+00:00'))
                gap = (curr_time - prev_time).total_seconds()

                if gap > gap_threshold_seconds:
                    # 间隔过大，开始新组
                    groups.append(current_group)
                    current_group = [activities[i]]
                else:
                    current_group.append(activities[i])
            except:
                # 时间解析失败，添加到当前组
                current_group.append(activities[i])

        groups.append(current_group)
        return groups

    def _calculate_app_end_time(self, activities):
        """计算应用会话的结束时间"""
        if not activities:
            return datetime.now().isoformat() + "Z"

        last_activity = activities[-1]

        # 尝试从最后一个interaction的time_offset计算
        interactions = last_activity.get('interactions', [])
        if interactions:
            max_offset = max(
                float(i.get('time_offset', 0)) for i in interactions
            )
            try:
                start_dt = datetime.fromisoformat(last_activity.get('start_time', '').replace('Z', '+00:00'))
                end_dt = start_dt + __import__('datetime').timedelta(seconds=max_offset + 2)
                return end_dt.isoformat() + "Z"
            except:
                pass

        # 默认返回最后一个activity的start_time
        return last_activity.get('start_time', datetime.now().isoformat() + "Z")

    def _extract_screenshots_in_timerange(self, session, start_time, end_time):
        """提取时间范围内的截图"""
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except:
            return []

        screenshots = []
        for screenshot in session.get('screenshots', []):
            try:
                ss_time = datetime.fromisoformat(screenshot.get('timestamp', '').replace('Z', '+00:00'))
                if start_dt <= ss_time <= end_dt:
                    screenshots.append(screenshot)
            except:
                continue

        return screenshots


    def fix_activity_durations(self, activities):
        """
        修复Activity的duration字段

        方法1: 通过下一个Activity的start_time计算
        方法2: 通过最后一个interaction的time_offset估算
        """
        if not activities:
            return activities

        for i, activity in enumerate(activities):
            if activity.get('duration', 0) > 0:
                continue  # 已有duration跳过

            # 获取下一个Activity的开始时间
            if i < len(activities) - 1:
                try:
                    next_start = datetime.fromisoformat(activities[i+1].get('start_time', '').replace('Z', '+00:00'))
                    curr_start = datetime.fromisoformat(activity.get('start_time', '').replace('Z', '+00:00'))
                    duration = (next_start - curr_start).total_seconds()
                except:
                    duration = 0
            else:
                # 最后一个Activity: 用最后一个interaction的offset估算
                interactions = activity.get('interactions', [])
                if interactions:
                    try:
                        max_offset = max(
                            float(i.get('time_offset', 0)) for i in interactions
                        )
                        duration = max_offset + 2  # 加2秒buffer
                    except:
                        duration = 5
                else:
                    duration = 5  # 默认5秒

            activity['duration'] = max(duration, 0)

        return activities


    def allocate_screenshots_for_app_session(self, app_session, quota=8):
        """
        为单个Application Session分配截图

        策略:
        1. 修复Activity duration
        2. 过滤短Activity (<5秒)
        3. 保底分配 (每个Activity ≥1张) + 时长加权
        4. 智能采样 (避开转场动画2秒，均匀分布)

        特殊处理:
        - 如果Activity数量 > quota: 按交互次数排序，优先分配
        - 如果没有有效Activity: 降级到均匀采样

        返回: List[截图]（长度≤quota）
        """
        activities = self.fix_activity_durations(app_session.get('activities', []))
        valid_activities = [a for a in activities if a.get('duration', 0) >= 5]

        if not valid_activities:
            # 降级：均匀采样
            return self._uniform_sample_screenshots(
                app_session.get('screenshots', []), quota
            )

        # 保底分配
        base_allocation = {i: 1 for i in range(len(valid_activities))}
        remaining = quota - len(valid_activities)

        if remaining < 0:
            # Activity数量超过配额，只能每个取1张或部分跳过
            # 策略：按交互次数排序，优先给交互多的Activity
            valid_activities_with_idx = [
                (i, a) for i, a in enumerate(valid_activities)
            ]
            valid_activities_with_idx.sort(
                key=lambda x: len(x[1].get('interactions', [])), reverse=True
            )
            valid_activities = [a for _, a in valid_activities_with_idx[:quota]]
            base_allocation = {i: 1 for i in range(len(valid_activities))}
            remaining = 0

        # 时长加权分配
        total_duration = sum(a.get('duration', 0) for a in valid_activities)
        if total_duration > 0:
            for i, activity in enumerate(valid_activities):
                weight = activity.get('duration', 0) / total_duration
                additional = int(remaining * weight)
                base_allocation[i] += additional

        # 智能采样
        selected_screenshots = []
        for i, activity in enumerate(valid_activities):
            quota_for_activity = base_allocation.get(i, 1)
            duration = activity.get('duration', 0)

            # 生成采样时刻
            if quota_for_activity == 1:
                sample_offsets = [min(2.0, duration / 2)]
            elif quota_for_activity == 2:
                sample_offsets = [
                    min(2.0, duration * 0.2),
                    max(duration - 2.0, duration * 0.8)
                ]
            else:
                interval = duration / (quota_for_activity - 1)
                sample_offsets = [j * interval for j in range(quota_for_activity)]

            # 从interactions中找最接近的截图
            for offset in sample_offsets:
                screenshot = self._find_nearest_screenshot_in_activity(
                    activity, offset
                )
                if screenshot:
                    selected_screenshots.append(screenshot)

        return selected_screenshots[:quota]  # 确保不超配额

    def _uniform_sample_screenshots(self, screenshots, quota):
        """均匀采样截图"""
        if not screenshots or quota <= 0:
            return []

        if len(screenshots) <= quota:
            return screenshots

        # 均匀采样
        indices = [int(i * len(screenshots) / quota) for i in range(quota)]
        return [screenshots[i] for i in indices]

    def _find_nearest_screenshot_in_activity(self, activity, offset):
        """从Activity的interactions中找到最接近目标offset的截图"""
        interactions = activity.get('interactions', [])
        screenshot_interactions = [
            i for i in interactions if i.get('action') == 'screenshot'
        ]

        if not screenshot_interactions:
            return None

        # 找最接近的
        best_screenshot = None
        best_diff = float('inf')

        for ss in screenshot_interactions:
            ss_offset = float(ss.get('time_offset', 0))
            diff = abs(ss_offset - offset)
            if diff < best_diff:
                best_diff = diff
                best_screenshot = ss

        return best_screenshot


class BehaviorAnalyzer:
    """行为分析器主类"""

    def __init__(self, output_dir: str = "data"):
        self.output_dir = output_dir
        self.sessions_dir = os.path.join(output_dir, "sessions")
        # 旧结构支持（向后兼容）
        self.processed_dir = os.path.join(output_dir, "processed")
        # 新结构：全局索引路径
        self.master_index_path = os.path.join(output_dir, "master_index.json")
        self.ensure_output_dirs()
        # 注：collector和parser在collect_and_process中按需初始化，使用session-specific路径
        self.parser = DataParser()
        self.processor = DataProcessor()

    def ensure_output_dirs(self):
        """确保输出目录存在"""
        # 创建主要目录结构
        for subdir in ["sessions"]:
            dir_path = os.path.join(self.output_dir, subdir)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        # 为了向后兼容，也创建旧结构的目录
        for subdir in ["raw", "processed"]:
            dir_path = os.path.join(self.output_dir, subdir)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
    
    def start_background_learning(self):
        """启动后台学习模式"""
        global learning_active, learning_thread
        
        if learning_active:
            print("后台学习模式已在运行中")
            return
        
        learning_active = True
        learning_thread = threading.Thread(target=self._background_learning_worker)
        learning_thread.daemon = True
        learning_thread.start()
        print("后台学习模式已启动")
    
    def stop_background_learning(self):
        """停止后台学习模式"""
        global learning_active
        
        if not learning_active:
            print("后台学习模式未运行")
            return
        
        learning_active = False
        if learning_thread and learning_thread.is_alive():
            learning_thread.join(timeout=5)
        print("后台学习模式已停止")
    
    def _background_learning_worker(self):
        """后台学习工作线程"""
        global learning_active
        
        # 启动数据收集
        self.collector.start_collection(duration_seconds=0)  # 0表示无限期运行
        
        try:
            last_process_time = time.time()
            process_interval = 60  # 每60秒处理一次数据
            
            while learning_active:
                current_time = time.time()
                
                # 检查是否需要处理数据
                if current_time - last_process_time >= process_interval:
                    # 处理收集到的数据
                    self._process_collected_data()
                    last_process_time = current_time
                
                # 短暂休眠，避免CPU占用过高
                time.sleep(1)
        finally:
            # 停止数据收集
            self.collector.stop_collection()
    
    def _process_collected_data(self):
        """
        处理收集到的数据

        注意：为了避免数据竞争，只处理非最新的文件。
        最新的文件可能还在被 DataCollector 写入。
        """
        try:
            # 获取最新的数据文件
            raw_dir = os.path.join(self.output_dir, "raw")
            logcat_files = sorted([f for f in os.listdir(raw_dir) if f.startswith("logcat_")])
            uiautomator_files = sorted([f for f in os.listdir(raw_dir) if f.startswith("uiautomator_")])
            window_files = sorted([f for f in os.listdir(raw_dir) if f.startswith("window_")])

            # 只处理非最新的文件（倒数第二个文件是已完成的）
            if len(logcat_files) < 2 or len(uiautomator_files) < 2 or len(window_files) < 2:
                return  # 没有足够的已完成数据文件

            # 获取倒数第二个文件（避免读取正在写入的最新文件）
            logcat_file = os.path.join(raw_dir, logcat_files[-2])
            uiautomator_file = os.path.join(raw_dir, uiautomator_files[-2])
            window_file = os.path.join(raw_dir, window_files[-2])
            
            # 获取截图文件
            screenshot_dir = self.collector.screenshot_collector.output_dir
            screenshot_files = []
            if os.path.exists(screenshot_dir):
                screenshot_files = [os.path.join(screenshot_dir, f) for f in os.listdir(screenshot_dir) if f.startswith("screenshot_")]
            
            # 解析数据
            logcat_events = self.parser.parse_logcat_data(logcat_file)
            uiautomator_events = self.parser.parse_uiautomator_data(uiautomator_file)
            window_events = self.parser.parse_window_data(window_file)
            
            # 解析截图事件
            screenshot_events = []
            for screenshot_file in screenshot_files:
                # 从文件名提取时间戳
                filename = os.path.basename(screenshot_file)
                timestamp_match = re.search(r'screenshot_(\d{8}_\d{6}_\d{3})\.png', filename)
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S_%f")
                        timestamp_iso = timestamp.isoformat() + "Z"
                        screenshot_events.append({
                            "timestamp": timestamp_iso,
                            "source": "screenshot",
                            "event_type": "screenshot",
                            "filepath": screenshot_file
                        })
                    except ValueError:
                        continue
            
            # 合并和排序事件
            all_events = self.processor.merge_and_sort_events(logcat_events, uiautomator_events, window_events, screenshot_events)
            
            # 分割会话
            sessions = self.processor.segment_into_sessions(all_events)
            
            # 处理每个会话
            processed_sessions = []
            all_search_content = []  # 收集所有会话的搜索内容
            
            for session in sessions:
                context_window = self.processor.build_context_window(session)
                if context_window:
                    # 添加原始事件数据
                    context_window["events"] = session["events"]
                    processed_sessions.append(context_window)
                    
                    # 收集搜索内容
                    if "search_content" in context_window:
                        all_search_content.extend(context_window["search_content"])
                    
                    # 保存会话数据
                    session_file = os.path.join(self.output_dir, "sessions", f"{session['session_id']}.json")
                    with open(session_file, 'w', encoding='utf-8') as f:
                        json.dump(context_window, f, indent=2, ensure_ascii=False)
            
            # 保存所有搜索内容
            if all_search_content:
                self.save_search_content(all_search_content)
            
            # 保存索引文件
            index_file = os.path.join(self.output_dir, "index.json")
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_sessions": len(processed_sessions),
                    "sessions": [{"session_id": s["context_window"]["start_time"], "file": f"sessions/{s['context_window']['start_time']}.json"} for s in processed_sessions]
                }, f, indent=2, ensure_ascii=False)
            
            print(f"后台处理完成，处理了 {len(processed_sessions)} 个会话")
                
        except Exception as e:
            print(f"后台处理数据时出错: {str(e)}")

    def prepare_for_vlm_batch(self, sessions):
        """
        为批量VLM分析准备数据

        输入: List[Session] (可能是数十个Session)
        输出: List[AppSessionVLMInput]

        流程:
        1. 遍历所有Session
        2. 分割为Application Sessions
        3. 为每个AppSession分配截图
        4. 构建VLM输入格式
        """
        app_sessions_data = []

        for session in sessions:
            # 分割为Application Sessions
            app_sessions = self.processor.segment_into_app_sessions(session)

            for app_session in app_sessions:
                # 为该AppSession分配截图
                selected_screenshots = self.processor.allocate_screenshots_for_app_session(
                    app_session, quota=8
                )

                # 构建VLM输入格式
                activities_summary = self._build_activities_summary(app_session.get('activities', []))

                vlm_input = {
                    "app_session_id": app_session.get('app_session_id', ''),
                    "app_name": app_session.get('app_name', ''),
                    "app_package": app_session.get('app_package', ''),
                    "start_time": app_session.get('start_time', ''),
                    "end_time": app_session.get('end_time', ''),
                    "duration": app_session.get('duration', 0),
                    "activities_summary": activities_summary,
                    "screenshots": selected_screenshots,
                    "interactions": self._extract_interactions(app_session.get('activities', [])),
                    "search_queries": self._extract_search_queries(app_session.get('activities', []))
                }

                app_sessions_data.append(vlm_input)

        return app_sessions_data

    def _build_activities_summary(self, activities):
        """构建Activity摘要"""
        if not activities:
            return "无活动"

        activity_names = [a.get('name', '未知').split('/')[-1] for a in activities]
        duration_total = sum(a.get('duration', 0) for a in activities)
        interaction_count = sum(len(a.get('interactions', [])) for a in activities)

        return f"访问{len(activities)}个页面，停留{int(duration_total)}秒，{interaction_count}次交互"

    def _extract_interactions(self, activities):
        """提取所有交互事件"""
        interactions = []
        for activity in activities:
            for interaction in activity.get('interactions', []):
                if interaction.get('action') != 'screenshot':
                    interactions.append({
                        "action": interaction.get('action', ''),
                        "target": interaction.get('target', ''),
                        "time_offset": interaction.get('time_offset', 0),
                        "content": interaction.get('content', '')
                    })
        return interactions

    def _extract_search_queries(self, activities):
        """提取搜索查询"""
        search_queries = []
        for activity in activities:
            for interaction in activity.get('interactions', []):
                if interaction.get('action') == 'text_input' and interaction.get('content'):
                    search_queries.append({
                        "content": interaction.get('content', ''),
                        "time_offset": interaction.get('time_offset', 0)
                    })
        return search_queries

    def get_all_sessions(self):
        """获取所有已处理的Session"""
        sessions = []
        if not os.path.exists(self.sessions_dir):
            return sessions

        for filename in os.listdir(self.sessions_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.sessions_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        session = json.load(f)
                        sessions.append(session)
                except:
                    continue

        return sessions

    def collect_and_process(self, duration_seconds: int = 60):
        """收集并处理数据，使用新的会话文件结构"""
        from src.learning.utils import (
            generate_session_id, create_session_folder,
            create_session_metadata, update_master_index
        )

        print(f"开始收集数据，将持续 {duration_seconds} 秒...")

        # 生成会话ID
        session_id = generate_session_id()
        print(f"会话ID: {session_id}")

        # 创建会话文件夹结构
        session_folder = create_session_folder(self.output_dir, session_id)
        print(f"会话文件夹: {session_folder}")

        # 初始化收集器（使用session-specific路径）
        collector = DataCollector(
            os.path.join(session_folder, "raw"),
            session_id=session_id
        )

        # 启动数据收集
        threads = collector.start_collection(duration_seconds)

        # 等待收集完成
        for thread in threads:
            thread.join()

        print("数据收集完成，开始处理...")

        # 获取会话的数据文件
        raw_dir = os.path.join(session_folder, "raw")
        logcat_file = os.path.join(raw_dir, "logcat.log")
        uiautomator_file = os.path.join(raw_dir, "uiautomator.log")
        window_file = os.path.join(raw_dir, "window.log")

        # 检查必要的文件
        if not all(os.path.exists(f) for f in [logcat_file, uiautomator_file, window_file]):
            print("错误：缺少必要的数据文件")
            return None

        # 获取截图文件
        screenshot_dir = os.path.join(session_folder, "screenshots")
        screenshot_files = []
        if os.path.exists(screenshot_dir):
            screenshot_files = [
                os.path.join(screenshot_dir, f)
                for f in os.listdir(screenshot_dir)
                if f.endswith(".png")
            ]

        # 解析数据
        logcat_events = self.parser.parse_logcat_data(logcat_file)
        uiautomator_events = self.parser.parse_uiautomator_data(uiautomator_file)
        window_events = self.parser.parse_window_data(window_file)

        # 解析截图事件（支持新格式的相对时间命名）
        screenshot_events = []
        if screenshot_files:
            # 获取会话开始时间
            session_start_time = None
            if logcat_events:
                try:
                    session_start_time = datetime.fromisoformat(
                        logcat_events[0]["timestamp"].replace('Z', '+00:00')
                    )
                except (ValueError, TypeError, IndexError):
                    pass

            for screenshot_file in screenshot_files:
                filename = os.path.basename(screenshot_file)
                try:
                    # 尝试新格式：HHmmSS_mmm.png
                    timestamp_match = re.search(r'^(\d{2})(\d{2})(\d{2})_(\d{3})\.png$', filename)
                    if timestamp_match and session_start_time:
                        hours = int(timestamp_match.group(1))
                        minutes = int(timestamp_match.group(2))
                        seconds = int(timestamp_match.group(3))
                        millis = int(timestamp_match.group(4))

                        time_offset = hours * 3600 + minutes * 60 + seconds + millis / 1000.0
                        screenshot_time = session_start_time + timedelta(seconds=time_offset)
                        # 确保时间戳格式一致：如果原始时间戳以Z结尾，则使用Z；如果以+00:00结尾，则转换为Z
                        timestamp_iso = screenshot_time.isoformat()
                        if timestamp_iso.endswith('+00:00'):
                            timestamp_iso = timestamp_iso[:-6] + 'Z'
                        elif not timestamp_iso.endswith('Z'):
                            timestamp_iso = timestamp_iso + 'Z'
                    else:
                        # 降级到旧格式或跳过
                        continue

                    screenshot_events.append({
                        "timestamp": timestamp_iso,
                        "source": "screenshot",
                        "event_type": "screenshot",
                        "filepath": screenshot_file
                    })
                except (ValueError, TypeError, AttributeError):
                    continue

        print(f"解析完成：logcat事件 {len(logcat_events)} 个，uiautomator事件 {len(uiautomator_events)} 个，window事件 {len(window_events)} 个，截图 {len(screenshot_events)} 个")

        # 合并和排序事件
        all_events = self.processor.merge_and_sort_events(logcat_events, uiautomator_events, window_events, screenshot_events)

        # 分割会话
        sessions = self.processor.segment_into_sessions(all_events)
        print(f"识别出 {len(sessions)} 个会话")

        # 获取会话时间范围
        if sessions:
            session_start_time = sessions[0]["start_time"]
            # 获取最后一个会话的结束时间
            session_end_time = sessions[-1]["events"][-1]["timestamp"] if sessions[-1]["events"] else session_start_time
        else:
            session_start_time = datetime.now().isoformat() + "Z"
            session_end_time = session_start_time

        # 处理每个会话
        processed_sessions = []
        all_search_content = []  # 收集所有会话的搜索内容

        for session in sessions:
            context_window = self.processor.build_context_window(session)
            if context_window:
                # 添加原始事件数据
                context_window["events"] = session["events"]
                processed_sessions.append(context_window)

                # 收集搜索内容
                if "search_content" in context_window:
                    all_search_content.extend(context_window["search_content"])

        # 创建会话元数据
        metadata = create_session_metadata(
            session_id=session_id,
            start_time=session_start_time,
            end_time=session_end_time,
            status="completed",
            statistics={
                "total_events": len(all_events),
                "screenshot_count": len(screenshot_events),
                "app_sessions": len(processed_sessions)
            }
        )

        # 保存metadata.json
        metadata_file = os.path.join(session_folder, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 保存处理后的events.json
        events_file = os.path.join(session_folder, "processed", "events.json")
        events_data = {
            "session_id": session_id,
            "events": all_events
        }
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)

        # 保存会话摘要（LLM就绪格式）
        summary_file = os.path.join(session_folder, "processed", "session_summary.json")
        if processed_sessions:
            summary_data = self.processor.prepare_for_llm({
                "context_window": {
                    "start_time": session_start_time,
                    "end_time": session_end_time
                },
                "app_sessions": [s for s in processed_sessions],
                "events": all_events,
                "search_content": all_search_content
            })
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)

        # 更新全局索引
        update_master_index(self.output_dir, session_id, metadata)

        print(f"处理完成，结果已保存到 {session_folder}")
        return session_id  # 返回会话ID而不是processed_sessions
    
    def get_latest_session_for_llm(self):
        """获取最新的会话数据并转换为适合LLM处理的格式"""
        from src.learning.utils import load_session_metadata, load_session_events, list_all_sessions

        # 获取所有会话列表
        all_sessions = list_all_sessions(self.output_dir)
        if not all_sessions:
            return None

        # 按修改时间获取最新会话（最后一个）
        latest_session_id = all_sessions[-1]

        # 加载会话元数据和事件
        metadata = load_session_metadata(self.output_dir, latest_session_id)
        if not metadata:
            return None

        # 加载会话事件
        session_events = load_session_events(self.output_dir, latest_session_id)
        if not session_events:
            return None

        # 构建适合LLM的数据格式
        session_folder = os.path.join(self.output_dir, "sessions", latest_session_id)
        processed_dir = os.path.join(session_folder, "processed")

        # 读取 session_summary.json
        summary_file = os.path.join(processed_dir, "session_summary.json")
        llm_data = None
        if os.path.exists(summary_file):
            with open(summary_file, 'r', encoding='utf-8') as f:
                llm_data = json.load(f)

        if not llm_data:
            return None

        # 添加元数据信息
        llm_data["session_id"] = latest_session_id
        llm_data["metadata"] = metadata

        # 处理截图路径
        screenshot_dir = os.path.join(session_folder, "screenshots")
        if os.path.exists(screenshot_dir):
            screenshot_files = [
                os.path.join(screenshot_dir, f)
                for f in os.listdir(screenshot_dir)
                if f.endswith(".png")
            ]
            llm_data["screenshots"] = [
                {"filepath": f, "filename": os.path.basename(f)}
                for f in sorted(screenshot_files)
            ]

        # 保存LLM数据到会话的processed目录
        llm_file = os.path.join(processed_dir, f"{latest_session_id}_llm.json")
        os.makedirs(processed_dir, exist_ok=True)
        with open(llm_file, 'w', encoding='utf-8') as f:
            json.dump(llm_data, f, indent=2, ensure_ascii=False)

        return llm_data
    
    def save_llm_data(self, session_data, filename=None, session_id=None):
        """保存LLM数据到文件"""
        if filename is None:
            if session_id is not None:
                filename = f"{session_id}_llm.json"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"llm_data_{timestamp}.json"
        
        output_dir = os.path.join(self.output_dir, "processed")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        print(f"LLM数据已保存到: {file_path}")
        return file_path
    
    def save_search_content(self, search_content, filename=None):
        """保存搜索内容到文件
        
        Args:
            search_content: 搜索内容列表
            filename: 输出文件名，如果为None则使用默认文件名
        """
        if filename is None:
            filename = "search_content.json"
        
        output_dir = os.path.join(self.output_dir, "processed")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(search_content, f, indent=2, ensure_ascii=False)
        
        return file_path


if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--vlm":
        # 运行VLM分析
        from vlm_analyzer import VLMAnalyzer
        import json
        
        # 检查配置文件
        config_file = "config.json"
        if not os.path.exists(config_file):
            print(f"错误: 配置文件 {config_file} 不存在")
            print("请复制 config.json.example 为 config.json 并填入您的API密钥")
            sys.exit(1)
        
        # 读取配置
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            api_key = config.get("api_key")
            model = config.get("model", "glm-4.1v-thinking-flash")
        
        if not api_key:
            print("错误: 配置文件中未找到API密钥")
            sys.exit(1)
        
        # 创建VLM分析器
        analyzer = VLMAnalyzer(api_key=api_key, model=model, api_url=config.get("api_url"))
        
        # 分析最新会话
        sessions_dir = "data/processed"
        if not os.path.exists(sessions_dir):
            print(f"错误: 目录 {sessions_dir} 不存在")
            sys.exit(1)
    else:
        # 默认行为：使用已有会话数据进行测试
        analyzer = BehaviorAnalyzer()
        
        # 直接使用已有的会话数据进行测试，不重新收集
        print("使用已有会话数据进行测试...")
        
        # 获取最新会话用于LLM
        latest_session = analyzer.get_latest_session_for_llm()
        if latest_session:
            print("\n最新会话数据（用于LLM分析）：")
            print(json.dumps(latest_session, indent=2, ensure_ascii=False))
            
            # 指出feed给LLM的文件路径
            print(f"\n可以将以下文件喂给LLM进行分析：")
            print(f"文件路径: {os.path.join(analyzer.processed_dir, sorted(os.listdir(analyzer.processed_dir))[-1])}")
        else:
            print("没有找到会话数据")