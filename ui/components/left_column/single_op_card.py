# -*- coding: utf-8 -*-
"""
單次操作模擬組件 (Single Op Card Component)
獨立封裝左側欄“單次操作模擬”卡片及其控件與執行調度。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Optional, Callable

from utils.registry import registry
from ui.components.common.ops_list_builder import OpsListBuilder
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD, RADIUS, BORDER_THIN


class SingleOpCard(ctk.CTkFrame):
    """單次操作模擬獨立卡片 UI 組件"""

    def __init__(
        self, 
        master: Any, 
        app_controller: Any = None, 
        on_execute: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        self.app = app_controller
        self.on_execute = on_execute or kwargs.get("on_execute")

        ctk_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }

        super().__init__(
            master=master,
            fg_color=PALETTE["card_bg"],
            corner_radius=RADIUS["md"],
            border_width=BORDER_THIN,
            border_color=PALETTE["card_border"],
            **ctk_kwargs
        )

        self.single_op = {
            "type_var": tk.StringVar(value="普通傷害"),
            "params": {}, "controls": {}, "params_frame": None, "linkage_frame": None
        }
        self.single_ops = [self.single_op]

        self._build_ui()

    def _build_ui(self):
        title_lbl = ctk.CTkLabel(
            self,
            text="單次操作模擬",
            font=FONT_GLOBAL_BOLD,
            text_color=PALETTE["text_main"]
        )
        title_lbl.pack(anchor="w", padx=10, pady=(8, 4))

        self.single_op_container = ctk.CTkFrame(self, fg_color="transparent")
        self.single_op_container.pack(fill=tk.X, padx=10, pady=2)

        # 🌟 使用 OpsListBuilder 渲染單次操作下拉框與參數行
        OpsListBuilder.create_ops_list_ui(
            self.single_ops, self.single_op_container, mode="single", app_controller=self.app
        )

        ctk.CTkButton(
            self, 
            text="執行單次操作", 
            command=self._handle_execute,
            fg_color=PALETTE["primary"], 
            hover_color=PALETTE["primary_hover"], 
            text_color=("#FFFFFF", "#0B0F19"),
            font=FONT_GLOBAL
        ).pack(pady=8, padx=10)

    def _handle_execute(self):
        if self.on_execute:
            self.on_execute()
        elif hasattr(self.app, "execute_single"):
            self.app.execute_single()

    def get_op_params(self) -> dict:
        """提取當前單次操作配置的參數字典"""
        return registry.extract_params(self.single_op)