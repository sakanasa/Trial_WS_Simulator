# -*- coding: utf-8 -*-
"""
主界面右栏面板视图 (Right Column View) - 自动换行终极修复版
采用 CTkTextbox (wrap="word", fg_color="transparent") 伪装文本区，
彻底解决 CTkLabel 动态 wraplength 导致的文本遮挡与计算卡顿问题。
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Any, List, Dict, Callable, Optional

from ui.components.right_column.single_op_tab import SingleOpTab
from ui.components.right_column.char_eval_tab import CharEvalTab
from ui.components.right_column.single_test_tab import SingleTestTab
from ui.components.right_column.multi_sim_tab import MultiSimTab
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


def _render_step_card(
    parent_frame: ctk.CTkFrame, 
    step: Dict[str, Any], 
    format_zone_func: Optional[Callable] = None
):
    """🌟 采用 CTkTextbox 伪装文本区的通用步骤日志卡片渲染器"""
    step_title = step.get("title") or (
        f"操作{step['index']}" if not step.get("is_cancel") else f"取消触发 (源自操作{step['index']})"
    )

    card_frame = ctk.CTkFrame(
        parent_frame,
        fg_color=PALETTE["card_bg"],
        corner_radius=12,
        border_width=2,
        border_color=PALETTE["card_border"]
    )
    card_frame.pack(fill=tk.X, pady=4, padx=2)

    # 1. 顶部标题（保持加粗单行显示）
    lbl_title = ctk.CTkLabel(
        card_frame, 
        text=step_title, 
        font=FONT_GLOBAL_BOLD, 
        text_color=PALETTE["text_main"], 
        justify="left", 
        anchor="w"
    )
    lbl_title.pack(anchor="w", padx=8, pady=(4, 2))

    # 2. 收集主体文本的多行内容
    content_lines = []
    content_lines.append(f"描述: {step['desc']}")
    content_lines.append(f"魂点: {step['soul']}")

    # 收集能力信息
    abilities = step.get("abilities", [])
    if abilities:
        ab_desc = []
        for ab in abilities:
            trig_mark = "（已触发）" if ab.get("triggered", False) else ""
            if ab.get("type") == "single":
                nested_op = ab.get("nested_op")
                op_type = nested_op.get("type", "能力") if isinstance(nested_op, dict) else ab.get("action", "能力")
                ab_desc.append(f"单次触发 [{op_type}]{trig_mark}")
            elif ab.get("type") == "multi":
                tot = ab.get("total", 1)
                cnt = ab.get("triggered_count", 0)
                rem = ab.get("remaining", tot - cnt)
                ab_desc.append(f"多次触发: 剩余 {rem}/{tot} 次")

        if ab_desc:
            content_lines.append("当前能力: " + "; ".join(ab_desc))

    # 收集局势多行文本
    if format_zone_func and "deck" in step:
        lines = format_zone_func(step["deck"], step["control"], step["stock"], step["level"], step["clock"])
        content_lines.extend(lines)

    # 3. 🌟 核心思路：将内容合成整体文本，放入 CTkTextbox 伪装成透明只读标签
    body_text = "\n".join(content_lines)

    # 根据行数与长文本估算自适应高度，防止文字裁切
    estimated_lines = sum(max(1, (len(line) + 20) // 25) for line in content_lines)
    textbox_height = max(35, estimated_lines * 20 + 8)

    text_display = ctk.CTkTextbox(
        card_frame,
        wrap="word",                 # 【关键】启用原生按单词/字符自动换行
        font=FONT_GLOBAL,
        fg_color="transparent",      # 【关键】背景透明，透出卡片背景
        text_color=PALETTE["text_sub"],
        border_width=0,              # 去掉 Textbox 自身的边框
        activate_scrollbars=False,   # 禁用滚动条
        height=textbox_height
    )
    text_display.pack(fill=tk.X, padx=4, pady=(0, 4))
    text_display.insert("1.0", body_text)
    text_display.configure(state="disabled")  # 设置为只读模式


class RightColumnView(ctk.CTkFrame):
    """右栏结果视图类（支持 2x2 自适应选项卡布局）"""

    @property
    def multi_winrate_label(self): return self.multi_tab.winrate_label
    @property
    def multi_avg_damage_label(self): return self.multi_tab.avg_damage_label
    @property
    def multi_ci_label(self): return self.multi_tab.ci_label
    @property
    def multi_diff_label(self): return self.multi_tab.diff_label
    @property
    def multi_time_label(self): return self.multi_tab.time_label

    def __init__(self, parent: tk.Widget, app_controller: Any, **kwargs):
        super().__init__(parent, fg_color=("#F1F5F9", "#111827"), **kwargs)
        self.app = app_controller
        self._build_ui()

    def _build_ui(self):
        # 1. 顶置 2x2 页签控制矩阵容器
        self.tab_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_btn_frame.pack(fill=tk.X, padx=6, pady=(6, 2))
        
        self.tab_btn_frame.grid_columnconfigure(0, weight=1)
        self.tab_btn_frame.grid_columnconfigure(1, weight=1)

        btn_opts = {"font": FONT_GLOBAL, "height": 28, "corner_radius": 6}

        self.btn_single = ctk.CTkButton(self.tab_btn_frame, text="单次操作", command=lambda: self.select_tab("单次操作"), **btn_opts)
        self.btn_single.grid(row=0, column=0, padx=1, pady=1, sticky="ew")

        self.btn_char = ctk.CTkButton(self.tab_btn_frame, text="单角色评估", command=lambda: self.select_tab("单角色评估"), **btn_opts)
        self.btn_char.grid(row=0, column=1, padx=1, pady=1, sticky="ew")

        self.btn_single_test = ctk.CTkButton(self.tab_btn_frame, text="单次测试", command=lambda: self.select_tab("单次测试"), **btn_opts)
        self.btn_single_test.grid(row=1, column=0, padx=1, pady=1, sticky="ew")

        self.btn_multi = ctk.CTkButton(self.tab_btn_frame, text="多次模拟", command=lambda: self.select_tab("多次模拟"), **btn_opts)
        self.btn_multi.grid(row=1, column=1, padx=1, pady=1, sticky="ew")

        self.buttons_dict = {
            "单次操作": self.btn_single, "单角色评估": self.btn_char,
            "单次测试": self.btn_single_test, "多次模拟": self.btn_multi
        }

        # 2. 挂载 4 个独立页签组件
        self.container_card = ctk.CTkFrame(self, fg_color=PALETTE["panel_bg"], corner_radius=12, border_width=0)
        self.container_card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.single_tab = SingleOpTab(self.container_card)
        self.char_tab = CharEvalTab(self.container_card)
        self.single_test_tab = SingleTestTab(self.container_card)
        self.multi_tab = MultiSimTab(self.container_card)

        self.tabs_dict = {
            "单次操作": self.single_tab, "单角色评估": self.char_tab,
            "单次测试": self.single_test_tab, "多次模拟": self.multi_tab
        }

        class NotebookCompat:
            def __init__(self, outer): self.outer = outer
            def select(self, target_tab):
                for name, tab in self.outer.tabs_dict.items():
                    if tab == target_tab:
                        self.outer.select_tab(name)
                        break

        self.notebook = NotebookCompat(self)
        self.select_tab("单次操作")

    def select_tab(self, tab_name: str):
        for name, tab in self.tabs_dict.items():
            if name == tab_name:
                tab.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
            else:
                tab.pack_forget()

        for name, btn in self.buttons_dict.items():
            if name == tab_name:
                btn.configure(fg_color=PALETTE["primary"], hover_color=PALETTE["primary_hover"], text_color=("#FFFFFF", "#0B0F19"))
            else:
                btn.configure(fg_color=PALETTE["secondary"], hover_color=PALETTE["secondary_hover"], text_color=PALETTE["text_main"])

    def render_single_op_result(self, msg: str, game_over: bool, before_lines: list, after_lines: list):
        """🌟 单次操作结果面板同样改用透明 CTkTextbox 自动换行"""
        self.select_tab("单次操作")

        res_text = "胜利" if game_over else "继续"
        self.single_tab.init_card.update_info(f"单次操作评估结果：{res_text}", before_lines)

        for child in self.single_tab.result_frame.winfo_children():
            child.destroy()

        result_card = ctk.CTkFrame(
            self.single_tab.result_frame, 
            fg_color=PALETTE["card_bg"], 
            corner_radius=12, 
            border_width=2, 
            border_color=PALETTE["card_border"]
        )
        result_card.pack(fill=tk.X, pady=(2, 6), padx=2)

        # 构建文本主体
        lines = [f"【操作结果】: {msg}", "", "【操作后状态】"]
        if after_lines:
            lines.extend(after_lines)

        body_text = "\n".join(lines)
        estimated_lines = sum(max(1, (len(l) + 20) // 25) for l in lines)
        textbox_height = max(50, estimated_lines * 20 + 8)

        text_display = ctk.CTkTextbox(
            result_card,
            wrap="word",
            font=FONT_GLOBAL,
            fg_color="transparent",
            text_color=PALETTE["text_main"],
            border_width=0,
            activate_scrollbars=False,
            height=textbox_height
        )
        text_display.pack(fill=tk.X, padx=6, pady=6)
        text_display.insert("1.0", body_text)
        text_display.configure(state="disabled")

    def render_char_results(self, steps_info: List[Dict[str, Any]], game_over: bool, before_lines: list = None, format_zone_func: Callable = None):
        """单角色评估结果渲染"""
        self.select_tab("单角色评估")

        result_txt = "游戏胜利！" if game_over else "所有操作完成，游戏继续。"
        self.char_tab.init_card.update_info(f"单角色评估结果：{result_txt}", before_lines)

        for widget in self.char_tab.result_frame.winfo_children():
            widget.destroy()

        for step in steps_info:
            _render_step_card(self.char_tab.result_frame, step, format_zone_func)

    def render_single_test_results(
        self, test_type: str, steps_info: List[Dict[str, Any]], game_over: bool, 
        our_failed: bool = False, before_lines: list = None, format_zone_func: Callable = None
    ):
        """单次测试日志渲染"""
        self.select_tab("单次测试")

        if our_failed: res_text = "我方败北（触发失败条件，操作强制截断）"
        elif game_over: res_text = "胜利（斩杀成功）"
        else: res_text = "未斩杀（继续）"

        self.single_test_tab.init_card.update_info(f"单次测试评估结果 ({test_type})：{res_text}", before_lines)

        for widget in self.single_test_tab.result_frame.winfo_children():
            widget.destroy()

        for step in steps_info:
            _render_step_card(self.single_test_tab.result_frame, step, format_zone_func)