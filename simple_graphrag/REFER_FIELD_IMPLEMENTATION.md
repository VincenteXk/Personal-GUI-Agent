# Refer 字段实现说明

## 概述

为关系（Relationship）添加了 `refer` 字段，用于表示除了主要的 source 和 target 之外，还有哪些其他实体参与了这个关系。这使得知识图谱能够更完整地表达多方参与的复杂关系。

## 使用场景

### 场景 1：通过平台分享内容

**文本**: "我通过微信把关于AI绘图的视频分享给小明"

**传统表达（不够完整）**:

- 关系: `我 -> 小明`
- 描述: "我分享视频给小明"
- 问题: 丢失了"通过微信"和"视频内容"这两个关键信息

**使用 Refer 字段（完整表达）**:

- 关系: `我 -> 小明:可联系人`
- 描述: "我把视频分享给小明"
- Refer: `["微信:交流平台", "关于AI绘图的视频"]`
- 优势: 完整捕获了 WHO（我）shared WHAT（视频）to WHOM（小明）through WHERE（微信）

### 场景 2：多工具参与的交易

**文本**: "我在美团上用支付宝订了张三的店的咖啡"

**传统表达**:

- 关系: `我 -> 张三的店:餐厅`
- 描述: "我订购了咖啡"
- 问题: 丢失了平台（美团）和支付方式（支付宝）信息

**使用 Refer 字段**:

- 关系: `我 -> 张三的店:餐厅`
- 描述: "我订购了咖啡"
- Refer: `["美团:购物平台", "支付宝:支付工具"]`
- 优势: 完整记录了订购过程中的所有参与方

## 核心原则

### 1. 实体提取原则

- **对象（名词）→ 实体**: "视频"、"商品"、"文章"
- **动作（动词）→ 关系描述**: "分享"、"购买"、"浏览"

✅ **正确**: "关于AI绘图的视频" 作为实体提取
❌ **错误**: 将"分享"作为实体提取

### 2. Refer 字段使用规则

- **主关系**: source → target（主要的两个参与方）
- **Refer字段**: 列出其他参与的实体/实体类（工具、平台、内容对象等）
- **格式**: 字符串数组，如 `["微信:交流平台", "视频内容"]`
- **空值**: 如果没有其他参与者，使用空数组 `[]`

### 3. 关系唯一性判断

**关系被认为是同一个当且仅当**:

- source 相同
- target 相同
- description 相同
- **refer 相同**（内容相同，顺序无关）

**示例：两次启动同一应用（相同关系，可合并）**:

```
关系1: 我 -> 某应用:可启动应用, description="打开应用", refer=[], count=1
关系2: 我 -> 某应用:可启动应用, description="打开应用", refer=[], count=1
→ 合并为: count=2
```

**示例：两次联系同一个人但目的不同（不同关系，不可合并）**:

```
关系1: 我 -> 小明:可联系人, description="联系小明", refer=["问作业"], count=1
关系2: 我 -> 小明:可联系人, description="联系小明", refer=["微信:交流平台","分享视频"], count=1
→ 保持为两条独立关系（refer 不同，表示不同的交互场景）
```

## 实现细节

### 1. 数据模型层 (Models)

#### `Relationship` 类 (`src/models/relationship.py`)

```python
@dataclass
class Relationship:
    source: str
    target: str
    description: str
    count: int
    refer: List[str] = field(default_factory=list)  # 新增字段
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**关键修改**:

- `__eq__`: 比较时包含 refer 字段（集合比较，顺序无关）
- `__hash__`: 哈希时包含 refer 字段
- `to_dict`/`from_dict`: 序列化/反序列化时包含 refer 字段

#### `RelationshipDelta` 类 (`src/models/delta.py`)

```python
@dataclass
class RelationshipDelta:
    source: str
    target: str
    description: str
    count: int = 1
    refer: List[str] = field(default_factory=list)  # 新增字段
    operation: str = "add"
```

### 2. 提取层 (Extractors)

#### `GraphExtractor` (`src/extractors/extractor.py`)

**输出格式更新**:

```
("relationship"|source|target|description|count|refer)
```

**解析逻辑**:

```python
# 解析 refer 字段
refer = []
if len(parts) >= 6:
    refer_str = parts[5].strip()
    if refer_str and refer_str.upper() != "NONE":
        refer = [r.strip() for r in refer_str.split(",") if r.strip()]
