#!/usr/bin/env python3
"""
用户观察者模块 - 监控用户行为并存储到知识库
"""

import os
import sys
import time
import json
import threading
from typing import Dict, Any, List, Optional

# 添加子模块路径
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'learning_mode'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphrag'))

# 导入learning_mode相关模块
from learning_mode.behavior_analyzer import BehaviorAnalyzer, DataCollector
from learning_mode.vlm_analyzer import VLMAnalyzer

# 导入graphrag相关模块
from graphrag.simple_graphrag.simplegraph import SimpleGraph

# 导入本地模块
from knowledge_base import KnowledgeBase


class UserObserver:
    """用户观察者类，用于监控用户行为并存储到知识库"""
    
    def __init__(self, device_id: Optional[str] = None, model_config: Optional[Any] = None):
        """
        初始化用户观察者
        
        Args:
            device_id: 设备ID
            model_config: 模型配置
        """
        self.device_id = device_id
        self.model_config = model_config
        self.knowledge_base = KnowledgeBase()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.vlm_analyzer = None
        self.graphrag = None
        self.data_collector = None
        self.is_learning = False
        self.learning_thread = None
        self._init_modules()
    
    def _init_modules(self):
        """初始化各个模块"""
        # 初始化VLM分析器
        if self.model_config and hasattr(self.model_config, 'api_key') and self.model_config.api_key:
            self.vlm_analyzer = VLMAnalyzer(
                api_key=self.model_config.api_key,
                model=getattr(self.model_config, 'model', 'glm-4.1v-thinking-flash')
            )
        
        # 初始化GraphRAG
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphrag', 'config.yaml')
            if os.path.exists(config_path):
                self.graphrag = SimpleGraph(config_path=config_path)
        except Exception as e:
            print(f"初始化GraphRAG失败: {e}")
        
        # 初始化数据收集器
        self.data_collector = DataCollector(device_id=self.device_id)
    
    def start_learning_loop(self, duration: Optional[int] = None):
        """启动学习循环"""
        if self.is_learning:
            print("学习模式已在运行中")
            return
        
        self.is_learning = True
        print("🎓 启动用户行为学习模式...")
        
        if duration:
            # 有时限的学习模式
            self._start_timed_learning(duration)
        else:
            # 持续学习模式
            self._start_continuous_learning()
    
    def _start_timed_learning(self, duration: int):
        """启动有时限的学习模式"""
        print(f"学习模式将持续 {duration} 秒")
        end_time = time.time() + duration
        
        # 启动数据收集
        self.data_collector.start_collection()
        
        try:
            while time.time() < end_time and self.is_learning:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n接收到停止信号，正在停止学习模式...")
        finally:
            self._stop_learning_and_analyze()
    
    def _start_continuous_learning(self):
        """启动持续学习模式"""
        print("持续学习模式已启动，按Ctrl+C停止")
        
        # 启动数据收集
        self.data_collector.start_collection()
        
        try:
            while self.is_learning:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n接收到停止信号，正在停止学习模式...")
        finally:
            self._stop_learning_and_analyze()
    
    def _stop_learning_and_analyze(self):
        """停止学习并分析收集的数据"""
        self.is_learning = False
        
        # 停止数据收集
        collected_data = self.data_collector.stop_collection()
        
        if not collected_data:
            print("未收集到数据")
            return
        
        print(f"收集到 {len(collected_data)} 条数据，开始分析...")
        
        # 分析收集到的数据
        self._analyze_collected_data(collected_data)
    
    def _analyze_collected_data(self, collected_data: List[Dict[str, Any]]):
        """分析收集到的数据"""
        if not self.vlm_analyzer:
            print("VLM分析器未初始化，跳过分析")
            return
        
        # 对收集到的数据进行分析
        for data in collected_data:
            if 'screenshot_path' in data and os.path.exists(data['screenshot_path']):
                # 使用VLM分析截图
                analysis_result = self.vlm_analyzer.analyze_image(
                    data['screenshot_path'], 
                    context=data.get('context', '')
                )
                
                if 'error' not in analysis_result:
                    # 将分析结果存储到知识库
                    self._store_analysis_result(data, analysis_result)
    
    def _store_analysis_result(self, data: Dict[str, Any], analysis_result: Dict[str, Any]):
        """将分析结果存储到知识库和GraphRAG"""
        # 提取关键信息
        timestamp = data.get('timestamp', time.time())
        app = data.get('app', 'unknown')
        action = analysis_result.get('action', 'unknown action')
        intent = analysis_result.get('intent', 'unknown intent')
        
        # 存储到本地知识库
        interaction = {
            'timestamp': timestamp,
            'app': app,
            'action': action,
            'intent': intent,
            'context': data.get('context', ''),
            'screenshot_path': data.get('screenshot_path', '')
        }
        
        self.knowledge_base.add_interaction(interaction)
        
        # 存储到GraphRAG
        if self.graphrag:
            try:
                # 构建任务描述
                task_description = f"用户行为: 在{app}应用中执行{action}操作，意图为{intent}"
                
                # 提交到GraphRAG
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                task_id = loop.run_until_complete(self.graphrag.submit_task(task_description))
                print(f"分析结果已提交到GraphRAG，任务ID: {task_id}")
                loop.close()
            except Exception as e:
                print(f"存储分析结果到GraphRAG失败: {e}")
    
    def stop_learning(self):
        """停止学习模式"""
        self.is_learning = False
        if self.learning_thread and self.learning_thread.is_alive():
            self.learning_thread.join(timeout=5)
        print("学习模式已停止")
    
    def get_user_habits(self, app: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户习惯"""
        return self.knowledge_base.query_habits(app=app, limit=limit)
    
    def search_related_habits(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索相关用户习惯"""
        return self.knowledge_base.search_habits(query=query, limit=limit)