# -*- coding: utf-8 -*-
"""
分支展開器抽象基類與註冊上下文 (Branch Expanders Base & Context)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Type, Optional, Any
from ..tree_model import TreeNode


class ExpansionContext:
    """分支展開上下文，傳遞節點計數器、進度回調及局部狀態"""
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
    """Operation 分支展開抽象基類"""

    @abstractmethod
    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        """將單個 operation 展開為下一層的決策/概率子節點列表"""
        pass


class EffectRegistry:
    """Operation 處理器註冊表"""
    _handlers: Dict[str, BaseEffectHandler] = {}

    @classmethod
    def register(cls, op_type: str, handler: BaseEffectHandler):
        cls._handlers[op_type] = handler

    @classmethod
    def get_handler(cls, op_type: str) -> Optional[BaseEffectHandler]:
        return cls._handlers.get(op_type)

    @classmethod
    def get_registered_operations(cls) -> List[str]:
        """獲取所有已註冊的操作名稱列表"""
        return list(cls._handlers.keys())


def register_effect(op_type: str):
    """註冊 Handler 的裝飾器"""
    def decorator(cls: Type[BaseEffectHandler]):
        EffectRegistry.register(op_type, cls())
        return cls
    return decorator