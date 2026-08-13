# -*- coding: utf-8 -*-
"""
试制 二六式黑白双翼模拟器
主程序启动入口 (Geek Indigo 双模式高颜值版)
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

import ui.builders.op_widget_factory

from ui.theme import PALETTE, FONT_GLOBAL  # 🌟 1. 引入全局常量

# 确保项目根目录在 sys.path 中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def set_dpi_awareness():
    """设置 High DPI 感知，防止 Windows 系统下 Tkinter 界面字体模糊"""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


# main.py 的头部与 main() 函数内修改：

def main():
    set_dpi_awareness()
    ctk.set_appearance_mode("Light")     
    ctk.set_default_color_theme("blue")  

    # 🌟 2. 将原硬编码改为引用 PALETTE，保证主窗口底座颜色完美对应
    root = ctk.CTk(fg_color=PALETTE["bg_main"]) 

    try:
        import tkinter.font as tkfont
        for font_name in ["TkDefaultFont", "TkTextFont", "TkFixedFont"]:
            default_font = tkfont.nametofont(font_name)
            # 🌟 3. 将原硬编码 -16 统一改为引用 FONT_GLOBAL 的像素字号 -14
            default_font.configure(family=FONT_GLOBAL[0], size=FONT_GLOBAL[1])
        root.option_add("*Font", FONT_GLOBAL)
    except Exception as e:
        print(f"[WARN] 全局默认字体设置提示: {e}")

    # GUI 主线程未捕获异常处理
    def handle_gui_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        
        if issubclass(exc_type, tk.TclError):
            err_str = str(exc_value)
            if "expected integer" in err_str or "expected floating-point" in err_str or "invalid command name" in err_str or "font" in err_str:
                return

        err_msg = f"主线程发生未捕获的异常：\n\n{exc_value}"
        print(f"[ERROR] {err_msg}", file=sys.stderr)
        traceback.print_exception(exc_type, exc_value, exc_tb)
        messagebox.showerror("运行错误", err_msg)

    root.report_callback_exception = handle_gui_exception

    # 启动主 UI 类
    try:
        from ui.app import App
        app = App(root)
    except Exception as e:
        print("[CRITICAL] 程序初始化失败堆栈如下：", file=sys.stderr)
        traceback.print_exc()
        messagebox.showerror("启动失败", f"程序初始化失败：\n{e}")
        sys.exit(1)

    root.mainloop()


if __name__ == "__main__":
    main()