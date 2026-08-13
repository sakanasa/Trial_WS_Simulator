# -*- coding: utf-8 -*-
"""
执行计划解析器 (Execution Plan Parser)
负责将界面上的角色配置与执行计划步骤转译为模拟引擎可执行的 tuple 顺序列表 (role_idx, start_op_idx, end_op_idx) 及 roles_config。
"""

from typing import Tuple, List, Dict, Any
from utils.registry import registry


class PlanParser:
    """执行计划解析与转换工具类"""

    @classmethod
    def parse_execution_plan(
        cls, 
        roles_list: List[dict], 
        plan_steps_list: List[dict]
    ) -> Tuple[List[Tuple[int, int, int]], List[Dict[str, Any]]]:
        """
        通用解析函数：将界面角色列表与步骤行转换为引擎执行序列
        返回: (execution_plan, roles_config)
        """
        roles_config = [
            {
                "soul": role["soul_var"].get(),
                "ops": [registry.extract_params(op) for op in role["ops"]]
            }
            for role in roles_list
        ]

        if plan_steps_list:
            plan = []
            for step in plan_steps_list:
                rname = step["role_var"].get()
                if not rname:
                    continue
                try:
                    ridx = int(rname.replace("角色", "")) - 1
                except ValueError:
                    continue
                s, e = step["start_var"].get() - 1, step["end_var"].get() - 1
                if 0 <= ridx < len(roles_config):
                    ops_len = len(roles_config[ridx]["ops"])
                    s, e = max(0, min(s, ops_len - 1)), max(s, min(e, ops_len - 1))
                    plan.append((ridx, s, e))
        else:
            plan = [(i, 0, len(rc["ops"]) - 1) for i, rc in enumerate(roles_config)]

        return plan, roles_config