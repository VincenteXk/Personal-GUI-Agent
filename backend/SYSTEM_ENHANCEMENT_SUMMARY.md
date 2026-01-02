# System 增强功能总结

本文档总结了对 SimpleGraphRAG 后端系统的增强，主要增加了对 System（类配置）和 Entity（实体）的全面管理功能。

## 更新日期

2025年1月2日

## 新增功能概览

### 1. System 管理功能

- ✅ 查看所有类定义
- ✅ 查看单个类的详细信息
- ✅ 添加新类到 System
- ✅ 更新现有类（只能增强，不能删除）
- ✅ 向类添加新属性
- ❌ **不支持删除类**（按需求设计）

### 2. Entity 管理功能

- ✅ 查看所有实体列表
- ✅ 查看单个实体的详细信息
- ✅ 更新实体描述
- ✅ 为实体添加/移除类
- ✅ 更新实体的属性值
- ✅ 为实体添加新类及其属性

---

## 文件修改清单

### 1. `backend/graph_service.py`

新增以下方法：

#### System 管理方法

- `get_system_classes()` - 获取所有类定义
- `get_class_definition(class_name)` - 获取指定类的定义
- `add_class_to_system(class_name, description, properties)` - 添加新类
- `update_class_definition(class_name, description, properties)` - 更新类定义
- `add_property_to_class(class_name, property_name, ...)` - 向类添加属性

#### Entity 管理方法

- `get_all_entities()` - 获取所有实体摘要
- `get_entity_detail(entity_name)` - 获取实体详情
- `update_entity(entity_name, description, add_classes, remove_classes)` - 更新实体
- `update_entity_property(entity_name, class_name, property_name, value)` - 更新属性值
- `add_class_to_entity(entity_name, class_name, properties)` - 为实体添加类

### 2. `backend/main.py`

新增以下 API 端点：

#### System API（9个新端点）

```
GET    /api/system/classes                    - 获取所有类
GET    /api/system/classes/{class_name}       - 获取指定类
POST   /api/system/classes                    - 添加新类
PUT    /api/system/classes/{class_name}       - 更新类
POST   /api/system/classes/{class_name}/properties - 添加属性
```

#### Entity API（5个新端点）

```
GET    /api/entities                          - 获取所有实体
GET    /api/entities/{entity_name}            - 获取实体详情
PUT    /api/entities/{entity_name}            - 更新实体
PUT    /api/entities/{entity_name}/properties - 更新属性值
POST   /api/entities/{entity_name}/classes    - 添加类到实体
```

新增 Pydantic 模型：

- `ClassCreate` - 创建类的请求模型
- `ClassUpdate` - 更新类的请求模型
- `PropertyAdd` - 添加属性的请求模型
- `EntityUpdate` - 更新实体的请求模型
- `PropertyUpdate` - 更新属性值的请求模型
- `ClassAddToEntity` - 为实体添加类的请求模型

### 3. 新增文件

#### `backend/API_DOCUMENTATION.md`

完整的 API 文档，包括：

- 所有接口的详细说明
- 请求/响应示例
- Python 和 JavaScript 使用示例
- 错误处理说明
- 开发和测试指南

#### `backend/test_api.py`

API 测试脚本，提供：

- System API 的完整测试
- Entity API 的完整测试
- 图数据 API 的测试
- 自动化测试流程

---

## 核心设计原则

### 1. 单调扩展原则（Monotonic Growth）

System 的设计遵循"只增不删"原则：

- ✅ 可以添加新类
- ✅ 可以向类添加新属性
- ✅ 可以增强属性约束（required: false → true）
- ❌ 不能删除类
- ❌ 不能删除属性
- ❌ 不能削弱约束（required: true → false）

**优势：**

- 保证系统配置的稳定性
- 避免破坏已有数据的完整性
- 支持增量式系统演化

### 2. 数据验证机制

所有更新操作都经过严格验证：

- 类定义必须存在于 System 中
- 属性必须在类定义中声明
- 必填属性必须有值
- 类型和约束自动检查

### 3. 关联数据管理

Entity 的更新自动处理关联数据：

- 添加类时自动创建必选属性
- 移除类时清理相关属性
- 更新属性时验证类归属

---

## 使用场景示例

### 场景 1：扩展 System 以支持新领域

```python
# 添加"AI工具"类到系统
import requests

response = requests.post(
    "http://localhost:8000/api/system/classes",
    json={
        "class_name": "AI工具",
        "description": "人工智能相关的工具和服务",
        "properties": [
            {
                "name": "功能类型",
                "description": "工具的主要功能类型",
                "required": True,
                "value_required": True
            },
            {
                "name": "开发公司",
                "description": "开发该工具的公司",
                "required": False,
                "value_required": False
            }
        ]
    }
)
```

### 场景 2：增强现有类的属性

```python
# 向"购物平台"类添加新属性
response = requests.post(
    "http://localhost:8000/api/system/classes/购物平台/properties",
    json={
        "property_name": "月活跃用户",
        "description": "平台的月活跃用户数",
        "required": False,
        "value_required": False
    }
)
```

### 场景 3：更新实体信息

