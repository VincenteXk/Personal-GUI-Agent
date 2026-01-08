"""
工具函数模块

提供学习模式模块中使用的通用工具函数。
"""

import os
import json
import time
import shutil
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional


def ensure_dir_exists(dir_path: str) -> None:
    """确保目录存在，不存在则创建
    
    Args:
        dir_path: 目录路径
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    ensure_dir_exists(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """从JSON文件加载数据
    
    Args:
        file_path: 文件路径
        
    Returns:
        加载的数据，失败返回None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_timestamp_str() -> str:
    """获取当前时间戳字符串
    
    Returns:
        格式化的时间戳字符串
    """
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def format_duration(seconds: float) -> str:
    """格式化时长为可读字符串
    
    Args:
        seconds: 时长（秒）
        
    Returns:
        格式化的时长字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def copy_file(src: str, dst: str) -> bool:
    """复制文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
        
    Returns:
        是否成功
    """
    try:
        ensure_dir_exists(os.path.dirname(dst))
        shutil.copy2(src, dst)
        return True
    except Exception:
        return False


def list_files_by_extension(dir_path: str, extension: str) -> List[str]:
    """列出目录中指定扩展名的所有文件
    
    Args:
        dir_path: 目录路径
        extension: 文件扩展名（如'.json'）
        
    Returns:
        文件路径列表
    """
    if not os.path.exists(dir_path):
        return []
    
    files = []
    for filename in os.listdir(dir_path):
        if filename.endswith(extension):
            files.append(os.path.join(dir_path, filename))
    
    return files


def get_latest_file(dir_path: str, extension: str = None) -> Optional[str]:
    """获取目录中最新修改的文件
    
    Args:
        dir_path: 目录路径
        extension: 文件扩展名（可选）
        
    Returns:
        最新文件路径，没有则返回None
    """
    if not os.path.exists(dir_path):
        return None
    
    files = []
    for filename in os.listdir(dir_path):
        if extension is None or filename.endswith(extension):
            file_path = os.path.join(dir_path, filename)
            files.append((file_path, os.path.getmtime(file_path)))
    
    if not files:
        return None
    
    # 按修改时间排序，返回最新的
    files.sort(key=lambda x: x[1], reverse=True)
    return files[0][0]


def is_valid_image_file(file_path: str) -> bool:
    """检查是否为有效的图片文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否为有效图片
    """
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def truncate_string(s: str, max_length: int = 100) -> str:
    """截断字符串到指定长度
    
    Args:
        s: 原字符串
        max_length: 最大长度
        
    Returns:
        截断后的字符串
    """
    if len(s) <= max_length:
        return s
    return s[:max_length-3] + "..."


def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """安全获取字典值

    Args:
        dictionary: 字典
        key: 键名
        default: 默认值

    Returns:
        字典值或默认值
    """
    try:
        return dictionary.get(key, default)
    except AttributeError:
        return default


def run_async(coro):
    """在同步上下文中运行异步协程

    Args:
        coro: 异步协程对象

    Returns:
        协程的执行结果
    """
    try:
        # 尝试获取当前事件循环
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 如果没有运行的事件循环，创建一个新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
