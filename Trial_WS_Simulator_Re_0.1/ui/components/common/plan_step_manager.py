# -*- coding: utf-8 -*-
"""
执行计划列表管理器 (Plan Step Manager)
统一管理高级模式与工况模式下的执行计划步骤行（角色选择下拉框、从操作 X 到操作 Y 输入框）的 UI 动态构建与角色联动更新。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, List, Callable

from ui.components.app_dropdown import AppDropdown, CTkControlButtons
from ui.theme import PALETTE, FONT_GLOBAL


class PlanStepManager:
    """执行计划列表通用 UI 渲染与更新管理类"""

    @classmethod
    def refresh_plan_ui(
        cls, 
        steps_list: list, 
        roles_list: list, 
        container: Any, 
        on_add: Callable[[int], None], 
        on_remove: Callable[[int], None], 
        on_up: Callable[[int], None], 
        on_down: Callable[[int], None]
    ):
        """重新挂载与物理对齐执行计划步骤行 UI"""
        # 🌟 空状态处理：若无步骤，隐藏容器
        if not steps_list:
            container.pack_forget()
            for child in container.winfo_children():
                child.destroy()
            return

        container.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=4, pady=(0, 6))

        valid_containers = set()
        role_names = [f"角色{i+1}" for i in range(len(roles_list))]

        for i, step in enumerate(steps_list):
            if "step_row" in step and step["step_row"].winfo_exists():
                step_row = step["step_row"]
                valid_containers.add(step_row)

                step_row.pack_forget()  # 🌟 解包确保物理重排
                step_row.pack(fill=tk.X, pady=2)

                if "ctrl_group" in step and step["ctrl_group"].winfo_exists():
                    step["ctrl_group"].configure_commands(
                        on_remove=lambda idx=i: on_remove(idx),
                        on_add=lambda idx=i: on_add(idx),
                        on_up=lambda idx=i: on_up(idx),
                        on_down=lambda idx=i: on_down(idx)
                    )

                combo = step.get("role_combo")
                if combo and combo.winfo_exists():
                    combo.configure(values=role_names)
                    if step["role_var"].get() not in role_names and role_names:
                        step["role_var"].set(role_names[0])

            else:
                step_row = ctk.CTkFrame(container, fg_color="transparent")
                step_row.pack(fill=tk.X, pady=2)
                step["step_row"] = step_row

                ctrl_group = CTkControlButtons(
                    step_row,
                    on_remove=lambda idx=i: on_remove(idx),
                    on_add=lambda idx=i: on_add(idx),
                    on_up=lambda idx=i: on_up(idx),
                    on_down=lambda idx=i: on_down(idx)
                )
                ctrl_group.pack(side=tk.LEFT, padx=1)
                step["ctrl_group"] = ctrl_group

                if not step["role_var"].get() and role_names:
                    step["role_var"].set(role_names[0])

                role_combo = AppDropdown(
                    step_row,
                    variable=step["role_var"],
                    values=role_names,
                    width=90
                )
                role_combo.pack(side=tk.LEFT, padx=4)
                step["role_combo"] = role_combo

                ctk.CTkLabel(
                    step_row, 
                    text="从操作", 
                    text_color=PALETTE["text_main"],
                    font=FONT_GLOBAL
                ).pack(side=tk.LEFT, padx=(4, 1))
                
                ctk.CTkEntry(
                    step_row, textvariable=step["start_var"], width=36, height=24, font=FONT_GLOBAL, fg_color=PALETTE["secondary"], border_color=PALETTE["input_border"], border_width=1.5, text_color=PALETTE["text_main"]
                ).pack(side=tk.LEFT, padx=2)

                ctk.CTkLabel(
                    step_row, 
                    text="到操作", 
                    text_color=PALETTE["text_main"],
                    font=FONT_GLOBAL
                ).pack(side=tk.LEFT, padx=(4, 1))
                
                ctk.CTkEntry(
                    step_row, textvariable=step["end_var"], width=36, height=24, font=FONT_GLOBAL, fg_color=PALETTE["secondary"], border_color=PALETTE["input_border"], border_width=1.5, text_color=PALETTE["text_main"]
                ).pack(side=tk.LEFT, padx=2)

                valid_containers.add(step_row)

        for child in container.winfo_children():
            if child not in valid_containers:
                child.destroy()

    @classmethod
    def update_role_options(cls, steps_list: list, roles_list: list):
        """当角色增删改变时，动态更新所有执行计划下拉框的可选项"""
        role_names = [f"角色{i+1}" for i in range(len(roles_list))]
        for step in steps_list:
            combo = step.get("role_combo")
            if combo and combo.winfo_exists():
                combo.configure(values=role_names)
                if step["role_var"].get() not in role_names and role_names:
                    step["role_var"].set(role_names[0])