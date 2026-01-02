# API 文档 - SimpleGraphRAG 后端系统

本文档描述了 SimpleGraphRAG 后端系统的所有 API 接口。

## 目录

- [任务管理 API](#任务管理-api)
- [图数据 API](#图数据-api)
- [System 管理 API](#system-管理-api)
- [Entity 管理 API](#entity-管理-api)
- [查询 API](#查询-api)

---

## 任务管理 API

### 1. 提交任务

**POST** `/api/tasks`

提交一个新的文本处理任务。

**请求体：**

```json
{
  "input_text": "我在抖音上刷到一家网红餐厅..."
}
```

**响应：**

```json
{
  "task_id": "task_1234567890"
}
```

### 2. 获取所有任务

**GET** `/api/tasks`

获取所有任务的列表。

**响应：**

```json
[
  {
    "task_id": "task_1234567890",
    "status": "completed",
    "input_text": "我在抖音上刷到...",
    "created_at": "2025-01-02T10:30:00",
    "duration": 5.2,
    "error": null
  }
]
```

### 3. 获取任务状态

**GET** `/api/tasks/{task_id}`

获取指定任务的状态信息。

**响应：**

```json
{
  "task_id": "task_1234567890",
  "status": "completed",
  "input_text": "我在抖音上刷到...",
  "created_at": "2025-01-02T10:30:00",
  "completed_at": "2025-01-02T10:30:05",
  "duration": 5.2,
  "error": null
}
```

### 4. 获取任务增量数据

**GET** `/api/tasks/{task_id}/delta`

获取任务产生的增量数据（新增的类、实体、关系）。

**响应：**

```json
{
  "task_id": "task_1234567890",
  "status": "completed",
  "has_delta": true,
  "delta": {
    "classes": [...],
    "entities": [...],
    "relationships": [...]
  },
  "stats": {
    "classes": 2,
    "entities": 5,
    "relationships": 3
  }
}
```

### 5. SSE 事件流

**GET** `/api/events`

建立 Server-Sent Events 连接，实时接收任务进度更新。

**事件格式：**

```javascript
data: {
  "event_type": "progress",
  "task_id": "task_1234567890",
  "step": "extraction",
  "message": "正在提取实体和关系...",
  "percentage": 50
}
```

---

## 图数据 API

### 1. 获取图数据

**GET** `/api/graph`

获取完整的图数据，格式化为前端可视化所需格式。

**响应：**

```json
{
  "nodes": [
    {
      "id": "entity_name",
      "label": "实体名称",
      "group": 1,
      "size": 15,
      "description": "实体描述",
      "node_type": "entity",
      "classes": ["类1", "类2"],
      "properties": {
        "类1": {"属性1": "值1"}
      }
    }
  ],
  "links": [
    {
      "source": "实体A",
      "target": "实体B",
      "value": 2.5,
      "description": "关系描述",
      "edge_type": "relationship",
      "count": 5,
      "refer": "来源引用"
    }
  ]
}
```

### 2. 获取统计信息

**GET** `/api/stats`

获取系统的统计信息。

**响应：**

```json
{
  "system": {
    "classes": 10,
    "predefined_entities": 5
  },
  "graph": {
    "entities": 50,
    "relationships": 75
  },
  "tasks": {
    "total": 20,
    "by_status": {
      "pending": 2,
      "running": 1,
      "completed": 15,
      "failed": 2,
      "cancelled": 0
    }
  }
}
```

---

## System 管理 API

### 1. 获取所有类定义

**GET** `/api/system/classes`

获取 System 中所有类的定义。

**响应：**

```json
[
  {
    "name": "购物平台",
    "description": "提供在线购物服务的电商平台",
    "properties": [
      {
        "name": "成立时间",
        "description": "平台成立的时间",
        "required": false,
        "value_required": false
      }
    ]
  }
]
```

### 2. 获取指定类定义

**GET** `/api/system/classes/{class_name}`

获取指定类的详细定义。

**参数：**

- `class_name`: 类名称（URL 编码）

**响应：**

```json
{
  "name": "购物平台",
  "description": "提供在线购物服务的电商平台",
  "properties": [
    {
      "name": "成立时间",
      "description": "平台成立的时间",
      "required": false,
      "value_required": false
    }
  ]
}
```

### 3. 添加新类

**POST** `/api/system/classes`

向 System 添加新的类定义。

**请求体：**

```json
{
  "class_name": "社交平台",
  "description": "提供社交互动功能的平台",
  "properties": [
    {
      "name": "用户数量",
      "description": "平台的注册用户总数",
      "required": false,
      "value_required": false
    },
    {
      "name": "主要功能",
      "description": "平台的核心功能",
      "required": true,
      "value_required": true
    }
  ]
}
```

**响应：**

```json
{
  "name": "社交平台",
  "description": "提供社交互动功能的平台",
  "properties": [...]
}
```

### 4. 更新类定义

**PUT** `/api/system/classes/{class_name}`

更新现有类的定义（只能增强，不能删除属性）。

**参数：**

- `class_name`: 类名称（URL 编码）

**请求体：**

```json
{
  "description": "更新后的类描述",
  "properties": [
    {
      "name": "新属性",
      "description": "新增的属性",
      "required": false,
      "value_required": false
    }
  ]
}
```

**响应：**

```json
{
  "name": "社交平台",
  "description": "更新后的类描述",
  "properties": [...]
}
```

### 5. 向类添加属性

**POST** `/api/system/classes/{class_name}/properties`

向指定类添加新的属性定义。

**参数：**

- `class_name`: 类名称（URL 编码）

**请求体：**

```json
{
  "property_name": "活跃用户数",
  "description": "日活跃用户数量",
  "required": false,
  "value_required": false
}
```

**响应：**

```json
{
  "name": "社交平台",
  "description": "...",
  "properties": [...]
}
```

---

## Entity 管理 API

### 1. 获取所有实体

**GET** `/api/entities`

获取所有实体的摘要信息。

**响应：**

```json
[
  {
    "name": "抖音",
    "description": "短视频社交平台",
    "classes": ["社交平台", "视频平台"],
    "created_at": "2025-01-02T10:30:00",
    "updated_at": "2025-01-02T10:35:00"
  }
]
```

### 2. 获取实体详情

**GET** `/api/entities/{entity_name}`

获取指定实体的详细信息，包括所有类和属性。

**参数：**

- `entity_name`: 实体名称（URL 编码）

**响应：**

```json
{
  "name": "抖音",
  "description": "短视频社交平台",
  "classes": [
    {
      "class_name": "社交平台",
      "description": "提供社交互动功能的平台",
      "properties": [
        {
          "name": "用户数量",
          "value": "10亿+",
          "description": "平台的注册用户总数",
          "required": false,
          "value_required": false
        }
      ]
    }
  ],
  "relationships": [
    {
      "source": "用户",
      "target": "抖音",
      "description": "用户使用抖音",
      "count": 1,
      "refer": null
    }
  ],
  "created_at": "2025-01-02T10:30:00",
  "updated_at": "2025-01-02T10:35:00"
}
```

### 3. 更新实体

**PUT** `/api/entities/{entity_name}`

更新实体的描述或类归属。

**参数：**

- `entity_name`: 实体名称（URL 编码）

**请求体：**

```json
{
  "description": "更新后的实体描述",
  "add_classes": ["新类1", "新类2"],
  "remove_classes": ["旧类1"]
}
```

**响应：**

```json
{
  "name": "抖音",
  "description": "更新后的实体描述",
  "classes": [...],
  "relationships": [...],
  "created_at": "...",
  "updated_at": "..."
}
```

### 4. 更新实体属性值

**PUT** `/api/entities/{entity_name}/properties`

更新实体在某个类下的某个属性的值。

**参数：**

- `entity_name`: 实体名称（URL 编码）

**请求体：**

```json
{
  "class_name": "社交平台",
  "property_name": "用户数量",
  "value": "12亿+"
}
```

**响应：**

```json
{
  "name": "抖音",
  "description": "...",
  "classes": [...],
  "relationships": [...],
  "created_at": "...",
  "updated_at": "..."
}
```

### 5. 为实体添加类

**POST** `/api/entities/{entity_name}/classes`

为实体添加新的类及其属性值。

**参数：**

- `entity_name`: 实体名称（URL 编码）

**请求体：**

```json
{
  "class_name": "视频平台",
  "properties": {
    "视频数量": "100亿+",
    "主要内容": "短视频"
  }
}
```

**响应：**

```json
{
  "name": "抖音",
  "description": "...",
  "classes": [...],
  "relationships": [...],
  "created_at": "...",
  "updated_at": "..."
}
```

---

## 查询 API

### 1. 关键词查询

**POST** `/api/search/keyword`

在知识图谱中搜索关键词，支持模糊查询和严格匹配。

可检索的内容类型包括：

- 实体名称和描述
- 实体类节点（entity:class）
- 类主节点和描述
- 属性名称和属性值
- 关系描述
- 关系refer字段

**请求体：**

```json
{
  "keyword": "小红书",
  "fuzzy": true,
  "limit": 50
}
```

**参数说明：**

- `keyword` (string, 必填): 搜索关键词
- `fuzzy` (boolean, 可选): 是否模糊查询，默认 `true`
  - `true`: 模糊匹配（包含即可）
  - `false`: 严格匹配（完全相等）
- `limit` (integer, 可选): 结果数量限制，默认 50

**响应：**

```json
[
  {
    "result_type": "entity_name",
    "matched_text": "小红书",
    "context": {
      "entity_name": "小红书"
    },
    "score": 1.0
  },
  {
    "result_type": "class_node",
    "matched_text": "小红书:购物平台",
    "context": {
      "node_id": "小红书:购物平台",
      "entity_name": "小红书",
      "class_name": "购物平台"
    },
    "score": 0.9
  },
  {
    "result_type": "relationship_description",
    "matched_text": "我在小红书上浏览内容",
    "context": {
      "source": "我",
      "target": "小红书:内容平台",
      "description": "我在小红书上浏览内容"
    },
    "score": 0.7
  }
]
```

**结果类型说明：**

- `entity_name`: 实体名称
- `entity_description`: 实体描述
- `class_node`: 实体类节点
- `class_master_node`: 类主节点
- `class_name`: 类名称
- `class_description`: 类描述
- `property_name`: 属性名称
- `property_value`: 属性值
- `relationship`: 关系
- `relationship_description`: 关系描述
- `relationship_refer`: 关系refer字段

### 2. 查询节点详情

**GET** `/api/search/node/{node_id}`

查询节点的详细信息，包括节点本身的所有信息和一层连接关系。

**参数说明：**

- `node_id` (string, 路径参数): 节点ID，可以是：
  - 实体名称（如 `小红书`）
  - 类节点ID（如 `小红书:购物平台`）
  - 类主节点名称（如 `购物平台`）

**响应示例 - 实体节点：**

```json
{
  "node_id": "小红书",
  "node_type": "entity",
  "node_info": {
    "name": "小红书",
    "description": "一个社交电商平台",
    "classes": ["购物平台", "内容平台", "可启动应用"],
    "properties": {
      "购物平台": {
        "成立时间": "2013"
      },
      "可启动应用": {
        "启动方式": "点击图标"
      }
    }
  },
  "one_hop_relationships": [
    {
      "source": "我",
      "target": "小红书:可启动应用",
      "description": "我打开小红书",
      "count": 1,
      "refer": []
    }
  ],
  "one_hop_neighbors": [
    {"node_id": "我"},
    {"node_id": "小红书:购物平台"}
  ],
  "statistics": {
    "relationships_count": 5,
    "neighbors_count": 3
  }
}
```

**响应示例 - 类节点：**

```json
{
  "node_id": "小红书:购物平台",
  "node_type": "class_node",
  "node_info": {
    "node_id": "小红书:购物平台",
    "entity_name": "小红书",
    "class_name": "购物平台",
    "description": "小红书的购物平台功能",
    "properties": {
      "成立时间": "2013"
    }
  },
  "one_hop_relationships": [...],
  "one_hop_neighbors": [...],
  "statistics": {
    "relationships_count": 2,
    "neighbors_count": 2
  }
}
```

**响应示例 - 类主节点：**

```json
{
  "node_id": "购物平台",
  "node_type": "class_master_node",
  "node_info": {
    "class_name": "购物平台",
    "description": "可以进行购物的平台",
    "properties": [
      {
        "name": "成立时间",
        "description": "平台的成立时间",
        "required": false,
        "value_required": false
      }
    ]
  },
  "one_hop_relationships": [...],
  "one_hop_neighbors": [...],
  "statistics": {
    "relationships_count": 3,
    "neighbors_count": 2
  }
}
```

### 3. 查询实体节点组

**GET** `/api/search/entity-group/{entity_name}`

查询实体节点组，包含：

- 实体节点本身的完整信息
- 该实体的所有类节点（entity:class）
- 所有这些节点的一层连接关系

**参数说明：**

- `entity_name` (string, 路径参数): 实体名称

**响应：**

```json
{
  "entity": {
    "name": "小红书",
    "description": "一个社交电商平台",
    "classes": ["购物平台", "内容平台", "可启动应用"],
    "properties": {
      "购物平台": {
        "成立时间": "2013"
      },
      "可启动应用": {
        "启动方式": "点击图标"
      }
    },
    "created_at": "2025-01-02T10:30:00",
    "updated_at": "2025-01-02T11:00:00"
  },
  "class_nodes": [
    {
      "node_id": "小红书:购物平台",
      "entity_name": "小红书",
      "class_name": "购物平台",
      "description": "小红书的购物平台功能"
    },
    {
      "node_id": "小红书:内容平台",
      "entity_name": "小红书",
      "class_name": "内容平台",
      "description": "小红书的内容平台功能"
    },
    {
      "node_id": "小红书:可启动应用",
      "entity_name": "小红书",
      "class_name": "可启动应用",
      "description": "小红书作为可启动应用"
    }
  ],
  "one_hop_relationships": [
    {
      "source": "我",
      "target": "小红书:可启动应用",
      "description": "我打开小红书",
      "count": 1,
      "refer": []
    },
    {
      "source": "我",
      "target": "小红书:购物平台",
      "description": "我在小红书上购物",
      "count": 2,
      "refer": []
    }
  ],
  "statistics": {
    "class_nodes_count": 3,
    "relationships_count": 8
  }
}
```

### 4. 查询类节点组

**GET** `/api/search/class-group/{class_name}`

查询类节点组，包含：

- 类主节点（类本身的定义信息）
- 所有实例化该类的实体类节点
- 所有这些节点的一层连接关系

**参数说明：**

- `class_name` (string, 路径参数): 类名称

**响应：**

```json
{
  "class_master_node": {
    "class_name": "购物平台",
    "description": "可以进行购物的平台"
  },
  "class_nodes": [
    {
      "node_id": "小红书:购物平台",
      "entity_name": "小红书",
      "class_name": "购物平台",
      "description": "小红书的购物平台功能"
    },
    {
      "node_id": "淘宝:购物平台",
      "entity_name": "淘宝",
      "class_name": "购物平台",
      "description": "淘宝的购物平台功能"
    },
    {
      "node_id": "京东:购物平台",
      "entity_name": "京东",
      "class_name": "购物平台",
      "description": "京东的购物平台功能"
    }
  ],
  "one_hop_relationships": [
    {
      "source": "我",
      "target": "小红书:购物平台",
      "description": "我在小红书上购物",
      "count": 2,
      "refer": []
    },
    {
      "source": "我",
      "target": "淘宝:购物平台",
      "description": "我在淘宝上购物",
      "count": 5,
      "refer": []
    }
  ],
  "statistics": {
    "instances_count": 3,
    "relationships_count": 10
  }
}
```

---

## 错误响应

所有 API 在发生错误时都会返回标准的错误响应：

```json
{
  "detail": "错误描述信息"
}
```

常见的 HTTP 状态码：

- `200 OK`: 请求成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

---

## 注意事项

1. **类删除限制**：System 不支持删除类定义，只能新增和增强（单调扩展）
2. **属性约束**：`required` 和 `value_required` 只能从 false 变为 true，不能降级
3. **实体验证**：更新实体属性时会自动验证属性是否在类定义中存在
4. **并发控制**：任务处理采用队列机制，支持并发提取，但合并阶段是串行的
5. **实时更新**：使用 SSE (`/api/events`) 可以实时接收任务进度和状态更新

---

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 添加新类到 System
response = requests.post(
    f"{BASE_URL}/api/system/classes",
    json={
        "class_name": "AI工具",
        "description": "人工智能相关的工具和服务",
        "properties": [
            {
                "name": "功能类型",
                "description": "工具的主要功能类型",
                "required": True,
                "value_required": True
            }
        ]
    }
)
print(response.json())

# 2. 获取实体详情
response = requests.get(f"{BASE_URL}/api/entities/抖音")
print(response.json())

# 3. 更新实体属性
response = requests.put(
    f"{BASE_URL}/api/entities/抖音/properties",
    json={
        "class_name": "社交平台",
        "property_name": "用户数量",
        "value": "15亿+"
    }
)
print(response.json())
```

### JavaScript 示例

```javascript
const BASE_URL = "http://localhost:8000";

// 1. 提交任务
async function submitTask(text) {
  const response = await fetch(`${BASE_URL}/api/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input_text: text })
  });
  return await response.json();
}

// 2. 获取所有类定义
async function getClasses() {
  const response = await fetch(`${BASE_URL}/api/system/classes`);
  return await response.json();
}

// 3. 监听任务进度（SSE）
function listenToEvents() {
  const eventSource = new EventSource(`${BASE_URL}/api/events`);
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Progress:", data);
  };
  
  return eventSource;
}
```

---

## 开发和测试

启动服务器：

```bash
cd backend
python main.py
```

服务器将在 `http://localhost:8000` 上运行。

访问交互式 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
