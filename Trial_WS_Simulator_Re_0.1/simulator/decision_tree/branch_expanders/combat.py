# -*- coding: utf-8 -*-
"""
战斗与伤害类 Operation 处理器 (Combat Operations Handlers)
包含：普通伤害、角色伤害、取消伤害、取消触发 4 种战斗机制的展开逻辑
"""
from typing import List
from ..tree_model import TreeNode, sanitize_card_dict
from ..tree_helpers import calc_damage_branches
from .base import BaseEffectHandler, ExpansionContext, register_effect


def expand_role_damage_helper(
    parent_node: TreeNode, damage: int, op_name: str, ctx: ExpansionContext
) -> List[TreeNode]:
    """战斗伤害分支展开核心辅助函数"""
    snapshot = parent_node.state_snapshot
    branches = calc_damage_branches(snapshot, damage)
    child_nodes = []

    for desc, p, used_N, used_C, cancel_pos in branches:
        next_state = snapshot.clone()
        next_state.enemy_deck_normal -= used_N
        next_state.enemy_deck_climax -= used_C

        if cancel_pos > 0:
            next_state.enemy_control_normal += used_N
            next_state.enemy_control_climax += used_C
            node_title = f"🎲 [{p*100:.1f}%] 伤害在第 {cancel_pos} 张取消"
            details = f"判定: {damage} 点伤害在第 {cancel_pos} 张取消。敌控室肉+{used_N}, 潮+1。"
        else:
            next_state.apply_enemy_damage(damage)
            node_title = f"🎲 [{p*100:.1f}%] 全部命中 {damage} 点"
            details = f"判定: {damage} 点伤害全部命中！敌计时区肉+{damage}。"

        child = TreeNode(
            name=node_title, 
            node_type="terminal" if next_state.game_over or next_state.my_failed else "chance",
            prob=p, state_snapshot=next_state, details=details, remaining_plan=parent_node.remaining_plan,
            node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
        )
        parent_node.add_child(child)
        child_nodes.append(child)

    return child_nodes


@register_effect("取消触发")
class CancelTriggerHandler(BaseEffectHandler):
    """【取消触发】解耦处理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        if ctx.slot and parent_node.state_snapshot:
            cards = parent_node.state_snapshot.condition_front_cards.get(ctx.slot, [])
            if cards:
                cards[0].setdefault("equipped_cancel_triggers", []).append(sanitize_card_dict(op))
        return [parent_node]


@register_effect("取消伤害")
class CancelDamageHandler(BaseEffectHandler):
    """【取消伤害】解耦处理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        base_dmg, bonus_type = op.get("cancel_damage_base", 1), op.get("cancel_damage_bonus", "0")
        bonus = ctx.cancelled_damage if bonus_type == "取消伤害" else (
            parent_node.state_snapshot.role_soul if bonus_type == "魂点" and parent_node.state_snapshot else 3
        )
        total_dmg = max(0, base_dmg + bonus)
        return expand_role_damage_helper(
            parent_node, total_dmg, f"取消伤害({base_dmg}+{bonus_type}({bonus})={total_dmg}点)", ctx
        )


@register_effect("普通伤害")
class NormalDamageHandler(BaseEffectHandler):
    """【普通伤害】解耦处理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        dmg = op.get("damage", 1)
        return expand_role_damage_helper(parent_node, dmg, f"普通伤害({dmg}点)", ctx)


@register_effect("角色伤害")
class RoleDamageHandler(BaseEffectHandler):
    """【角色伤害】解耦处理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        base_dmg = op.get("role_damage_base", 0)
        soul = parent_node.state_snapshot.role_soul if parent_node.state_snapshot else 3
        return expand_role_damage_helper(parent_node, base_dmg + soul, f"角色伤害({base_dmg + soul}点)", ctx)