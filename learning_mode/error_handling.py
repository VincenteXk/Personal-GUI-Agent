"""
错误处理和日志记录模块
提供统一的错误处理和日志记录功能
"""

import os
import sys
import traceback
import logging
from datetime import datetime
from typing import Optional, Dict, Any


class Logger:
    """统一日志记录器"""
    
    def __init__(self, name: str = "gui_agent", log_dir: str = "logs", log_level: int = logging.INFO):
        self.name = name
        self.log_dir = log_dir
        self.log_level = log_level
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 创建日志目录
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 创建日志记录器
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 创建文件处理器
            log_file = os.path.join(self.log_dir, f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(self.log_level)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            
            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器到日志记录器
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """记录一般信息"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """记录警告信息"""
        self.logger.warning(message)
    
    def error(self, message: str, exception: Optional[Exception] = None):
        """记录错误信息"""
        if exception:
            self.logger.error(f"{message}: {str(exception)}")
            self.logger.debug(traceback.format_exc())
        else:
            self.logger.error(message)
    
    def critical(self, message: str, exception: Optional[Exception] = None):
        """记录严重错误信息"""
        if exception:
            self.logger.critical(f"{message}: {str(exception)}")
            self.logger.debug(traceback.format_exc())
        else:
            self.logger.critical(message)


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger()
    
    def handle_exception(self, exception: Exception, context: str = "", reraise: bool = False) -> Dict[str, Any]:
        """
        处理异常
        
        Args:
            exception: 异常对象
            context: 异常上下文信息
            reraise: 是否重新抛出异常
            
        Returns:
            包含错误信息的字典
        """
        error_info = {
            "error": True,
            "type": type(exception).__name__,
            "message": str(exception),
            "context": context,
            "traceback": traceback.format_exc()
        }
        
        # 记录错误
        self.logger.error(f"{context}: {str(exception)}", exception)
        
        # 如果需要，重新抛出异常
        if reraise:
            raise exception
        
        return error_info
    
    def handle_file_error(self, file_path: str, operation: str, exception: Exception) -> Dict[str, Any]:
        """
        处理文件操作错误
        
        Args:
            file_path: 文件路径
            operation: 操作类型
            exception: 异常对象
            
        Returns:
            包含错误信息的字典
        """
        context = f"文件{operation}失败: {file_path}"
        return self.handle_exception(exception, context)
    
    def handle_api_error(self, api_name: str, exception: Exception) -> Dict[str, Any]:
        """
        处理API调用错误
        
        Args:
            api_name: API名称
            exception: 异常对象
            
        Returns:
            包含错误信息的字典
        """
        context = f"API调用失败: {api_name}"
        return self.handle_exception(exception, context)
    
    def handle_data_error(self, data_type: str, operation: str, exception: Exception) -> Dict[str, Any]:
        """
        处理数据处理错误
        
        Args:
            data_type: 数据类型
            operation: 操作类型
            exception: 异常对象
            
        Returns:
            包含错误信息的字典
        """
        context = f"{data_type}数据{operation}失败"
        return self.handle_exception(exception, context)


# 创建默认的全局日志记录器和错误处理器
default_logger = Logger()
default_error_handler = ErrorHandler(default_logger)


def log_info(message: str):
    """记录信息日志"""
    default_logger.info(message)


def log_warning(message: str):
    """记录警告日志"""
    default_logger.warning(message)


def log_error(message: str, exception: Optional[Exception] = None):
    """记录错误日志"""
    default_logger.error(message, exception)


def log_debug(message: str):
    """记录调试日志"""
    default_logger.debug(message)


def handle_exception(exception: Exception, context: str = "", reraise: bool = False) -> Dict[str, Any]:
    """处理异常"""
    return default_error_handler.handle_exception(exception, context, reraise)


def handle_file_error(file_path: str, operation: str, exception: Exception) -> Dict[str, Any]:
    """处理文件操作错误"""
    return default_error_handler.handle_file_error(file_path, operation, exception)


def handle_api_error(api_name: str, exception: Exception) -> Dict[str, Any]:
    """处理API调用错误"""
    return default_error_handler.handle_api_error(api_name, exception)


def handle_data_error(data_type: str, operation: str, exception: Exception) -> Dict[str, Any]:
    """处理数据处理错误"""
    return default_error_handler.handle_data_error(data_type, operation, exception)


# 装饰器：自动处理异常
def exception_handler(context: str = "", reraise: bool = False, return_on_error: Any = None):
    """
    异常处理装饰器
    
    Args:
        context: 异常上下文信息
        reraise: 是否重新抛出异常
        return_on_error: 发生异常时的返回值
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = handle_exception(e, context or f"{func.__name__}调用", reraise)
                if not reraise:
                    return return_on_error
        return wrapper
    return decorator