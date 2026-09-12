# -*- coding: utf-8 -*-
"""
分支生成包入口 (Branch Expanders Package Initializer)
導出 DecisionTreeBuilder、剪枝器與所有的 Operation 註冊分發接口。
"""
from .base import ExpansionContext, BaseEffectHandler, EffectRegistry, register_effect
from .dispatcher import resolve_operation
from .pruning import BasePruner, ProbabilityPruner, DeadStatePruner, TreePrunerManager, default_pruner_manager
from .builder import DecisionTreeBuilder

# 導入所有具象 Handler 模塊以觸發自動註冊
from . import deck, combat, compound

__all__ = [
    "DecisionTreeBuilder",
    "ExpansionContext",
    "BaseEffectHandler",
    "EffectRegistry",
    "register_effect",
    "resolve_operation",
    "BasePruner",
    "ProbabilityPruner",
    "DeadStatePruner",
    "TreePrunerManager",
    "default_pruner_manager",
]