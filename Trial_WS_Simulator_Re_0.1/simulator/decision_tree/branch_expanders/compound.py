# -*- coding: utf-8 -*-
"""
复合与阶段类 Operation 处理器 (Compound Operations Handlers)
包含：多步骤操作链式展开
"""
from typing import List
from ..tree_model import TreeNode
from .base import BaseEffectHandler, ExpansionContext, register_effect
from .dispatcher import resolve_operation


@register_effect("多步骤操作")
class MultiStepOperationHandler(BaseEffectHandler):
    """【多步骤操作】解耦处理器：顺序链式展开包含的子操作列表"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        steps = op.get("steps", [])

        # 兼容旧配置：若未配置 steps，默认展开 [普通伤害, 推顶烧]
        if not steps:
            initial_dmg = op.get("initial_damage", 1)
            push_burn_sub_op = dict(op)
            push_burn_sub_op["type"] = "推顶烧"
            push_burn_sub_op.setdefault("push_count", 1)
            push_burn_sub_op.setdefault("base_damage", op.get("burn_damage", 1))
            push_burn_sub_op.setdefault("damage_bonus", op.get("burn_bonus_type", "等级"))
            push_burn_sub_op.setdefault("base_times", 1)
            push_burn_sub_op.setdefault("times_bonus", "0")

            steps = [
                {"type": "普通伤害", "damage": initial_dmg},
                push_burn_sub_op
            ]

        current_leaves = [parent_node]

        for step_op in steps:
            next_leaves = []
            for leaf in current_leaves:
                if leaf.state_snapshot.game_over or leaf.state_snapshot.my_failed:
                    next_leaves.append(leaf)
                    continue

                res_nodes = resolve_operation(leaf, step_op, ctx)
                if res_nodes is not None:
                    next_leaves.extend(res_nodes)
                else:
                    next_leaves.append(leaf)

            current_leaves = next_leaves

        return current_leaves