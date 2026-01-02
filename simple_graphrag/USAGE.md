# 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

设置你的API密钥：

```bash
export MIMO_API_KEY="your-api-key-here"
```

或者在Windows PowerShell中：

```powershell
$env:MIMO_API_KEY="your-api-key-here"
```

### 3. 运行示例

**普通模式**（只显示关键信息）：

```bash
python main.py
```

**详细模式**（显示所有处理细节）：

```bash
python main.py --verbose
# 或
python main.py -v
```

也可以通过环境变量启用详细模式：

```bash
export SIMPLERAG_VERBOSE=1
python main.py
```

详细模式会显示：

- 输入文本的完整内容
- LLM的请求和响应详情
- 实体和关系的解析过程
- 图的合并和更新统计
- 各个阶段的处理日志

## 基本用法

### 初始化数据库

```python
from pathlib import Path
from src.database.manager import GraphDatabaseManager

# 创建管理器
config_path = Path("config/config.yaml")
manager = GraphDatabaseManager(config_path)

# 输入文本（不需要手动分片）
text = """
微软公司是一家总部位于美国华盛顿州雷德蒙德的科技公司。
比尔·盖茨是微软公司的联合创始人。
萨提亚·纳德拉是微软公司的现任CEO。
"""

# 初始化数据库
graph = manager.initialize_database(text)
```

### 增量更新

```python
# 新的文本数据
new_text = """
微软公司在2023年发布了Windows 11操作系统。
微软公司还开发了Azure云服务平台。
"""

# 增量更新
updated_graph = manager.incremental_update(new_text)
```

### 查询图数据

```python
# 获取所有实体
entities = graph.get_entities()
for entity in entities:
    print(f"{entity.name} ({entity.entity_type})")
    print(f"  描述: {entity.description}")

# 获取特定实体的关系
relationships = graph.get_relationships("微软公司")
for rel in relationships:
    print(f"{rel.source} -> {rel.target}")
    print(f"  关系: {rel.description}")
    print(f"  强度: {rel.strength}")
```

### 导出为NetworkX图

```python
import networkx as nx

# 转换为NetworkX图
G = graph.to_networkx()

# 可以用于可视化或其他图分析
print(f"节点数: {G.number_of_nodes()}")
print(f"边数: {G.number_of_edges()}")
```

## 自定义配置

### 修改实体类型

编辑 `config/config.yaml`：

```yaml
entity_types:
  - ORGANIZATION
  - PERSON
  - GEO
  - EVENT
  - PRODUCT  # 添加新类型
```

### 自定义提示词

编辑 `prompts/extract_graph.txt` 来自定义提取提示词。

提示词模板支持以下变量：

- `{entity_types}`: 实体类型列表
- `{input_text}`: 输入文本
- `{tuple_delimiter}`: 元组分隔符
- `{record_delimiter}`: 记录分隔符
- `{completion_delimiter}`: 完成标记
- `{language}`: 输出语言

### 修改存储路径

在 `config/config.yaml` 中修改：

```yaml
graph_database:
  storage_path: "output/graph.pkl"  # 修改为你想要的路径
```

## 注意事项

1. **输入格式**: 输入文本不需要手动分片，系统会自动处理
2. **实体去重**: 相同名称和类型的实体会自动合并
3. **关系更新**: 如果关系已存在，会更新关系强度
4. **API限制**: 注意LLM API的调用频率限制

## 故障排除

### API密钥错误

确保环境变量 `MIMO_API_KEY` 已正确设置。

### 提示词文件未找到

检查 `config/config.yaml` 中的提示词路径是否正确。

### 解析错误

如果LLM返回的格式不符合预期，检查：

1. 提示词模板是否正确
2. 分隔符配置是否匹配
3. LLM模型是否支持JSON格式输出
