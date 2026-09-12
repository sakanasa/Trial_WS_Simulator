# -*- coding: utf-8 -*-
"""
可摺疊通用卡片組件 (Collapsible Card Component)
統一中欄各種需要摺疊/展開的 UI 卡片邊框、標題欄、▼/▲ 狀態控制與內嵌容器。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Optional, Callable

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class CollapsibleCard(ctk.CTkFrame):
    """可摺疊通用卡片組件"""

    def __init__(
        self, 
        master: Any, 
        title: str, 
        is_expanded: bool = True, 
        **kwargs
    ):
        # 🌟 核心修復：顯式將默認高度設置為 height=1，防止空內容時被 CTkFrame 默認 200px 撐出空白
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

        # 內部存放右側操作按鍵（如 +, 清空等）的動作容器
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
        # 🌟 核心修復：內部內容容器同樣顯式設置 height=1
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent", height=1)
        self.content_frame.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=4, pady=(0, 6))

    def toggle(self):
        """摺疊/展開邏輯切換"""
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.arrow_btn.configure(text="▲")
            self.is_expanded = False
        else:
            self.content_frame.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=4, pady=(0, 6))
            self.arrow_btn.configure(text="▼")
            self.is_expanded = True

    def add_header_button(self, text: str, command: Callable, width: int = 24, font: tuple = FONT_GLOBAL) -> ctk.CTkButton:
        """在頭部右側追加操作按鈕（插入在箭頭按鈕左側）"""
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