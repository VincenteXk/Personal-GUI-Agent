"""测试"我"实体的关系查询"""
import requests

r = requests.get('http://localhost:8000/api/entities/我')
data = r.json()
rels = data.get('relationships', [])
print(f'共 {len(rels)} 个关系:')
for rel in rels[:10]:
    desc = rel.get('description', '')[:50] if rel.get('description') else 'N/A'
    print(f"  - {rel.get('source')} -> {rel.get('target')}")
    print(f"    描述: {desc}")
