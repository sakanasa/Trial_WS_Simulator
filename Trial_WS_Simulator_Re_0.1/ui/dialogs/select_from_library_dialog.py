# -*- coding: utf-8 -*-
"""
内部卡库选择对话框 (Select From Library Dialog)
独立封装供卡区表格、编辑器导入卡牌时使用的通用卡库选择与文件导入弹窗。
"""

import copy
import json
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from typing import Any, List, Optional, Callable

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class SelectFromLibraryDialog(ctk.CTkToplevel):
    """程序内部自定义卡库选择对话框类（供工况网格与编辑器导入卡牌使用）"""

    def __init__(self, parent: tk.Widget, app_controller: Any, on_select: Callable[[dict], None], **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app_controller
        self.on_select = on_select
        self.title("WS 自定义卡片选择器")
        self.geometry("1100x780")
        
        self.configure(fg_color=PALETTE["bg_main"])
        
        self.after(10, lambda: self.lift())
        self.after(50, lambda: self.focus_force())

        self.transient(parent)
        self.grab_set()

        self.cards_data = getattr(self.app, "custom_cards_data", [])
        self.selected_index: int = 0
        self.selected_card: Optional[dict] = None
        self.card_buttons: List[ctk.CTkButton] = []

        self._build_ui()
        if self.cards_data:
            self._select_card_by_index(0)

    def _build_ui(self):
        label_font = FONT_GLOBAL
        header_font = FONT_GLOBAL_BOLD

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 1. 顶部说明栏
        ctk.CTkLabel(
            main_frame, 
            text="请从左侧选择要导入的卡牌，或从外部 JSON 加载：", 
            font=header_font, 
            text_color=PALETTE["text_main"]
        ).pack(side=tk.TOP, anchor="w", pady=(0, 6))

        # 2. 底部操作按钮栏
        btn_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

        ctk.CTkButton(
            btn_row, text="取消", width=80, height=32, font=label_font,
            fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"],
            command=self.destroy
        ).pack(side=tk.LEFT, padx=4)

        ctk.CTkButton(
            btn_row, text="确认导入所选卡牌", width=150, height=32, font=header_font,
            fg_color=PALETTE["primary"], text_color=("#FFFFFF", "#0B0F19"), hover_color=PALETTE["primary_hover"],
            command=self._confirm_selection
        ).pack(side=tk.RIGHT, padx=4)

        ctk.CTkButton(
            btn_row, text="从外部 JSON 文件导入...", height=32, font=label_font,
            fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"],
            command=self._import_from_external_file
        ).pack(side=tk.RIGHT, padx=4)

        # 3. 中间双栏卡片
        pane = ctk.CTkFrame(main_frame, fg_color="transparent")
        pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=4)

        # 左侧卡片：卡片选择列表
        left_card = ctk.CTkFrame(pane, fg_color=PALETTE["card_bg"], corner_radius=12, border_width=1, border_color=PALETTE["card_border"], width=340)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 4))
        left_card.pack_propagate(False)

        ctk.CTkLabel(left_card, text="卡片选择列表", font=header_font, text_color=PALETTE["text_main"]).pack(anchor="w", padx=10, pady=(8, 4))

        scroll_list = ctk.CTkScrollableFrame(left_card, fg_color="transparent")
        scroll_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 6))

        self.card_buttons.clear()
        if not self.cards_data:
            ctk.CTkLabel(scroll_list, text="当前内部卡库为空", font=label_font, text_color=PALETTE["text_sub"]).pack(pady=20, padx=10)
        else:
            for idx, card in enumerate(self.cards_data):
                btn_text = f" 第 {idx+1} 张 : [{card.get('type', '角色')}] {card.get('name', '未命名')} "
                btn = ctk.CTkButton(
                    scroll_list, text=btn_text, font=label_font, anchor="w",
                    fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"],
                    height=32,
                    command=lambda i=idx: self._select_card_by_index(i)
                )
                btn.pack(fill=tk.X, pady=2, padx=2)
                self.card_buttons.append(btn)

        # 右侧卡片：详细属性与能力
        right_card = ctk.CTkFrame(pane, fg_color=PALETTE["card_bg"], corner_radius=12, border_width=1, border_color=PALETTE["card_border"])
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))

        ctk.CTkLabel(right_card, text="选中卡牌详细属性与能力", font=header_font, text_color=PALETTE["text_main"]).pack(anchor="w", padx=10, pady=(8, 4))

        self.detail_text = ctk.CTkTextbox(right_card, wrap="word", font=FONT_GLOBAL, fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"])
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    def _select_card_by_index(self, idx: int):
        if not (0 <= idx < len(self.cards_data)):
            return

        self.selected_index = idx
        card = self.cards_data[idx]
        self.selected_card = card

        for i, btn in enumerate(self.card_buttons):
            if i == idx:
                btn.configure(fg_color=PALETTE["primary"], text_color=("#FFFFFF", "#0B0F19"))
            else:
                btn.configure(fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"])

        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", tk.END)

        lines = [
            f"【当前选择】: 第 {idx+1} 张卡牌",
            f"【卡牌名称】: {card.get('name', '未命名')}",
            f"【卡牌种类】: {card.get('type', '角色')}",
            f"【等级/费用】: Level {card.get('level', 0)} / Cost {card.get('cost', 0)}",
            f"【基础力量】: {card.get('power', 0)}",
            f"【基础魂点】: {card.get('soul', 1)}    【触发魂点】: {card.get('trigger_soul', 0)}",
            f"【触发标记】: {card.get('trigger', '无')}",
            "──────────────────────────────────────────",
            "【7 步特有能力配置】:"
        ]

        effects = card.get("effects", {})
        phase_labels = [
            ("pre_attack", "(1) 攻击前"), ("attack_type", "(2) 攻击方式"),
            ("on_attack", "(3) 攻击时"), ("trigger_step", "(4) 判定阶段"),
            ("deal_damage", "(5) 伤害结算"), ("on_reverse", "(6) 击倒对手时"),
            ("post_attack", "(7) 攻击结束")
        ]

        has_eff = False
        if isinstance(effects, dict):
            for pk, plabel in phase_labels:
                ops = effects.get(pk, [])
                if ops:
                    has_eff = True
                    op_names = [op.get("type", "操作") if isinstance(op, dict) else "操作" for op in ops]
                    lines.append(f"  > {plabel}: {', '.join(op_names)}")

        if not has_eff:
            lines.append("  > (无特殊能力配置)")

        self.detail_text.insert(tk.END, "\n".join(lines))
        self.detail_text.configure(state="disabled")

    def _confirm_selection(self):
        if not self.selected_card:
            messagebox.showwarning("提示", "请先选择一张卡牌！", parent=self)
            return
        card_copy = copy.deepcopy(self.selected_card)
        self.destroy()
        if hasattr(self, "on_select") and callable(self.on_select):
            self.on_select(card_copy)

    def _import_from_external_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], parent=self)
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                card_data = data[0] if isinstance(data, list) and data else data
                if isinstance(card_data, dict):
                    self.destroy()
                    if hasattr(self, "on_select") and callable(self.on_select):
                        self.on_select(card_data)
                else:
                    messagebox.showerror("格式错误", "选择的文件不包含有效的卡牌 JSON 数据！", parent=self)
            except Exception as e:
                messagebox.showerror("读取失败", f"文件打开失败：\n{e}", parent=self)