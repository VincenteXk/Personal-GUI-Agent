# 快速开始指南

## 启动后端服务

```powershell
cd backend
python main.py
```

服务器将在 `http://localhost:8000` 启动

## 访问 API 文档

浏览器打开：

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## 基础使用示例

### 1. 查看当前系统的所有类

```powershell
curl http://localhost:8000/api/system/classes
```

### 2. 添加新类到系统

```powershell
curl -X POST http://localhost:8000/api/system/classes `
  -H "Content-Type: application/json" `
  -d '{
    "class_name": "视频平台",
    "description": "提供视频内容的平台",
    "properties": [
      {
        "name": "视频数量",
        "description": "平台上的视频总数",
        "required": false,
        "value_required": false
      }
    ]
  }'
```

### 3. 查看所有实体

```powershell
curl http://localhost:8000/api/entities
```

### 4. 查看特定实体详情

```powershell
# 需要先有实体数据，可以通过提交任务创建
curl http://localhost:8000/api/entities/抖音
```

### 5. 提交文本处理任务

```powershell
curl -X POST http://localhost:8000/api/tasks `
  -H "Content-Type: application/json" `
  -d '{
    "input_text": "我在抖音上刷到一家网红餐厅，名叫张三的店，于是打开美团外卖订了他们家的招牌套餐。"
  }'
```

### 6. 更新实体属性

```powershell
curl -X PUT http://localhost:8000/api/entities/抖音/properties `
  -H "Content-Type: application/json" `
  -d '{
    "class_name": "社交平台",
    "property_name": "用户数量",
    "value": "10亿+"
  }'
```

## 运行测试脚本

```powershell
# 确保服务器已启动
python test_api.py
```

## 主要功能

### System 管理

- ✅ 查看所有类定义
- ✅ 添加新类
- ✅ 更新类属性
- ✅ 向类添加新属性
- ❌ **不支持删除类**（设计决策）

### Entity 管理

- ✅ 查看所有实体
- ✅ 查看实体详情
- ✅ 更新实体描述
- ✅ 为实体添加/移除类
- ✅ 更新实体属性值

### 图数据

- ✅ 获取完整图数据（节点+边）
- ✅ 获取统计信息

### 任务处理

- ✅ 提交文本处理任务
- ✅ 查询任务状态
- ✅ 实时进度推送（SSE）
- ✅ 获取任务增量数据

## 下一步

查看完整文档：

- `API_DOCUMENTATION.md` - 完整的 API 参考
- `SYSTEM_ENHANCEMENT_SUMMARY.md` - 系统增强功能说明

## 常见问题

**Q: 如何确认服务器是否正常运行？**

```powershell
curl http://localhost:8000/api/stats
```

**Q: 如何查看所有可用的接口？**  
访问 <http://localhost:8000/docs>

**Q: 如何停止服务器？**  
在运行服务器的终端按 `Ctrl+C`
