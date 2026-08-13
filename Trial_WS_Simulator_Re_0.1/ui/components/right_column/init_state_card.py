# -*- coding: utf-8 -*-
"""
公用初始局势卡片组件 (Init State Card Component) - 自动换行终极修复版
统一右栏“单次操作”、“单角色评估”、“单次测试”选项卡中顶部的初始局势摘要与 7 区显示。
使用透明 CTkTextbox 伪装文本区，彻底解决长数据（如潮位置、等级/计时区）被右边界裁切截断的问题。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, List, Optional

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class InitStateCard(ctk.CTkFrame):
    """公用初始局势卡片 UI 组件"""

    DEFAULT_STATE_DESCRIPTIONS = [
        "卡组: 未执行",
        "卡组潮位置(底起): 未执行",
        "库存区: 未执行",
        "库存区潮位置(底起): 未执行",
        "控制室: 未执行",
        "等级区(底→顶): 未执行",
        "计时区(底→顶): 未执行"
    ]

    def __init__(self, master: Any, default_summary: str = "评估结果：未执行", **kwargs):
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

        self.default_summary = default_summary
        self._build_ui()

    def _build_ui(self):
        # 1. 结果摘要行
        self.summary_label = ctk.CTkLabel(
            self,
            text=self.default_summary,
            font=FONT_GLOBAL_BOLD,
            text_color=PALETTE["text_main"],
            justify="left"
        )
        self.summary_label.pack(anchor="w", padx=8, pady=(6, 2))

        ctk.CTkFrame(self, height=1, fg_color=PALETTE["card_border"]).pack(fill=tk.X, pady=4, padx=6)

        # 2. 初始局势标题
        ctk.CTkLabel(
            self,
            text="初始局势状态",
            font=FONT_GLOBAL_BOLD,
            text_color=PALETTE["text_main"],
            justify="left"
        ).pack(anchor="w", padx=8, pady=(2, 2))

        # 3. 🌟 核心优化：使用透明 CTkTextbox 承载 7 行局势长文本，实现原生按词自动换行
        body_text = "\n".join(self.DEFAULT_STATE_DESCRIPTIONS)

        self.text_display = ctk.CTkTextbox(
            self,
            wrap="word",                 # 【关键】原生按单词自动折行，绝不截断
            font=FONT_GLOBAL,
            fg_color="transparent",      # 【关键】背景透明，完美融合卡片背景
            text_color=PALETTE["text_sub"],
            border_width=0,              # 无边框
            activate_scrollbars=False,   # 禁用滚动条
            height=145                   # 默认 7 行文字高度
        )
        self.text_display.pack(fill=tk.X, padx=4, pady=(0, 4))
        self.text_display.insert("1.0", body_text)
        self.text_display.configure(state="disabled")

    def update_info(self, summary_text: str, before_lines: Optional[list] = None):
        """快捷更新摘要与局势文本"""
        if summary_text:
            self.summary_label.configure(text=summary_text)

        if before_lines and len(before_lines) >= 7:
            lines = before_lines[:7]
            body_text = "\n".join(lines)

            # 根据行数与长字符估算自适应高度，防止高度不足导致遮挡
            estimated_lines = sum(max(1, (len(l) + 20) // 25) for l in lines)
            calc_height = max(140, estimated_lines * 20 + 8)

            self.text_display.configure(state="normal")
            self.text_display.delete("1.0", tk.END)
            self.text_display.insert("1.0", body_text)
            self.text_display.configure(height=calc_height, state="disabled")