# 简化版GraphRAG

一个基于大模型的图数据库系统，支持增量式更新。

## 功能特性

1. **增量式更新**: 支持从初始数据建立数据库，以及后续的增量更新
2. **无需手动分片**: 输入格式特殊，系统自动处理
3. **大模型驱动**: 使用大模型进行实体查找和关系判断
4. **可配置实体类型**: 通过配置文件定义实体类别
5. **提示词模板**: 提示词模板显式放在文件中，易于修改和定制
6. **🆕 两阶段异步处理**: 提取阶段并行处理，合并阶段串行执行，确保性能和质量
7. **🆕 智能合并**: LLM驱动的智能合并，支持去重、对齐和冲突解决
8. **🆕 任务管理**: 完整的任务生命周期管理，支持取消、进度追踪和阶段结果获取

## 项目结构

```
simple_graphrag/
├── config/
│   └── config.yaml          # 配置文件
├── prompts/
│   ├── extract_graph.txt     # 实体和关系提取提示词
│   └── summarize_descriptions.txt  # 描述总结提示词
├── src/
│   ├── models/              # 数据模型
│   │   ├── entity.py        # 实体模型
│   │   ├── relationship.py  # 关系模型
│   │   └── graph.py         # 图模型
│   ├── llm/                 # LLM客户端
│   │   └── client.py        # LLM客户端封装
│   ├── extractors/          # 提取器
│   │   └── extractor.py     # 实体和关系提取器
│   └── database/            # 数据库管理
│       └── manager.py        # 图数据库管理器
├── main.py                  # 主入口示例
└── README.md               # 本文件
```

## 安装依赖

```bash
pip install openai pyyaml networkx
```

## 配置

1. 复制 `config/config.yaml` 并根据需要修改配置
2. 设置环境变量 `MIMO_API_KEY`（或修改配置文件中的API密钥）

### 配置文件说明

- `models`: LLM模型配置
- `entity_types`: 实体类型列表（如：ORGANIZATION, PERSON, GEO, EVENT）
- `prompts`: 提示词模板路径
- `graph_database`: 图数据库存储配置
- `extraction`: 提取相关配置（分隔符、语言等）

## 使用方法

### 启用详细日志

可以通过两种方式启用详细日志：

1. **命令行参数**：

```bash
python main.py --verbose
# 或
python main.py -v
```

1. **环境变量**：

```bash
export SIMPLERAG_VERBOSE=1
python main.py
```

详细日志模式下会显示：

- 输入文本的完整内容
- LLM请求和响应的详细信息
- 实体和关系的解析过程
- 图的合并和更新过程
- 各个阶段的处理统计信息

### 1. 初始化数据库

```python
from pathlib import Path
from src.database.manager import GraphDatabaseManager

# 配置文件路径
config_path = Path("config/config.yaml")

# 初始化管理器
manager = GraphDatabaseManager(config_path)

# 输入文本（格式特殊，不需要手动分片）
initial_text = """
微软公司是一家总部位于美国华盛顿州雷德蒙德的科技公司。
比尔·盖茨是微软公司的联合创始人。
"""

# 初始化数据库
graph = manager.initialize_database(initial_text)
```

### 2. 增量更新数据库

```python
# 新的输入文本
new_text = """
微软公司在2023年发布了Windows 11操作系统。
萨提亚·纳德拉是微软公司的现任CEO。
"""

# 增量更新
updated_graph = manager.incremental_update(new_text)
```

### 3. 查看图数据

```python
# 获取所有实体
entities = graph.get_entities()
for entity in entities:
    print(f"{entity.name} ({entity.entity_type}): {entity.description}")

# 获取所有关系
relationships = graph.get_relationships()
for rel in relationships:
    print(f"{rel.source} -> {rel.target}: {rel.description}")
```

## 设计原则

1. **类型安全**: 使用Python类型提示确保类型安全
2. **代码解耦**: 模块化设计，各组件职责清晰
3. **可扩展性**: 易于添加新的实体类型、关系类型或提取策略
4. **最佳实践**: 遵循Python编码规范和设计模式

## 核心模块说明

### Entity（实体）

- 表示知识图谱中的节点
- 包含名称、类型、描述等信息
- 支持去重和描述更新

### Relationship（关系）

- 表示知识图谱中的边
- 包含源实体、目标实体、描述和强度
- 支持关系强度更新

### Graph（图）

- 管理实体和关系的集合
- 支持图的合并（用于增量更新）
- 支持保存和加载

### GraphExtractor（提取器）

- 使用LLM从文本中提取实体和关系
- 解析LLM响应并转换为结构化数据

### GraphDatabaseManager（管理器）

- 提供初始化和增量更新接口
- 管理配置和LLM客户端
- 处理图的持久化

## 注意事项

1. 确保输入文本格式符合要求（不需要手动分片）
2. 实体类型需要在配置文件中定义
3. LLM API密钥需要正确配置
4. 增量更新时会自动合并重复的实体和关系

## 示例

运行 `main.py` 查看完整示例：

```bash
python main.py
```

## 许可证

MIT License
