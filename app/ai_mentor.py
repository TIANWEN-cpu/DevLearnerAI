"""AI 导师模块（向后兼容 shim）。

本模块将所有请求委托给 app.ai 子模块，保持旧导入路径的兼容性。
新代码应直接从 app.ai 子模块导入。

公开接口: AIMentorPanel、AIMentorDock。
"""

from app.ai.chat_handler import AIMentorDock, AIMentorPanel  # noqa: F401

__all__ = [
    "AIMentorPanel",
    "AIMentorDock",
]
