"""
工具模块
提供公共功能，减少代码重复
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime


def ensure_dir_exists(dir_path: str) -> None:
    """确保目录存在，不存在则创建"""
    os.makedirs(dir_path, exist_ok=True)


def get_latest_file(directory: str, pattern: str = "*.json") -> Optional[str]:
    """
    获取目录中最新修改的文件
    
    Args:
        directory: 目录路径
        pattern: 文件模式，如"*.json"
        
    Returns:
        最新文件的完整路径，如果没有找到则返回None
    """
    if not os.path.exists(directory):
        return None
    
    import glob
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None
    
    # 按修改时间排序，获取最新的
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1]


def save_json(data: Any, file_path: str, indent: int = 2) -> bool:
    """
    保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
        indent: JSON缩进
        
    Returns:
        是否保存成功
    """
    try:
        ensure_dir_exists(os.path.dirname(file_path))
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存JSON文件失败: {e}")
        return False


def load_json(file_path: str) -> Optional[Any]:
    """
    从JSON文件加载数据
    
    Args:
        file_path: 文件路径
        
    Returns:
        加载的数据，失败则返回None
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON文件失败: {e}")
        return None


def format_timestamp(timestamp: str) -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: 原始时间戳
        
    Returns:
        格式化后的时间戳
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp


def print_summary(title: str, items: List[Dict[str, Any]], key_field: str, count_field: str = "count") -> None:
    """
    打印摘要信息
    
    Args:
        title: 标题
        items: 项目列表
        key_field: 键字段名
        count_field: 计数字段名
    """
    print(f"\n{title}:")
    for item in items:
        key = item.get(key_field, "未知")
        count = item.get(count_field, 0)
        print(f"  {key}: {count}")


class Timer:
    """计时器工具类"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
    
    def stop(self):
        """停止计时"""
        self.end_time = time.time()
    
    def elapsed(self) -> float:
        """获取经过的时间（秒）"""
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time
    
    def elapsed_str(self) -> str:
        """获取格式化的经过时间"""
        elapsed = self.elapsed()
        if elapsed < 60:
            return f"{elapsed:.1f}秒"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes}分{seconds}秒"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            return f"{hours}小时{minutes}分{seconds}秒"


def validate_file_path(file_path: str, extensions: List[str] = None) -> bool:
    """
    验证文件路径
    
    Args:
        file_path: 文件路径
        extensions: 允许的扩展名列表，如['.json', '.txt']
        
    Returns:
        是否有效
    """
    if not os.path.exists(file_path):
        return False
    
    if not os.path.isfile(file_path):
        return False
    
    if extensions:
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in extensions:
            return False
    
    return True


def get_file_size_str(file_path: str) -> str:
    """
    获取文件大小的字符串表示

    Args:
        file_path: 文件路径

    Returns:
        文件大小字符串
    """
    try:
        size = os.path.getsize(file_path)
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024*1024):.1f}MB"
        else:
            return f"{size/(1024*1024*1024):.1f}GB"
    except:
        return "未知"


def run_async(coro):
    """
    安全地运行异步协程，兼容已有循环和新循环

    Args:
        coro: 异步协程对象

    Returns:
        协程执行结果

    Raises:
        RuntimeError: 如果检测到运行中的事件循环但未安装 nest_asyncio
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 如果已经有运行的循环（例如在 Jupyter 或 FastAPI 中）
        try:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        except ImportError:
            raise RuntimeError(
                "检测到已运行的事件循环，但未安装 nest_asyncio。"
                "请运行: pip install nest_asyncio"
            )
    else:
        return asyncio.run(coro)