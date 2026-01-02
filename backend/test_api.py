"""
测试 API 端点的脚本
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_system_apis():
    """测试 System 管理 API"""
    print("=" * 60)
    print("测试 System 管理 API")
    print("=" * 60)

    # 1. 获取所有类
    print("\n1. 获取所有类定义...")
    response = requests.get(f"{BASE_URL}/api/system/classes")
    if response.status_code == 200:
        classes = response.json()
        print(f"   成功！共有 {len(classes)} 个类")
        for cls in classes[:3]:  # 只显示前3个
            print(f"   - {cls['name']}: {cls.get('description', '')[:50]}...")
    else:
        print(f"   失败：{response.status_code}")

    # 2. 添加新类
    print("\n2. 添加新类 'AI工具'...")
    new_class = {
        "class_name": "AI工具",
        "description": "人工智能相关的工具和服务",
        "properties": [
            {
                "name": "功能类型",
                "description": "工具的主要功能类型",
                "required": True,
                "value_required": True,
            },
            {
                "name": "开发公司",
                "description": "开发该工具的公司",
                "required": False,
                "value_required": False,
            },
        ],
    }
    response = requests.post(f"{BASE_URL}/api/system/classes", json=new_class)
    if response.status_code == 200:
        result = response.json()
        print(f"   成功！类 '{result['name']}' 已添加")
        print(f"   属性数量: {len(result['properties'])}")
    else:
        print(f"   失败：{response.status_code} - {response.text}")

    # 3. 获取特定类
    print("\n3. 获取类 'AI工具' 的定义...")
    response = requests.get(f"{BASE_URL}/api/system/classes/AI工具")
    if response.status_code == 200:
        cls = response.json()
        print(f"   类名: {cls['name']}")
        print(f"   描述: {cls['description']}")
        print(f"   属性:")
        for prop in cls["properties"]:
            print(f"     - {prop['name']}: {prop.get('description', '')}")
    else:
        print(f"   失败：{response.status_code}")

    # 4. 向类添加属性
    print("\n4. 向类 'AI工具' 添加新属性 '发布时间'...")
    new_property = {
        "property_name": "发布时间",
        "description": "工具首次发布的时间",
        "required": False,
        "value_required": False,
    }
    response = requests.post(
        f"{BASE_URL}/api/system/classes/AI工具/properties", json=new_property
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   成功！属性已添加")
        print(f"   类 '{result['name']}' 现有 {len(result['properties'])} 个属性")
    else:
        print(f"   失败：{response.status_code} - {response.text}")


def test_entity_apis():
    """测试 Entity 管理 API"""
    print("\n" + "=" * 60)
    print("测试 Entity 管理 API")
    print("=" * 60)

    # 1. 获取所有实体
    print("\n1. 获取所有实体...")
    response = requests.get(f"{BASE_URL}/api/entities")
    if response.status_code == 200:
        entities = response.json()
        print(f"   成功！共有 {len(entities)} 个实体")
        for entity in entities[:5]:  # 只显示前5个
            print(f"   - {entity['name']}: {entity.get('description', '')[:40]}...")
    else:
        print(f"   失败：{response.status_code}")
        return

    if not entities:
        print("   没有实体可供测试，跳过后续测试")
        return

    # 2. 获取第一个实体的详情
    test_entity = entities[0]["name"]
    print(f"\n2. 获取实体 '{test_entity}' 的详情...")
    response = requests.get(f"{BASE_URL}/api/entities/{test_entity}")
    if response.status_code == 200:
        entity = response.json()
        print(f"   名称: {entity['name']}")
        print(f"   描述: {entity['description']}")
        print(f"   类: {[c['class_name'] for c in entity['classes']]}")
        print(f"   关系数量: {len(entity['relationships'])}")
    else:
        print(f"   失败：{response.status_code}")

    # 3. 更新实体描述
    print(f"\n3. 更新实体 '{test_entity}' 的描述...")
    update_data = {"description": f"{test_entity} 的更新描述（测试）"}
    response = requests.put(f"{BASE_URL}/api/entities/{test_entity}", json=update_data)
    if response.status_code == 200:
        result = response.json()
        print(f"   成功！新描述: {result['description']}")
    else:
        print(f"   失败：{response.status_code} - {response.text}")

    # 4. 为实体添加类（如果AI工具类存在）
    print(f"\n4. 为实体 '{test_entity}' 添加类 'AI工具'...")
    class_data = {
        "class_name": "AI工具",
        "properties": {"功能类型": "测试功能", "开发公司": "测试公司"},
    }
    response = requests.post(
        f"{BASE_URL}/api/entities/{test_entity}/classes", json=class_data
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   成功！实体现有 {len(result['classes'])} 个类")
    else:
        print(f"   失败：{response.status_code} - {response.text}")

    # 5. 更新实体属性
    print(f"\n5. 更新实体 '{test_entity}' 的属性值...")
    property_data = {
        "class_name": "AI工具",
        "property_name": "功能类型",
        "value": "自然语言处理",
    }
    response = requests.put(
        f"{BASE_URL}/api/entities/{test_entity}/properties", json=property_data
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   成功！属性已更新")
        # 查找并显示更新后的值
        for cls in result["classes"]:
            if cls["class_name"] == "AI工具":
                for prop in cls["properties"]:
                    if prop["name"] == "功能类型":
                        print(f"   新值: {prop['value']}")
    else:
        print(f"   失败：{response.status_code} - {response.text}")


def test_graph_apis():
    """测试图数据 API"""
    print("\n" + "=" * 60)
    print("测试图数据 API")
    print("=" * 60)

    # 1. 获取图数据
    print("\n1. 获取图数据...")
    response = requests.get(f"{BASE_URL}/api/graph")
    if response.status_code == 200:
        graph_data = response.json()
        print(f"   成功！")
        print(f"   节点数: {len(graph_data['nodes'])}")
        print(f"   边数: {len(graph_data['links'])}")
    else:
        print(f"   失败：{response.status_code}")

    # 2. 获取统计信息
    print("\n2. 获取统计信息...")
    response = requests.get(f"{BASE_URL}/api/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"   成功！")
        print(f"   System:")
        print(f"     - 类数: {stats['system']['classes']}")
        print(f"     - 预定义实体: {stats['system']['predefined_entities']}")
        print(f"   Graph:")
        print(f"     - 实体数: {stats['graph']['entities']}")
        print(f"     - 关系数: {stats['graph']['relationships']}")
        print(f"   Tasks:")
        print(f"     - 总数: {stats['tasks']['total']}")
        print(f"     - 完成: {stats['tasks']['by_status']['completed']}")
    else:
        print(f"   失败：{response.status_code}")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("SimpleGraphRAG API 测试")
    print("=" * 60)
    print(f"\n目标服务器: {BASE_URL}")
    print("\n请确保后端服务器正在运行：python backend/main.py")
    input("\n按 Enter 键开始测试...")

    try:
        # 测试服务器连接
        print("\n检查服务器连接...")
        response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            print("✓ 服务器连接正常")
        else:
            print(f"✗ 服务器响应异常：{response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"✗ 无法连接到服务器：{e}")
        print(f"\n请先启动后端服务器：")
        print(f"  cd backend")
        print(f"  python main.py")
        return

    # 运行测试
    try:
        test_graph_apis()
        test_system_apis()
        test_entity_apis()

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试过程中出现错误：{e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
