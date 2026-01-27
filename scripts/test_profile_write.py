"""测试画像写入GraphRAG"""
import requests

# 测试写入
r = requests.put('http://localhost:8000/api/entities/我/properties', 
                 json={'class_name': '用户', 'property_name': 'language_style', 'value': 'casual'})
print(f'写入测试: {r.status_code} - {r.json()}')

# 验证结果
r2 = requests.get('http://localhost:8000/api/entities/我')
data = r2.json()
for cls in data.get('classes', []):
    if cls.get('class_name') == '用户':
        props = cls.get('properties', [])
        print(f'用户类属性: {props}')
