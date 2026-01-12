"""
工具函数模块

提供学习模式模块中使用的通用工具函数。
"""

import os
import json
import shutil
import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import re


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

import json
import re

def extract_json_from_llm_response(raw_response: str) -> dict:
    """
    从LLM/VLM响应中提取JSON，健壮处理多种格式和错误

    策略:
    1. 直接JSON解析
    2. 提取markdown代码块 (```json ... ```)
    3. 括号匹配查找首个{...}对象
    4. 修复常见JSON错误（未闭合引号、单引号等）
    5. 字段补全（确保必要字段存在）

    Args:
        raw_response: LLM的原始响应文本

    Returns:
        提取的JSON对象

    Raises:
        ValueError: 无法从响应中提取有效的JSON
    """
    import re
    import json

    # 去除首尾空白
    response = raw_response.strip()

    # 尝试1：直接解析（如果已经是纯JSON）
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 尝试2：提取markdown代码块中的JSON
    code_block_patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
    ]

    for pattern in code_block_patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

    # 尝试3：查找第一个{...}对象
    brace_start = response.find('{')
    if brace_start != -1:
        brace_count = 0
        for i in range(brace_start, len(response)):
            if response[i] == '{':
                brace_count += 1
            elif response[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = response[brace_start:i+1]

                    # 尝试直接解析
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # 尝试修复常见错误
                        fixed_json = _fix_json_errors(json_str)
                        try:
                            return json.loads(fixed_json)
                        except json.JSONDecodeError:
                            pass

    raise ValueError("无法从响应中提取有效的JSON")


def _fix_json_errors(json_str: str) -> str:
    """
    修复常见的JSON格式错误

    处理以下问题:
    - 单引号替换为双引号
    - 尾部逗号
    - 未闭合的字符串
    - 控制字符转义

    Args:
        json_str: 不完全有效的JSON字符串

    Returns:
        修复后的JSON字符串
    """
    import re

    # 1. 将单引号中的内容转换为双引号（但要保护已存在的转义序列）
    # 简单方法：替换不在双引号内的单引号
    result = []
    in_double_quote = False
    escape_next = False

    for i, char in enumerate(json_str):
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            in_double_quote = not in_double_quote
            result.append(char)
        elif char == "'" and not in_double_quote:
            # 在双引号外的单引号替换为双引号
            result.append('"')
        else:
            result.append(char)

    json_str = ''.join(result)

    # 2. 移除尾部逗号（在]或}之前）
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

    # 3. 修复没有引号的字段名（如果有明显的模式）
    # 匹配: fieldname: 这样的模式并添加引号
    json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)

    # 4. 修复特殊字符（如未转义的换行符）
    json_str = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

    return json_str


# ==================== 新的会话文件组织系统 ====================

def generate_session_id(timestamp_iso: str = None) -> str:
    """生成新格式的会话ID: YYYYMMDD_HHMMSS_<4-hex>

    Args:
        timestamp_iso: ISO 8601格式的时间戳，如果为None则使用当前时间

    Returns:
        格式化的会话ID，例如: 20260110_153045_a3f2
    """
    try:
        if timestamp_iso:
            # 处理 ISO 8601 格式：去掉Z后缀并解析
            if isinstance(timestamp_iso, str):
                dt = datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00'))
            else:
                dt = timestamp_iso
        else:
            dt = datetime.now()
    except (ValueError, TypeError):
        dt = datetime.now()

    # 生成 YYYYMMDD_HHMMSS 部分
    timestamp_str = dt.strftime('%Y%m%d_%H%M%S')
    # 生成 4 字符的十六进制随机ID
    short_id = secrets.token_hex(2)  # 2字节 = 4个十六进制字符
    return f"{timestamp_str}_{short_id}"


def create_session_folder(base_dir: str, session_id: str) -> str:
    """为会话创建完整的文件夹结构

    Args:
        base_dir: 数据根目录，例如 'data'
        session_id: 会话ID，例如 '20260110_153045_a3f2'

    Returns:
        创建的会话文件夹路径
    """
    session_folder = os.path.join(base_dir, "sessions", session_id)

    # 创建所有子目录
    subdirs = ["raw", "screenshots", "processed", "analysis"]
    for subdir in subdirs:
        subdir_path = os.path.join(session_folder, subdir)
        ensure_dir_exists(subdir_path)

    return session_folder


def create_session_metadata(
    session_id: str,
    start_time: str,
    end_time: str = None,
    status: str = "in_progress",
    statistics: Dict[str, Any] = None
) -> Dict[str, Any]:
    """创建会话元数据对象

    Args:
        session_id: 会话ID
        start_time: 开始时间（ISO 8601格式）
        end_time: 结束时间（ISO 8601格式）
        status: 会话状态 ('in_progress', 'completed', 'failed')
        statistics: 统计信息字典

    Returns:
        会话元数据字典
    """
    metadata = {
        "session_id": session_id,
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "data_sources": {
            "logcat": "raw/logcat.log",
            "uiautomator": "raw/uiautomator.log",
            "window": "raw/window.log"
        },
        "statistics": statistics or {
            "total_events": 0,
            "screenshot_count": 0,
            "app_sessions": 0
        },
        "tags": []
    }

    # 如果有end_time，计算duration
    if end_time:
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            duration = (end - start).total_seconds()
            metadata["duration_seconds"] = duration
        except (ValueError, TypeError):
            pass

    return metadata


