"""GraphRAG查询执行器 - 提供知识库查询能力。"""

from dataclasses import dataclass
from typing import Any, Optional
import requests

from task_framework.interfaces import (
    TaskExecutorInterface,
    ExecutionResult,
    TaskCapability,
    TaskParameter,
)


@dataclass
class GraphRAGConfig:
    """GraphRAG配置。"""

    backend_url: str = "http://localhost:8000"  # GraphRAG后端服务地址
    timeout: int = 30  # 请求超时时间（秒）


class GraphRAGQueryExecutor(TaskExecutorInterface):
    """
    GraphRAG查询执行器。

    提供对GraphRAG知识库的查询能力，支持：
    - 关键词查询
    - 实体查询
    - 关系查询
    - 路径查询

    注意：这是一个只读查询器，不支持写入操作。

    Example:
        >>> executor = GraphRAGQueryExecutor(config)
        >>> result = executor.execute_task(
        ...     "graphrag_query",
        ...     {"query": "用户在微信中的常用操作", "query_type": "keyword"},
        ...     {}
        ... )
    """

    def __init__(self, config: Optional[GraphRAGConfig] = None):
        self.config = config or GraphRAGConfig()

    # can_handle 方法现在由父类 TaskExecutorInterface 提供默认实现

    def execute_task(
        self,
        task_type: str,
        task_params: dict[str, Any],
        context: dict[str, Any],
    ) -> ExecutionResult:
        """
        执行GraphRAG查询任务。

        Args:
            task_type: 任务类型
            task_params: 任务参数
                - query: 查询关键词（必需）
                - fuzzy: 是否模糊查询（可选，默认True）
                - limit: 返回结果数量限制（可选，默认10）
            context: 执行上下文

        Returns:
            ExecutionResult 执行结果
        """
        print(f"\n{'='*60}")
        print(f"🔍 GraphRAGQueryExecutor 开始执行")
        print(f"任务类型: {task_type}")
        print(f"任务参数: {task_params}")
        print(f"{'='*60}\n")

        if not self.can_handle(task_type):
            return ExecutionResult(
                success=False,
                message=f"不支持的任务类型: {task_type}",
                data={},
            )

        # 提取查询参数
        query = task_params.get("query")
        if not query:
            return ExecutionResult(
                success=False,
                message="缺少必需的字段: query",
                data={},
            )

        fuzzy = task_params.get("fuzzy", True)
        limit = task_params.get("limit", 10)

        # 执行查询
        try:
            print(f"🔎 查询GraphRAG: '{query}' (fuzzy={fuzzy}, limit={limit})")
            results = self._query_graphrag(query, fuzzy, limit)

            print(f"✅ 查询成功，返回 {len(results)} 条结果\n")
            return ExecutionResult(
                success=True,
                message=f"查询成功，返回 {len(results)} 条结果",
                data={
                    "results": results,
                    "query": query,
                    "fuzzy": fuzzy,
                    "count": len(results),
                },
            )

        except Exception as e:
            print(f"❌ 查询失败: {str(e)}\n")
            return ExecutionResult(
                success=False,
                message=f"查询异常: {str(e)}",
                data={
                    "error": str(e),
                    "query": query,
                },
            )

    def _query_graphrag(
        self, query: str, fuzzy: bool, limit: int
    ) -> list[dict[str, Any]]:
        """
        调用GraphRAG后端API进行关键词查询。

        Args:
            query: 查询关键词
            fuzzy: 是否模糊查询
            limit: 结果数量限制

        Returns:
            查询结果列表

        Raises:
            Exception: 查询失败时抛出异常
        """
        url = f"{self.config.backend_url}/api/search/keyword"

        # 构建请求体（注意：后端使用 POST 方法，参数名是 keyword）
        payload = {
            "keyword": query,
            "fuzzy": fuzzy,
            "limit": limit,
        }

        try:
            # 使用 POST 方法发送请求
            response = requests.post(
                url,
                json=payload,
                timeout=self.config.timeout,
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            raise Exception(
                f"无法连接到GraphRAG后端服务: {self.config.backend_url}。请确保服务已启动。"
            )
        except requests.exceptions.Timeout:
            raise Exception(f"查询超时（{self.config.timeout}秒）")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP错误: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"查询异常: {str(e)}")

    def get_capabilities(self) -> list[TaskCapability]:
        """
        获取执行器的能力列表。

        Returns:
            TaskCapability 列表，描述每种查询类型
        """
        return [
            TaskCapability(
                task_type="graphrag_query",
                name="知识库查询",
                description="从知识图谱中搜索相关信息（关键词查询）",
                parameters=[
                    TaskParameter(
                        name="query",
                        description="查询关键词（支持实体、类、关系、属性的搜索）",
                        required=True,
                        example="用户在微信中的操作",
                        value_type="string",
                    ),
                    TaskParameter(
                        name="fuzzy",
                        description="是否模糊匹配（True=模糊，False=严格匹配）",
                        required=False,
                        example="true",
                        value_type="boolean",
                    ),
                    TaskParameter(
                        name="limit",
                        description="返回结果数量限制",
                        required=False,
                        example="10",
                        value_type="number",
                    ),
                ],
                examples=[
                    {
                        "description": "查询用户偏好",
                        "task_data": {"query": "用户的购物偏好", "limit": 10},
                    },
                    {
                        "description": "查询应用信息",
                        "task_data": {"query": "微信", "fuzzy": False},
                    },
                    {
                        "description": "查询关系",
                        "task_data": {"query": "用户与应用的关系"},
                    },
                ],
                limitations=[
                    "仅支持关键词查询（模糊/严格匹配）",
                    "只读查询，不支持写入操作",
                    "需要GraphRAG后端服务运行（默认 http://localhost:8000）",
                    "查询性能依赖后端数据量和索引状态",
                ],
            ),
        ]
