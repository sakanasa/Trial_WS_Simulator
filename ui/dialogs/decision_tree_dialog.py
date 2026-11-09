# -*- coding: utf-8 -*-
"""
決策樹與節點模擬彈窗 (Decision Tree & Sub-Node Simulation Dialog) - CustomTkinter 適配版
支持複雜的局勢博弈決策與智能評估：
1. 【顯示決策樹】：多線程推演全量決策樹，頂欄按按鈕顯式鎖定 width，絕對零位移；
2. 【彩色高亮與戰局預測】：融入 Expectimax 算法生成拓撲圖，標出每個決策點的最高期望勝率與 ⭐最優推薦；
3. 【已註冊操作展示】：顯示當前系統所有生效註冊的 Operation 列表。
"""

import threading
import tkinter as tk
import time
from tkinter import ttk, messagebox
import customtkinter as ctk
from typing import Any, Dict, Optional

from simulator.decision_tree import build_full_decision_tree, TreeNode, get_registered_operations_info
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD, FONT_FAMILY


class DecisionTreeDialog(ctk.CTkToplevel):
    """決策樹分析與節點模擬對話框類"""

    def __init__(self, parent: tk.Widget, app_controller: Any, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app_controller
        self.title("殘局模式決策樹分析 ver.1.5")
        self.geometry("1280x820+80+60")
        self.minsize(1050, 650)

        self.configure(fg_color=PALETTE["bg_main"])

        self.after(10, lambda: self.lift())
        self.after(50, lambda: self.focus_force())

        self.root_node: Optional[TreeNode] = None
        self.node_map: Dict[str, TreeNode] = {}
        self.selected_node: Optional[TreeNode] = None

        self._build_ui()

    def _build_ui(self):
        label_font = FONT_GLOBAL
        header_font = FONT_GLOBAL_BOLD

        mode_idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        bg_card = PALETTE["card_bg"]
        border_card = PALETTE["card_border"]
        text_main = PALETTE["text_main"]
        text_sub = PALETTE["text_sub"]
        sec_color = PALETTE["secondary"]

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=2)
        main_frame.rowconfigure(2, weight=1)

        # 1. 🌟 頂部操作欄卡片
        top_bar = ctk.CTkFrame(main_frame, fg_color=PALETTE["panel_bg"], corner_radius=12, border_width=1, border_color=border_card)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6), padx=2)

        top_inner = ctk.CTkFrame(top_bar, fg_color="transparent")
        top_inner.pack(fill=tk.X, padx=8, pady=6)

        # 左側控制組：保留“顯示決策樹”按鈕
        left_group = ctk.CTkFrame(top_inner, fg_color="transparent")
        left_group.pack(side=tk.LEFT)

        self.btn_build_tree = ctk.CTkButton(
            left_group, text="🌳 顯示決策樹", command=self.generate_and_render_tree_async,
            fg_color=PALETTE["primary"], hover_color=PALETTE["primary_hover"], text_color=("#FFFFFF", "#0B0F19"), 
            font=header_font, width=120, height=30
        )
        self.btn_build_tree.pack(side=tk.LEFT, padx=4)

        # 右側狀態組
        right_group = ctk.CTkFrame(top_inner, fg_color="transparent")
        right_group.pack(side=tk.RIGHT)

        self.top_progress_lbl = ctk.CTkLabel(
            right_group, text="就緒", font=label_font, text_color=text_main, width=130, anchor="e"
        )
        self.top_progress_lbl.pack(side=tk.RIGHT, padx=(4, 0))

        self.top_progress_bar = ctk.CTkProgressBar(right_group, progress_color=PALETTE["primary"], width=120, height=10)
        self.top_progress_bar.pack(side=tk.RIGHT, padx=4)
        self.top_progress_bar.set(0.0)

        # 2. 中間樹狀拓撲圖卡片
        tree_card = ctk.CTkFrame(main_frame, fg_color=PALETTE["panel_bg"], corner_radius=12, border_width=1, border_color=border_card)
        tree_card.grid(row=1, column=0, sticky="nsew", pady=4, padx=2)

        ctk.CTkLabel(
            tree_card, 
            text="決策樹拓撲 (藍色高亮最優路線 | 綠色為斬殺 | 紅色為敗北)", 
            font=header_font, 
            text_color=text_main
        ).pack(anchor="w", padx=10, pady=(8, 4))

        try:
            scaling = ctk.get_widget_scaling(self)
        except Exception:
            scaling = 1.0

        tree_font_size = int(-16 * scaling)
        tree_header_size = int(-16 * scaling)
        tree_row_height = int(36 * scaling)

        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure(
            "Treeview", 
            font=(FONT_FAMILY, tree_font_size), 
            rowheight=tree_row_height, 
            background=bg_card[mode_idx], 
            fieldbackground=bg_card[mode_idx], 
            foreground=text_main[mode_idx],
            borderwidth=0,
            relief="flat"
        )
        
        style.configure(
            "Treeview.Heading", 
            font=(FONT_FAMILY, tree_header_size, "bold"), 
            background=sec_color[mode_idx], 
            foreground=text_main[mode_idx],
            relief="flat",
            borderwidth=1,
            lightcolor=border_card[mode_idx],
            darkcolor=border_card[mode_idx]
        )

        style.map("Treeview", background=[("selected", PALETTE["primary"][mode_idx])], foreground=[("selected", "#FFFFFF")])
        style.map("Treeview.Heading", background=[("active", border_card[mode_idx])])

        cols = ("exp_winrate", "prob", "cum_prob", "enemy_deck", "enemy_clock", "enemy_level", "my_soul", "status")
        tree_inner = ctk.CTkFrame(tree_card, fg_color="transparent")
        tree_inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.tree = ttk.Treeview(tree_inner, columns=cols, selectmode="browse")

        self.tree.tag_configure("optimal", foreground=PALETTE["optimal"][mode_idx], font=(FONT_FAMILY, tree_font_size, "bold"))
        self.tree.tag_configure("win", foreground=PALETTE["success"][mode_idx])
        self.tree.tag_configure("fail", foreground=PALETTE["danger"][mode_idx])

        self.tree.heading("#0", text="節點名稱 / 執行步驟", anchor="w")
        self.tree.heading("exp_winrate", text="期望勝率", anchor="center")
        self.tree.heading("prob", text="單步概率", anchor="center")
        self.tree.heading("cum_prob", text="累積概率", anchor="center")
        self.tree.heading("enemy_deck", text="敵牌組 (肉/潮)", anchor="center")
        self.tree.heading("enemy_clock", text="敵傷害區", anchor="center")
        self.tree.heading("enemy_level", text="敵等級區", anchor="center")
        self.tree.heading("my_soul", text="當前魂點", anchor="center")
        self.tree.heading("status", text="分支狀態", anchor="center")

        self.tree.column("#0", width=460, anchor="w")
        self.tree.column("exp_winrate", width=95, anchor="center")
        self.tree.column("prob", width=85, anchor="center")
        self.tree.column("cum_prob", width=85, anchor="center")
        self.tree.column("enemy_deck", width=110, anchor="center")
        self.tree.column("enemy_clock", width=85, anchor="center")
        self.tree.column("enemy_level", width=85, anchor="center")
        self.tree.column("my_soul", width=75, anchor="center")
        self.tree.column("status", width=95, anchor="center")

        scroll_y = ttk.Scrollbar(tree_inner, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(tree_inner, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_node_selected)

        # 3. 下半部分：選中節點詳情卡片與已註冊操作展示卡片
        bottom_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        bottom_container.grid(row=2, column=0, sticky="nsew", pady=(4, 0), padx=2)

        bottom_container.rowconfigure(0, weight=1)
        bottom_container.columnconfigure(0, weight=2)
        bottom_container.columnconfigure(1, weight=1)

        # 左下：選中節點局勢明細
        detail_card = ctk.CTkFrame(bottom_container, fg_color=PALETTE["panel_bg"], corner_radius=12, border_width=1, border_color=border_card)
        detail_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ctk.CTkLabel(detail_card, text="選中節點局勢明細與戰局預測", font=header_font, text_color=text_main).pack(anchor="w", padx=8, pady=(6, 2))

        self.detail_text = ctk.CTkTextbox(
            detail_card, 
            wrap="word", 
            font=FONT_GLOBAL, 
            fg_color=sec_color, 
            text_color=text_main, 
            height=150
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # 🌟 右下：已註冊操作展示區 (替換原自選節點後續計算結果)
        res_card = ctk.CTkFrame(bottom_container, fg_color=PALETTE["panel_bg"], corner_radius=12, border_width=1, border_color=border_card)
        res_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ctk.CTkLabel(res_card, text="已註冊操作", font=header_font, text_color=text_main).pack(anchor="w", padx=8, pady=(6, 4))

        # 使用 CTkTextbox 支持自動換行與滾動
        self.txt_registered_ops = ctk.CTkTextbox(
            res_card, 
            wrap="word", 
            font=label_font, 
            fg_color=sec_color, 
            text_color=text_main, 
            height=150
        )
        self.txt_registered_ops.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # 加載填入當前已註冊的操作列表
        self.refresh_registered_ops_display()

    def refresh_registered_ops_display(self):
        """填入並更新已註冊操作的內容"""
        ops_info = get_registered_operations_info()
        self.txt_registered_ops.configure(state="normal")
        self.txt_registered_ops.delete("1.0", tk.END)
        self.txt_registered_ops.insert("1.0", ops_info)
        self.txt_registered_ops.configure(state="disabled")

    # ==================== 功能：後臺線程構建並渲染決策樹 ====================

    def generate_and_render_tree_async(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.node_map.clear()

        # 渲染前順便更新一下最新的註冊操作列表
        self.refresh_registered_ops_display()

        my_deck = getattr(self.app, "condition_deck_cards", [])
        my_control = getattr(self.app, "condition_control_cards", [])

        e_deck_normal = self.app.left_col.deck_normal.get()
        e_deck_climax = self.app.left_col.deck_climax.get()
        e_control_normal = self.app.left_col.control_normal.get()
        e_control_climax = self.app.left_col.control_climax.get()

        e_level_meat = sum(1 for v in self.app.left_col.level_vars if v.get() == "肉")
        e_level_climax = sum(1 for v in self.app.left_col.level_vars if v.get() == "潮")
        e_clock_meat = sum(1 for v in self.app.left_col.clock_vars if v.get() == "肉")
        e_clock_climax = sum(1 for v in self.app.left_col.clock_vars if v.get() == "潮")

        e_front_roles = getattr(self.app, "enemy_front_roles", {})
        c_roles = getattr(self.app, "condition_roles", [])
        c_front_cards = getattr(self.app, "condition_front_cards", {})

        self.btn_build_tree.configure(state="disabled")
        self.top_progress_bar.configure(mode="indeterminate")
        self.top_progress_bar.start()
        self.top_progress_lbl.configure(text="推演中...")

        start_time = time.time()

        def _tree_build_thread():
            try:
                def on_tree_progress(count):
                    self.after(0, lambda: self.top_progress_lbl.configure(text=f"生成節點: {count}"))

                root_node = build_full_decision_tree(
                    my_deck=my_deck,
                    my_control=my_control,
                    my_stock=getattr(self.app, "condition_stock_cards", []),
                    my_level=getattr(self.app, "condition_level_cards", {}),
                    my_clock=getattr(self.app, "condition_clock_cards", {}),
                    enemy_deck_normal=e_deck_normal,
                    enemy_deck_climax=e_deck_climax,
                    enemy_control_normal=e_control_normal,
                    enemy_control_climax=e_control_climax,
                    enemy_level_meat=e_level_meat,
                    enemy_level_climax=e_level_climax,
                    enemy_clock_meat=e_clock_meat,
                    enemy_clock_climax=e_clock_climax,
                    enemy_front_roles=e_front_roles,
                    condition_roles=c_roles,
                    condition_front_cards=c_front_cards,
                    on_progress_cb=on_tree_progress,
                )
                elapsed = time.time() - start_time
                self.after(0, lambda: self._on_tree_build_done(root_node, elapsed))

            except Exception as e:
                err = e
                self.after(0, lambda: self._on_tree_build_error(err))

        threading.Thread(target=_tree_build_thread, daemon=True).start()

    def _on_tree_build_done(self, root_node: TreeNode, elapsed: float):
        self.root_node = root_node

        def _insert_tree_node(parent_item_id: str, node: TreeNode, node_idx: int) -> str:
            item_id = f"node_{len(self.node_map)}"
            self.node_map[item_id] = node

            snap = node.state_snapshot

            node_title = node.name
            if node.is_optimal:
                node_title = f"⭐【最優推薦】{node_title}"

            exp_winrate_str = f"{node.exp_winrate * 100:.1f}%"
            prob_str = f"{node.prob * 100:.1f}%"
            cum_prob_str = f"{node.cum_prob * 100:.2f}%"

            e_deck_str = f"{snap.enemy_deck_normal}肉 / {snap.enemy_deck_climax}潮" if snap else "-"
            e_clock_str = f"{snap.enemy_clock_meat + snap.enemy_clock_climax}張" if snap else "-"
            e_level_str = f"Level {snap.enemy_level_meat + snap.enemy_level_climax}" if snap else "-"
            soul_str = str(snap.role_soul) if snap else "-"

            status_str = "運行中"
            if snap:
                if snap.game_over:
                    status_str = "勝利(斬殺)"
                elif snap.my_failed:
                    status_str = "我方敗北"

            values = (exp_winrate_str, prob_str, cum_prob_str, e_deck_str, e_clock_str, e_level_str, soul_str, status_str)

            node_tags = []
            if node.is_optimal:
                node_tags.append("optimal")
            if snap:
                if snap.game_over:
                    node_tags.append("win")
                elif snap.my_failed:
                    node_tags.append("fail")

            is_open = (parent_item_id == "")
            inserted_id = self.tree.insert(
                parent_item_id, "end", item_id, text=node_title, values=values, open=is_open, tags=tuple(node_tags)
            )

            for child_idx, child in enumerate(node.children):
                _insert_tree_node(inserted_id, child, child_idx)

            return inserted_id

        _insert_tree_node("", self.root_node, 0)

        self.top_progress_bar.stop()
        self.top_progress_bar.configure(mode="determinate")
        self.top_progress_bar.set(1.0)
        self.top_progress_lbl.configure(text=f"推演完成({elapsed:.1f}s)")
        self.btn_build_tree.configure(state="normal")

        messagebox.showinfo("生成成功", f"決策樹推演完畢(共生成 {len(self.node_map)} 個節點，耗時 {elapsed:.2f}s)！", parent=self)

    def _on_tree_build_error(self, error: Exception):
        self.top_progress_bar.stop()
        self.top_progress_bar.configure(mode="determinate")
        self.top_progress_bar.set(0.0)
        self.top_progress_lbl.configure(text="失敗")
        self.btn_build_tree.configure(state="normal")
        messagebox.showerror("生成失敗", f"構建決策樹時發生錯誤：\n{error}", parent=self)

    def _on_node_selected(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        node = self.node_map.get(item_id)
        if not node:
            return

        self.selected_node = node

        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", tk.END)

        snap = node.state_snapshot
        lines = [
            f"================================================──────────",
            f"【選中節點】: {node.name}",
            f"【期望勝率】: {node.exp_winrate * 100:.2f}%    【單步概率】: {node.prob*100:.2f}%    【累積概率】: {node.cum_prob*100:.2f}%",
            f"================================================──────────",
        ]

        parent_node = getattr(node, "parent", None)

        if node.node_type == "decision" or any(getattr(c, "node_type", "") == "choice" for c in node.children):
            lines.extend([
                "💡【決策節點分析與推薦】",
                f"  ★ 最高期望勝率：{node.exp_winrate * 100:.2f}%",
                "  ★ 各操作期望勝率對比："
            ])
            for child in node.children:
                mark = " ⭐ (當前局勢下的最佳選擇)" if child.is_optimal else " ❌"
                lines.append(f"    ► {child.name}: 期望勝率 {child.exp_winrate * 100:.2f}%{mark}")
            lines.append("----------------------------------------------------------")

        elif node.node_type == "choice" or node.is_optimal or (parent_node and getattr(parent_node, "node_type", "") == "decision"):
            mark_str = "⭐ 是 (當前局勢下的最佳選擇)" if node.is_optimal else "❌ 否 (存在期望勝率更高的操作)"
            lines.extend([
                "💡【當前決策評估】",
                f"  ★ 當前決策操作：{node.name}",
                f"  ★ 本分支期望勝率：{node.exp_winrate * 100:.2f}%",
                f"  ★ 是否推薦：{mark_str}",
                "----------------------------------------------------------"
            ])

        lines.append("【我方前列狀態】:")
        for s in ["前列1", "前列2", "前列3"]:
            c_list = snap.condition_front_cards.get(s, [])
            if c_list:
                c = c_list[0]
                c_name = c.get("name", "自定義角色")
                c_lvl = c.get("level", 0)
                c_pwr = c.get("power", 500)
                c_base_soul = c.get("soul", 1)
                c_trig_soul = c.get("trigger_soul", 0)
                lines.append(f"  ► {s} [{c_name}] : Lv.{c_lvl} | 力量:{c_pwr} | 基礎魂:{c_base_soul} | 觸發魂:{c_trig_soul} | 當前攻擊魂:{snap.role_soul}")
            else:
                lines.append(f"  ► {s} : [空]")

        lines.append("----------------------------------------------------------")

        lines.append("【敵方前列狀態】:")
        for s in ["前列1", "前列2", "前列3"]:
            e_role = snap.enemy_front_roles.get(s, {})
            lvl_item = e_role.get("level", "0")
            enemy_lvl_str = str(lvl_item.get()) if hasattr(lvl_item, "get") else str(lvl_item or "空")
            enemy_pwr = e_role.get("power", 500)
            if hasattr(enemy_pwr, "get"):
                enemy_pwr = enemy_pwr.get()
            is_rev = e_role.get("is_reversed", False)
            rev_str = "已擊倒" if is_rev else "正常"

            if enemy_lvl_str == "空":
                lines.append(f"  ► 敵{s} : [空]")
            else:
                my_cards = snap.condition_front_cards.get(s, [])
                matchup_pred = ""
                if my_cards:
                    my_pwr = int(my_cards[0].get("power", 500) or 500)
                    if my_pwr >= int(enemy_pwr or 500):
                        matchup_pred = f"  [正面戰鬥預估: 我方{my_pwr} >= 敵方{enemy_pwr} ➔ 預測擊倒]"
                    else:
                        matchup_pred = f"  [正面戰鬥預估: 我方{my_pwr} < 敵方{enemy_pwr} ➔ 無法擊倒]"

                lines.append(f"  ► 敵{s} : Lv.{enemy_lvl_str} | 力量:{enemy_pwr} | 狀態:{rev_str}{matchup_pred}")

        lines.append("----------------------------------------------------------")

        lines.extend([
            f"【敵方牌組局勢】: 肉 {snap.enemy_deck_normal} 張，潮 {snap.enemy_deck_climax} 張 (共 {snap.enemy_deck_total} 張) | 控室潮 {snap.enemy_control_climax} 張",
            f"【敵方等級/傷害】: Level {snap.enemy_level_meat + snap.enemy_level_climax} (傷害區 {snap.enemy_clock_meat + snap.enemy_clock_climax} 張)",
            "----------------------------------------------------------",
            f"【節點事件說明】: {node.details}"
        ])

        self.detail_text.insert(tk.END, "\n".join(lines))
        self.detail_text.configure(state="disabled")