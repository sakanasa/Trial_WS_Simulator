# -*- coding: utf-8 -*-
"""
通用界面平滑动画工具 (UI Animations Utility) - 无描边平滑版
包含颜色平滑过渡、高亮亮起与淡出、删除红光闪烁动画函数，供全软件各类列表卡片重排时复用。
"""

import customtkinter as ctk
from ui.theme import PALETTE


def get_hex(color_val):
    """智能解析颜色：支持 tuple 双色、单色 hex 以及 transparent 透明转色"""
    if color_val == "transparent":
        mode_idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        return PALETTE["card_bg"][mode_idx]
    if isinstance(color_val, tuple):
        mode = ctk.get_appearance_mode()
        return color_val[0] if mode.lower() == "light" else color_val[1]
    return color_val


def hex_to_rgb(hex_str):
    hex_str = str(hex_str).lstrip('#')
    if len(hex_str) < 6:
        return (248, 250, 252)
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def animate_color_step(widget, param_name, start_val, end_val, steps=10, interval=20, on_complete=None):
    """颜色平滑渐变核心算法"""
    start_hex = get_hex(start_val)
    end_hex = get_hex(end_val)

    start_rgb = hex_to_rgb(start_hex)
    end_rgb = hex_to_rgb(end_hex)

    def step(current_step):
        if current_step > steps:
            try:
                widget.configure(**{param_name: end_val})
            except Exception:
                pass
            if on_complete:
                on_complete()
            return

        t = current_step / steps
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t)

        current_hex = rgb_to_hex((r, g, b))
        try:
            widget.configure(**{param_name: current_hex})
            widget.after(interval, lambda: step(current_step + 1))
        except Exception:
            if on_complete:
                on_complete()

    step(0)


def animate_widget_bg(widget, start_color=("#D1FAE5", "#064E3B"), end_color="transparent", steps=10, interval=20):
    """平滑背景高亮淡出动画（无描边）"""
    animate_color_step(widget, "fg_color", start_color, end_color, steps=steps, interval=interval)


def animate_delete_red_glow(widget, on_complete=None, steps=8, interval=15):
    """🌟 彻底无描边版：仅对背景色进行平滑淡入警示红，无突兀红线描边"""
    start_bg = PALETTE["card_bg"]
    end_bg = ("#FEE2E2", "#4C0519")  # 浅色模式粉红 / 深色模式深酒红

    animate_color_step(widget, "fg_color", start_bg, end_bg, steps=steps, interval=interval, on_complete=on_complete)