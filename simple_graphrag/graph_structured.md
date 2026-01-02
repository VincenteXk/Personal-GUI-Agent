# Simple GraphRAG 图数据结构化导出

## 统计
- **entity_count**: 4
- **class_node_count**: 7
- **class_master_node_count**: 11
- **total_node_count**: 22
- **relationship_count**: 6

## 系统架构（按类汇总）
- **人工智能模型**: 1 个实体
  - 实体: Xiaomi MIMO
- **信息流**: 1 个实体
  - 实体: 小米社区
- **可启动应用**: 2 个实体
  - 实体: 小米社区, 手机浏览器
- **搜索工具**: 1 个实体
  - 实体: 手机浏览器
- **用户**: 1 个实体
  - 实体: 我
- **科技产品**: 1 个实体
  - 实体: Xiaomi MIMO

## 实体
### Xiaomi MIMO
- **描述**: 小米公司发布的人工智能大模型
- **类**:
  - **人工智能模型** (`Xiaomi MIMO:人工智能模型`)
    - 属性: 发布状态=最新发布
  - **科技产品** (`Xiaomi MIMO:科技产品`)
    - 属性: 产品类型=人工智能大模型

### 小米社区
- **描述**: 小米公司的官方社区应用
- **类**:
  - **可启动应用** (`小米社区:可启动应用`)
    - 属性: 启动方式=打开APP
  - **信息流** (`小米社区:信息流`)

### 我
- **描述**: 用户本人
- **类**:
  - **用户** (`我:用户`)

### 手机浏览器
- **描述**: 安装在手机上的网页浏览器应用
- **类**:
  - **可启动应用** (`手机浏览器:可启动应用`)
    - 属性: 启动方式=打开
  - **搜索工具** (`手机浏览器:搜索工具`)
    - 属性: 搜索对象=Xiaomi MIMO大模型

## 关系（显式 Relationship）
- **我** (entity) -> **Xiaomi MIMO:人工智能模型** (class_node): 我对最新发布的Xiaomi MIMO大模型产生浓厚兴趣 (strength=8)
- **我** (entity) -> **小米社区:信息流** (class_node): 我在小米社区查看最新的产品动态和科技资讯 (strength=8)
- **我** (entity) -> **小米社区:可启动应用** (class_node): 我习惯每天打开小米社区APP (strength=9)
- **我** (entity) -> **手机浏览器:可启动应用** (class_node): 我随即打开了手机浏览器 (strength=9)
- **我** (entity) -> **手机浏览器:搜索工具** (class_node): 我使用手机浏览器搜索并尝试使用Xiaomi MIMO大模型 (strength=9)
- **手机浏览器:搜索工具** (class_node) -> **Xiaomi MIMO:人工智能模型** (class_node): 手机浏览器被用来搜索Xiaomi MIMO大模型 (strength=8)
