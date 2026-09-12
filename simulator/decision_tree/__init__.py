# -*- coding: utf-8 -*-
"""
決策樹子包入口 (Decision Tree Package Initializer)
統一導出決策樹數據模型、數學輔助函數、分支生成器與推演評估算法，確保外部 100% 向後兼容。
"""

from .tree_model import (
    TreeNode,
    GameStateSnapshot,
    sanitize_card_dict,
    sanitize_zone_data,
)

from .tree_helpers import (
    format_card_info,
    get_umi_draw_combinations,
    group_slots_by_equivalence,
    get_position_permutations,
    calc_damage_branches,
)

from .branch_expanders import (
    DecisionTreeBuilder,
    EffectRegistry,
    BasePruner,
    ProbabilityPruner,
    DeadStatePruner,
    TreePrunerManager,
)

from .tree_evaluator import (
    build_full_decision_tree,
    evaluate_tree_expectations,
    get_registered_operations_info,
)

__all__ = [
    "TreeNode",
    "GameStateSnapshot",
    "sanitize_card_dict",
    "sanitize_zone_data",
    "format_card_info",
    "get_umi_draw_combinations",
    "group_slots_by_equivalence",
    "get_position_permutations",
    "calc_damage_branches",
    "DecisionTreeBuilder",
    "EffectRegistry",
    "BasePruner",
    "ProbabilityPruner",
    "DeadStatePruner",
    "TreePrunerManager",
    "build_full_decision_tree",
    "evaluate_tree_expectations",
    "get_registered_operations_info",
]