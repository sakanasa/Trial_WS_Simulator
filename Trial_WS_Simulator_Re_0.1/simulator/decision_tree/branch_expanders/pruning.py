# -*- coding: utf-8 -*-
"""
决策树剪枝策略模块 (Decision Tree Pruning Strategies)
包含分支剪枝基类、概率剪枝、败北剪枝及剪枝管理器，方便后续扩展复杂剪枝逻辑。
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..tree_model import TreeNode


class BasePruner(ABC):
    """剪枝策略基类"""

    @abstractmethod
    def should_prune(self, node: TreeNode, context_info: Optional[Dict[str, Any]] = None) -> bool:
        """判定单个节点是否应当被剪枝（返回 True 则剪枝/丢弃）"""
        pass

    def filter_branches(self, nodes: List[TreeNode], context_info: Optional[Dict[str, Any]] = None) -> List[TreeNode]:
        """批量过滤节点列表"""
        return [node for node in nodes if not self.should_prune(node, context_info)]


class ProbabilityPruner(BasePruner):
    """低概率分支剪枝器：裁剪发生概率低于设定阈值的小概率分支（极大地抑制分支膨胀）"""

    def __init__(self, min_prob_threshold: float = 1e-5):
        self.min_prob_threshold = min_prob_threshold

    def should_prune(self, node: TreeNode, context_info: Optional[Dict[str, Any]] = None) -> bool:
        # 胜利节点（game_over）绝对不剪枝，其余概率极低的分支可裁剪
        if node.state_snapshot and node.state_snapshot.game_over:
            return False
        return node.prob < self.min_prob_threshold


class DeadStatePruner(BasePruner):
    """无效/败北状态剪枝器：自动裁剪败北节点（my_failed）"""

    def should_prune(self, node: TreeNode, context_info: Optional[Dict[str, Any]] = None) -> bool:
        if node.state_snapshot and node.state_snapshot.my_failed:
            return True
        return False


class TreePrunerManager:
    """剪枝器管理器：支持组合叠加多种剪枝策略"""

    def __init__(self, pruners: Optional[List[BasePruner]] = None):
        # 默认注册败北剪枝，概率剪枝可按需开启
        self.pruners: List[BasePruner] = pruners if pruners is not None else [
            DeadStatePruner()
        ]

    def add_pruner(self, pruner: BasePruner):
        """动态添加自定义剪枝逻辑（方便后续增加复杂剪枝）"""
        self.pruners.append(pruner)

    def prune_leaves(self, nodes: List[TreeNode], context_info: Optional[Dict[str, Any]] = None) -> List[TreeNode]:
        """对叶子节点列表按顺序应用所有剪枝策略"""
        filtered = list(nodes)
        for pruner in self.pruners:
            filtered = pruner.filter_branches(filtered, context_info)
        return filtered


# 全局默认剪枝管理器单例
default_pruner_manager = TreePrunerManager()