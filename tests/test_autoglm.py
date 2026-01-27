import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.AutoGLM import PhoneAgent
from src.AutoGLM.model import ModelConfig

#初始化键盘支持问题
import subprocess
subprocess.run(["adb", "shell", "settings", "put", "secure", "show_ime_with_hard_keyboard", "1"])
subprocess.run(["adb", "shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"])
#subprocess.run(["adb", "shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"])

# Configure model
model_config = ModelConfig(
    base_url="https://api-inference.modelscope.cn/v1",
    model_name="ZhipuAI/AutoGLM-Phone-9B",
    api_key='ms-0f350401-afb3-48ce-b585-9caeb45d1276',
)
# model_config = ModelConfig(
#     base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
#     model_name="glm-4.6v-flash",
#     api_key='5c548a94d1f641cd80238cebc5bb0422.Az50KakhJPjgi1og',
# )

# 创建 Agent
agent = PhoneAgent(model_config=model_config)

# 执行任务
result = agent.run("去美团点一个紫燕百味鸡外卖")
print(result)