def update_master_index(
    base_dir: str,
    session_id: str,
    metadata: Dict[str, Any],
    update_existing: bool = True
) -> None:
    """更新或创建全局索引文件master_index.json

    Args:
        base_dir: 数据根目录
        session_id: 会话ID
        metadata: 会话元数据字典
        update_existing: 如果会话已存在是否更新
    """
    index_path = os.path.join(base_dir, "master_index.json")

    # 加载或创建索引
    if os.path.exists(index_path):
        index = load_json(index_path)
    else:
        index = {
            "version": "2.0",
            "last_updated": datetime.now().isoformat() + "Z",
            "total_sessions": 0,
            "index_entries": []
        }

    # 查找是否已存在该会话
    entry_index = None
    for i, entry in enumerate(index["index_entries"]):
        if entry.get("session_id") == session_id:
            entry_index = i
            break

    # 构建索引条目
    entry = {
        "session_id": session_id,
        "start_time": metadata.get("start_time"),
        "end_time": metadata.get("end_time"),
        "duration_seconds": metadata.get("duration_seconds"),
        "folder_path": f"sessions/{session_id}",
        "status": metadata.get("status", "in_progress"),
        "statistics": metadata.get("statistics", {}),
        "tags": metadata.get("tags", []),
        "has_analysis": os.path.exists(
            os.path.join(base_dir, "sessions", session_id, "analysis", "vlm_analysis.json")
        )
    }

    # 更新或添加条目
    if entry_index is not None:
        if update_existing:
            index["index_entries"][entry_index] = entry
    else:
        index["index_entries"].append(entry)

    # 更新索引元数据
    index["last_updated"] = datetime.now().isoformat() + "Z"
    index["total_sessions"] = len(index["index_entries"])

    # 保存索引
    save_json(index, index_path)


def query_sessions_by_date_range(
    base_dir: str,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    """按日期范围查询会话

    Args:
        base_dir: 数据根目录
        start_date: 开始日期（ISO 8601格式）
        end_date: 结束日期（ISO 8601格式）

    Returns:
        匹配的会话条目列表
    """
    index_path = os.path.join(base_dir, "master_index.json")

    if not os.path.exists(index_path):
        return []

    index = load_json(index_path)
    if not index:
        return []

    results = []

    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        for entry in index.get("index_entries", []):
            try:
                session_time = datetime.fromisoformat(
                    entry.get("start_time", "").replace('Z', '+00:00')
                )
                if start <= session_time <= end:
                    results.append(entry)
            except (ValueError, TypeError):
                continue
    except (ValueError, TypeError):
        pass

    return results


def query_sessions_by_timestamp(
    base_dir: str,
    timestamp: str
) -> Optional[Dict[str, Any]]:
    """查找包含指定时间戳的会话

    Args:
        base_dir: 数据根目录
        timestamp: ISO 8601格式的时间戳

    Returns:
        匹配的会话条目，或None
    """
    if not timestamp:
        return None

    index_path = os.path.join(base_dir, "master_index.json")

    if not os.path.exists(index_path):
        return None

    index = load_json(index_path)
    if not index:
        return None

    try:
        target_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        for entry in index.get("index_entries", []):
            try:
                start_time_str = entry.get("start_time", "")
                end_time_str = entry.get("end_time", "")

                if not start_time_str:
                    continue

                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))

                # 如果有end_time，检查时间戳是否在范围内
                if end_time_str:
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    if start_time <= target_time <= end_time:
                        return entry
                else:
                    # 如果没有end_time，只检查是否>= start_time
                    if target_time >= start_time:
                        return entry
            except (ValueError, TypeError, AttributeError):
                continue
    except (ValueError, TypeError):
        pass

    return None


def get_recent_sessions(base_dir: str, n: int = 10) -> List[Dict[str, Any]]:
    """获取最近的N个会话

    Args:
        base_dir: 数据根目录
        n: 要获取的会话数量

    Returns:
        最近的会话条目列表（按时间降序排列）
    """
    index_path = os.path.join(base_dir, "master_index.json")

    if not os.path.exists(index_path):
        return []

    index = load_json(index_path)
    if not index:
        return []

    entries = index.get("index_entries", [])

    # 按start_time降序排列
    try:
        sorted_entries = sorted(
            entries,
            key=lambda x: datetime.fromisoformat(
                x.get("start_time", "").replace('Z', '+00:00')
            ),
            reverse=True
        )
    except (ValueError, TypeError):
        sorted_entries = entries

    return sorted_entries[:n]


def get_session_by_id(base_dir: str, session_id: str) -> Optional[Dict[str, Any]]:
    """从索引中获取指定会话的条目

    Args:
        base_dir: 数据根目录
        session_id: 会话ID

    Returns:
        会话条目，或None
    """
    index_path = os.path.join(base_dir, "master_index.json")

    if not os.path.exists(index_path):
        return None

    index = load_json(index_path)
    if not index:
        return None

    for entry in index.get("index_entries", []):
        if entry.get("session_id") == session_id:
            return entry

    return None


