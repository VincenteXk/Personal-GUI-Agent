# Open-AutoGLM package initialization

# 将父目录添加到系统路径，以便可以导入共享配置
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 定义包的公共接口
__all__ = ['main', 'phone_agent']