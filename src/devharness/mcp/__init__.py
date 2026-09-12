from __future__ import annotations

__all__ = ['McpServer']


def __getattr__(name):
    # Preserve the package import without preloading the executable server module.
    if name == 'McpServer':
        from .server import McpServer
        return McpServer
    raise AttributeError(name)
