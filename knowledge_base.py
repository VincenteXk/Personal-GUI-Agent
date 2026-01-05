#!/usr/bin/env python3
"""
知识库模块 - 使用图结构存储用户交互数据
"""

import os
import sys
import time
import json
import networkx as nx
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# 添加子模块路径
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphrag'))

# 导入graphrag相关模块
from graphrag.simple_graphrag.simplegraph import SimpleGraph


@dataclass
class UserInteraction:
    """用户交互数据结构"""
    timestamp: float
    app: str
    action: str
    intent: str
    context: Dict[str, Any]
    screenshot_path: Optional[str] = None
    success: Optional[bool] = None


class KnowledgeBase:
    """知识库类，使用图结构存储用户交互数据"""
    
    def __init__(self, storage_path: str = "knowledge_base.json"):
        """
        初始化知识库
        
        Args:
            storage_path: 本地存储路径
        """
        self.storage_path = storage_path
        self.graph = nx.DiGraph()
        self.graphrag = None
        self._load_knowledge_base()
        self._init_graphrag()
    
    def _init_graphrag(self):
        """初始化GraphRAG"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphrag', 'config.yaml')
            if os.path.exists(config_path):
                self.graphrag = SimpleGraph(config_path=config_path)
                print("✅ GraphRAG初始化成功")
            else:
                print("⚠️ 未找到GraphRAG配置文件，仅使用本地知识库")
        except Exception as e:
            print(f"⚠️ GraphRAG初始化失败: {e}，仅使用本地知识库")
    
    def _load_knowledge_base(self):
        """加载本地知识库"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
                print(f"✅ 本地知识库加载成功: {len(self.graph.nodes)} 个节点, {len(self.graph.edges)} 条边")
            except Exception as e:
                print(f"⚠️ 本地知识库加载失败: {e}，创建新知识库")
                self.graph = nx.DiGraph()
        else:
            print("📝 创建新的本地知识库")
            self.graph = nx.DiGraph()
    
    def _save_knowledge_base(self):
        """保存本地知识库"""
        try:
            data = nx.node_link_data(self.graph)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 本地知识库已保存: {len(self.graph.nodes)} 个节点, {len(self.graph.edges)} 条边")
        except Exception as e:
            print(f"⚠️ 本地知识库保存失败: {e}")
    
    def add_interaction(self, interaction: UserInteraction):
        """
        添加用户交互数据
        
        Args:
            interaction: 用户交互数据
        """
        # 创建应用节点
        app_node = f"app:{interaction.app}"
        if not self.graph.has_node(app_node):
            self.graph.add_node(app_node, type="app", name=interaction.app)
        
        # 创建动作节点
        action_node = f"action:{interaction.app}:{interaction.action}"
        if not self.graph.has_node(action_node):
            self.graph.add_node(
                action_node, 
                type="action", 
                app=interaction.app,
                action=interaction.action,
                intent=interaction.intent,
                contexts=[]
            )
        
        # 更新动作节点的上下文列表
        if 'contexts' not in self.graph.nodes[action_node]:
            self.graph.nodes[action_node]['contexts'] = []
        
        self.graph.nodes[action_node]['contexts'].append({
            'timestamp': interaction.timestamp,
            'context': interaction.context,
            'screenshot_path': interaction.screenshot_path,
            'success': interaction.success
        })
        
        # 创建应用到动作的边
        self.graph.add_edge(app_node, action_node, weight=1)
        
        # 保存本地知识库
        self._save_knowledge_base()
        
        # 同时添加到GraphRAG
        if self.graphrag:
            self._add_to_graphrag(interaction)
    
    def _add_to_graphrag(self, interaction: UserInteraction):
        """
        将交互数据添加到GraphRAG
        
        Args:
            interaction: 用户交互数据
        """
        try:
            import asyncio
            
            # 构建实体和关系
            entities = [
                {"name": interaction.app, "type": "Application", "description": f"应用: {interaction.app}"},
                {"name": interaction.action, "type": "Action", "description": f"操作: {interaction.action}"}
            ]
            
            # 如果有意图，添加意图实体
            if interaction.intent:
                entities.append({
                    "name": interaction.intent, 
                    "type": "Intent", 
                    "description": f"意图: {interaction.intent}"
                })
            
            # 构建关系
            relations = [
                {"source": interaction.app, "target": interaction.action, "description": "执行操作"}
            ]
            
            # 如果有意图，添加意图关系
            if interaction.intent:
                relations.append({
                    "source": interaction.action, 
                    "target": interaction.intent, 
                    "description": "表达意图"
                })
            
            # 异步添加到GraphRAG
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 添加实体和关系
            for entity in entities:
                loop.run_until_complete(self.graphrag.add_entity(entity))
            
            for relation in relations:
                loop.run_until_complete(self.graphrag.add_relation(relation))
            
            # 添加交互记录作为文档
            doc_text = f"在{interaction.app}应用中执行{interaction.action}操作"
            if interaction.intent:
                doc_text += f"，意图为{interaction.intent}"
            
            doc = {
                "text": doc_text,
                "metadata": {
                    "timestamp": interaction.timestamp,
                    "app": interaction.app,
                    "action": interaction.action,
                    "intent": interaction.intent
                }
            }
            
            loop.run_until_complete(self.graphrag.add_document(doc))
            loop.close()
            
            print(f"✅ 交互数据已添加到GraphRAG: {interaction.app} -> {interaction.action}")
            
        except Exception as e:
            print(f"⚠️ 添加到GraphRAG失败: {e}")
    
    def search_habits(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相关习惯
        
        Args:
            query: 查询字符串
            limit: 返回结果数量限制
            
        Returns:
            相关习惯列表
        """
        results = []
        
        # 从本地知识库搜索
        for node_id, node_data in self.graph.nodes(data=True):
            if node_data.get('type') == 'action':
                # 简单的关键词匹配
                if (query.lower() in node_data.get('app', '').lower() or 
                    query.lower() in node_data.get('action', '').lower() or
                    query.lower() in node_data.get('intent', '').lower()):
                    
                    # 获取最近的上下文
                    contexts = node_data.get('contexts', [])
                    recent_contexts = sorted(contexts, key=lambda x: x['timestamp'], reverse=True)[:3]
                    
                    results.append({
                        'app': node_data.get('app'),
                        'action': node_data.get('action'),
                        'intent': node_data.get('intent'),
                        'contexts': recent_contexts,
                        'source': 'local_kb'
                    })
        
        # 从GraphRAG搜索
        if self.graphrag:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                query_result = loop.run_until_complete(self.graphrag.query(query))
                
                if query_result and 'results' in query_result:
                    for item in query_result['results'][:limit]:
                        results.append({
                            'text': item.get('text', ''),
                            'metadata': item.get('metadata', {}),
                            'source': 'graphrag'
                        })
                
                loop.close()
                
            except Exception as e:
                print(f"⚠️ 从GraphRAG搜索失败: {e}")
        
        # 按相关性排序并限制结果数量
        return results[:limit]
    
    def get_app_habits(self, app_name: str) -> List[Dict[str, Any]]:
        """
        获取特定应用的习惯
        
        Args:
            app_name: 应用名称
            
        Returns:
            该应用的习惯列表
        """
        app_node = f"app:{app_name}"
        if not self.graph.has_node(app_node):
            return []
        
        habits = []
        for successor in self.graph.successors(app_node):
            if self.graph.nodes[successor].get('type') == 'action':
                node_data = self.graph.nodes[successor]
                contexts = node_data.get('contexts', [])
                recent_contexts = sorted(contexts, key=lambda x: x['timestamp'], reverse=True)[:3]
                
                habits.append({
                    'app': node_data.get('app'),
                    'action': node_data.get('action'),
                    'intent': node_data.get('intent'),
                    'contexts': recent_contexts
                })
        
        return habits
    
    def add_feedback(self, feedback: Dict[str, Any]):
        """
        添加反馈
        
        Args:
            feedback: 反馈数据
        """
        # 将反馈存储到本地知识库
        feedback_node = f"feedback:{int(feedback['timestamp'])}"
        self.graph.add_node(
            feedback_node,
            type="feedback",
            timestamp=feedback['timestamp'],
            original_task=feedback['original_task'],
            refined_task=feedback['refined_task'],
            success=feedback['success']
        )
        
        # 保存本地知识库
        self._save_knowledge_base()
        
        # 同时添加到GraphRAG
        if self.graphrag:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                doc_text = f"指令反馈: 原始指令='{feedback['original_task']}', 优化指令='{feedback['refined_task']}', 成功={feedback['success']}"
                
                doc = {
                    "text": doc_text,
                    "metadata": {
                        "type": "feedback",
                        "timestamp": feedback['timestamp'],
                        "original_task": feedback['original_task'],
                        "refined_task": feedback['refined_task'],
                        "success": feedback['success']
                    }
                }
                
                loop.run_until_complete(self.graphrag.add_document(doc))
                loop.close()
                
                print(f"✅ 反馈已添加到GraphRAG: {feedback['original_task']} -> {feedback['success']}")
                
            except Exception as e:
                print(f"⚠️ 添加反馈到GraphRAG失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取知识库统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_nodes': len(self.graph.nodes),
            'total_edges': len(self.graph.edges),
            'app_nodes': 0,
            'action_nodes': 0,
            'feedback_nodes': 0,
            'total_interactions': 0
        }
        
        for node_id, node_data in self.graph.nodes(data=True):
            node_type = node_data.get('type')
            if node_type == 'app':
                stats['app_nodes'] += 1
            elif node_type == 'action':
                stats['action_nodes'] += 1
                # 统计交互次数
                contexts = node_data.get('contexts', [])
                stats['total_interactions'] += len(contexts)
            elif node_type == 'feedback':
                stats['feedback_nodes'] += 1
        
        return stats