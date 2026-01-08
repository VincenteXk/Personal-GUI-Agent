"""应用包名配置文件"""

from src.shared.config import APP_PACKAGE_MAPPINGS, get_app_name_from_package, get_package_from_app_name

# 将共享配置中的映射赋值给本地变量（保持向后兼容）
APP_PACKAGES = APP_PACKAGE_MAPPINGS

def get_app_name(package_name: str) -> str:
    """
    根据包名获取应用名称
    
    Args:
        package_name: 应用包名
        
    Returns:
        对应的应用名称，如果找不到则返回原始包名
    """
    # 遍历映射字典查找对应的应用名称
    for pkg, name in APP_NAME_TO_PACKAGE.items():
        if pkg == package_name:
            return name
    return package_name

def get_package_name(app_name: str) -> str | None:
    """
    根据应用名称获取包名
    
    Args:
        app_name: 应用名称
        
    Returns:
        对应的包名，如果找不到则返回None
    """
    return get_package_from_app_name(app_name)

def list_supported_apps() -> list:
    """
    获取支持的应用列表
    
    Returns:
        支持的应用名称列表
    """
    return list(APP_NAME_TO_PACKAGE.keys())