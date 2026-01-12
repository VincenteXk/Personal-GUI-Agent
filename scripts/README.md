# 图数据库重新初始化与批量加载脚本

## 概述

本脚本用于重新初始化知识图数据库，并异步加载 `data/eval/profile1` 目录下 7 条用户行为的 VLM（视觉语言模型）分析结果。

**脚本位置**: `scripts/reinit_graph_with_profile.py`

## 功能特性

✅ **备份现有数据**: 自动备份现有图数据库，支持回滚
✅ **批量数据加载**: 异步处理 7 条 VLM 分析记录
✅ **智能数据转换**: 将 VLM JSON 转换为详细的自然语言描述
✅ **并发处理**: 支持 3 个并发任务，平衡性能与资源
✅ **详细日志**: 完整的处理进度和结果统计

## 前置要求

- Python 3.8+
- 项目已配置好 SimpleGraph
- 环境变量已设置（MIMO_API_KEY 等）
- 7 个 VLM JSON 文件位于 `data/eval/profile1/*/analysis/*_vlm.json`

## 快速开始

### 1. 检查设置

在运行主脚本之前，先运行测试脚本验证环境：

```bash
python scripts/test_setup_v2.py
```

预期输出：
```
✓ SimpleGraph 导入成功
✓ 配置文件存在
✓ 找到 7 个 VLM 文件
✓ 确认找到 7 个文件

✅ 所有测试通过！可以运行脚本
```

### 2. 运行脚本

```bash
python scripts/reinit_graph_with_profile.py
```

## 脚本工作流

脚本按以下 5 个步骤执行：

### 步骤 1: 备份现有数据库
- 检查是否存在现有的 `graph.pkl` 文件
- 如果存在，将其重命名为 `graph.pkl.backup`
- 支持通过恢复备份文件来回滚

### 步骤 2: 初始化图数据库
- 创建新的 SimpleGraph 实例
- 配置最大并发数为 3
- 启用智能合并功能

### 步骤 3: 启动任务处理器
- 启动异步任务处理器
- 初始化提取 workers（可并行）和合并 worker（串行）

### 步骤 4: 加载并处理 VLM 数据
- 扫描发现 7 个 VLM JSON 文件
- 对每个文件进行：
  - ✓ 读取 JSON 数据
  - ✓ 提取 session_id 和时间信息
  - ✓ 转换为自然语言（保留所有详情）
  - ✓ 异步提交到图数据库
- 等待所有任务完成

### 步骤 5: 保存并总结
- 保存生成的图数据库
- 输出详细的统计信息
- 显示文件位置和备份信息

## VLM 数据转换规则

脚本将 VLM JSON 数据转换为包含以下内容的自然语言文本：

### 1. 会话时间和应用信息
```
在2026年1月12日11:28，我使用微信应用。
```

### 2. 主要行为描述
```
我在微信中浏览朋友圈和发现页内容。
```

### 3. 详细操作序列（按时间顺序）
```
具体操作包括：启动桌面应用，打开天气应用查看天气，
打开微信进入主界面，进入微信发现页，返回主界面，
进入朋友圈浏览，最后返回桌面。
```

### 4. 聊天详情（如果存在）
```
我与张三在微信中交流，发送了消息"晚上一起吃饭吗？"，
收到回复"好的，6点见"。
```

### 5. 购物详情（如果存在）
```
我查看了"iPhone 15 Pro Max"，价格为9999元，
来自"Apple官方旗舰店"，进行了浏览和收藏操作。
```

### 6. 用户意图
```
我的意图是浏览社交媒体内容，获取信息或娱乐。
```

### 7. 关键观察
```
无文本输入，主要活动在微信浏览朋友圈和发现页。
```

## 输出示例

脚本运行时会输出类似以下内容：

```
============================================================
图数据库重新初始化与批量加载
============================================================

[步骤 1/5] 备份现有数据库...
✓ 已备份图数据库到: .../graph.pkl.backup

[步骤 2/5] 初始化图数据库...
✓ 图数据库初始化完成

[步骤 3/5] 启动任务处理器...
启动 3 个提取workers和1个合并worker...

[步骤 4/5] 加载并处理 VLM 数据...
✓ 找到 7 个 VLM 分析文件
  1. 20260112_112849_5cd5_vlm.json
  2. 20260112_113122_af03_vlm.json
  ...

[1/7] 处理: 20260112_112849_5cd5_vlm.json
  ✓ 转换成功 (文本长度: 425 字符)
  ✓ 任务已提交: abc12345...
...

已提交所有任务，等待处理完成...
已提交 7 个任务
✓ 所有任务处理完成! (完成: 7, 失败: 0)

[步骤 5/5] 保存数据库并输出总结...
保存图数据库...
✓ 图数据库已保存到: .../graph.pkl

============================================================
处理完成总结
============================================================
总处理文件数: 7
成功提交任务数: 7
失败数: 0

图数据库统计信息:
  - 实体数: 245
  - 关系数: 189
  - 类数: 12

文件位置:
  - 图数据库: .../graph.pkl
  - 可视化: .../graph_visualization.html
  - 备份: .../graph.pkl.backup
============================================================
```

