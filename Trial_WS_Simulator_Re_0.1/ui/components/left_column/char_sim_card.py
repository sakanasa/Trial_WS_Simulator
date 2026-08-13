# -*- coding: utf-8 -*-
"""
单角色操作模拟组件 (Char Sim Card Component)
独立封装左侧栏“单角色操作模拟”卡片及其内部操作列表管理与执行调度。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, List, Optional, Callable

from utils.registry import registry
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD
from ui.components.common.ops_list_builder import OpsListBuilder

class CharSimCard(ctk.CTkFrame):
    """单角色操作模拟独立卡片 UI 组件"""

    def __init__(
        self, 
        master: Any, 
        app_controller: Any = None, 
        on_execute: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        self.app = app_controller
        self.on_execute = on_execute or kwargs.get("on_execute")

        # 🌟 过滤白名单：只保留 CTkFrame 官方支持的属性，彻底过滤掉自定义参数
        valid_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }

        super().__init__(
            master=master,
            fg_color=PALETTE["card_bg"],
            corner_radius=12,
            border_width=2,
            border_color=PALETTE["card_border"],
            **valid_kwargs
        )

        self.init_soul_var = tk.IntVar(value=3)
        self.char_ops: List[dict] = []

        self._build_ui()
        self.add_operation()  # 初始化默认增加 1 条操作

    def _build_ui(self):
        title_lbl = ctk.CTkLabel(
            self,
            text="单角色操作模拟",
            font=FONT_GLOBAL_BOLD,
            text_color=PALETTE["text_main"]
        )
        title_lbl.pack(anchor="w", padx=10, pady=(8, 4))

        entry_opts = {
            "width": 50,
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"],
            "border_width": 1.5,
            "text_color": PALETTE["text_main"]
        }

        # 初始魂点行
        soul_row = ctk.CTkFrame(self, fg_color="transparent")
        soul_row.pack(fill=tk.X, padx=10, pady=2)
        ctk.CTkLabel(soul_row, text="角色初始魂点:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT)
        ctk.CTkEntry(soul_row, textvariable=self.init_soul_var, **entry_opts).pack(side=tk.LEFT, padx=6)

        # 操作控件存放容器
        self.char_ops_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.char_ops_frame.pack(fill=tk.X, pady=4, padx=10, expand=True)

        # 执行模拟按钮
        ctk.CTkButton(
            self,
            text="执行单角色模拟",
            command=self._handle_execute,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=("#FFFFFF", "#0B0F19"),
            font=FONT_GLOBAL
        ).pack(pady=8, padx=10)

    def _handle_execute(self):
        """按钮点击事件处理：优先触发独立的 on_execute 回调"""
        if self.on_execute:
            self.on_execute()
        elif hasattr(self.app, "execute_character_sim"):
            self.app.execute_character_sim()

    def add_operation(self, insert_index: Optional[int] = None):
        """为其追加一条算卡操作"""
        idx = len(self.char_ops) if insert_index is None else insert_index + 1
        new_op = {
            "type_var": tk.StringVar(value="普通伤害"),
            "params_frame": None, "row_frame": None, "linkage_frame": None,
            "cancel_detail_frame": None, "controls": {}, "params": {}
        }
        self.char_ops.insert(idx, new_op)
        self.refresh_ops_ui()

    def refresh_ops_ui(self):
        """刷新操作列表组件"""
        OpsListBuilder.create_ops_list_ui(self.char_ops, self.char_ops_frame, mode="char", app_controller=self.app)

    def get_soul(self) -> int:
        """获取当前输入的魂点"""
        return self.init_soul_var.get()

    def get_ops_params(self) -> list:
        """提取已配置的操作参数字典列表"""
        return [registry.extract_params(op) for op in self.char_ops]