# -*- coding: utf-8 -*-
"""
主界面左側面板視圖 (Left Column View) - Geek Indigo 統一樣式高顏值版
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Dict, Any, Callable

from utils.registry import registry
from ui.components.app_dropdown import AppDropdown
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD
from ui.components.left_column.char_sim_card import CharSimCard
from ui.components.left_column.single_op_card import SingleOpCard

class LeftColumnView(ctk.CTkFrame):  
    """左側面板配置視圖類（底部固定 + 上部獨立滾動）"""

    def __init__(
        self,
        parent: tk.Widget,
        app_controller: Any,
        **kwargs
    ):
        super().__init__(parent, fg_color=("#F1F5F9", "#111827"), **kwargs)
        self.app = app_controller

        self._init_variables()
        self._build_ui()

    def _init_variables(self):
        self.deck_normal = tk.IntVar(value=17)
        self.deck_climax = tk.IntVar(value=8)

        self.control_normal = tk.IntVar(value=0)
        self.control_climax = tk.IntVar(value=0)

        self.stock_normal = tk.IntVar(value=7)
        self.stock_climax = tk.IntVar(value=0)

        self.level_vars = [tk.StringVar(value="肉" if i >= 2 else "無") for i in range(4)]
        self.clock_vars = [tk.StringVar(value="肉" if i < 4 else "無") for i in range(6)]

    def _create_card_frame(self, parent: Any, title_text: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=PALETTE["card_bg"], corner_radius=12, border_width=2, border_color=PALETTE["card_border"])
        card.pack(fill=tk.X, pady=6, padx=6)

        title_lbl = ctk.CTkLabel(
            card, 
            text=title_text, 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        )
        title_lbl.pack(anchor="w", padx=10, pady=(8, 4))
        return card

    def toggle_theme(self):
        current_resolved_mode = ctk.get_appearance_mode()
        new_mode = "Light" if current_resolved_mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        
        if hasattr(self.app, "set_theme"):
            self.app.set_theme(new_mode)

    def _build_ui(self):
        entry_opts = {
            "width": 50,
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"],
            "border_width": 1.5,
            "text_color": PALETTE["text_main"]
        }

        # 1. 底部固定區域
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, pady=6, padx=6)

        ctk.CTkButton(
            btn_row, 
            text="AI說明書", 
            command=self.app.open_ai_manual,
            fg_color=PALETTE["secondary"], 
            hover_color=PALETTE["secondary_hover"], 
            text_color=PALETTE["text_main"],
            font=FONT_GLOBAL,
            width=100
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            btn_row, 
            text="切換主題", 
            command=self.toggle_theme,
            fg_color=PALETTE["secondary"], 
            hover_color=PALETTE["secondary_hover"], 
            text_color=PALETTE["text_main"],
            font=FONT_GLOBAL,
            width=100
        ).pack(side=tk.RIGHT, padx=2)

        # 2. 上部獨立滾動區域
        scroll_content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))

        # 2.1 牌組設置
        deck_card = self._create_card_frame(scroll_content, "牌組設置")
        d_grid = ctk.CTkFrame(deck_card, fg_color="transparent")
        d_grid.pack(fill=tk.X, padx=10, pady=(0, 8))

        ctk.CTkLabel(d_grid, text="肉數量:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).grid(row=0, column=0, sticky="w", padx=2)
        ctk.CTkEntry(d_grid, textvariable=self.deck_normal, **entry_opts).grid(row=0, column=1, padx=6, pady=2)
        ctk.CTkLabel(d_grid, text="潮數量:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).grid(row=1, column=0, sticky="w", padx=2)
        ctk.CTkEntry(d_grid, textvariable=self.deck_climax, **entry_opts).grid(row=1, column=1, padx=6, pady=2)

        # 2.2 控制室設置
        control_card = self._create_card_frame(scroll_content, "控制室設置")
        c_grid = ctk.CTkFrame(control_card, fg_color="transparent")
        c_grid.pack(fill=tk.X, padx=10, pady=(0, 8))

        ctk.CTkLabel(c_grid, text="肉數量:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).grid(row=0, column=0, sticky="w", padx=2)
        ctk.CTkEntry(c_grid, textvariable=self.control_normal, **entry_opts).grid(row=0, column=1, padx=6, pady=2)
        ctk.CTkLabel(c_grid, text="潮數量:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).grid(row=1, column=0, sticky="w", padx=2)
        ctk.CTkEntry(c_grid, textvariable=self.control_climax, **entry_opts).grid(row=1, column=1, padx=6, pady=2)

        # 2.3 能量區設置
        stock_card = self._create_card_frame(scroll_content, "能量區設置")
        s_grid = ctk.CTkFrame(stock_card, fg_color="transparent")
        s_grid.pack(fill=tk.X, padx=10, pady=(0, 8))

        ctk.CTkLabel(s_grid, text="肉數量:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).grid(row=0, column=0, sticky="w", padx=2)
        ctk.CTkEntry(s_grid, textvariable=self.stock_normal, **entry_opts).grid(row=0, column=1, padx=6, pady=2)
        ctk.CTkLabel(s_grid, text="潮數量:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).grid(row=1, column=0, sticky="w", padx=2)
        ctk.CTkEntry(s_grid, textvariable=self.stock_climax, **entry_opts).grid(row=1, column=1, padx=6, pady=2)

        # 2.4 等級區與傷害區
        lc_card = self._create_card_frame(scroll_content, "等級區與傷害區設置")
        grid_frame = ctk.CTkFrame(lc_card, fg_color="transparent")
        grid_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        level_box = ctk.CTkFrame(
            grid_frame, 
            fg_color="transparent", 
            corner_radius=6, 
            border_width=1.5,
            border_color=PALETTE["input_border"]
        )
        level_box.grid(row=0, column=0, rowspan=4, columnspan=1, padx=(0, 4), pady=(0, 6), sticky="nw")

        clock_box = ctk.CTkFrame(
            grid_frame, 
            fg_color="transparent", 
            corner_radius=6, 
            border_width=1.5,
            border_color=PALETTE["input_border"]
        )
        clock_box.grid(row=4, column=0, columnspan=6, padx=0, pady=(2, 0), sticky="ew")

        options = ["無", "肉", "潮"]

        for row_idx, var in enumerate(self.level_vars):
            AppDropdown(level_box, variable=var, values=options, width=58, height=28).grid(row=row_idx, column=0, padx=4, pady=3)

        for col_idx, var in enumerate(self.clock_vars):
            AppDropdown(clock_box, variable=var, values=options, width=58, height=28).grid(row=0, column=col_idx, padx=3, pady=4)

        # 2.5 單次操作模擬
        self.single_op_card = SingleOpCard(
            scroll_content,
            app_controller=self.app,
            on_execute=self.app.execute_single
        )
        self.single_op_card.pack(fill=tk.X, pady=4, padx=2)

        # 2.6 🌟 單角色操作模擬：實例化獨立組件並傳入 on_execute 回調
        self.char_sim_card = CharSimCard(
            scroll_content, 
            on_execute=self.app.execute_character_sim,
            app_controller=self.app
        )
        self.char_sim_card.pack(fill=tk.X, pady=4, padx=2)