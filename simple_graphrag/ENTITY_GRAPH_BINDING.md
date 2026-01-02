# Entity-Graph 自动绑定机制

## 概述

实体（Entity）现在支持自动绑定到图（Graph），简化了系统配置（System）的使用。

## 关键改进

### 1. Entity 自动绑定 Graph

当实体添加到图中时，会自动绑定该图的引用：

```python
entity = Entity(name="淘宝", description="购物平台")
graph.add_entity(entity)  # 自动绑定 graph

# 后续操作自动使用 graph.system，不需要显式传递
entity.add_class("购物平台")  # ✓ 自动使用 graph.system
entity.set_property_value("购物平台", "类型", "电商")  # ✓ 自动使用 graph.system
```

### 2. 推荐使用 `Graph.create_entity()`

更简洁的方式，一次性创建实体并实例化多个类：

```python
entity = graph.create_entity(
    name="小红书",
    description="社交购物平台",
    class_names=["购物平台", "社交平台"],
    class_properties={
        "购物平台": {"类型": "社交电商"},
        "社交平台": {"用户数": "2亿"}
    }
)
```

### 3. 动态扩展 System

支持在图创建后动态添加类定义，立即生效：

```python
# 动态添加新类
graph.add_class_definition(ClassDefinition(
    name="社交平台",
    description="社交平台类",
    properties=[...]
))

# 立即可以使用
entity = graph.create_entity(
    name="微信",
    class_names=["社交平台"]  # ✓ 新类立即可用
)
```

### 4. 给已有实体添加类

便捷方法为已存在的实体添加新类：

```python
graph.add_class_to_entity(
    entity_name="淘宝",
    class_name="社交平台",
    properties={"用户数": "8亿"}
)
```

## 向后兼容

旧代码仍然可以显式传递 `system` 参数：

```python
entity.add_class("购物平台", system=my_system)  # ✓ 仍然支持
```

## 内部实现

- Entity 持有 `_graph` 属性（弱引用语义，避免循环引用）
- `Entity.add_class()` 和 `set_property_value()` 优先使用绑定的 system
- `Graph.add_entity()` 自动设置 entity._graph = self
- Graph 不再缓存"类主节点"，每次直接查询 system（单一真相源）

## 测试

参见 `test_entity_graph_binding.py` 了解完整示例。
