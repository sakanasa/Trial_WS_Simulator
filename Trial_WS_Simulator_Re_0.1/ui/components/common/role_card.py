# -*- coding: utf-8 -*-
"""
角色卡片組件與管理器 (Role Card & Role List Manager)
統一管理高級模式與工況模式下的角色卡片（角色1、角色2...）的 UI 掛載、控制按鈕綁定、初始魂點輸入與操作列表渲染。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, List, Optional, Callable

from ui.components.common.ops_list_builder import OpsListBuilder
from ui.components.app_dropdown import CTkControlButtons
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class RoleListManager:
    """角色卡片列表通用 UI 渲染與排序管理類"""

    @classmethod
    def refresh_roles_ui(
        cls, 
        roles_list: list, 
        container: Any, 
        mode: str, 
        on_add: Callable[[int], None], 
        on_remove: Callable[[int], None], 
        on_up: Callable[[int], None], 
        on_down: Callable[[int], None],
        app_controller: Any = None
    ):
        """重新掛載與物理對齊角色卡片列表 UI"""
        valid_containers = set()

        for i, role in enumerate(roles_list):
            role_name = f"角色{i+1}"

            if "role_card" in role and role["role_card"].winfo_exists():
                role_card = role["role_card"]
                valid_containers.add(role_card)

                role_card.pack_forget()  # 🌟 解包確保物理重排
                role_card.pack(fill=tk.X, pady=4, padx=4)

                if "title_label" in role and role["title_label"].winfo_exists():
                    if role["title_label"].cget("text") != role_name:
                        role["title_label"].configure(text=role_name)

                if "ctrl_group" in role and role["ctrl_group"].winfo_exists():
                    role["ctrl_group"].configure_commands(
                        on_remove=lambda idx=i: on_remove(idx),
                        on_add=lambda idx=i: on_add(idx),
                        on_up=lambda idx=i: on_up(idx),
                        on_down=lambda idx=i: on_down(idx)
                    )

                OpsListBuilder.create_ops_list_ui(
                    role["ops"], role["ops_frame"], mode=mode, role=role, app_controller=app_controller
                )

            else:
                # 構建全新的角色卡片
                role_card = ctk.CTkFrame(
                    container, 
                    fg_color=PALETTE["card_bg"],
                    corner_radius=12, 
                    border_width=2, 
                    border_color=PALETTE["card_border"]
                )
                role_card.pack(fill=tk.X, pady=4, padx=4)
                role["role_card"] = role_card

                top_row = ctk.CTkFrame(role_card, fg_color="transparent")
                top_row.pack(fill=tk.X, padx=6, pady=4)

                # 控制按鈕 [- + ▲ ▼]
                ctrl_group = CTkControlButtons(
                    top_row,
                    on_remove=lambda idx=i: on_remove(idx),
                    on_add=lambda idx=i: on_add(idx),
                    on_up=lambda idx=i: on_up(idx),
                    on_down=lambda idx=i: on_down(idx)
                )
                ctrl_group.pack(side=tk.LEFT, padx=1)
                role["ctrl_group"] = ctrl_group

                # 角色標題
                title_label = ctk.CTkLabel(top_row, text=role_name, font=FONT_GLOBAL_BOLD, text_color=PALETTE["text_main"])
                title_label.pack(side=tk.LEFT, padx=(8, 8))
                role["title_label"] = title_label

                # 初始魂點
                ctk.CTkLabel(top_row, text="初始魂點:", text_color=PALETTE["text_sub"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=(12, 2))
                
                ctk.CTkEntry(
                    top_row, textvariable=role["soul_var"], width=40, height=24, font=FONT_GLOBAL, fg_color=PALETTE["secondary"], border_color=PALETTE["input_border"], border_width=1.5, text_color=PALETTE["text_main"]
                ).pack(side=tk.LEFT, padx=2)

                ops_container = ctk.CTkFrame(role_card, fg_color="transparent")
                ops_container.pack(fill=tk.X, expand=True, padx=4, pady=(2, 6))
                role["ops_frame"] = ops_container

                valid_containers.add(role_card)
                OpsListBuilder.create_ops_list_ui(
                    role["ops"], ops_container, mode=mode, role=role, app_controller=app_controller
                )

        # 清理多餘已被刪除的角色卡片容器
        for child in container.winfo_children():
            if child not in valid_containers:
                child.destroy()