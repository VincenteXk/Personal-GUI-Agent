# 新会话文件组织系统 - 快速开始指南

## 什么改变了？

旧结构：文件分散在 `data/raw/`, `data/sessions/`, `data/processed/`, `data/processed/analysis/` 等多个目录

新结构：一个会话 = 一个文件夹 (`data/sessions/20260110_153045_a3f2/`)

## 核心改进

| 方面 | 旧格式 | 新格式 |
|------|--------|--------|
| 会话ID | `session_2026-01-10T00-09-16.536000Z.json` | `20260110_000916_536a` |
| 截图名 | `screenshot_20260110_000947_779.png` | `000947_779.png` (相对时间) |
| 文件结构 | 分散在多个目录 | 集中在会话文件夹 |
| 查询方式 | 扫描文件系统 | 查询 master_index.json |
| 数据继承 | 不清晰 | raw → processed → analysis |

## 文件夹结构示例

```
data/sessions/20260110_153045_a3f2/
├── metadata.json                     # 会话信息
├── raw/
│   ├── logcat.log
│   ├── uiautomator.log
│   └── window.log
├── screenshots/
│   ├── 000947_779.png
│   └── 000953_125.png
├── processed/
│   ├── events.json                   # 解析的事件
│   └── session_summary.json          # LLM就绪格式
└── analysis/
    └── vlm_analysis.json             # VLM分析结果

data/master_index.json                # 全局索引
```

## 常见操作

### 1. 检查新系统是否工作

```bash
python scripts/test_session_organization.py
```

### 2. 迁移旧数据（可选）

```bash
python scripts/migrate_sessions.py
```

按照提示操作，旧数据会被备份到 `data/archive/`

### 3. 手动查询会话

```python
from src.learning.utils import (
    get_recent_sessions,
    load_session_metadata,
    query_sessions_by_timestamp
)

# 获取最近的5个会话
recent = get_recent_sessions("data", n=5)
for session in recent:
    print(f"{session['session_id']}: {session['start_time']}")

# 按时间戳查询（查找包含该时刻的会话）
session = query_sessions_by_timestamp("data", "2026-01-10T15:35:00Z")
if session:
    print(f"找到会话: {session['session_id']}")

# 加载会话详细信息
metadata = load_session_metadata("data", "20260110_153045_a3f2")
print(f"会话时长: {metadata['duration_seconds']} 秒")
print(f"事件数: {metadata['statistics']['total_events']}")
```

### 4. 查看全局索引

```bash
cat data/master_index.json | python -m json.tool | less
```

## 对现有代码的影响

### BehaviorAnalyzer
无需修改，自动使用新结构：
```python
analyzer = BehaviorAnalyzer()
analyzer.collect_and_process(60)  # 自动创建新格式会话
```

### VLMAnalyzer
自动支持相对路径：
```python
vlm = VLMAnalyzer(api_key=key)
# 自动处理 "screenshots/000947_779.png" 这样的相对路径
vlm.analyze_session_with_screenshots(session_data)
```

### 自定义代码
如果你有自定义的代码访问会话数据，可能需要更新：

**旧方式：**
```python
with open("data/sessions/session_2026-01-10T00-09-16.536000Z.json") as f:
    data = json.load(f)
```

**新方式：**
```python
from src.learning.utils import load_session_metadata, load_session_summary

# 方式1：使用工具函数
metadata = load_session_metadata("data", "20260110_000916_536a")
summary = load_session_summary("data", "20260110_000916_536a")

# 方式2：直接访问文件（与旧方式兼容）
session_folder = "data/sessions/20260110_000916_536a"
with open(f"{session_folder}/processed/session_summary.json") as f:
    data = json.load(f)
```

## 数据保存位置对照

| 数据类型 | 旧位置 | 新位置 |
|---------|--------|--------|
| 原始logcat | `data/raw/logcat_*.log` | `data/sessions/<id>/raw/logcat.log` |
| UIAutomator事件 | `data/raw/uiautomator_*.log` | `data/sessions/<id>/raw/uiautomator.log` |
| 窗口事件 | `data/raw/window_*.log` | `data/sessions/<id>/raw/window.log` |
| 截图 | `data/screenshots/screenshot_*.png` | `data/sessions/<id>/screenshots/*.png` |
| 会话JSON | `data/sessions/session_*.json` | `data/sessions/<id>/processed/events.json` |
| LLM数据 | `data/processed/session_*_llm.json` | `data/sessions/<id>/processed/session_summary.json` |
| VLM分析 | `data/processed/analysis/*.json` | `data/sessions/<id>/analysis/vlm_analysis.json` |
| 索引 | `data/index.json` | `data/master_index.json` |

## 性能提升

- ✅ **查询速度快** - 不再扫描文件系统，直接查询JSON索引
- ✅ **存储清晰** - 每个会话独立，易于备份和归档
- ✅ **可扩展** - 支持轻松切换到按月份分层结构

## 故障排除

### 问题：master_index.json 损坏或丢失

**解决：** 重建索引
```python
from src.learning.utils import rebuild_master_index
rebuild_master_index("data")
```

### 问题：旧会话找不到

**解决：** 运行迁移脚本
```bash
python scripts/migrate_sessions.py
```

### 问题：新会话未出现在索引中

**解决：** 手动更新索引
```python
from src.learning.utils import get_session_by_id, update_master_index

# 从metadata.json读取元数据
metadata = load_session_metadata("data", "20260110_153045_a3f2")

# 更新索引
update_master_index("data", "20260110_153045_a3f2", metadata)
```

## 需要帮助？

- 查看 [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) 获取完整技术细节
- 查看 [README计划文件](../.claude/plans/) 获取设计文档
- 运行测试脚本了解系统工作原理：`python scripts/test_session_organization.py`

---

**祝你使用愉快！** 🚀
