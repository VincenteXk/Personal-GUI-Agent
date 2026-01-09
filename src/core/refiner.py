#!/usr/bin/env python3
"""
指令优化器模块 - 结合用户习惯优化指令
"""
#我暂时注释掉了两处对graphrag的使用，来调试之前的学习部分

import os
import sys
import json
import time
from typing import Dict, Any, List, Optional

# 导入graphrag相关模块
#from graphrag.simple_graphrag.simplegraph import SimpleGraph

# 导入本地模块
from src.learning.utils import run_async


class InstructionRefiner:
    """指令优化器类，使用知识库中的用户习惯优化指令"""
    
    def __init__(self, model_config: Optional[Any] = None):
        """
        初始化指令优化器
        
        Args:
            model_config: 模型配置
        """
        self.model_config = model_config
        self.graphrag = None
        self._init_modules()
    
    def _init_modules(self):
        """初始化各个模块"""
        # 初始化GraphRAG
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphrag', 'config.yaml')
        # if os.path.exists(config_path):
        #     self.graphrag = SimpleGraph(config_path=config_path)
    
    def refine_task(self, task: str) -> str:
        """
        优化任务指令
        
        Args:
            task: 原始任务指令
            
        Returns:
            优化后的任务指令
        """
        print(f"🔍 优化指令: {task}")
        
        # 1. 从本地知识库查询相关习惯
        local_habits = self.knowledge_base.search_habits(query=task, limit=5)
        
        # 2. 从GraphRAG查询相关习惯
        graphrag_habits = []
        if self.graphrag:
            try:
                async def _do_query():
                    return await self.graphrag.query(task)

                # 查询相关习惯
                query_result = run_async(_do_query())

                if query_result and 'results' in query_result:
                    for item in query_result['results'][:5]:
                        graphrag_habits.append(item.get('text', ''))

            except Exception as e:
                print(f"从GraphRAG查询失败: {e}")
        
        # 3. 结合习惯优化指令
        refined_task = self._combine_habits_with_task(task, local_habits, graphrag_habits)
        
        print(f"✅ 优化后指令: {refined_task}")
        return refined_task
    
    def _combine_habits_with_task(self, task: str, local_habits: List[Dict[str, Any]], graphrag_habits: List[str]) -> str:
        """
        结合用户习惯优化任务指令
        
        Args:
            task: 原始任务指令
            local_habits: 本地知识库中的习惯
            graphrag_habits: GraphRAG中的习惯
            
        Returns:
            优化后的任务指令
        """
        # 如果没有相关习惯，直接返回原始指令
        if not local_habits and not graphrag_habits:
            return task
        
        # 提取习惯中的关键信息
        habit_contexts = []
        
        # 处理本地习惯
        for habit in local_habits:
            if 'action' in habit and 'intent' in habit:
                habit_contexts.append(f"习惯: 在{habit.get('app', '未知应用')}中{habit['action']}，意图为{habit['intent']}")
        
        # 处理GraphRAG习惯
        for habit_text in graphrag_habits:
            if habit_text.strip():
                habit_contexts.append(f"习惯: {habit_text}")
        
        # 如果没有提取到有效的习惯信息，返回原始指令
        if not habit_contexts:
            return task
        
        # 构建优化后的指令
        habit_context = "\n".join(habit_contexts[:3])  # 最多使用3个最相关的习惯
        
        refined_prompt = f"""
基于以下用户习惯，优化执行指令：

原始指令: {task}

用户习惯:
{habit_context}

请根据用户习惯优化指令，使其更符合用户的操作习惯和偏好。优化后的指令应该:
1. 保持原始指令的核心目标
2. 融入用户的操作习惯
3. 更加具体和可执行
"""
        
        # 如果有模型配置，使用模型优化指令
        if self.model_config:
            try:
                from src.AutoGLM.model import ModelClient
                from src.AutoGLM.model.client import MessageBuilder

                model_client = ModelClient(self.model_config)
                
                messages = []
                messages.append(MessageBuilder.create_system_message("你是一个指令优化助手，擅长根据用户习惯优化执行指令。"))
                messages.append(MessageBuilder.create_user_message(refined_prompt))
                
                response = model_client.request(messages)
                refined_task = response.raw_content.strip()
                
                # 简单处理可能的格式问题
                if refined_task.startswith('"') and refined_task.endswith('"'):
                    refined_task = refined_task[1:-1]
                
                return refined_task
            except Exception as e:
                print(f"使用模型优化指令失败: {e}")
        
        # 如果没有模型配置或模型优化失败，使用简单的规则优化
        return self._simple_rule_based_refinement(task, habit_contexts)
    
    def _simple_rule_based_refinement(self, task: str, habit_contexts: List[str]) -> str:
        """
        基于简单规则的指令优化
        
        Args:
            task: 原始任务指令
            habit_contexts: 习惯上下文列表
            
        Returns:
            优化后的任务指令
        """
        # 这里可以实现一些简单的规则来优化指令
        # 例如，如果用户习惯在特定应用中使用特定操作，可以将其添加到指令中
        
        # 提取最相关的习惯
        relevant_habits = []
        for habit in habit_contexts:
            # 简单的关键词匹配
            if any(keyword in task.lower() for keyword in ["打开", "启动", "运行", "使用"]):
                if "应用" in habit or "app" in habit.lower():
                    relevant_habits.append(habit)
        
        # 如果找到相关习惯，将其添加到指令中
        if relevant_habits:
            habit_info = "\n".join(relevant_habits[:1])  # 只使用最相关的一个习惯
            return f"{task}\n\n注意: {habit_info}"
        
        return task
    
    def add_feedback(self, original_task: str, refined_task: str, success: bool):
        """
        添加反馈，用于优化未来的指令
        
        Args:
            original_task: 原始任务指令
            refined_task: 优化后的任务指令
            success: 任务是否成功执行
        """
        feedback = {
            'timestamp': time.time(),
            'original_task': original_task,
            'refined_task': refined_task,
            'success': success
        }
        
        # 将反馈存储到知识库
        self.knowledge_base.add_feedback(feedback)