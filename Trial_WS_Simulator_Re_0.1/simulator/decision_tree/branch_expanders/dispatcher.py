# -*- coding: utf-8 -*-
"""
分支展开统一分发器 (Branch Expanders Dispatcher)
"""
from typing import List, Optional
from ..tree_model import TreeNode
from .base import EffectRegistry, ExpansionContext

def resolve_operation(parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> Optional[List[TreeNode]]:
    """
    统一操作分发函数
    若匹配到已解耦注册的 Handler 则返回展开节点列表；未匹配则返回 None 走兜底流程。
    """
    if not op or not isinstance(op, dict):
        return [parent_node]

    op_type = op.get("type", "")
    handler = EffectRegistry.get_handler(op_type)

    if handler:
        return handler.expand(parent_node, op, ctx)
    
    return None