## 文件位置

### 输入文件
- **VLM 数据**: `data/eval/profile1/*/analysis/*_vlm.json` (7 个文件)
- **配置文件**: `graphrag/simple_graphrag/config/config.yaml`

### 输出文件
- **图数据库**: `graphrag/simple_graphrag/output/graph.pkl`
- **可视化**: `graphrag/simple_graphrag/output/graph_visualization.html`
- **备份**: `graphrag/simple_graphrag/output/graph.pkl.backup`

## 并发配置

脚本使用以下并发策略：

- **提取 Workers**: 3 个（并行）
  - 并行处理 VLM 数据的提取和转换
  - 支持最多 3 个任务同时运行

- **合并 Worker**: 1 个（串行）
  - 使用 LLM 进行智能合并
  - 保证数据一致性

这种两阶段架构（并行提取 + 串行合并）在性能和稳定性之间取得了平衡。

## 错误处理

脚本包含以下错误处理机制：

1. **VLM 文件读取失败**: 自动跳过，继续处理下一个文件
2. **数据转换失败**: 记录错误并跳过
3. **任务提交失败**: 记录错误并统计失败数
4. **任务处理失败**: 记录失败并继续

所有错误都会被记录到日志中，脚本最后输出失败统计。

## 故障排除

### 问题：找不到 VLM 文件
**解决方案**: 检查 `data/eval/profile1` 目录是否存在，以及 VLM 文件位置是否正确。

### 问题：导入错误
**解决方案**: 确保已安装所有依赖，运行 `python scripts/test_setup_v2.py` 检查环境。

### 问题：任务提交失败
**解决方案**: 检查环境变量（如 MIMO_API_KEY）是否正确设置。

### 问题：内存不足
**解决方案**: 减少并发数（修改脚本中的 `max_concurrent_tasks=3`）。

## 回滚步骤

如果需要恢复之前的图数据库：

```bash
# 1. 备份当前生成的数据库
mv graphrag/simple_graphrag/output/graph.pkl graphrag/simple_graphrag/output/graph.pkl.new

# 2. 恢复备份
mv graphrag/simple_graphrag/output/graph.pkl.backup graphrag/simple_graphrag/output/graph.pkl
```

## 脚本详细信息

### 主要类

#### `VLMDataProcessor`
- **功能**: 处理 VLM JSON 数据转换
- **关键方法**:
  - `parse_session_time()`: 从 session_id 提取时间
  - `vlm_to_text()`: 将 VLM 数据转换为自然语言

#### `GraphDatabaseManager`
- **功能**: 管理图数据库的初始化和操作
- **关键方法**:
  - `backup_existing_database()`: 备份现有数据库
  - `initialize_database()`: 创建新的 SimpleGraph 实例
  - `get_statistics()`: 获取图数据库统计信息

#### `ProfileDataLoader`
- **功能**: 加载 VLM 分析文件
- **关键方法**:
  - `discover_vlm_files()`: 扫描发现 VLM 文件
  - `load_vlm_file()`: 读取单个 VLM 文件
  - `extract_session_id()`: 从文件名提取 session_id

### 异步函数

#### `process_all_vlm_files()`
- 主要处理流程，负责遍历和处理所有 VLM 文件

#### `wait_for_all_tasks()`
- 等待所有任务完成，定期输出进度

#### `save_and_summarize()`
- 保存图数据库并输出最终统计

## 性能参考

基于 7 条 VLM 记录的处理：

- **总处理时间**: 约 2-5 分钟（取决于网络和 LLM 速度）
- **单条记录处理时间**: 约 20-45 秒
- **生成的实体数**: 200-300 个
- **生成的关系数**: 150-250 个

## 扩展使用

### 处理其他 Profile
修改脚本中的 `ProfileDataLoader()` 调用：

```python
# 处理 profile2
loader = ProfileDataLoader(profile_path="data/eval/profile2")
```

### 修改并发数
编辑 `GraphDatabaseManager.initialize_database()` 中的：

```python
max_concurrent_tasks=5  # 改为 5 个并发
```

### 禁用智能合并
```python
enable_smart_merge=False  # 改为 False
```

## 注意事项

⚠️ **重要**:
- 脚本会覆盖现有的图数据库，请提前备份
- 首次运行会自动创建备份，可以通过恢复备份回滚
- 需要有效的 API 密钥来处理 LLM 任务
- 网络连接稳定对脚本成功很重要

## 许可证

此脚本是项目的一部分，遵循项目的许可证。

## 支持

如有问题或建议，请查看脚本的日志输出或联系开发团队。
