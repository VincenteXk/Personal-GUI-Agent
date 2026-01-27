"""为"用户"类添加必需的属性"""
import requests

base = 'http://localhost:8000'
class_name = '用户'

# 添加所需属性
properties = [
    {'property_name': 'language_style', 'description': '语言风格偏好', 'required': False, 'value_required': False},
    {'property_name': 'common_apps', 'description': '常用应用列表', 'required': False, 'value_required': False},
    {'property_name': 'default_mode', 'description': '默认交互模式', 'required': False, 'value_required': False},
    {'property_name': 'preferences', 'description': '用户偏好JSON', 'required': False, 'value_required': False},
]

for prop in properties:
    r = requests.post(f'{base}/api/system/classes/{class_name}/properties', json=prop)
    name = prop["property_name"]
    print(f'{name}: {r.status_code}')
    if r.status_code != 200:
        print(f'  Error: {r.json()}')
    else:
        print(f'  OK: {r.json().get("message", "success")}')

# 验证
print("\n验证属性:")
r = requests.get(f'{base}/api/system/classes/{class_name}')
print(r.json())
