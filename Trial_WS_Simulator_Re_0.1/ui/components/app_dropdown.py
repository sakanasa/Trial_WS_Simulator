# -*- coding: utf-8 -*-
"""
全局统一下拉框组件 (AppDropdown) - Geek Indigo 统一样式版
使用动态修补 (Monkey Patch) 拦截几何绘制，100% 完美支持亮/暗色模式自适应切换
"""

import sys
import tkinter as tk
from typing import Union
import customtkinter as ctk

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD

# =====================================================================
# 1. 动态修补 (Monkey Patch) 绘图引擎，在底层无缝绘制高精度实心三角形
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
    
    # 获取 Canvas 中已有的箭头
    existing = self._canvas.find_withtag("dropdown_arrow")
    
    # 如果已存在但不是 polygon (例如原生 font_shapes 渲染的 text)，清除之，防止渲染冲突
    if existing:
        if self._canvas.type(existing[0]) != "polygon":
            self._canvas.delete("dropdown_arrow")
            existing = None
            
    if not existing:
        # 创建实心多边形
        self._canvas.create_polygon(0, 0, 0, 0, 0, 0, tags="dropdown_arrow")
        self._canvas.tag_raise("dropdown_arrow")
        requires_recoloring = True
        
    # 精准几何计算：1:2 高宽比例，保证底部尖端为完美的 90 度直角
    half_width = size / 3.0    
    half_height = size / 6.0   
    
    self._canvas.coords(
        "dropdown_arrow",
        x_position - half_width, y_position - half_height,  # 左上
        x_position + half_width, y_position - half_height,  # 右上
        x_position, y_position + half_height                # 底部直角顶点（向下）
    )
    
    return requires_recoloring

# 替换全局底层的箭头绘制逻辑
DrawEngine.draw_dropdown_arrow = custom_draw_dropdown_arrow


# =====================================================================
# 2. 精简版 AppDropdown 包装类 (对 LeftColumn 保持 100% 接口兼容)
# =====================================================================

class AppDropdown(ctk.CTkOptionMenu):
    """
    Geek Indigo 下拉框外观包装类。
    100% 支持亮/暗模式主题自适应。
    """
    DEFAULT_STYLE = {
        "fg_color": PALETTE["secondary"],                   # 控件主底色
        "button_color": PALETTE["secondary_hover"],         # 箭头区域底色
        "button_hover_color": PALETTE["secondary_hover"],   # 箭头悬停色
        "dropdown_fg_color": PALETTE["secondary"],          # 🌟 弹出菜单背景色
        "dropdown_hover_color": PALETTE["secondary_hover"], # 🌟 弹出菜单悬停色
        "dropdown_text_color": PALETTE["text_main"],        # 🌟 弹出菜单文字色
        "text_color": PALETTE["text_main"],                 # 选中文字色
        "font": FONT_GLOBAL,
        "corner_radius": 6,
        "height": 28,
        "dynamic_resizing": False
    }

    def __init__(self, master, **kwargs):
        style = self.DEFAULT_STYLE.copy()
        style.update(kwargs)
        
        # 🌟 彻底弹出边框参数，防止 CustomTkinter 抛出 ValueError 崩溃
        style.pop("border_color", None)
        style.pop("border_width", None)
        
        super().__init__(master, **style)

# app_dropdown.py 末尾

class CTkControlButtons(ctk.CTkFrame):
    """
    Geek Indigo 统一样式的 [- + ▲ ▼] 控制按钮组。
    采用封装的透明 CTkFrame 承载，自动对齐，高度契合系统配色。
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
        
        # 统一样式参数（采用 -12 像素绝对字号保证紧凑图标显示正常）
        btn_opts = {
            "width": 24,
            "height": 24,
            "corner_radius": 4,
            "font": ("微软雅黑", -12, "bold"),
            "fg_color": PALETTE["secondary"],
            "text_color": PALETTE["text_main"],
            "hover_color": PALETTE["secondary_hover"],
            "border_width": 0                     # 🌟 显式 0px 无边框
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
        """动态重绑定回调逻辑（解决列表重拍重绘后的命令刷新）"""
        if on_remove is not None:
            self.btn_remove.configure(command=on_remove)
        if on_add is not None:
            self.btn_add.configure(command=on_add)
        if on_up is not None:
            self.btn_up.configure(command=on_up)
        if on_down is not None:
            self.btn_down.configure(command=on_down)