def load_session_metadata(base_dir: str, session_id: str) -> Optional[Dict[str, Any]]:
    """加载会话的metadata.json文件

    Args:
        base_dir: 数据根目录
        session_id: 会话ID

    Returns:
        元数据字典，或None
    """
    metadata_path = os.path.join(
        base_dir, "sessions", session_id, "metadata.json"
    )
    return load_json(metadata_path)


def load_session_events(base_dir: str, session_id: str) -> Optional[Dict[str, Any]]:
    """加载会话的events.json文件（处理后的事件）

    Args:
        base_dir: 数据根目录
        session_id: 会话ID

    Returns:
        事件数据，或None
    """
    events_path = os.path.join(
        base_dir, "sessions", session_id, "processed", "events.json"
    )
    return load_json(events_path)


def load_session_summary(base_dir: str, session_id: str) -> Optional[Dict[str, Any]]:
    """加载会话的session_summary.json文件（LLM就绪格式）

    Args:
        base_dir: 数据根目录
        session_id: 会话ID

    Returns:
        会话摘要，或None
    """
    summary_path = os.path.join(
        base_dir, "sessions", session_id, "processed", "session_summary.json"
    )
    return load_json(summary_path)


def load_session_analysis(base_dir: str, session_id: str) -> Optional[Dict[str, Any]]:
    """加载会话的vlm_analysis.json文件（VLM分析结果）

    Args:
        base_dir: 数据根目录
        session_id: 会话ID

    Returns:
        分析结果，或None
    """
    analysis_path = os.path.join(
        base_dir, "sessions", session_id, "analysis", "vlm_analysis.json"
    )
    return load_json(analysis_path)


def list_all_sessions(base_dir: str) -> List[str]:
    """列出所有会话的ID

    Args:
        base_dir: 数据根目录

    Returns:
        会话ID列表
    """
    sessions_dir = os.path.join(base_dir, "sessions")

    if not os.path.exists(sessions_dir):
        return []

    sessions = []
    for item in os.listdir(sessions_dir):
        item_path = os.path.join(sessions_dir, item)
        # 检查是否为目录且有metadata.json
        if os.path.isdir(item_path):
            metadata_path = os.path.join(item_path, "metadata.json")
            if os.path.exists(metadata_path):
                sessions.append(item)

    return sorted(sessions, reverse=True)  # 最新的在前


def rebuild_master_index(base_dir: str) -> None:
    """从文件系统重建master_index.json

    当master_index.json损坏或丢失时使用此函数

    Args:
        base_dir: 数据根目录
    """
    sessions_dir = os.path.join(base_dir, "sessions")

    index = {
        "version": "2.0",
        "last_updated": datetime.now().isoformat() + "Z",
        "total_sessions": 0,
        "index_entries": []
    }

    if not os.path.exists(sessions_dir):
        save_json(index, os.path.join(base_dir, "master_index.json"))
        return

    # 扫描所有会话文件夹
    for session_id in os.listdir(sessions_dir):
        session_folder = os.path.join(sessions_dir, session_id)
        if not os.path.isdir(session_folder):
            continue

        metadata_path = os.path.join(session_folder, "metadata.json")
        if not os.path.exists(metadata_path):
            continue

        metadata = load_json(metadata_path)
        if not metadata:
            continue

        # 构建索引条目
        entry = {
            "session_id": session_id,
            "start_time": metadata.get("start_time"),
            "end_time": metadata.get("end_time"),
            "duration_seconds": metadata.get("duration_seconds"),
            "folder_path": f"sessions/{session_id}",
            "status": metadata.get("status", "unknown"),
            "statistics": metadata.get("statistics", {}),
            "tags": metadata.get("tags", []),
            "has_analysis": os.path.exists(
                os.path.join(session_folder, "analysis", "vlm_analysis.json")
            )
        }

        index["index_entries"].append(entry)

    # 按时间排序
    try:
        index["index_entries"].sort(
            key=lambda x: datetime.fromisoformat(
                x.get("start_time", "").replace('Z', '+00:00')
            ),
            reverse=True
        )
    except (ValueError, TypeError):
        pass

    index["total_sessions"] = len(index["index_entries"])
    index["last_updated"] = datetime.now().isoformat() + "Z"

    save_json(index, os.path.join(base_dir, "master_index.json"))


def detect_session_format(session_path: str) -> str:
    """检测会话数据的格式版本

    Args:
        session_path: 会话路径或会话ID

    Returns:
        版本标识: 'v2' (新格式-文件夹), 'v1' (旧格式-JSON文件), 或 'unknown'
    """
    if os.path.isdir(session_path):
        # 如果是目录，检查是否为新格式
        if os.path.exists(os.path.join(session_path, "metadata.json")):
            return "v2"
        return "v2"  # 仍作为v2处理
    elif session_path.endswith(".json"):
        return "v1"

    return "unknown"