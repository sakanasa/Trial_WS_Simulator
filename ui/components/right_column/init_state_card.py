# -*- coding: utf-8 -*-
"""
公用初始局勢卡片組件 (Init State Card Component) - 自動換行終極修復版
統一右欄“單次操作”、“單角色評估”、“單次測試”選項卡中頂部的初始局勢摘要與 7 區顯示。
使用透明 CTkTextbox 偽裝文本區，徹底解決長數據（如潮位置、等級/傷害區）被右邊界裁切截斷的問題。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, List, Optional

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD, BORDER_THIN


class InitStateCard(ctk.CTkFrame):
    """公用初始局勢卡片 UI 組件"""

    DEFAULT_STATE_DESCRIPTIONS = [
        "牌組: 未執行",
        "牌組潮位置(底起): 未執行",
        "能量區: 未執行",
        "能量區潮位置(底起): 未執行",
        "控制室: 未執行",
        "等級區(底→頂): 未執行",
        "傷害區(底→頂): 未執行"
    ]

    def __init__(self, master: Any, default_summary: str = "評估結果：未執行", **kwargs):
        ctk_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }

        super().__init__(
            master=master,
            fg_color=PALETTE["card_bg"],
            corner_radius=12,
            border_width=BORDER_THIN,
            border_color=PALETTE["card_border"],
            **ctk_kwargs
        )

        self.default_summary = default_summary
        self._build_ui()

    def _build_ui(self):
        # 1. 結果摘要行
        self.summary_label = ctk.CTkLabel(
            self,
            text=self.default_summary,
            font=FONT_GLOBAL_BOLD,
            text_color=PALETTE["text_main"],
            justify="left"
        )
        self.summary_label.pack(anchor="w", padx=8, pady=(6, 2))

        ctk.CTkFrame(self, height=1, fg_color=PALETTE["card_border"]).pack(fill=tk.X, pady=4, padx=6)

        # 2. 初始局勢標題
        ctk.CTkLabel(
            self,
            text="初始局勢狀態",
            font=FONT_GLOBAL_BOLD,
            text_color=PALETTE["text_main"],
            justify="left"
        ).pack(anchor="w", padx=8, pady=(2, 2))

        # 3. 🌟 核心優化：使用透明 CTkTextbox 承載 7 行局勢長文本，實現原生按詞自動換行
        body_text = "\n".join(self.DEFAULT_STATE_DESCRIPTIONS)

        self.text_display = ctk.CTkTextbox(
            self,
            wrap="word",                 # 【關鍵】原生按單詞自動折行，絕不截斷
            font=FONT_GLOBAL,
            fg_color="transparent",      # 【關鍵】背景透明，完美融合卡片背景
            text_color=PALETTE["text_sub"],
            border_width=0,              # 無邊框
            activate_scrollbars=False,   # 禁用滾動條
            height=145                   # 默認 7 行文字高度
        )
        self.text_display.pack(fill=tk.X, padx=4, pady=(0, 4))
        self.text_display.insert("1.0", body_text)
        self.text_display.configure(state="disabled")

    def update_info(self, summary_text: str, before_lines: Optional[list] = None):
        """快捷更新摘要與局勢文本"""
        if summary_text:
            self.summary_label.configure(text=summary_text)

        if before_lines and len(before_lines) >= 7:
            lines = before_lines[:7]
            body_text = "\n".join(lines)

            # 根據行數與長字符估算自適應高度，防止高度不足導致遮擋
            estimated_lines = sum(max(1, (len(l) + 20) // 25) for l in lines)
            calc_height = max(140, estimated_lines * 20 + 8)

            self.text_display.configure(state="normal")
            self.text_display.delete("1.0", tk.END)
            self.text_display.insert("1.0", body_text)
            self.text_display.configure(height=calc_height, state="disabled")