```

#### 提取提示词 (`config/prompts/extract_graph.txt`)

**关键规则**:

1. **动作 vs 对象**:
   - 动作(动词) → 关系描述
   - 对象(名词) → 实体

2. **Refer 使用**:
   - 多方参与时使用 refer 列出额外参与者
   - 格式: `entity1,entity2` (逗号分隔，无空格)
   - 无参与者时使用 `NONE`

3. **示例**:

```
STEP 3 - Relationships:
("relationship"|我|小明:可联系人|我把视频分享给小明|1|微信:交流平台,关于AI绘图的视频)^
```

#### 检查提示词 (`config/prompts/check_extraction.txt`)

**新增检查点**:

- 多方参与的关系必须包含 refer
- Refer 中的实体必须在实体列表中存在
- 格式检查: 逗号分隔，无空格

### 3. 合并层 (Combiners)

#### `Graph.add_relationship` (`src/models/graph.py`)

**修改要点**:

```python
# 检查是否已存在相同的关系（包括 refer 字段）
for existing_rel in self._relationships:
    existing_refer_set = set([r.upper() for r in existing_rel.refer])
    new_refer_set = set([r.upper() for r in relationship.refer])
    
    if (source_match and target_match and description_match 
        and existing_refer_set == new_refer_set):  # refer 必须相同
        # 累加次数
        existing_rel.increment_count(relationship.count)
        return existing_rel
```

#### `Combiner` (`src/combiners/combiner.py`)

**修改要点**:

```python
# 检查关系是否已存在（包括 refer 字段）
new_refer_set = set([r.upper() for r in relationship.refer])
existing = any(
    ... and set([r.upper() for r in rel.refer]) == new_refer_set
    for rel in self.graph.get_relationships()
)
```

#### `SmartMerger` (`src/combiners/smart_merger.py`)

**智能合并提示词更新** (`config/prompts/smart_merge.txt`):

```
9. 【关键】Refer字段决定关系唯一性:
   - 关系唯一性判断：source + target + description + refer 都相同
   - 合并规则：refer 不同 = 不同关系，不可合并
   - Refer字段处理：
     * 输出时必须包含 "refer" 字段
     * 无参与者时使用空数组 []
     * 合并时比较 refer 数组内容（顺序无关）
```

**JSON 输出格式**:

```json
{
  "optimized_relationships": [
    {
      "source": "我",
      "target": "小明:可联系人",
      "description": "我把视频分享给小明",
      "count": 1,
      "refer": ["微信:交流平台", "关于AI绘图的视频"],
      "operation": "add"
    }
  ]
}
```

### 4. 主流程 (`simplegraph.py`)

**转换为增量格式时传递 refer**:

```python
relationship_deltas.append(
    RelationshipDelta(
        source=relationship.source,
        target=relationship.target,
        description=relationship.description,
        count=relationship.count,
        refer=relationship.refer,  # 传递 refer 字段
        operation="add",
    )
)
```

**应用合并结果时传递 refer**:

```python
relationship = Relationship(
    source=rel_delta.source,
    target=rel_delta.target,
    description=rel_delta.description,
    count=rel_delta.count,
    refer=rel_delta.refer,  # 传递 refer 字段
)
```

## 向后兼容性

所有修改都保持向后兼容：

1. **默认值**: refer 字段默认为空数组 `[]`
2. **解析容错**: 旧格式的关系记录（5个字段）依然可以正确解析
3. **序列化兼容**: `from_dict` 方法会检查 refer 字段是否存在，不存在时使用空数组

## 测试建议

### 测试用例 1: 基本 refer 功能

```
输入: "我通过微信把一个关于AI的视频分享给小明"
预期:
  - 实体: 我, 微信, 小明, 关于AI的视频
  - 关系: 我 -> 小明:可联系人
  - Refer: ["微信:交流平台", "关于AI的视频"]
```

### 测试用例 2: 相同关系合并

```
输入1: "我打开抖音"
输入2: "我又打开抖音"
预期:
  - 关系: 我 -> 抖音:可启动应用, refer=[], count=2
```

### 测试用例 3: 不同 refer 不合并

```
输入1: "我联系小明问作业"
输入2: "我通过微信分享视频给小明"
预期:
  - 关系1: 我 -> 小明, refer=[], count=1
  - 关系2: 我 -> 小明, refer=["微信:交流平台", "视频"], count=1
  - 保持为两条独立关系
```

## 提示词优化总结

### 优化前问题

- 提示词冗长，重复内容多
- 规则分散，难以快速理解
- 示例不够聚焦核心功能

### 优化后改进

1. **精简规则表述**: 从长段落压缩为关键点
2. **移除重复**: 合并相似规则，避免冗余
3. **聚焦示例**: 每个示例突出一个核心概念
4. **保留原有示例**: 未删除用户原本的例子
5. **结构优化**:
   - `extract_graph.txt`: 从 389 行优化到 322 行
   - `check_extraction.txt`: 从 180 行优化到 92 行

## 总结

通过添加 `refer` 字段，SimpleGraphRAG 现在能够：

1. ✅ 完整表达多方参与的复杂关系
2. ✅ 准确区分相似但不同的关系（通过 refer 区分）
3. ✅ 正确合并相同的关系（refer 相同时才合并）
4. ✅ 保持向后兼容（旧数据依然可用）
5. ✅ 优化了提示词长度和清晰度

这使得知识图谱更加精确和有表达力，能够回答更复杂的查询，如：

- "我通过哪些平台分享过内容给小明？"
- "哪些交易使用了支付宝？"
- "我在哪些场景下联系过小明？"
