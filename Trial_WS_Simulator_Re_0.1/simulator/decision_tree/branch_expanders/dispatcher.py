# -*- coding: utf-8 -*-
"""
分支展開統一分發器 (Branch Expanders Dispatcher)
"""
from typing import List, Optional
from ..tree_model import TreeNode
from .base import EffectRegistry, ExpansionContext

def resolve_operation(parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> Optional[List[TreeNode]]:
    """
    統一操作分發函數
    若匹配到已解耦註冊的 Handler 則返回展開節點列表；未匹配則返回 None 走兜底流程。
    """
    if not op or not isinstance(op, dict):
        return [parent_node]

    op_type = op.get("type", "")
    handler = EffectRegistry.get_handler(op_type)

    if handler:
        return handler.expand(parent_node, op, ctx)
    
    return None