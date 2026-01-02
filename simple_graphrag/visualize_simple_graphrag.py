"""
Simple GraphRAG 图数据可视化脚本
从 graph.pkl 文件加载图数据并生成交互式可视化
每个实体与其类节点归为一组（使用相同的 group ID）
"""

from pathlib import Path
from graph_visualizer import GraphVisualizer
from src.models.graph import Graph


def visualize_graph_from_pkl(
    graph_pkl_path: str = "output/graph.pkl",
    output_html_path: str = "output/graph_visualization.html",
    title: str = "Simple GraphRAG 知识图谱",
):
    """
    从 graph.pkl 文件加载图数据并生成可视化

    Args:
        graph_pkl_path: Graph pickle 文件路径（相对于脚本目录）
        output_html_path: 输出 HTML 文件路径（相对于脚本目录）
        title: 可视化标题
    """
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    graph_file = script_dir / graph_pkl_path
    output_file = script_dir / output_html_path

    # 检查文件是否存在
    if not graph_file.exists():
        print(f"错误: 图文件不存在: {graph_file}")
        print(f"请确保文件路径正确，或先运行 pipeline 生成图数据")
        return

    print(f"正在加载图数据: {graph_file}")

    try:
        # 加载图
        graph = Graph.load(graph_file)
        print(f"图数据加载成功！")
        print(f"  - 实体节点: {graph.get_entity_count()} 个")
        print(f"  - 类节点: {graph.get_class_node_count()} 个")
        print(f"  - 关系: {graph.get_relationship_count()} 个")
    except Exception as e:
        print(f"加载图数据失败: {e}")
        return

    # 创建可视化器
    gv = GraphVisualizer(title=title)

    # 使用 from_simple_graphrag 方法从 Graph 对象加载数据
    print(f"\n正在处理图数据...")
    gv.from_simple_graphrag(graph)
    print(f"图数据已加载到可视化器")

    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 生成可视化
    print(f"\n正在生成可视化文件: {output_file}")
    gv.render_to_html(output_file)

    print(f"\n可视化文件已生成: {output_file}")
    print(f"请在浏览器中打开该文件查看可视化结果")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Simple GraphRAG 图数据可视化工具")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="output/graph.pkl",
        help="输入的 graph.pkl 文件路径（默认: output/graph.pkl）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output/graph_visualization.html",
        help="输出的 HTML 文件路径（默认: output/graph_visualization.html）",
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        default="Simple GraphRAG 知识图谱",
        help="可视化标题（默认: Simple GraphRAG 知识图谱）",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        default=True,
        help="自动在浏览器中打开可视化文件",
    )

    args = parser.parse_args()

    # 生成可视化
    visualize_graph_from_pkl(
        graph_pkl_path=args.input,
        output_html_path=args.output,
        title=args.title,
    )

    # 如果需要，自动打开浏览器
    if args.open:
        import webbrowser

        script_dir = Path(__file__).parent
        output_file = script_dir / args.output
        if output_file.exists():
            visualization_url = output_file.resolve().as_uri()
            print(f"\n正在打开浏览器: {visualization_url}")
            webbrowser.open(visualization_url)
        else:
            print(f"\n错误: 输出文件不存在: {output_file}")


if __name__ == "__main__":
    main()
