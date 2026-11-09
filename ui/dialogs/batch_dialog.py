# -*- coding: utf-8 -*-
"""
矩陣批量統計彈窗 (Batch Statistics Dialog) - Geek Indigo 統一樣式高顏值版
1. 全量採用 FONT_GLOBAL (-14px 五號字) 與 FONT_GLOBAL_BOLD。
2. 配置底座與卡片完全對應 Geek Indigo / GitHub 黑碳灰規範，消除直角白邊。
3. 文本框字體統一為等寬 Consolas (-13px)，保證矩陣結果輸出完美對齊。
"""

import time
import random
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import Any, List

from core.engine import build_deck, stabilize
from simulator.runner import SimulationRunner
from simulator.statistics import format_elapsed_time, calc_winrate, calc_avg_damage
from utils.registry import registry
from ui.components.app_dropdown import AppDropdown
from ui.components.common.preset_toolbar import PresetToolbar
from ui.dialogs.kill_rate_chart_dialog import KillRateChartDialog
from services.batch_matrix_service import batch_matrix_service

# 統一自中央主題庫引入配色與字體規範
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class BatchStatisticsDialog(ctk.CTkToplevel):
    """矩陣批量統計分析對話框類"""

    def __init__(self, parent: tk.Widget, app_controller: Any, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app_controller
        self.title("矩陣批量統計分析")
        self.geometry("1000x700+80+60")

        # 🌟 配置窗口大底色，防止深色模式下閃白
        self.configure(fg_color=PALETTE["bg_main"])

        self.after(10, lambda: self.lift())
        self.after(50, lambda: self.focus_force())

        self._init_variables()
        self._build_ui()

    def _init_variables(self):
        self.var_options = ["無", "牌組潮數", "牌組肉數", "傷害區肉數", "等級區肉數"]

        # 縱列 (軸1) 變量
        self.batch_var1 = tk.StringVar(value="等級區肉數")
        self.batch_from1 = tk.IntVar(value=0)
        self.batch_to1 = tk.IntVar(value=3)

        # 橫行 (軸2) 變量
        self.batch_var2 = tk.StringVar(value="傷害區肉數")
        self.batch_from2 = tk.IntVar(value=0)
        self.batch_to2 = tk.IntVar(value=6)

        # 🌟 最近一次計算出的矩陣結果，供命名存檔使用
        self.last_result: dict = None

    def _build_ui(self):
        """🌟 三級色彩結構重構：消除多餘嵌套，對齊 left_column 統一樣式"""
        
        # ==========================================
        # 二級結構：左列與右列面板 (背景色: #F1F5F9 / #111827)
        # ==========================================
        left_col = ctk.CTkFrame(
            self, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=8, 
            width=380
        )
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, padx=(8, 4), pady=8)
        left_col.pack_propagate(False)

        right_col = ctk.CTkFrame(
            self, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=8
        )
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)

        # 輸入框統一樣式配置（對齊 left_column 控件）
        entry_opts = {
            "width": 45,
            "height": 28,
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"], # 🌟 統一高對比度描邊
            "border_width": 1.5,                     # 🌟 統一 1.5px 描邊
            "text_color": PALETTE["text_main"]
        }

        # ==========================================
        # 三級結構 (左列內部)：獨立配置卡片 (背景色: card_bg)
        # ==========================================

        # --- 卡片 1：橫行 (軸2) 配置 ---
        row2_card = ctk.CTkFrame(
            left_col, 
            fg_color=PALETTE["card_bg"], 
            corner_radius=8, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        row2_card.pack(fill=tk.X, padx=6, pady=6)

        ctk.CTkLabel(
            row2_card, 
            text="橫行 (軸2) 配置", 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        ).pack(anchor="w", padx=10, pady=(8, 4))

        r2 = ctk.CTkFrame(row2_card, fg_color="transparent")
        r2.pack(fill=tk.X, padx=10, pady=(0, 8))

        ctk.CTkLabel(r2, text="變量:", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(0, 2))
        AppDropdown(r2, variable=self.batch_var2, values=self.var_options, width=110).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(r2, text="從", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(6, 2))
        ctk.CTkEntry(r2, textvariable=self.batch_from2, **entry_opts).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(r2, text="到", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(6, 2))
        ctk.CTkEntry(r2, textvariable=self.batch_to2, **entry_opts).pack(side=tk.LEFT, padx=2)

        # --- 卡片 2：縱列 (軸1) 配置 ---
        row1_card = ctk.CTkFrame(
            left_col, 
            fg_color=PALETTE["card_bg"], 
            corner_radius=8, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        row1_card.pack(fill=tk.X, padx=6, pady=6)

        ctk.CTkLabel(
            row1_card, 
            text="縱列 (軸1) 配置", 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        ).pack(anchor="w", padx=10, pady=(8, 4))

        r1 = ctk.CTkFrame(row1_card, fg_color="transparent")
        r1.pack(fill=tk.X, padx=10, pady=(0, 8))

        ctk.CTkLabel(r1, text="變量:", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(0, 2))
        AppDropdown(r1, variable=self.batch_var1, values=self.var_options, width=110).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(r1, text="從", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(6, 2))
        ctk.CTkEntry(r1, textvariable=self.batch_from1, **entry_opts).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(r1, text="到", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(6, 2))
        ctk.CTkEntry(r1, textvariable=self.batch_to1, **entry_opts).pack(side=tk.LEFT, padx=2)

        # --- 左列底部的控制按鍵與進度條 ---
        self.start_btn = ctk.CTkButton(
            left_col,
            text="開始矩陣批量統計",
            command=self.run_batch_statistics,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=("#FFFFFF", "#0B0F19"),
            font=FONT_GLOBAL_BOLD,
            height=36
        )
        self.start_btn.pack(fill=tk.X, padx=6, pady=(12, 6))

        self.progress_bar = ctk.CTkProgressBar(left_col, progress_color=PALETTE["primary"], height=8)
        self.progress_bar.pack(fill=tk.X, padx=6, pady=4)
        self.progress_bar.set(0.0)

        self.progress_label = ctk.CTkLabel(left_col, text="總進度：0%", font=FONT_GLOBAL, text_color=PALETTE["text_sub"])
        self.progress_label.pack(pady=(0, 8))

        # ==========================================
        # 三級結構 (右列內部)：結果展示卡片 (背景色: card_bg)
        # ==========================================
        right_card = ctk.CTkFrame(
            right_col, 
            fg_color=PALETTE["card_bg"], 
            corner_radius=8, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        right_card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        result_header = ctk.CTkFrame(right_card, fg_color="transparent")
        result_header.pack(fill=tk.X, padx=10, pady=(8, 4))

        ctk.CTkLabel(
            result_header,
            text="=== 矩陣統計分析結果 ===",
            font=FONT_GLOBAL_BOLD,
            text_color=PALETTE["text_main"]
        ).pack(side=tk.LEFT)

        ctk.CTkButton(
            result_header, text="斬殺率比較圖", command=self._open_kill_rate_chart,
            fg_color=PALETTE["secondary"], hover_color=PALETTE["secondary_hover"],
            text_color=PALETTE["text_main"], font=FONT_GLOBAL, width=100, height=26
        ).pack(side=tk.RIGHT)

        # 🌟 斬殺率矩陣具名存檔／匯入工具列（內嵌控件，不使用彈窗）
        self.matrix_preset_toolbar = PresetToolbar(
            right_card,
            get_names=batch_matrix_service.get_names,
            on_save=self._save_batch_matrix_as,
            on_import=self._import_batch_matrix,
            on_delete=lambda name: batch_matrix_service.delete_preset(name),
        )
        self.matrix_preset_toolbar.pack(fill=tk.X, padx=10, pady=(0, 6), anchor="w")

        # 結果輸出框（保持原有的 secondary 配色與等寬字體，不影響功能）
        self.result_text = ctk.CTkTextbox(
            right_card, 
            wrap="none", 
            font=("Consolas", -13), 
            fg_color=PALETTE["secondary"], 
            text_color=PALETTE["text_main"]
        )
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    def run_batch_statistics(self):
        var1 = self.batch_var1.get()
        var2 = self.batch_var2.get()

        if var1 == "無" and var2 == "無":
            messagebox.showwarning("警告", "必須至少選擇一個有效的矩陣變量！", parent=self)
            return

        mode = self.app.middle_col.multi_mode_var.get()
        if mode == "常規":
            sim_times = self.app.middle_col.reg_sim_times.get()
            ops_params = [registry.extract_params(op) for op in self.app.reg_ops]
            execution_plan, roles_params = None, None
        elif mode == "高級":
            sim_times = self.app.middle_col.adv_sim_times.get()
            execution_plan, roles_params = self.app._get_advanced_execution_plan()
            ops_params = None
        else:  # 殘局模式
            sim_times = self.app.middle_col.cond_sim_times.get()
            execution_plan, roles_params = self.app._get_condition_execution_plan()
            ops_params = None

        def get_range(var_name, f_val, t_val):
            if var_name == "無":
                return [None]
            s, e = f_val.get(), t_val.get()
            return list(range(s, e + 1)) if s <= e else list(range(s, e - 1, -1))

        range1 = get_range(var1, self.batch_from1, self.batch_to1)
        range2 = get_range(var2, self.batch_from2, self.batch_to2)
        total_combinations = len(range1) * len(range2)

        self.progress_bar.set(0.0)
        self.start_btn.configure(state="disabled")

        fixed = self.app._get_fixed_state_params()
        level_meat_def = sum(1 for v in self.app.left_col.level_vars if v.get() == "肉")
        clock_meat_def = sum(1 for v in self.app.left_col.clock_vars if v.get() == "肉")

        def _batch_thread():
            start_time = time.time()
            winrate_matrix = [[0.0] * len(range2) for _ in range(len(range1))]
            avg_dmg_matrix = [[0.0] * len(range2) for _ in range(len(range1))]

            combination_count = 0

            for i, val1 in enumerate(range1):
                for j, val2 in enumerate(range2):
                    wins = 0
                    total_dmg = 0

                    for k in range(sim_times):
                        d, c, s, l, cl = self._build_batch_cell_state(
                            var1, val1, var2, val2, fixed, level_meat_def, clock_meat_def
                        )
                        stabilize_func = lambda: stabilize(d, c, l, cl)

                        if mode == "常規":
                            game_over = False
                            dmg = 0
                            for op in ops_params:
                                opt = op["type"]
                                if opt in registry.types and registry.types[opt]["execute"]:
                                    over, _, extra = registry.execute(opt, d, c, s, l, cl, op, stabilize_func)
                                    dmg += extra.get("total_damage", 0)
                                    if over:
                                        game_over = True
                                        break
                        else:
                            game_over = False
                            dmg = 0
                            pending_pass = {}
                            global_ice_armors = []
                            role_states = [{"soul": rp["soul"], "abilities": [], "ops": rp["ops"]} for rp in roles_params]

                            for role_idx, start_idx, end_idx in execution_plan:
                                if game_over:
                                    break
                                rstate = role_states[role_idx]
                                over, seg_dmg, _ = SimulationRunner.simulate_role_ops_segment(
                                    d, c, s, l, cl, rstate, rstate["ops"],
                                    start_idx, end_idx, pending_pass, role_idx, len(roles_params),
                                    collect_steps=False, global_ice_armors=global_ice_armors
                                )
                                dmg += seg_dmg
                                if over:
                                    game_over = True

                        total_dmg += dmg
                        if game_over:
                            wins += 1

                    winrate_matrix[i][j] = calc_winrate(wins, sim_times)
                    avg_dmg_matrix[i][j] = calc_avg_damage(total_dmg, sim_times)

                    combination_count += 1
                    pct = int((combination_count / total_combinations) * 100)
                    self.after(0, lambda c=combination_count, p=pct: self._update_progress(c, p))

            elapsed = time.time() - start_time
            self.after(0, lambda: self._render_results(winrate_matrix, avg_dmg_matrix, range1, range2, var1, var2, elapsed))

        threading.Thread(target=_batch_thread, daemon=True).start()

    def _build_batch_cell_state(self, var1, val1, var2, val2, fixed, level_meat_def, clock_meat_def):
        d_normal = fixed["deck_normal"]
        d_climax = fixed["deck_climax"]
        c_normal = fixed["control_normal"]
        c_climax = fixed["control_climax"]

        clock_meat = None
        level_meat = None

        if var1 == "牌組潮數" and val1 is not None: d_climax = val1
        elif var1 == "牌組肉數" and val1 is not None: d_normal = val1
        elif var1 == "傷害區肉數" and val1 is not None: clock_meat = val1
        elif var1 == "等級區肉數" and val1 is not None: level_meat = val1

        if var2 == "牌組潮數" and val2 is not None: d_climax = val2
        elif var2 == "牌組肉數" and val2 is not None: d_normal = val2
        elif var2 == "傷害區肉數" and val2 is not None: clock_meat = val2
        elif var2 == "等級區肉數" and val2 is not None: level_meat = val2

        deck = build_deck(d_normal, d_climax)
        control = ["普通"] * c_normal + ["名場面"] * c_climax
        stock = ["普通"] * fixed["stock_normal"] + ["名場面"] * fixed["stock_climax"]

        l_climax = fixed["level_climax_count"]
        l_meat = level_meat if level_meat is not None else level_meat_def
        level = ["名場面"] * l_climax + ["普通"] * min(l_meat, 4 - l_climax)
        random.shuffle(level)

        cl_climax = fixed["clock_climax_count"]
        cl_meat = clock_meat if clock_meat is not None else clock_meat_def
        clock = ["名場面"] * cl_climax + ["普通"] * min(cl_meat, 6 - cl_climax)
        random.shuffle(clock)

        return deck, control, stock, level, clock

    def _update_progress(self, current, pct):
        """🌟 進度條自適應刷新"""
        self.progress_bar.set(pct / 100.0)
        self.progress_label.configure(text=f"總進度：{pct}%")

    def _render_results(self, winrate_matrix, avg_dmg_matrix, range1, range2, var1, var2, elapsed):
        self.start_btn.configure(state="normal")
        self.result_text.delete("1.0", tk.END)

        def build_table(matrix, title):
            lines = [title]
            cols = [str(v) if v is not None else "-" for v in range2]
            lines.append("\t" + "\t".join(cols))
            for i, r_val in enumerate(range1):
                r_label = str(r_val) if r_val is not None else "-"
                row_vals = [f"{matrix[i][j]:.2f}" for j in range(len(range2))]
                lines.append(f"{r_label}\t" + "\t".join(row_vals))
            return "\n".join(lines)

        txt = build_table(winrate_matrix, f"=== 斬殺率矩陣 (%) [縱軸: {var1} \\ 橫軸: {var2}] ===")
        txt += "\n\n" + build_table(avg_dmg_matrix, f"=== 平均傷害矩陣 [縱軸: {var1} \\ 橫軸: {var2}] ===")
        txt += f"\n\n總計算耗時: {format_elapsed_time(elapsed)}"

        self.result_text.insert("1.0", txt)

        # 🌟 記錄最近一次結果，供下方工具列命名存檔使用
        self.last_result = {
            "var1": var1, "var2": var2,
            "range1": range1, "range2": range2,
            "winrate_matrix": winrate_matrix, "avg_dmg_matrix": avg_dmg_matrix,
        }

    def _save_batch_matrix_as(self, name: str):
        if not self.last_result:
            return
        batch_matrix_service.set_preset(name, self.last_result)

    def _import_batch_matrix(self, name: str):
        data = batch_matrix_service.get_preset(name)
        if not data:
            return
        self.last_result = data
        self._render_results(
            data["winrate_matrix"], data["avg_dmg_matrix"],
            data["range1"], data["range2"], data["var1"], data["var2"], 0.0
        )

    def _open_kill_rate_chart(self):
        KillRateChartDialog(self, app_controller=self.app)