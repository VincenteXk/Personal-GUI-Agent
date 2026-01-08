"""GraphRAG查询执行器 - 提供知识库查询能力。"""

from dataclasses import dataclass
from typing import Any, Optional
import requests

from task_framework.interfaces import TaskExecutorInterface, ExecutionResult


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

    def can_handle(self, task_type: str) -> bool:
        """
        检查是否能处理指定类型的任务。

        支持的任务类型：
        - graphrag_query: 通用查询
        - knowledge_search: 知识搜索
        - entity_query: 实体查询
        - relationship_query: 关系查询
        """
        supported_types = [
            "graphrag_query",
            "knowledge_search",
            "entity_query",
            "relationship_query",
        ]
        return task_type in supported_types

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

    def get_capabilities(self) -> dict[str, Any]:
        """
        获取执行器的能力描述。

        Returns:
            能力字典
        """
        return {
            "name": "GraphRAGQueryExecutor",
            "description": "GraphRAG知识库查询执行器",
            "supported_task_types": [
                "graphrag_query",
                "knowledge_search",
                "entity_query",
                "relationship_query",
            ],
            "features": [
                "关键词查询",
                "实体查询",
                "关系查询",
                "路径查询",
            ],
            "query_types": {
                "keyword": "基于关键词的全文搜索",
                "entity": "查询特定实体的信息",
                "relationship": "查询实体之间的关系",
                "path": "查询实体之间的路径",
            },
            "limitations": [
                "只读查询，不支持写入",
                "需要GraphRAG后端服务运行",
                "查询性能依赖后端服务状态",
            ],
        }
