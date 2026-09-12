# -*- coding: utf-8 -*-
"""
執行計劃列表管理器 (Plan Step Manager)
統一管理高級模式與工況模式下的執行計劃步驟行（角色選擇下拉框、從操作 X 到操作 Y 輸入框）的 UI 動態構建與角色聯動更新。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, List, Callable

from ui.components.app_dropdown import AppDropdown, CTkControlButtons
from ui.theme import PALETTE, FONT_GLOBAL


class PlanStepManager:
    """執行計劃列表通用 UI 渲染與更新管理類"""

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
        """重新掛載與物理對齊執行計劃步驟行 UI"""
        # 🌟 空狀態處理：若無步驟，隱藏容器
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

                step_row.pack_forget()  # 🌟 解包確保物理重排
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
                    text="從操作", 
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
        """當角色增刪改變時，動態更新所有執行計劃下拉框的可選項"""
        role_names = [f"角色{i+1}" for i in range(len(roles_list))]
        for step in steps_list:
            combo = step.get("role_combo")
            if combo and combo.winfo_exists():
                combo.configure(values=role_names)
                if step["role_var"].get() not in role_names and role_names:
                    step["role_var"].set(role_names[0])