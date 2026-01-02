"""
通用图数据可视化模块
支持多种数据源：NetworkX图、simple_graphrag的Graph对象、手动添加节点和边
使用 D3.js 生成交互式力导向图可视化
"""

import json
from typing import Optional, Dict, List, Union, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GraphVisualizer:
    """图数据可视化器，支持多种数据源并生成基于 D3.js 的交互式可视化"""

    def __init__(self, title: str = "图数据展示系统"):
        """
        初始化可视化器

        Args:
            title: 可视化标题
        """
        self.nodes: List[Dict[str, Any]] = []
        self.links: List[Dict[str, Any]] = []
        self.title = title
        self._node_id_map: Dict[str, int] = {}  # 用于跟踪节点ID到索引的映射

    def add_node(
        self,
        node_id: str,
        label: Optional[str] = None,
        group: int = 1,
        size: int = 10,
        description: Optional[str] = None,
        **kwargs,
    ):
        """
        添加节点

        Args:
            node_id: 唯一标识符
            label: 显示的文字标签（默认使用node_id）
            group: 分组（不同颜色，默认1）
            size: 节点大小（默认10）
            description: 节点描述（用于tooltip）
            **kwargs: 其他自定义属性
        """
        node_data = {
            "id": str(node_id),
            "label": label if label else str(node_id),
            "group": group,
            "size": size,
        }

        if description:
            node_data["description"] = description

        # 添加其他自定义属性
        node_data.update(kwargs)

        self.nodes.append(node_data)
        self._node_id_map[str(node_id)] = len(self.nodes) - 1

    def add_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        description: Optional[str] = None,
        **kwargs,
    ):
        """
        添加边

        Args:
            source: 源节点ID
            target: 目标节点ID
            weight: 边的权重/粗细（默认1.0）
            description: 边描述（用于tooltip）
            **kwargs: 其他自定义属性
        """
        edge_data = {
            "source": str(source),
            "target": str(target),
            "value": weight,
        }

        if description:
            edge_data["description"] = description

        # 添加其他自定义属性
        edge_data.update(kwargs)

        self.links.append(edge_data)

    def from_networkx(
        self,
        G,
        node_size_attr: Optional[str] = None,
        node_group_attr: Optional[str] = None,
        edge_weight_attr: Optional[str] = None,
    ):
        """
        从 NetworkX 图对象加载数据

        Args:
            G: NetworkX 图对象
            node_size_attr: 节点大小属性名（从节点属性中读取）
            node_group_attr: 节点分组属性名（从节点属性中读取）
            edge_weight_attr: 边权重属性名（从边属性中读取）
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("需要安装networkx: pip install networkx")

        # 清空现有数据
        self.nodes = []
        self.links = []
        self._node_id_map = {}

        # 添加节点
        for node_id, node_data in G.nodes(data=True):
            label = node_data.get("label") or node_data.get("title") or str(node_id)
            description = node_data.get("description") or node_data.get("title")
            size = (
                node_data.get(node_size_attr)
                if node_size_attr
                else node_data.get("size", 10)
            )
            group = (
                node_data.get(node_group_attr)
                if node_group_attr
                else node_data.get("group", 1)
            )

            # 提取其他属性
            extra_attrs = {
                k: v
                for k, v in node_data.items()
                if k
                not in [
                    "label",
                    "title",
                    "description",
                    "size",
                    "group",
                    node_size_attr,
                    node_group_attr,
                ]
            }

            self.add_node(
                node_id=str(node_id),
                label=label,
                group=group,
                size=size,
                description=description,
                **extra_attrs,
            )

        # 添加边
        for source, target, edge_data in G.edges(data=True):
            weight = (
                edge_data.get(edge_weight_attr)
                if edge_weight_attr
                else edge_data.get("weight", 1.0)
            )
            if isinstance(weight, (int, float)):
                weight = float(weight)
            else:
                weight = 1.0

            description = edge_data.get("description") or edge_data.get("title")

            # 提取其他属性
            extra_attrs = {
                k: v
                for k, v in edge_data.items()
                if k not in ["weight", "description", "title", edge_weight_attr]
            }

            self.add_edge(
                source=str(source),
                target=str(target),
                weight=weight,
                description=description,
                **extra_attrs,
            )

    def from_simple_graphrag(self, graph, render_class_master_nodes: bool = True):
        """
        从 simple_graphrag 的 Graph 对象加载数据

        Args:
            graph: simple_graphrag.src.models.graph.Graph 对象
            render_class_master_nodes: 是否渲染类主节点（默认True）
        """
        # 清空现有数据
        self.nodes = []
        self.links = []
        self._node_id_map = {}

        # 先添加类主节点（类本身，跨实体共享）
        if render_class_master_nodes and hasattr(graph, "get_class_master_nodes"):
            for master in graph.get_class_master_nodes():
                self.add_node(
                    node_id=master.node_id,
                    label=master.class_name,
                    group=0,  # 类主节点使用独立分组
                    size=12,
                    description=master.description or f"类主节点: {master.class_name}",
                    node_type="class_master",
                    classes=[master.class_name],
                )

        # 临时存储实体到类节点的连线（稍后计算次数）
        entity_to_class_edges = []

        # 添加实体节点（中心节点）
        for i, entity in enumerate(graph.get_entities()):
            classes = [c.class_name for c in entity.classes]
            self.add_node(
                node_id=entity.name,
                label=entity.name,
                group=i + 1,  # 实体节点组
                size=15,
                description=entity.description or f"实体: {entity.name}",
                node_type="entity",
                classes=classes,
            )

            for class_name in classes:
                class_node_id = f"{entity.name}:{class_name}"
                class_node_desc = f"实体: {entity.name} 拥有 {class_name} 类"
                if hasattr(graph, "get_class_node"):
                    class_node = graph.get_class_node(entity.name, class_name)
                    if class_node and class_node.description:
                        class_node_desc = class_node.description

                self.add_node(
                    node_id=class_node_id,
                    label=class_node_id,
                    group=i + 1,  # 实体节点组
                    size=10,
                    description=class_node_desc,
                    node_type="class_node",
                    classes=[class_name],
                )
                # 暂时不添加边，先存储起来
                entity_to_class_edges.append(
                    {
                        "source": entity.name,
                        "target": class_node_id,
                        "description": f"实体: {entity.name} 拥有 {class_name} 类",
                        "edge_type": "has_class",
                    }
                )

                # 类节点连接到类主节点（如果类主节点存在且启用渲染）
                # 次数暂时为0
                if render_class_master_nodes and hasattr(
                    graph, "get_class_master_node"
                ):
                    if graph.get_class_master_node(class_name) is not None:
                        self.add_edge(
                            source=class_node_id,
                            target=class_name,
                            weight=1.0,  # 线粗细
                            description=f"{class_node_id} 属于 {class_name} 类",
                            edge_type="instance_of_class",
                            count=0,  # 次数为0（暂时）
                        )

        # 添加关系边
        for relationship in graph.get_relationships():
            # 使用次数计算权重（用于显示线条粗细）
            weight = min(relationship.count * 0.5, 10.0)  # 次数越多线越粗，最大10
            self.add_edge(
                source=relationship.source,
                target=relationship.target,
                weight=weight,
                description=relationship.description,
                edge_type="relationship",
                count=relationship.count,  # 保存次数
            )

        # 动态计算实体到类节点的连线次数
        # 统计每个类节点的外部连线次数总和
        class_node_counts = {}
        for link in self.links:
            if link.get("edge_type") == "relationship":
                source = link.get("source")
                target = link.get("target")
                count = link.get("count", 1)

                # 如果源或目标是类节点，累加次数
                if ":" in source:
                    class_node_counts[source] = class_node_counts.get(source, 0) + count
                if ":" in target:
                    class_node_counts[target] = class_node_counts.get(target, 0) + count

        # 现在添加实体到类节点的边，使用计算出的次数
        for edge_info in entity_to_class_edges:
            class_node_id = edge_info["target"]
            count = class_node_counts.get(class_node_id, 0)
            weight = min(count * 0.5, 10.0) if count > 0 else 1.0

            self.add_edge(
                source=edge_info["source"],
                target=edge_info["target"],
                weight=weight,
                description=edge_info["description"],
                edge_type=edge_info["edge_type"],
                count=count,  # 使用计算出的次数
            )

    def render_to_html(
        self,
        output_file: Union[str, Path] = "graph_output.html",
        width: Optional[int] = None,
        height: Optional[int] = None,
        charge_strength: float = -800,
        link_distance: float = 120,
        collision_radius: float = 40,
    ):
        """
        生成 HTML 可视化文件

        Args:
            output_file: 输出文件路径
            width: 画布宽度（默认使用窗口宽度）
            height: 画布高度（默认使用窗口高度）
            charge_strength: 节点斥力强度（默认-400，负值表示排斥）
            link_distance: 连接距离（默认100）
            collision_radius: 碰撞检测半径（默认30）
        """
        # 验证数据
        if not self.nodes:
            raise ValueError("没有节点数据，无法生成可视化。请先添加节点。")

        # 验证边的引用
        node_ids = {node["id"] for node in self.nodes}
        invalid_links = []
        for i, link in enumerate(self.links):
            source = str(link.get("source", ""))
            target = str(link.get("target", ""))
            if source not in node_ids or target not in node_ids:
                invalid_links.append((i, source, target))

        if invalid_links:
            logger.warning(
                f"发现 {len(invalid_links)} 条边引用了不存在的节点，这些边将被忽略。"
            )
            self.links = [
                link
                for i, link in enumerate(self.links)
                if i not in [idx for idx, _, _ in invalid_links]
            ]

        # 检测同起终点的多条边，并为它们添加索引
        edge_count_map = {}  # (source, target) -> count
        for link in self.links:
            source = str(link.get("source", ""))
            target = str(link.get("target", ""))
            key = (source, target)
            edge_count_map[key] = edge_count_map.get(key, 0) + 1

        # 为每条边添加索引和边类型信息
        edge_index_map = {}  # (source, target) -> current_index
        for link in self.links:
            source = str(link.get("source", ""))
            target = str(link.get("target", ""))
            key = (source, target)

            if key not in edge_index_map:
                edge_index_map[key] = 0
            else:
                edge_index_map[key] += 1

            link["edge_index"] = edge_index_map[key]
            link["edge_count"] = edge_count_map[key]
            link["is_curved"] = (
                edge_index_map[key] > 0
            )  # 第一条边（index=0）使用直线，其他使用曲线

        # 统计重复边信息
        duplicate_edges = sum(1 for count in edge_count_map.values() if count > 1)
        if duplicate_edges > 0:
            logger.debug(
                f"检测到 {duplicate_edges} 对节点之间存在多条边，将使用曲线显示"
            )

        # 准备数据
        data = {"nodes": self.nodes, "links": self.links}

        # 验证 group ID 的唯一性（调试用）
        groups = set(node.get("group", 1) for node in self.nodes)
        logger.debug(f"检测到 {len(groups)} 个不同的分组 (Group IDs: {sorted(groups)})")

        json_data = json.dumps(data, ensure_ascii=False, default=str)

        # 使用窗口尺寸或指定尺寸
        width_js = width if width else "window.innerWidth"
        height_js = height if height else "window.innerHeight"

        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        #canvas-container {{
            width: 100vw;
            height: 100vh;
        }}
        
        .links line {{
            stroke: #999;
            stroke-opacity: 0.6;
            stroke-width: 1.5px;
            transition: stroke-opacity 0.2s;
        }}
        
        .links line:hover {{
            stroke-opacity: 1;
            stroke-width: 2.5px;
        }}
        
        .links path {{
            stroke: #999;
            stroke-opacity: 0.6;
            stroke-width: 1.5px;
            fill: none;
            transition: stroke-opacity 0.2s;
        }}
        
        .links path:hover {{
            stroke-opacity: 1;
            stroke-width: 2.5px;
        }}
        
        .nodes path {{
            stroke: #fff;
            stroke-width: 2px;
            cursor: pointer;
            /* 注意：不要对 transform 做 transition，否则拖拽时节点图形会“慢半拍” */
            transition: stroke-width 0.2s, stroke 0.2s;
        }}
        
        .nodes path:hover {{
            stroke-width: 4px;
            stroke: #ff9900;
        }}
        
        .labels text {{
            fill: #e0e0e0;
            font-size: 12px;
            pointer-events: none;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
            font-weight: 500;
        }}
        
        .tooltip {{
            position: absolute;
            padding: 10px 14px;
            background: rgba(0, 0, 0, 0.9);
            color: #fff;
            border-radius: 6px;
            font-size: 13px;
            display: none;
            pointer-events: none;
            z-index: 1000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .tooltip strong {{
            color: #ff9900;
        }}
        
        #header {{
            position: absolute;
            top: 20px;
            left: 20px;
            color: white;
            z-index: 10;
            background: rgba(0, 0, 0, 0.5);
            padding: 15px 20px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}
        
        #header h1 {{
            margin: 0 0 5px 0;
            font-size: 24px;
            font-weight: 600;
        }}
        
        #header p {{
            margin: 0;
            font-size: 13px;
            opacity: 0.8;
        }}
        
        #stats {{
            position: absolute;
            top: 20px;
            right: 20px;
            color: white;
            z-index: 10;
            background: rgba(0, 0, 0, 0.5);
            padding: 15px 20px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
            font-size: 13px;
        }}
        
        #stats div {{
            margin: 5px 0;
        }}
        
        .legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            color: white;
            z-index: 10;
            background: rgba(0, 0, 0, 0.5);
            padding: 15px 20px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
            font-size: 12px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 8px;
            border: 2px solid #fff;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>{self.title}</h1>
        <p>支持拖拽、滚轮缩放、自动布局</p>
    </div>
    
    <div id="stats">
        <div><strong>节点数:</strong> <span id="node-count">{len(self.nodes)}</span></div>
        <div><strong>边数:</strong> <span id="link-count">{len(self.links)}</span></div>
    </div>
    
    <div id="tooltip" class="tooltip"></div>
    <div id="canvas-container"></div>

    <script>
        const data = {json_data};

        const width = {width_js if isinstance(width_js, int) else 'window.innerWidth'};
        const height = {height_js if isinstance(height_js, int) else 'window.innerHeight'};

        const svg = d3.select("#canvas-container")
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .call(d3.zoom()
                .scaleExtent([0.1, 4])
                .on("zoom", (event) => {{
                    container.attr("transform", event.transform);
                }}));

        const container = svg.append("g");

        // 颜色比例尺 - 使用支持更多颜色的方案
        // 组合多个颜色方案以支持更多分组
        const baseColors = d3.schemeSet3.concat(d3.schemeCategory10).concat(d3.schemePastel1);
        // 如果还不够，创建一个颜色生成器来循环使用这些颜色
        const colorScale = d3.scaleOrdinal(baseColors);

        // 为“类节点三角形”提供稳定的两端连接：预先解析它连接的实体节点与类主节点
        const nodeById = new Map(data.nodes.map(n => [String(n.id), n]));
        const classNodeLinkMap = new Map(); // classNodeId -> {{ entityId, classMasterId }}
        data.links.forEach(l => {{
            const s = String(l.source);
            const t = String(l.target);
            if (l.edge_type === "has_class") {{
                // entity -> entity:class
                classNodeLinkMap.set(t, Object.assign({{}}, classNodeLinkMap.get(t), {{ entityId: s }}));
            }} else if (l.edge_type === "instance_of_class") {{
                // entity:class -> class
                classNodeLinkMap.set(s, Object.assign({{}}, classNodeLinkMap.get(s), {{ classMasterId: t }}));
            }}
        }});

        // 动态“延长连线”：根据节点度数/文本字节数，让复杂区域自动拉开
        const getNodeId = (x) => (typeof x === "object" && x !== null ? String(x.id) : String(x));

        // 统计节点度数（incident edges 数）
        const nodeDegree = new Map();
        data.links.forEach(l => {{
            const s = getNodeId(l.source);
            const t = getNodeId(l.target);
            nodeDegree.set(s, (nodeDegree.get(s) || 0) + 1);
            nodeDegree.set(t, (nodeDegree.get(t) || 0) + 1);
        }});

        // 统计节点文本“字节数”（label/description/id），用于信息量更大的节点拉开距离
        const encoder = new TextEncoder();
        const nodeTextBytes = new Map();
        data.nodes.forEach(n => {{
            const id = String(n.id);
            const text = String(n.label || "") + " " + String(n.description || "") + " " + id;
            nodeTextBytes.set(id, encoder.encode(text).length);
        }});

        // 自定义 force：让类节点尽量处于（类主节点, 实体节点）的中点附近，从而形成更稳定的“V”结构
        function classNodeBetweenForce(strength = 0.08) {{
            let nodes = [];
            function force(alpha) {{
                for (const n of nodes) {{
                    if (n.node_type !== "class_node") continue;
                    const rel = classNodeLinkMap.get(String(n.id));
                    if (!rel) continue;
                    const master = rel.classMasterId ? nodeById.get(String(rel.classMasterId)) : null;
                    const entity = rel.entityId ? nodeById.get(String(rel.entityId)) : null;
                    if (!master || !entity) continue;
                    if (master.x == null || master.y == null || entity.x == null || entity.y == null) continue;
                    const tx = (master.x + entity.x) / 2;
                    const ty = (master.y + entity.y) / 2;
                    n.vx += (tx - n.x) * strength * alpha;
                    n.vy += (ty - n.y) * strength * alpha;
                }}
            }}
            force.initialize = function(_nodes) {{ nodes = _nodes; }};
            return force;
        }}

        // 力学模拟器配置（保持自由布局：不做强制分层）
        const simulation = d3.forceSimulation(data.nodes)
            .alphaDecay(0.01) // 减慢能量衰减，让节点有更多时间被斥力推开
            .velocityDecay(0.3) // 降低摩擦力，让移动更顺滑
            .force("link", d3.forceLink(data.links)
                .id(d => d.id)
                .distance(d => {{
                    const sid = getNodeId(d.source);
                    const tid = getNodeId(d.target);
                    const deg1 = nodeDegree.get(sid) || 0;
                    const deg2 = nodeDegree.get(tid) || 0;
                    const degMax = Math.max(deg1, deg2);
                    const byteSum = (nodeTextBytes.get(sid) || 0) + (nodeTextBytes.get(tid) || 0);

                    // 基础距离
                    const base = (d.edge_type === "has_class" || d.edge_type === "instance_of_class")
                        ? Math.max(100, {link_distance} * 0.9)
                        : {link_distance} * 1.2;

                    // 极大增强度数带来的疏散度
                    let degExtra;
                    if (degMax <= 5) {{
                        degExtra = degMax * 30;
                    }} else if (degMax <= 20) {{
                        degExtra = 150 + (degMax - 5) * 15;
                    }} else if (degMax <= 100) {{
                        // 中大型核心，显著拉开
                        degExtra = 400 + (degMax - 20) * 8;
                    }} else {{
                        // 超级核心（上百连接），暴力疏散
                        degExtra = 1000 + (degMax - 100) * 5;
                    }}
                    
                    const byteExtra = Math.sqrt(Math.max(0, byteSum)) * 2.5;
                    const maxExtra = degMax > 100 ? 2500 : 1200;
                    return base + Math.min(maxExtra, degExtra + byteExtra);
                }}))
            .force("charge", d3.forceManyBody().strength(d => {{
                const deg = nodeDegree.get(getNodeId(d)) || 0;
                // 暴力斥力：度数越高，斥力越强
                let strength = {charge_strength};
                
                if (deg > 1) {{
                    // 使用 log2 增长斥力，度数越大推得越远
                    strength *= (1 + Math.log2(deg) * 2.0);
                }}

                if (d.node_type === "class_master") return strength * 0.8;
                if (d.node_type === "class_node") return strength * 0.4;
                return strength;
            }}))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => {{
                const deg = nodeDegree.get(getNodeId(d)) || 0;
                const baseR = (d.size || 10) + {collision_radius} * 0.6;
                // 度数越高，碰撞保护圈越大，确保节点不会重叠且周围有呼吸空间
                return baseR * (1 + Math.min(3, Math.sqrt(deg) * 0.3));
            }}))
            .force("between", classNodeBetweenForce(0.10));

        // 绘制边 - 分离直线和曲线边
        const links = container.append("g").attr("class", "links");
        
        // 直线边（第一条边）
        const straightLinks = links.selectAll("line.straight")
            .data(data.links.filter(d => !d.is_curved))
            .enter().append("line")
            .attr("class", "straight")
            .attr("stroke-width", d => Math.sqrt(d.value || 1) + 1);
        
        // 曲线边（重复边）
        const curvedLinks = links.selectAll("path.curved")
            .data(data.links.filter(d => d.is_curved))
            .enter().append("path")
            .attr("class", "curved")
            .attr("stroke-width", d => Math.sqrt(d.value || 1) + 1)
            .attr("marker-end", "url(#arrowhead)");
        
        // 创建箭头标记（用于曲线边）
        svg.append("defs").append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 15)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "#999");

        // 节点形状：类主节点=方形，实体节点=圆点，类节点=三角形
        const nodeSymbolType = (d) => {{
            if (d.node_type === "class_master") return d3.symbolSquare;
            if (d.node_type === "class_node") return d3.symbolTriangle;
            return d3.symbolCircle;
        }};

        const nodeSymbolSize = (d) => {{
            // d3.symbol.size 是面积；这里用 size 近似控制视觉大小
            const r = d.size || 10;
            return Math.max(60, r * r * 10);
        }};

        // 类节点三角形的朝向：尽量让它“面向”两端（类主节点/实体节点）的角平分方向（近似）
        const triangleRotationDeg = (d) => {{
            if (d.node_type !== "class_node") return 0;
            const rel = classNodeLinkMap.get(String(d.id));
            if (!rel) return 0;
            const master = rel.classMasterId ? nodeById.get(String(rel.classMasterId)) : null;
            const entity = rel.entityId ? nodeById.get(String(rel.entityId)) : null;
            if (!master || !entity) return 0;
            if (master.x == null || master.y == null || entity.x == null || entity.y == null) return 0;
            const a1 = Math.atan2(master.y - d.y, master.x - d.x);
            const a2 = Math.atan2(entity.y - d.y, entity.x - d.x);
            const sinSum = Math.sin(a1) + Math.sin(a2);
            const cosSum = Math.cos(a1) + Math.cos(a2);
            if (sinSum === 0 && cosSum === 0) return 0;
            const bis = Math.atan2(sinSum, cosSum);
            // d3.symbolTriangle 默认朝上；将其朝向角平分方向（经验偏移 -90°）
            return (bis * 180 / Math.PI) - 90;
        }};

        // 绘制节点
        const node = container.append("g")
            .attr("class", "nodes")
            .selectAll("path")
            .data(data.nodes)
            .enter().append("path")
            .attr("d", d3.symbol()
                .type(nodeSymbolType)
                .size(nodeSymbolSize))
            .attr("fill", d => colorScale(d.group || 1))
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

        // 绘制节点文字标签
        const label = container.append("g")
            .attr("class", "labels")
            .selectAll("text")
            .data(data.nodes)
            .enter().append("text")
            .text(d => d.label || d.id)
            .attr("dx", 12)
            .attr("dy", 4);

        // 绘制边的次数标签（只显示次数>0的边）
        const edgeLabels = container.append("g")
            .attr("class", "edge-labels")
            .selectAll("text")
            .data(data.links.filter(d => d.count && d.count > 0))
            .enter().append("text")
            .attr("class", "edge-label")
            .text(d => d.count)
            .attr("font-size", "11px")
            .attr("fill", "#FFD700")
            .attr("font-weight", "bold")
            .attr("text-anchor", "middle")
            .attr("pointer-events", "none")
            .style("text-shadow", "0 0 3px rgba(0, 0, 0, 0.8), 0 0 3px rgba(0, 0, 0, 0.8)");

        // 交互：显示Tooltip
        const tooltip = d3.select("#tooltip");
        
        node.on("mouseover", (event, d) => {{
            let tooltipHtml = `<strong>ID:</strong> ${{d.id}}<br>`;
            if (d.label && d.label !== d.id) {{
                tooltipHtml += `<strong>标签:</strong> ${{d.label}}<br>`;
            }}
            if (d.description) {{
                tooltipHtml += `<strong>描述:</strong> ${{d.description}}<br>`;
            }}
            if (d.group) {{
                tooltipHtml += `<strong>分组:</strong> ${{d.group}}<br>`;
            }}
            // 显示其他自定义属性
            Object.keys(d).forEach(key => {{
                if (!['id', 'label', 'description', 'group', 'size', 'x', 'y', 'fx', 'fy', 'vx', 'vy', 'index'].includes(key)) {{
                    tooltipHtml += `<strong>${{key}}:</strong> ${{d[key]}}<br>`;
                }}
            }});
            
            tooltip.style("display", "block")
                .html(tooltipHtml);
        }})
        .on("mousemove", (event) => {{
            tooltip.style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
        }})
        .on("mouseout", () => {{
            tooltip.style("display", "none");
        }});

        // 边的交互 - 直线边
        straightLinks.on("mouseover", (event, d) => {{
            let tooltipHtml = `<strong>源:</strong> ${{d.source.id || d.source}}<br>`;
            tooltipHtml += `<strong>目标:</strong> ${{d.target.id || d.target}}<br>`;
            if (d.description) {{
                tooltipHtml += `<strong>描述:</strong> ${{d.description}}<br>`;
            }}
            if (d.count !== undefined && d.count !== null) {{
                tooltipHtml += `<strong>次数:</strong> ${{d.count}}<br>`;
            }}
            if (d.edge_count > 1) {{
                tooltipHtml += `<strong>边索引:</strong> ${{d.edge_index + 1}} / ${{d.edge_count}}<br>`;
            }}
            // 显示其他自定义属性
            Object.keys(d).forEach(key => {{
                if (!['source', 'target', 'description', 'value', 'count', 'index', 'edge_index', 'edge_count', 'is_curved', 'edge_type'].includes(key)) {{
                    tooltipHtml += `<strong>${{key}}:</strong> ${{d[key]}}<br>`;
                }}
            }});
            
            tooltip.style("display", "block")
                .html(tooltipHtml);
        }})
        .on("mousemove", (event) => {{
            tooltip.style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
        }})
        .on("mouseout", () => {{
            tooltip.style("display", "none");
        }});
        
        // 边的交互 - 曲线边
        curvedLinks.on("mouseover", (event, d) => {{
            let tooltipHtml = `<strong>源:</strong> ${{d.source.id || d.source}}<br>`;
            tooltipHtml += `<strong>目标:</strong> ${{d.target.id || d.target}}<br>`;
            if (d.description) {{
                tooltipHtml += `<strong>描述:</strong> ${{d.description}}<br>`;
            }}
            if (d.count !== undefined && d.count !== null) {{
                tooltipHtml += `<strong>次数:</strong> ${{d.count}}<br>`;
            }}
            if (d.edge_count > 1) {{
                tooltipHtml += `<strong>边索引:</strong> ${{d.edge_index + 1}} / ${{d.edge_count}}<br>`;
            }}
            // 显示其他自定义属性
            Object.keys(d).forEach(key => {{
                if (!['source', 'target', 'description', 'value', 'count', 'index', 'edge_index', 'edge_count', 'is_curved', 'edge_type'].includes(key)) {{
                    tooltipHtml += `<strong>${{key}}:</strong> ${{d[key]}}<br>`;
                }}
            }});
            
            tooltip.style("display", "block")
                .html(tooltipHtml);
        }})
        .on("mousemove", (event) => {{
            tooltip.style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
        }})
        .on("mouseout", () => {{
            tooltip.style("display", "none");
        }});

        // 更新物理引擎位置
        simulation.on("tick", () => {{
            // 更新直线边
            straightLinks.attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            // 更新曲线边
            curvedLinks.attr("d", d => {{
                const source = d.source;
                const target = d.target;
                const edgeIndex = d.edge_index || 0;
                const edgeCount = d.edge_count || 1;
                
                // 计算曲线的偏移量（根据边的索引）
                const offset = (edgeIndex - (edgeCount - 1) / 2) * 20; // 每条边偏移20像素
                
                // 计算起点和终点的角度
                const dx = target.x - source.x;
                const dy = target.y - source.y;
                const angle = Math.atan2(dy, dx);
                const perpAngle = angle + Math.PI / 2;
                
                // 计算控制点（垂直于连接线的方向）
                const controlX = (source.x + target.x) / 2 + Math.cos(perpAngle) * offset;
                const controlY = (source.y + target.y) / 2 + Math.sin(perpAngle) * offset;
                
                // 使用二次贝塞尔曲线
                return `M${{source.x}},${{source.y}} Q${{controlX}},${{controlY}} ${{target.x}},${{target.y}}`;
            }});

            node.attr("transform", d => {{
                const rot = triangleRotationDeg(d);
                return `translate(${{d.x}},${{d.y}}) rotate(${{rot}})`;
            }});

            label.attr("x", d => d.x)
                .attr("y", d => d.y);

            // 更新边的次数标签位置
            edgeLabels.attr("x", d => {{
                if (d.is_curved) {{
                    const source = d.source;
                    const target = d.target;
                    const edgeIndex = d.edge_index || 0;
                    const edgeCount = d.edge_count || 1;
                    const offset = (edgeIndex - (edgeCount - 1) / 2) * 20;
                    const dx = target.x - source.x;
                    const dy = target.y - source.y;
                    const angle = Math.atan2(dy, dx);
                    const perpAngle = angle + Math.PI / 2;
                    const controlX = (source.x + target.x) / 2 + Math.cos(perpAngle) * offset;
                    return controlX;
                }} else {{
                    return (d.source.x + d.target.x) / 2;
                }}
            }})
            .attr("y", d => {{
                if (d.is_curved) {{
                    const source = d.source;
                    const target = d.target;
                    const edgeIndex = d.edge_index || 0;
                    const edgeCount = d.edge_count || 1;
                    const offset = (edgeIndex - (edgeCount - 1) / 2) * 20;
                    const dx = target.x - source.x;
                    const dy = target.y - source.y;
                    const angle = Math.atan2(dy, dx);
                    const perpAngle = angle + Math.PI / 2;
                    const controlY = (source.y + target.y) / 2 + Math.sin(perpAngle) * offset;
                    return controlY;
                }} else {{
                    return (d.source.y + d.target.y) / 2;
                }}
            }});
        }});

        // 拖拽函数
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
            // 立刻同步图形与标签位置，避免“连线端点跟随但节点图形延迟”
            d.x = event.x;
            d.y = event.y;

            const rot = triangleRotationDeg(d);
            d3.select(this).attr(
                "transform",
                `translate(${{d.x}},${{d.y}}) rotate(${{rot}})`
            );
            label.filter(n => n.id === d.id)
                .attr("x", d.x)
                .attr("y", d.y);
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}

        // 窗口大小自适应
        window.addEventListener("resize", () => {{
            const w = window.innerWidth;
            const h = window.innerHeight;
            svg.attr("width", w).attr("height", h);
            simulation.force("center", d3.forceCenter(w / 2, h / 2)).alpha(0.3).restart();
        }});
    </script>
</body>
</html>"""

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)

        logger.info(f"生成交互式图谱: {output_path}")
        logger.info(f"节点数: {len(self.nodes)}, 边数: {len(self.links)}")
