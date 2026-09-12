# -*- coding: utf-8 -*-
"""
全局統一下拉框組件 (AppDropdown) - Geek Indigo 統一樣式版
使用動態修補 (Monkey Patch) 攔截幾何繪製，100% 完美支持亮/暗色模式自適應切換
"""

import sys
import tkinter as tk
from typing import Union
import customtkinter as ctk

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD

# =====================================================================
# 1. 動態修補 (Monkey Patch) 繪圖引擎，在底層無縫繪製高精度實心三角形
# =====================================================================

try:
    from customtkinter.windows.widgets.core_rendering import DrawEngine
except ImportError:
    try:
        from customtkinter.windows.widgets.draw_engine import DrawEngine
    except ImportError:
        try:
            from customtkinter import DrawEngine
        except ImportError:
            import customtkinter.windows.widgets.core_rendering.draw_engine as de
            DrawEngine = de.DrawEngine

def custom_draw_dropdown_arrow(self, x_position: Union[int, float], y_position: Union[int, float], size: Union[int, float]):
    x_position, y_position, size = round(x_position), round(y_position), round(size)
    requires_recoloring = False
    
    # 獲取 Canvas 中已有的箭頭
    existing = self._canvas.find_withtag("dropdown_arrow")
    
    # 如果已存在但不是 polygon (例如原生 font_shapes 渲染的 text)，清除之，防止渲染衝突
    if existing:
        if self._canvas.type(existing[0]) != "polygon":
            self._canvas.delete("dropdown_arrow")
            existing = None
            
    if not existing:
        # 創建實心多邊形
        self._canvas.create_polygon(0, 0, 0, 0, 0, 0, tags="dropdown_arrow")
        self._canvas.tag_raise("dropdown_arrow")
        requires_recoloring = True
        
    # 精準幾何計算：1:2 高寬比例，保證底部尖端為完美的 90 度直角
    half_width = size / 3.0    
    half_height = size / 6.0   
    
    self._canvas.coords(
        "dropdown_arrow",
        x_position - half_width, y_position - half_height,  # 左上
        x_position + half_width, y_position - half_height,  # 右上
        x_position, y_position + half_height                # 底部直角頂點（向下）
    )
    
    return requires_recoloring

# 替換全局底層的箭頭繪製邏輯
DrawEngine.draw_dropdown_arrow = custom_draw_dropdown_arrow


# =====================================================================
# 2. 精簡版 AppDropdown 包裝類 (對 LeftColumn 保持 100% 接口兼容)
# =====================================================================

class AppDropdown(ctk.CTkOptionMenu):
    """
    Geek Indigo 下拉框外觀包裝類。
    100% 支持亮/暗模式主題自適應。
    """
    DEFAULT_STYLE = {
        "fg_color": PALETTE["secondary"],                   # 控件主底色
        "button_color": PALETTE["secondary_hover"],         # 箭頭區域底色
        "button_hover_color": PALETTE["secondary_hover"],   # 箭頭懸停色
        "dropdown_fg_color": PALETTE["secondary"],          # 🌟 彈出菜單背景色
        "dropdown_hover_color": PALETTE["secondary_hover"], # 🌟 彈出菜單懸停色
        "dropdown_text_color": PALETTE["text_main"],        # 🌟 彈出菜單文字色
        "text_color": PALETTE["text_main"],                 # 選中文字色
        "font": FONT_GLOBAL,
        "corner_radius": 6,
        "height": 28,
        "dynamic_resizing": False
    }

    def __init__(self, master, **kwargs):
        style = self.DEFAULT_STYLE.copy()
        style.update(kwargs)
        
        # 🌟 徹底彈出邊框參數，防止 CustomTkinter 拋出 ValueError 崩潰
        style.pop("border_color", None)
        style.pop("border_width", None)
        
        super().__init__(master, **style)

# app_dropdown.py 末尾

class CTkControlButtons(ctk.CTkFrame):
    """
    Geek Indigo 統一樣式的 [- + ▲ ▼] 控制按鈕組。
    採用封裝的透明 CTkFrame 承載，自動對齊，高度契合系統配色。
    """
    def __init__(
        self, 
        master, 
        on_remove=None, 
        on_add=None, 
        on_up=None, 
        on_down=None, 
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        # 統一樣式參數（採用 -12 像素絕對字號保證緊湊圖標顯示正常）
        btn_opts = {
            "width": 24,
            "height": 24,
            "corner_radius": 4,
            "font": ("微軟雅黑", -12, "bold"),
            "fg_color": PALETTE["secondary"],
            "text_color": PALETTE["text_main"],
            "hover_color": PALETTE["secondary_hover"],
            "border_width": 0                     # 🌟 顯式 0px 無邊框
        }

        self.btn_remove = ctk.CTkButton(self, text="-", command=on_remove, **btn_opts)
        self.btn_remove.grid(row=0, column=0, padx=1)

        self.btn_add = ctk.CTkButton(self, text="+", command=on_add, **btn_opts)
        self.btn_add.grid(row=0, column=1, padx=1)

        self.btn_up = ctk.CTkButton(self, text="▲", command=on_up, **btn_opts)
        self.btn_up.grid(row=0, column=2, padx=1)

        self.btn_down = ctk.CTkButton(self, text="▼", command=on_down, **btn_opts)
        self.btn_down.grid(row=0, column=3, padx=1)

    def configure_commands(self, on_remove=None, on_add=None, on_up=None, on_down=None):
        """動態重綁定回調邏輯（解決列表重拍重繪後的命令刷新）"""
        if on_remove is not None:
            self.btn_remove.configure(command=on_remove)
        if on_add is not None:
            self.btn_add.configure(command=on_add)
        if on_up is not None:
            self.btn_up.configure(command=on_up)
        if on_down is not None:
            self.btn_down.configure(command=on_down)