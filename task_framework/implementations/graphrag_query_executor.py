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
        task_data: dict[str, Any],
        config: dict[str, Any],
    ) -> ExecutionResult:
        """
        执行GraphRAG查询任务。

        Args:
            task_type: 任务类型
            task_data: 任务数据
                - query: 查询字符串（必需）
                - query_type: 查询类型（可选：keyword/entity/relationship/path）
                - limit: 返回结果数量限制（可选，默认5）
            config: 执行配置

        Returns:
            ExecutionResult 执行结果
        """
        if not self.can_handle(task_type):
            return ExecutionResult(
                success=False,
                message=f"不支持的任务类型: {task_type}",
                data={},
            )

        # 提取查询参数
        query = task_data.get("query")
        if not query:
            return ExecutionResult(
                success=False,
                message="缺少必需的字段: query",
                data={},
            )

        query_type = task_data.get("query_type", "keyword")
        limit = task_data.get("limit", 5)

        # 执行查询
        try:
            result = self._query_graphrag(query, query_type, limit)

            if result.get("success", False):
                return ExecutionResult(
                    success=True,
                    message=f"查询成功，返回 {len(result.get('results', []))} 条结果",
                    data={
                        "results": result.get("results", []),
                        "query": query,
                        "query_type": query_type,
                        "count": len(result.get("results", [])),
                    },
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=result.get("error", "查询失败"),
                    data={"query": query, "query_type": query_type},
                )

        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"查询异常: {str(e)}",
                data={
                    "error": str(e),
                    "query": query,
                    "query_type": query_type,
                },
            )

    def _query_graphrag(
        self, query: str, query_type: str, limit: int
    ) -> dict[str, Any]:
        """
        调用GraphRAG后端API进行查询。

        Args:
            query: 查询字符串
            query_type: 查询类型
            limit: 结果数量限制

        Returns:
            查询结果字典
        """
        try:
            # 根据查询类型选择API端点
            endpoint_map = {
                "keyword": "/api/search/keyword",
                "entity": "/api/search/entity",
                "relationship": "/api/search/relationship",
                "path": "/api/search/path",
            }

            endpoint = endpoint_map.get(query_type, "/api/search/keyword")
            url = f"{self.config.backend_url}{endpoint}"

            # 构建请求参数
            params = {
                "query": query,
                "limit": limit,
            }

            # 发送请求
            response = requests.get(
                url,
                params=params,
                timeout=self.config.timeout,
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"无法连接到GraphRAG后端服务: {self.config.backend_url}",
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"查询超时（{self.config.timeout}秒）",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP错误: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"查询异常: {str(e)}",
            }

    def get_capabilities(self) -> list[TaskCapability]:
        """
        获取执行器的能力列表。

        Returns:
            TaskCapability 列表，描述每种查询类型
        """
        return [
            TaskCapability(
                task_type="graphrag_query",
                name="GraphRAG知识库查询",
                description="从知识图谱数据库中查询相关信息，支持多种查询类型",
                parameters=[
                    TaskParameter(
                        name="query",
                        description="查询字符串（自然语言描述你想查什么）",
                        required=True,
                        example="用户在微信中的常用操作",
                        value_type="string",
                    ),
                    TaskParameter(
                        name="query_type",
                        description="查询类型：keyword(关键词搜索), entity(实体查询), relationship(关系查询), path(路径查询)",
                        required=False,
                        example="keyword",
                        value_type="string",
                    ),
                    TaskParameter(
                        name="limit",
                        description="返回结果数量限制",
                        required=False,
                        example="5",
                        value_type="number",
                    ),
                ],
                examples=[
                    {
                        "description": "关键词搜索",
                        "task_data": {
                            "query": "用户的购物偏好",
                            "query_type": "keyword",
                            "limit": 5,
                        },
                    },
                    {
                        "description": "实体查询",
                        "task_data": {
                            "query": "微信",
                            "query_type": "entity",
                            "limit": 3,
                        },
                    },
                    {
                        "description": "关系查询",
                        "task_data": {
                            "query": "用户与应用的关系",
                            "query_type": "relationship",
                        },
                    },
                ],
                limitations=[
                    "只读查询，不支持写入操作",
                    "需要GraphRAG后端服务运行在配置的地址",
                    "查询性能依赖后端服务状态和数据量",
                ],
            ),
            TaskCapability(
                task_type="knowledge_search",
                name="知识搜索",
                description="通用知识搜索（等同于 graphrag_query 的 keyword 模式）",
                parameters=[
                    TaskParameter(
                        name="query",
                        description="搜索关键词或问题",
                        required=True,
                        example="用户喜欢什么类型的商品",
                    ),
                    TaskParameter(
                        name="limit",
                        description="返回结果数量",
                        required=False,
                        example="5",
                        value_type="number",
                    ),
                ],
            ),
            TaskCapability(
                task_type="entity_query",
                name="实体查询",
                description="查询特定实体的详细信息和相关数据",
                parameters=[
                    TaskParameter(
                        name="query",
                        description="实体名称或标识符",
                        required=True,
                        example="微信",
                    ),
                ],
            ),
            TaskCapability(
                task_type="relationship_query",
                name="关系查询",
                description="查询实体之间的关系和连接",
                parameters=[
                    TaskParameter(
                        name="query",
                        description="关系查询描述",
                        required=True,
                        example="用户与常用应用之间的关系",
                    ),
                ],
            ),
        ]
