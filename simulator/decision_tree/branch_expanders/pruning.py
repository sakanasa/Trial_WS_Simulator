# -*- coding: utf-8 -*-
"""
決策樹剪枝策略模塊 (Decision Tree Pruning Strategies)
包含分支剪枝基類、概率剪枝、敗北剪枝及剪枝管理器，方便後續擴展複雜剪枝邏輯。
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..tree_model import TreeNode


class BasePruner(ABC):
    """剪枝策略基類"""

    @abstractmethod
    def should_prune(self, node: TreeNode, context_info: Optional[Dict[str, Any]] = None) -> bool:
        """判定單個節點是否應當被剪枝（返回 True 則剪枝/丟棄）"""
        pass

    def filter_branches(self, nodes: List[TreeNode], context_info: Optional[Dict[str, Any]] = None) -> List[TreeNode]:
        """批量過濾節點列表"""
        return [node for node in nodes if not self.should_prune(node, context_info)]


class ProbabilityPruner(BasePruner):
    """低概率分支剪枝器：裁剪髮生概率低於設定閾值的小概率分支（極大地抑制分支膨脹）"""

    def __init__(self, min_prob_threshold: float = 1e-5):
        self.min_prob_threshold = min_prob_threshold

    def should_prune(self, node: TreeNode, context_info: Optional[Dict[str, Any]] = None) -> bool:
        # 勝利節點（game_over）絕對不剪枝，其餘概率極低的分支可裁剪
        if node.state_snapshot and node.state_snapshot.game_over:
            return False
        return node.prob < self.min_prob_threshold


class DeadStatePruner(BasePruner):
    """無效/敗北狀態剪枝器：自動裁剪敗北節點（my_failed）"""

    def should_prune(self, node: TreeNode, context_info: Optional[Dict[str, Any]] = None) -> bool:
        if node.state_snapshot and node.state_snapshot.my_failed:
            return True
        return False


class TreePrunerManager:
    """剪枝器管理器：支持組合疊加多種剪枝策略"""

    def __init__(self, pruners: Optional[List[BasePruner]] = None):
        # 默認註冊敗北剪枝，概率剪枝可按需開啟
        self.pruners: List[BasePruner] = pruners if pruners is not None else [
            DeadStatePruner()
        ]

    def add_pruner(self, pruner: BasePruner):
        """動態添加自定義剪枝邏輯（方便後續增加複雜剪枝）"""
        self.pruners.append(pruner)

    def prune_leaves(self, nodes: List[TreeNode], context_info: Optional[Dict[str, Any]] = None) -> List[TreeNode]:
        """對葉子節點列表按順序應用所有剪枝策略"""
        filtered = list(nodes)
        for pruner in self.pruners:
            filtered = pruner.filter_branches(filtered, context_info)
        return filtered


# 全局默認剪枝管理器單例
default_pruner_manager = TreePrunerManager()