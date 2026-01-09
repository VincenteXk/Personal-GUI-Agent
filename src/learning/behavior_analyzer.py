import json
import re
import subprocess
import time
import os
import cv2
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import threading
from queue import Queue
import logging
from typing import Dict, List, Tuple, Optional, Any
import queue
import shutil

from src.shared.config import APP_PACKAGE_MAPPINGS

# 全局变量用于学习模式
learning_active = False
learning_thread = None


class ScreenshotCollector:
    """截图收集器，负责在特定事件触发时捕获屏幕截图"""
    
    def __init__(self, output_dir: str = "data/screenshots"):
        self.output_dir = output_dir
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
            截图文件路径
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 检查最小截图间隔
        current_time = time.time()
        if current_time - self.last_screenshot_time < self.min_screenshot_interval:
            return None  # 跳过截图，防止过于频繁
        
        # 生成截图文件名
        filename = os.path.join(self.output_dir, f"screenshot_{timestamp.strftime('%Y%m%d_%H%M%S_%f')[:-3]}.png")
        
        try:
            # 使用adb pull方式截图，避免Windows系统下PNG文件头损坏问题
            # 首先在设备上截图
            device_screenshot_path = "/sdcard/screenshot_temp.png"
            cmd_capture = ['adb', 'shell', 'screencap', '-p', device_screenshot_path]
            subprocess.run(cmd_capture, capture_output=True, check=True)
            
            # 然后从设备拉取截图到本地
            cmd_pull = ['adb', 'pull', device_screenshot_path, filename]
            subprocess.run(cmd_pull, capture_output=True, check=True)
            
            # 删除设备上的临时截图文件
            cmd_remove = ['adb', 'shell', 'rm', device_screenshot_path]
            subprocess.run(cmd_remove, capture_output=True, check=True)
            
            self.last_screenshot_time = current_time
            return filename
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
    
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = output_dir
        self.ensure_output_dir()
        self.stop_event = threading.Event()
        self.threads = []
        self.screenshot_collector = ScreenshotCollector()  # 添加截图收集器
        
    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def collect_logcat(self, duration_seconds: int = 60):
        """收集logcat数据"""
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
                        # 示例: START u0 from pid 1234 com.dianping.v1/.NovaMainActivity
                        # 或者: START u0 {act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10200000 cmp=com.dianping.v1/.NovaMainActivity}
                        match = re.search(r'START u0.*? cmp=([^/]+)/([^ ]+)', line)
                        if not match:
                            # 尝试另一种格式
                            match = re.search(r'START u0.*? ([^/]+)/([^ ]+)', line)
                        
                        if match:
                            app_package, activity = match.groups()
                            # 清理应用包名，移除可能包含的Intent信息
                            app_package = re.sub(r'^[^a-zA-Z]', '', app_package)
                            app_package = re.sub(r'[^a-zA-Z.]*$', '', app_package)
                            
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
                    coord_match = re.search(r'bounds=\[(\d+,\d+)\]\[(\d+,\d+)\]', line)
                    if coord_match:
                        coordinates = {
                            "top_left": coord_match.group(1),
                            "bottom_right": coord_match.group(2)
                        }
                    
                    # 创建目标描述
                    target_parts = []
                    if text:
                        target_parts.append(f"text={text}")
                    if resource_id:
                        target_parts.append(f"id={resource_id}")
                    if class_name:
                        target_parts.append(f"class={class_name}")
                    if content_desc:
                        target_parts.append(f"desc={content_desc}")
                    
                    target = ", ".join(target_parts) if target_parts else "未知元素"
                    
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
        sessions = []
        current_session = None
        
        for event in events:
            event_time = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
            
            # 检查是否需要新会话
            if (current_session is None or 
                (event_time - current_session["last_event_time"]).total_seconds() > session_timeout_seconds):
                
                if current_session:
                    sessions.append(current_session)
                
                current_session = {
                    "session_id": f"session_{event['timestamp'].replace(':', '-')}",
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
    
    def build_app_sessions(self, events):
        """构建应用会话，优化交互事件处理"""
        app_sessions = []
        current_app = None
        current_activities = []
        
        for event in events:
            if event["event_type"] == "current_focus":
                app_package = event.get("app_package", "")
                activity = event.get("activity", "")
                
                # 如果应用包名不为空
                if app_package:
                    # 如果是新应用，保存当前应用会话
                    if current_app is None or current_app["app_package"] != app_package:
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
                    
                    # 检查是否是新活动
                    if not current_activities or current_activities[-1]["name"] != activity:
                        # 计算上一个活动的持续时间
                        if current_activities:
                            prev_activity = current_activities[-1]
                            if "duration" not in prev_activity:
                                prev_activity["duration"] = 0
                        
                        # 添加新活动
                        current_activities.append({
                            "name": activity,
                            "start_time": event["timestamp"],
                            "interactions": []
                        })
            
            elif event["event_type"] == "ui_event":
                # 添加交互事件到当前活动
                if current_activities:
                    current_activity = current_activities[-1]
                    
                    # 计算时间偏移量
                    activity_start_time = current_activity["start_time"]
                    try:
                        # 将时间戳字符串转换为datetime对象
                        event_dt = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                        activity_dt = datetime.fromisoformat(activity_start_time.replace('Z', '+00:00'))
                        time_offset = (event_dt - activity_dt).total_seconds()
                    except:
                        time_offset = 0
                    
                    # 创建交互事件
                    interaction = {
                        "action": event["action"],
                        "target": event.get("target", ""),
                        "time_offset": time_offset
                    }
                    
                    # 如果有内容，添加内容字段
                    if "content" in event:
                        interaction["content"] = event["content"]
                    
                    # 合并连续的相同window_change事件
                    if (event["action"] == "window_change" and 
                        current_activity["interactions"] and 
                        current_activity["interactions"][-1]["action"] == "window_change" and
                        current_activity["interactions"][-1]["target"] == event.get("target", "")):
                        # 更新最后一个window_change事件的时间偏移
                        current_activity["interactions"][-1]["time_offset"] = time_offset
                    else:
                        # 添加新交互事件
                        current_activity["interactions"].append(interaction)
            
            elif event["event_type"] == "screenshot":
                # 添加截图事件到当前活动
                if current_activities:
                    current_activity = current_activities[-1]
                    
                    # 计算时间偏移量
                    activity_start_time = current_activity["start_time"]
                    try:
                        # 将时间戳字符串转换为datetime对象
                        event_dt = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                        activity_dt = datetime.fromisoformat(activity_start_time.replace('Z', '+00:00'))
                        time_offset = (event_dt - activity_dt).total_seconds()
                    except:
                        time_offset = 0
                    
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
        # 简化摘要生成，只保留基本结构
        summary_parts = []
        
        for app_session in app_sessions:
            app_name = app_session["app_name"]
            activities = app_session["activities"]
            
            if not activities:
                continue
                
            # 只记录应用打开
            summary_parts.append(f"打开{app_name}")
            
            # 统计交互次数，不详细描述
            total_interactions = sum(len(activity["interactions"]) for activity in activities)
            if total_interactions > 0:
                summary_parts.append(f"进行了{total_interactions}次交互")
        
        return "，".join(summary_parts) + "。"
    
    def prepare_for_llm(self, session):
        """为LLM准备结构化数据，包含详细的交互信息"""
        if not session:
            return None
            
        # 提取基本会话信息
        context_window = session.get("context_window", {})
        app_sessions = session.get("app_sessions", [])
        search_content = session.get("search_content", [])
        
        # 构建LLM友好的数据结构
        llm_data = {
            "session_info": {
                "start_time": context_window.get("start_time"),
                "end_time": context_window.get("end_time"),
                "duration_minutes": context_window.get("duration_minutes")
            },
            "user_activities": [],
            "screenshots": [],  # 单独的截图列表
            "search_content": search_content  # 添加搜索内容
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
        
        # 按时间戳排序截图
        llm_data["screenshots"].sort(key=lambda x: x.get("timestamp", ""))
        
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
        self.processed_dir = os.path.join(output_dir, "processed")
        self.ensure_output_dirs()
        self.collector = DataCollector(os.path.join(output_dir, "raw"))
        self.parser = DataParser()
        self.processor = DataProcessor()
    
    def ensure_output_dirs(self):
        """确保输出目录存在"""
        for subdir in ["raw", "sessions", "processed"]:
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
        """收集并处理数据"""
        print(f"开始收集数据，将持续 {duration_seconds} 秒...")
        
        # 启动数据收集
        threads = self.collector.start_collection(duration_seconds)
        
        # 等待收集完成
        for thread in threads:
            thread.join()
        
        print("数据收集完成，开始处理...")
        
        # 获取最新的数据文件
        raw_dir = os.path.join(self.output_dir, "raw")
        logcat_files = [f for f in os.listdir(raw_dir) if f.startswith("logcat_")]
        uiautomator_files = [f for f in os.listdir(raw_dir) if f.startswith("uiautomator_")]
        window_files = [f for f in os.listdir(raw_dir) if f.startswith("window_")]
        
        if not logcat_files or not uiautomator_files or not window_files:
            print("错误：缺少必要的数据文件")
            return None
        
        # 获取最新文件
        logcat_file = os.path.join(raw_dir, sorted(logcat_files)[-1])
        uiautomator_file = os.path.join(raw_dir, sorted(uiautomator_files)[-1])
        window_file = os.path.join(raw_dir, sorted(window_files)[-1])
        
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
        
        print(f"解析完成：logcat事件 {len(logcat_events)} 个，uiautomator事件 {len(uiautomator_events)} 个，window事件 {len(window_events)} 个，截图 {len(screenshot_events)} 个")
        
        # 合并和排序事件
        all_events = self.processor.merge_and_sort_events(logcat_events, uiautomator_events, window_events, screenshot_events)
        
        # 分割会话
        sessions = self.processor.segment_into_sessions(all_events)
        print(f"识别出 {len(sessions)} 个会话")
        
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
        
        print(f"处理完成，结果已保存到 {self.output_dir}")
        return processed_sessions
    
    def get_latest_session_for_llm(self):
        """获取最新的会话数据并转换为适合LLM处理的格式"""
        # 获取最新的会话文件
        session_files = [f for f in os.listdir(self.sessions_dir) if f.endswith(".json")]
        if not session_files:
            return None
        
        # 按修改时间排序，获取最新的
        session_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.sessions_dir, x)))
        latest_session_file = os.path.join(self.sessions_dir, session_files[-1])
        
        # 读取会话数据
        with open(latest_session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        
        # 提取会话ID
        session_id = os.path.splitext(os.path.basename(latest_session_file))[0]
        
        # 转换为LLM格式
        llm_data = self.processor.prepare_for_llm(session_data)
        
        # 保存LLM数据
        self.save_llm_data(llm_data, session_id=session_id)
        
        # 如果有截图，复制截图文件到processed目录
        if llm_data.get("screenshots"):
            screenshots_dir = os.path.join(self.processed_dir, "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            for screenshot in llm_data["screenshots"]:
                src_path = screenshot["filepath"]
                if os.path.exists(src_path):
                    filename = os.path.basename(src_path)
                    dst_path = os.path.join(screenshots_dir, filename)
                    shutil.copy2(src_path, dst_path)
                    # 更新路径为相对路径
                    screenshot["filepath"] = f"screenshots/{filename}"
        
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
        analyzer = VLMAnalyzer(api_key=api_key, model=model)
        
        # 分析最新会话
        sessions_dir = "data/processed"
        if not os.path.exists(sessions_dir):
            print(f"错误: 目录 {sessions_dir} 不存在")
            sys.exit(1)
        
        print("开始使用VLM分析最新会话...")
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
                if "detailed_actions" in analysis:
                    print("详细行为:")
                    for action in analysis["detailed_actions"]:
                        print(f"  - {action}")
                if "intent" in analysis:
                    print(f"用户意图: {analysis['intent']}")
                if "confidence" in analysis:
                    print(f"分析置信度: {analysis['confidence']}")
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