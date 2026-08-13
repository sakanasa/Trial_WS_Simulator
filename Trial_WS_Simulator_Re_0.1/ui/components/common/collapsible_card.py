# -*- coding: utf-8 -*-
"""
可折叠通用卡片组件 (Collapsible Card Component)
统一中栏各种需要折叠/展开的 UI 卡片边框、标题栏、▼/▲ 状态控制与内嵌容器。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Optional, Callable

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class CollapsibleCard(ctk.CTkFrame):
    """可折叠通用卡片组件"""

    def __init__(
        self, 
        master: Any, 
        title: str, 
        is_expanded: bool = True, 
        **kwargs
    ):
        # 🌟 核心修复：显式将默认高度设置为 height=1，防止空内容时被 CTkFrame 默认 200px 撑出空白
        kwargs.setdefault("height", 1)

        ctk_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }

        super().__init__(
            master=master,
            fg_color=PALETTE["card_bg"],
            corner_radius=12,
            border_width=2,
            border_color=PALETTE["card_border"],
            **ctk_kwargs
        )

        self.title_text = title
        self.is_expanded = is_expanded

        self._build_header()
        self._build_content()

        if not self.is_expanded:
            self.content_frame.pack_forget()
            self.arrow_btn.configure(text="▲")

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=1)
        self.header_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(6, 4))

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text=self.title_text, 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        )
        self.title_label.pack(side=tk.LEFT)

        # 内部存放右侧操作按键（如 +, 清空等）的动作容器
        self.actions_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.actions_frame.pack(side=tk.RIGHT)

        self.arrow_btn = ctk.CTkButton(
            self.actions_frame, 
            text="▼" if self.is_expanded else "▲", 
            width=24, 
            height=24, 
            command=self.toggle,
            fg_color="transparent",
            text_color=PALETTE["text_main"],
            hover_color=PALETTE["secondary_hover"]
        )
        self.arrow_btn.pack(side=tk.RIGHT, padx=(2, 0))

    def _build_content(self):
        # 🌟 核心修复：内部内容容器同样显式设置 height=1
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent", height=1)
        self.content_frame.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=4, pady=(0, 6))

    def toggle(self):
        """折叠/展开逻辑切换"""
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.arrow_btn.configure(text="▲")
            self.is_expanded = False
        else:
            self.content_frame.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=4, pady=(0, 6))
            self.arrow_btn.configure(text="▼")
            self.is_expanded = True

    def add_header_button(self, text: str, command: Callable, width: int = 24, font: tuple = FONT_GLOBAL) -> ctk.CTkButton:
        """在头部右侧追加操作按钮（插入在箭头按钮左侧）"""
        btn = ctk.CTkButton(
            self.actions_frame,
            text=text,
            width=width,
            height=24,
            corner_radius=4,
            font=font,
            fg_color=PALETTE["secondary"],
            text_color=PALETTE["text_main"],
            hover_color=PALETTE["secondary_hover"],
            command=command
        )
        btn.pack(side=tk.RIGHT, padx=2)
        return btn