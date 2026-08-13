# -*- coding: utf-8 -*-
"""
分支生成包入口 (Branch Expanders Package Initializer)
导出 DecisionTreeBuilder、剪枝器与所有的 Operation 注册分发接口。
"""
from .base import ExpansionContext, BaseEffectHandler, EffectRegistry, register_effect
from .dispatcher import resolve_operation
from .pruning import BasePruner, ProbabilityPruner, DeadStatePruner, TreePrunerManager, default_pruner_manager
from .builder import DecisionTreeBuilder

# 导入所有具象 Handler 模块以触发自动注册
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