```python
# 更新"抖音"实体，添加新类
response = requests.put(
    "http://localhost:8000/api/entities/抖音",
    json={
        "description": "短视频社交平台，字节跳动旗下产品",
        "add_classes": ["AI工具"]
    }
)
```

### 场景 4：批量更新实体属性

```python
# 更新实体的多个属性值
entity_name = "抖音"

# 更新属性1
requests.put(
    f"http://localhost:8000/api/entities/{entity_name}/properties",
    json={
        "class_name": "社交平台",
        "property_name": "用户数量",
        "value": "10亿+"
    }
)

# 更新属性2
requests.put(
    f"http://localhost:8000/api/entities/{entity_name}/properties",
    json={
        "class_name": "AI工具",
        "property_name": "功能类型",
        "value": "推荐算法"
    }
)
```

---

## 测试方法

### 1. 自动化测试

运行提供的测试脚本：

```bash
# 确保后端服务器正在运行
cd backend
python main.py

# 在另一个终端运行测试
python test_api.py
```

### 2. 交互式测试

使用 FastAPI 自动生成的交互式文档：

```bash
# 启动服务器后访问
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
```

### 3. curl 命令测试

```bash
# 获取所有类
curl http://localhost:8000/api/system/classes

# 获取所有实体
curl http://localhost:8000/api/entities

# 添加新类
curl -X POST http://localhost:8000/api/system/classes \
  -H "Content-Type: application/json" \
  -d '{
    "class_name": "测试类",
    "description": "这是一个测试类",
    "properties": []
  }'
```

---

## 性能考虑

### 1. 缓存策略

当前实现直接访问内存中的 System 和 Graph 对象，性能良好：

- 类定义查询：O(1)
- 实体查询：O(n)，n 为实体总数
- 属性更新：O(1)

### 2. 并发安全

- 读操作无锁，直接访问
- 写操作通过 SimpleGraph 的内部机制保证一致性
- 任务处理采用队列机制，避免竞态条件

### 3. 扩展性

当实体数量较大时，可考虑：

- 添加分页支持（`/api/entities?page=1&size=50`）
- 添加搜索过滤（`/api/entities?class=购物平台`）
- 添加缓存层（Redis）

---

## 未来改进方向

### 1. 功能增强

- [ ] 支持批量操作（批量更新实体）
- [ ] 支持属性的数据类型定义（字符串、数字、日期等）
- [ ] 支持属性的枚举值约束
- [ ] 支持类的继承关系
- [ ] 支持实体的软删除

### 2. API 优化

- [ ] 添加分页和过滤功能
- [ ] 添加排序功能
- [ ] 添加搜索功能（全文搜索）
- [ ] 添加批量操作接口
- [ ] 添加导出/导入功能（JSON/YAML）

### 3. 安全性

- [ ] 添加身份验证（JWT）
- [ ] 添加权限控制（RBAC）
- [ ] 添加操作日志
- [ ] 添加数据备份机制

### 4. 监控和日志

- [ ] 添加 API 调用统计
- [ ] 添加性能监控
- [ ] 添加错误追踪
- [ ] 添加审计日志

---

## 常见问题（FAQ）

### Q1: 为什么不支持删除类？

**A:** 这是有意的设计决策。删除类可能导致：

- 已有实体的数据不一致
- 历史数据的完整性问题
- 需要复杂的级联删除逻辑

采用"只增不删"的设计可以保证系统的稳定性和数据完整性。

### Q2: 如何处理错误的类定义？

**A:** 如果添加了错误的类，可以：

1. 通过更新描述来修正信息
2. 添加注释属性说明该类已废弃
3. 在应用层过滤不需要的类

### Q3: 更新类定义会影响已有实体吗？

**A:** 会的，以增强的方式：

- 添加新属性：已有实体不会自动获得该属性，但可以手动添加
- 修改描述：不影响实体
- 增强约束：已有实体需要满足新约束（建议在更新前检查）

### Q4: 如何批量更新多个实体？

**A:** 当前需要逐个调用 API。未来版本将支持批量操作接口。临时方案：

```python
entities = ["实体1", "实体2", "实体3"]
for entity in entities:
    update_entity(entity, {"description": "新描述"})
```

### Q5: API 是否支持事务？

**A:** 当前不支持跨接口的事务。每个 API 调用都是原子的。如果需要事务性操作，建议：

1. 在应用层实现补偿逻辑
2. 或者等待未来版本支持批量操作

---

## 技术栈

- **Web 框架**: FastAPI
- **数据模型**: Pydantic
- **图处理**: 自定义 SimpleGraph
- **LLM 集成**: 自定义 LLMClient
- **日志**: Python logging
- **并发**: asyncio

---

## 贡献者

本次增强由 AI 助手完成，基于用户需求进行系统性设计和实现。

---

## 变更日志

### v1.1.0 (2025-01-02)

- ✨ 新增 System 管理完整接口
- ✨ 新增 Entity 管理完整接口
- 📝 添加完整 API 文档
- 🧪 添加自动化测试脚本
- 🔒 实现单调扩展原则，禁止删除类

### v1.0.0 (之前)

- 基础的任务处理功能
- 图数据查询功能
- SSE 进度推送

---

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件
- 参与项目讨论

---

**祝使用愉快！** 🎉
