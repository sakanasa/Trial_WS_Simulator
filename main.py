# -*- coding: utf-8 -*-
"""
試製 二六式黑白雙翼模擬器
主程序啟動入口 (Geek Indigo 雙模式高顏值版)
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

import ui.builders.op_widget_factory

from ui.theme import PALETTE, FONT_GLOBAL  # 🌟 1. 引入全局常量

# 確保項目根目錄在 sys.path 中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def set_dpi_awareness():
    """設置 High DPI 感知，防止 Windows 系統下 Tkinter 界面字體模糊"""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


# main.py 的頭部與 main() 函數內修改：

def main():
    set_dpi_awareness()
    ctk.set_appearance_mode("Light")     
    ctk.set_default_color_theme("blue")  

    # 🌟 2. 將原硬編碼改為引用 PALETTE，保證主窗口底座顏色完美對應
    root = ctk.CTk(fg_color=PALETTE["bg_main"]) 

    try:
        import tkinter.font as tkfont
        for font_name in ["TkDefaultFont", "TkTextFont", "TkFixedFont"]:
            default_font = tkfont.nametofont(font_name)
            # 🌟 3. 將原硬編碼 -16 統一改為引用 FONT_GLOBAL 的像素字號 -14
            default_font.configure(family=FONT_GLOBAL[0], size=FONT_GLOBAL[1])
        root.option_add("*Font", FONT_GLOBAL)
    except Exception as e:
        print(f"[WARN] 全局默認字體設置提示: {e}")

    # GUI 主線程未捕獲異常處理
    def handle_gui_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        
        if issubclass(exc_type, tk.TclError):
            err_str = str(exc_value)
            if "expected integer" in err_str or "expected floating-point" in err_str or "invalid command name" in err_str or "font" in err_str:
                return

        err_msg = f"主線程發生未捕獲的異常：\n\n{exc_value}"
        print(f"[ERROR] {err_msg}", file=sys.stderr)
        traceback.print_exception(exc_type, exc_value, exc_tb)
        messagebox.showerror("運行錯誤", err_msg)

    root.report_callback_exception = handle_gui_exception

    # 啟動主 UI 類
    try:
        from ui.app import App
        app = App(root)
    except Exception as e:
        print("[CRITICAL] 程序初始化失敗堆棧如下：", file=sys.stderr)
        traceback.print_exc()
        messagebox.showerror("啟動失敗", f"程序初始化失敗：\n{e}")
        sys.exit(1)

    root.mainloop()


if __name__ == "__main__":
    main()