# -*- coding: utf-8 -*-
"""
分支展开器抽象基类与注册上下文 (Branch Expanders Base & Context)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Type, Optional, Any
from ..tree_model import TreeNode


class ExpansionContext:
    """分支展开上下文，传递节点计数器、进度回调及局部状态"""
    def __init__(
        self, 
        slot: Optional[str] = None, 
        cancelled_damage: int = 0, 
        remaining_slots: Optional[List[str]] = None,
        node_counter_ref: Optional[list] = None, 
        on_progress_cb: Optional[Any] = None
    ):
        self.slot = slot
        self.cancelled_damage = cancelled_damage
        self.remaining_slots = remaining_slots or []
        self.node_counter_ref = node_counter_ref
        self.on_progress_cb = on_progress_cb


class BaseEffectHandler(ABC):
    """Operation 分支展开抽象基类"""

    @abstractmethod
    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        """将单个 operation 展开为下一层的决策/概率子节点列表"""
        pass


class EffectRegistry:
    """Operation 处理器注册表"""
    _handlers: Dict[str, BaseEffectHandler] = {}

    @classmethod
    def register(cls, op_type: str, handler: BaseEffectHandler):
        cls._handlers[op_type] = handler

    @classmethod
    def get_handler(cls, op_type: str) -> Optional[BaseEffectHandler]:
        return cls._handlers.get(op_type)

    @classmethod
    def get_registered_operations(cls) -> List[str]:
        """获取所有已注册的操作名称列表"""
        return list(cls._handlers.keys())


def register_effect(op_type: str):
    """注册 Handler 的装饰器"""
    def decorator(cls: Type[BaseEffectHandler]):
        EffectRegistry.register(op_type, cls())
        return cls
    return decorator