"""
结构化导出 Simple GraphRAG 的图数据。

导出内容：
- 系统架构：类主节点、类节点、以及隐式结构边（has_class / instance_of_class）
- 现有实体：实体、实体所属类、属性值
- 实体类：类定义（System）、类主节点、类到实体的映射与统计
- 关系：显式 Relationship 列表，并标注端点类型（entity / class_node / class_master）

用法示例：
  python .\simple_graphrag\export_structured_graph.py --graph .\simple_graphrag\output\graph.pkl --format json --out .\simple_graphrag\output\graph_structured.json
  python .\simple_graphrag\export_structured_graph.py --graph .\simple_graphrag\output\graph.pkl --format md  --out .\simple_graphrag\output\graph_structured.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple


# 确保从任何工作目录运行都能导入 simple_graphrag/src 下的模块（import src.*）
PROJECT_ROOT = Path(__file__).resolve().parent  # .../simple_graphrag
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.entity import (
    ClassDefinition,
    ClassNode,
    ClassMasterNode,
    Entity,
)
from src.models.graph import Graph
from src.models.relationship import Relationship


NodeType = Literal["entity", "class_node", "class_master", "unknown"]


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _safe_sort_key(s: str) -> Tuple[str, str]:
    # 兼容中文/英文混排：先按 upper，再按原值兜底
    return (s.upper(), s)


def _node_type(
    node_id: str,
    entity_ids: set[str],
    class_node_ids: set[str],
    class_master_ids: set[str],
) -> NodeType:
    k = node_id.upper()
    if k in entity_ids:
        return "entity"
    if k in class_node_ids:
        return "class_node"
    if k in class_master_ids:
        return "class_master"
    return "unknown"


def _entity_to_dict(entity: Entity) -> Dict[str, Any]:
    return {
        "name": entity.name,
        "description": entity.description,
        "classes": [
            {
                "class_name": ci.class_name,
                "class_node_id": f"{entity.name}:{ci.class_name}",
                "properties": {
                    prop_name: {"property_name": pv.property_name, "value": pv.value}
                    for prop_name, pv in ci.properties.items()
                },
            }
            for ci in entity.classes
        ],
        "created_at": _iso(entity.created_at),
        "updated_at": _iso(entity.updated_at),
    }


def _relationship_to_dict(
    rel: Relationship,
    entity_ids: set[str],
    class_node_ids: set[str],
    class_master_ids: set[str],
) -> Dict[str, Any]:
    src_t = _node_type(rel.source, entity_ids, class_node_ids, class_master_ids)
    tgt_t = _node_type(rel.target, entity_ids, class_node_ids, class_master_ids)
    return {
        "source": {"id": rel.source, "type": src_t},
        "target": {"id": rel.target, "type": tgt_t},
        "description": rel.description,
        "count": rel.count,
        "created_at": _iso(rel.created_at),
        "updated_at": _iso(rel.updated_at),
    }


def _class_definition_to_dict(class_def: ClassDefinition) -> Dict[str, Any]:
    # ClassDefinition / PropertyDefinition 都是 dataclass
    return class_def.to_dict()


def build_structured_graph_export(graph: Graph) -> Dict[str, Any]:
    """
    将 Graph 转为结构化数据（适合 JSON 序列化）。
    """
    entities = sorted(graph.get_entities(), key=lambda e: _safe_sort_key(e.name))
    class_nodes = sorted(
        graph.get_class_nodes(), key=lambda n: _safe_sort_key(n.node_id)
    )
    class_master_nodes = sorted(
        graph.get_class_master_nodes(), key=lambda n: _safe_sort_key(n.node_id)
    )
    relationships = graph.get_relationships()

    entity_ids = {e.name.upper() for e in entities}
    class_node_ids = {n.node_id.upper() for n in class_nodes}
    class_master_ids = {n.node_id.upper() for n in class_master_nodes}

    # ---- 1) 实体/关系明细
    entities_out = [_entity_to_dict(e) for e in entities]
    relationships_out = [
        _relationship_to_dict(r, entity_ids, class_node_ids, class_master_ids)
        for r in sorted(
            relationships,
            key=lambda r: (
                _safe_sort_key(r.source),
                _safe_sort_key(r.target),
                r.description,
            ),
        )
    ]

    # ---- 2) 类/实体映射与统计
    class_to_entities: Dict[str, List[str]] = defaultdict(list)
    class_property_coverage: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"present": 0, "has_value": 0})
    )

    for e in entities:
        for ci in e.classes:
            cn = ci.class_name
            class_to_entities[cn].append(e.name)
            for prop_name, pv in ci.properties.items():
                class_property_coverage[cn][prop_name]["present"] += 1
                if pv.value is not None and str(pv.value).strip() != "":
                    class_property_coverage[cn][prop_name]["has_value"] += 1

    for cn, names in class_to_entities.items():
        names.sort(key=_safe_sort_key)

    # ---- 3) 类定义（System 是唯一真相源）
    class_defs: Dict[str, Dict[str, Any]] = (
        graph.system.get_all_class_definitions_dict()
    )

    # ---- 4) 系统架构（隐式结构边）
    # 与 Graph.to_networkx 保持一致：class_node -> entity (has_class)
    #                         class_node -> class_master (instance_of_class)
    architecture_edges: List[Dict[str, Any]] = []
    for cn in class_nodes:
        architecture_edges.append(
            {
                "source": {"id": cn.node_id, "type": "class_node"},
                "target": {"id": cn.entity_name, "type": "entity"},
                "edge_type": "has_class",
                "description": f"{cn.entity_name}拥有{cn.class_name}类",
            }
        )
        architecture_edges.append(
            {
                "source": {"id": cn.node_id, "type": "class_node"},
                "target": {"id": cn.class_name, "type": "class_master"},
                "edge_type": "instance_of_class",
                "description": f"{cn.node_id}属于{cn.class_name}类",
            }
        )

    # ---- 5) 输出汇总
    out: Dict[str, Any] = {
        "statistics": {
            "entity_count": graph.get_entity_count(),
            "class_node_count": graph.get_class_node_count(),
            "class_master_node_count": graph.get_class_master_node_count(),
            "total_node_count": graph.get_total_node_count(),
            "relationship_count": graph.get_relationship_count(),
        },
        "system_architecture": {
            "class_master_nodes": [
                {
                    "class_name": n.class_name,
                    "node_id": n.node_id,
                    "description": n.description,
                    "created_at": _iso(n.created_at),
                    "updated_at": _iso(n.updated_at),
                }
                for n in class_master_nodes
            ],
            "class_nodes": [
                {
                    "node_id": n.node_id,
                    "entity_name": n.entity_name,
                    "class_name": n.class_name,
                    "description": n.description,
                    "created_at": _iso(n.created_at),
                    "updated_at": _iso(n.updated_at),
                }
                for n in class_nodes
            ],
            "structure_edges": architecture_edges,
        },
        "entities": entities_out,
        "entity_classes": {
            "class_definitions": class_defs,
            "class_to_entities": {
                k: v
                for k, v in sorted(
                    class_to_entities.items(), key=lambda kv: _safe_sort_key(kv[0])
                )
            },
            "class_property_coverage": {
                cls_name: {
                    prop_name: stats
                    for prop_name, stats in sorted(
                        props.items(), key=lambda kv: _safe_sort_key(kv[0])
                    )
                }
                for cls_name, props in sorted(
                    class_property_coverage.items(),
                    key=lambda kv: _safe_sort_key(kv[0]),
                )
            },
        },
        "relationships": relationships_out,
        "generated_at": datetime.now().isoformat(),
    }

    return out


def to_markdown(structured: Dict[str, Any]) -> str:
    stats = structured.get("statistics", {})
    classes = structured.get("entity_classes", {})
    class_to_entities = classes.get("class_to_entities", {})
    entities = structured.get("entities", [])
    relationships = structured.get("relationships", [])

    lines: List[str] = []
    lines.append("# Simple GraphRAG 图数据结构化导出")
    lines.append("")
    lines.append("## 统计")
    for k in [
        "entity_count",
        "class_node_count",
        "class_master_node_count",
        "total_node_count",
        "relationship_count",
    ]:
        if k in stats:
            lines.append(f"- **{k}**: {stats[k]}")
    lines.append("")

    lines.append("## 系统架构（按类汇总）")
    for class_name, ents in class_to_entities.items():
        lines.append(f"- **{class_name}**: {len(ents)} 个实体")
        if ents:
            lines.append(f"  - 实体: {', '.join(ents)}")
    lines.append("")

    lines.append("## 实体")
    for e in entities:
        lines.append(f"### {e.get('name')}")
        desc = e.get("description", "")
        if desc:
            lines.append(f"- **描述**: {desc}")
        cls_list = e.get("classes", []) or []
        if cls_list:
            lines.append("- **类**:")
            for ci in cls_list:
                lines.append(
                    f"  - **{ci.get('class_name')}** (`{ci.get('class_node_id')}`)"
                )
                props = ci.get("properties", {}) or {}
                if props:
                    # 只展示有值的属性
                    shown = []
                    for _, pv in props.items():
                        if pv is None:
                            continue
                        val = pv.get("value")
                        if val is None or str(val).strip() == "":
                            continue
                        shown.append(f"{pv.get('property_name')}={val}")
                    if shown:
                        lines.append(f"    - 属性: {', '.join(shown)}")
        lines.append("")

    lines.append("## 关系（显式 Relationship）")
    for r in relationships:
        s = r.get("source", {})
        t = r.get("target", {})
        lines.append(
            f"- **{s.get('id')}** ({s.get('type')}) -> **{t.get('id')}** ({t.get('type')}): {r.get('description')} (次数={r.get('count')})"
        )
    lines.append("")

    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="结构化导出 Simple GraphRAG 的图数据")
    parser.add_argument(
        "--graph",
        type=str,
        default="./output/graph.pkl",
        help="Graph pickle 路径（通常为 simple_graphrag/output/graph.pkl）",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="json",
        choices=["json", "md", "markdown"],
        help="输出格式：json 或 md",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="输出文件路径（不填则输出到 stdout）",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON 美化输出（缩进）",
    )
    args = parser.parse_args()
    if args.format == "markdown":
        args.format = "md"

    if args.out == "" or args.out is None:
        args.out = f"./output/graph_structured.{args.format}"

    graph_path = Path(args.graph)
    if not graph_path.exists():
        raise FileNotFoundError(f"找不到图文件: {graph_path}")

    graph = Graph.load(graph_path)
    structured = build_structured_graph_export(graph)

    fmt = args.format.lower()
    if fmt == "json":
        if args.pretty:
            content = json.dumps(structured, ensure_ascii=False, indent=2)
        else:
            content = json.dumps(structured, ensure_ascii=False)
    else:
        content = to_markdown(structured)

    if args.out:
        out_path = Path(args.out)
        _write_text(out_path, content)
    else:
        print(content)


if __name__ == "__main__":
    main()
