# -*- coding: utf-8 -*-
"""
工况模式战场画布组件 (ConditionFieldCanvas) - 极致紧凑收拢版
包含规则：
1. 画布水平宽度收拢至卡组右边缘；
2. 底部平台缩略为“我方”，按钮缩略为“手牌”和“概览”；
3. 控制栏与标题在有效战场区域内精准居中显示；
4. 保持绝对几何对齐与零重叠。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Dict, Callable, Optional, Any
from ui.components.app_dropdown import AppDropdown
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD
from core.models import get_card_level, get_card_trigger_soul, get_card_base_soul

class ConditionFieldCanvas(ctk.CTkFrame):
    """工况模式可视化网格画布（极致紧凑收拢 WS 正统战场）"""

    def _set_appearance_mode(self, mode_string):
        """当主题改变时，同步强制刷新 Canvas 及内部控件的底色"""
        super()._set_appearance_mode(mode_string)
        self._update_canvas_theme()

    def _update_canvas_theme(self):
        """实时将 Canvas 背景、分割线和内部嵌入控件的颜色与全局 PALETTE 拉平"""
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return

        mode_idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        bg_color = PALETTE["card_bg"][mode_idx]
        panel_bg = PALETTE["panel_bg"][mode_idx]
        border_color = PALETTE["card_border"][mode_idx]

        self.canvas.configure(bg=bg_color)
        self.canvas.itemconfig("divider_red", fill="#EF4444")

        # 刷新敌方顶部标识栏
        if hasattr(self, "enemy_top_frame") and self.enemy_top_frame.winfo_exists():
            self.enemy_top_frame.configure(fg_color=panel_bg, border_color=border_color, bg_color=bg_color)

        # 刷新我方底部控制栏
        if hasattr(self, "hand_bottom_frame") and self.hand_bottom_frame.winfo_exists():
            self.hand_bottom_frame.configure(fg_color=panel_bg, border_color=border_color, bg_color=bg_color)

        # 重新触发展板绘制以更新矢量槽位颜色
        self._redraw_grid()

    def __init__(
        self,
        parent: tk.Widget,
        on_zone_click: Callable[[str], None],
        on_overview_click: Callable[[], None],
        enemy_front_roles: Optional[Dict[str, Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_zone_click = on_zone_click
        self.on_overview_click = on_overview_click

        self.zone_rects: Dict[str, int] = {}
        self.zone_texts: Dict[str, int] = {}

        self._init_ui()

        self.zone_stats = {
            "卡组": {"cx": 0, "chara": 0, "total": 0},
            "控制室": {"cx": 0, "chara": 0, "total": 0},
            "库存": {"cx": 0, "chara": 0, "total": 0},
            "思出": {"cx": 0, "chara": 0, "total": 0},
        }

        self.single_zone_cards: Dict[str, Optional[dict]] = {}

    def update_zone_stats(self, zone_name: str, cx: int = 0, chara: int = 0, total: int = 0):
        """更新单个区域统计数据并自动重绘画布"""
        if zone_name in self.zone_stats:
            if cx is not None:
                self.zone_stats[zone_name]["cx"] = cx
            if chara is not None:
                self.zone_stats[zone_name]["chara"] = chara
            if total is not None:
                self.zone_stats[zone_name]["total"] = total
            self._redraw_grid()  # 触发画布自动刷新重绘

    def set_all_zone_stats(self, stats_dict: dict, single_zone_cards: dict = None):
        """批量更新所有区域统计数据与单张卡牌区域数据，并自动刷新画布"""
        for zone_name, stats in stats_dict.items():
            if zone_name in self.zone_stats:
                self.zone_stats[zone_name].update(stats)
        if single_zone_cards:
            self.single_zone_cards.update(single_zone_cards)
        self._redraw_grid()  # 触发画布自动刷新重绘

    def _init_ui(self):
        label_font = FONT_GLOBAL
        bold_font = FONT_GLOBAL_BOLD

        # 1. 战场 Canvas 容器
        self.canvas = tk.Canvas(self, height=560, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 2. 敌我分界红虚线
        self.canvas.create_line(0, 0, 0, 0, fill="#EF4444", dash=(4, 4), width=1.5, tags="divider_red")

        # 3. 🌟【新增】敌方顶部控制/标识栏 (格式与我方底部控制栏完全相同)
        self.enemy_top_frame = ctk.CTkFrame(
            self.canvas, 
            fg_color=PALETTE["panel_bg"], 
            corner_radius=8, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )

        self.top_label = ctk.CTkLabel(self.enemy_top_frame, text="敌方", font=bold_font, text_color=PALETTE["text_main"])
        self.top_label.pack(side=tk.LEFT, expand=True, padx=12, pady=4)

        self.enemy_top_id = self.canvas.create_window(
            0, 0, window=self.enemy_top_frame, anchor="center"
        )

        # 4. 我方底部控制栏（精简缩略版：手牌 / 我方 / 概览）
        self.hand_bottom_frame = ctk.CTkFrame(
            self.canvas, 
            fg_color=PALETTE["panel_bg"], 
            corner_radius=8, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )

        self.hand_btn = ctk.CTkButton(
            self.hand_bottom_frame, text="手牌", width=60, height=26, corner_radius=6,
            font=bold_font,
            fg_color=PALETTE["primary"], text_color=("#FFFFFF", "#0B0F19"), hover_color=PALETTE["primary_hover"],
            command=lambda: self.on_zone_click("手牌")
        )
        self.hand_btn.pack(side=tk.LEFT, padx=(6, 8), pady=4)

        self.bottom_label = ctk.CTkLabel(self.hand_bottom_frame, text="我方", font=bold_font, text_color=PALETTE["text_main"])
        self.bottom_label.pack(side=tk.LEFT, expand=True, padx=4)

        self.overview_btn = ctk.CTkButton(
            self.hand_bottom_frame, text="概览", width=60, height=26, corner_radius=6,
            font=bold_font,
            fg_color=PALETTE["primary"], text_color=("#FFFFFF", "#0B0F19"), hover_color=PALETTE["primary_hover"],
            command=self.on_overview_click
        )
        self.overview_btn.pack(side=tk.RIGHT, padx=(8, 6), pady=4)

        self.hand_bottom_id = self.canvas.create_window(
            0, 0, window=self.hand_bottom_frame, anchor="center"
        )

        self.canvas.bind("<Configure>", self._redraw_grid)

    def _draw_stat_zone(
        self, 
        zone_name: str, 
        cx: float, 
        cy: float, 
        w: float, 
        h: float, 
        border_col: str = None
    ):
        """绘制统计卡槽（0 张牌时呈现 75% 不透明度虚线占位效果）"""
        mode_idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        card_bg_color = PALETTE["secondary"][mode_idx]
        card_border_color = PALETTE["card_border"][mode_idx]
        text_color = PALETTE["text_main"][mode_idx]
        text_sub_color = PALETTE["text_sub"][mode_idx]
        hover_bg_color = PALETTE["secondary_hover"][mode_idx]
        accent_color = PALETTE["primary"][mode_idx]

        # 获取当前区域统计数据
        stats = self.zone_stats.get(zone_name, {"cx": 0, "chara": 0, "total": 0, "soul1": 0, "soul2": 0})
        cx_num = stats.get("cx", 0)
        chara_num = stats.get("chara", 0)
        soul1_num = stats.get("soul1", 0)
        soul2_num = stats.get("soul2", 0)
        total_num = stats.get("total", 0)

        # 1. 判断是否为空槽位 (0 张牌时呈现 75% 不透明度与虚线效果)
        if total_num == 0:
            fill_bg = PALETTE["panel_bg"][mode_idx]  # 🌟 替换硬编码颜色
            b_dash = (6, 3)
            b_width = 1.0
            act_color = text_sub_color
        else:
            fill_bg = card_bg_color
            b_dash = None
            b_width = 1.2
            act_color = accent_color

        b_col = border_col if border_col else card_border_color

        rect_kwargs = {
            "fill": fill_bg,
            "outline": b_col,
            "width": b_width,
            "tags": ("zone_elem", f"zone_{zone_name}")
        }
        if b_dash:
            rect_kwargs["dash"] = b_dash

        rect_id = self.canvas.create_rectangle(
            cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
            **rect_kwargs
        )

        font_top = FONT_GLOBAL_BOLD
        font_mid = FONT_GLOBAL_BOLD
        font_bot = FONT_GLOBAL

        display_name = f"{zone_name}区" if zone_name in ("库存", "思出") else zone_name

        if zone_name in ("库存", "思出"):
            y_top_line1 = cy - h * 0.28
            y_mid       = cy
            y_bot       = cy + h * 0.28

            self.canvas.create_text(
                cx, y_top_line1,
                text=f"{cx_num}潮{chara_num}肉，{soul1_num}魂{soul2_num}爆",
                fill=act_color,
                font=font_top,
                justify="center",
                tags=("zone_elem", f"zone_{zone_name}")
            )

        elif zone_name in ("卡组", "控制室"):
            y_top_line1 = cy - h * 0.30
            y_top_line2 = cy - h * 0.16
            y_mid       = cy + h * 0.01
            y_bot       = cy + h * 0.30

            self.canvas.create_text(
                cx, y_top_line1,
                text=f"{cx_num}潮{chara_num}肉",
                fill=act_color,
                font=font_top,
                justify="center",
                tags=("zone_elem", f"zone_{zone_name}")
            )

            self.canvas.create_text(
                cx, y_top_line2,
                text=f"{soul1_num}魂{soul2_num}爆",
                fill=act_color,
                font=font_top,
                justify="center",
                tags=("zone_elem", f"zone_{zone_name}")
            )

        self.canvas.create_text(
            cx, y_mid,
            text=display_name,
            fill=text_color if total_num > 0 else text_sub_color,
            font=font_mid,
            justify="center",
            tags=("zone_elem", f"zone_{zone_name}")
        )

        self.canvas.create_text(
            cx, y_bot,
            text=f"共{total_num}张",
            fill=text_sub_color,
            font=font_bot,
            justify="center",
            tags=("zone_elem", f"zone_{zone_name}")
        )

        tag_name = f"zone_{zone_name}"
        self.canvas.tag_bind(tag_name, "<Button-1>", lambda e=None, zn=zone_name: self.on_zone_click(zn))
        self.canvas.tag_bind(tag_name, "<Enter>", lambda e=None, r=rect_id: self.canvas.itemconfig(r, fill=hover_bg_color))
        self.canvas.tag_bind(tag_name, "<Leave>", lambda e=None, r=rect_id: self.canvas.itemconfig(r, fill=fill_bg))

    def _draw_single_card_zone(
        self,
        zone_name: str,
        display_label: str,
        cx: float,
        cy: float,
        w: float,
        h: float,
        border_col: str = None
    ):
        """绘制单张卡牌槽位（支持 10字居中自动换行、字体加大、无牌半透明/虚线区分）"""
        card = self.single_zone_cards.get(zone_name)
        
        mode_idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        card_bg_color = PALETTE["secondary"][mode_idx]
        card_border_color = PALETTE["card_border"][mode_idx]
        text_color = PALETTE["text_main"][mode_idx]
        text_sub_color = PALETTE["text_sub"][mode_idx]
        hover_bg_color = PALETTE["secondary_hover"][mode_idx]
        accent_color = PALETTE["primary"][mode_idx]

        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2

        # 🌟 描边颜色：优先使用传入的颜色 (如红/绿)，无传入时使用主题灰色
        b_col = border_col if border_col else card_border_color

        # -------------------------------------------------------------
        # 改进 3：75% 不透明度空槽位占位效果 (有牌时为 100% 实体卡片)
        # -------------------------------------------------------------
        if not card:
            empty_bg = PALETTE["panel_bg"][mode_idx]  # 🌟 替换硬编码颜色
            empty_text_color = PALETTE["text_sub"][mode_idx]

            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=empty_bg,
                outline=b_col,  # 🌟 空槽虚线框使用自定义描边色 (红/绿/灰)
                width=1.2,
                dash=(6, 3),
                tags=("zone_elem", f"zone_{zone_name}")
            )
            self.canvas.create_text(
                cx, cy,
                text=display_label,
                fill=empty_text_color,
                font=FONT_GLOBAL,
                justify="center",
                tags=("zone_elem", f"zone_{zone_name}")
            )
        else:
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=card_bg_color,
                outline=b_col,  # 🌟 实体卡片实线框使用自定义描边色 (红/绿/灰)
                width=1.5,
                tags=("zone_elem", f"zone_{zone_name}")
            )

            pad_x = max(3, int(w * 0.05))
            pad_y = max(3, int(h * 0.04))
            font_corner = FONT_GLOBAL
            font_center = FONT_GLOBAL_BOLD

            # [1/5] 左上角：X级 / Y费 (两行)
            lvl = get_card_level(card)
            cost = card.get("cost", 0)
            self.canvas.create_text(
                x1 + pad_x, y1 + pad_y,
                text=f"{lvl}级\n{cost}费",
                fill=text_color,
                font=font_corner,
                anchor="nw",
                justify="left",
                tags=("zone_elem", f"zone_{zone_name}")
            )

            # [2/5] 右上角：描述触发标记与触发魂点数
            trig_symbol = card.get("trigger", "无")
            if not trig_symbol or str(trig_symbol).lower() == "none":
                trig_symbol = "无"
            trig_soul = get_card_trigger_soul(card)

            soul_str = "魂" if trig_soul == 1 else ("爆" if trig_soul == 2 else "")
            symbol_str = "" if trig_symbol == "无" else str(trig_symbol)

            if trig_symbol == "无" and trig_soul == 0:
                trig_text = "无"
            else:
                trig_text = f"{symbol_str}{soul_str}"

            self.canvas.create_text(
                x2 - pad_x, y1 + pad_y,
                text=trig_text,
                fill=accent_color if trig_text != "无" else text_sub_color,
                font=font_corner,
                anchor="ne",
                justify="right",
                tags=("zone_elem", f"zone_{zone_name}")
            )

            # [3/5] 左下角：力量值
            pwr = card.get("power", 500)
            self.canvas.create_text(
                x1 + pad_x, y2 - pad_y,
                text=str(pwr),
                fill=text_color,
                font=font_corner,
                anchor="sw",
                justify="left",
                tags=("zone_elem", f"zone_{zone_name}")
            )

            # [4/5] 卡名移至正中央，字数上限 10，每行最多 5 个字自动换行
            raw_name = str(card.get("name") or card.get("kind") or "角色")
            name_10 = raw_name[:10]
            if len(name_10) > 5:
                formatted_name = f"{name_10[:5]}\n{name_10[5:]}"
            else:
                formatted_name = name_10

            self.canvas.create_text(
                cx, cy,
                text=formatted_name,
                fill=text_color,
                font=font_center,
                anchor="center",
                justify="center",
                tags=("zone_elem", f"zone_{zone_name}")
            )

            # [5/5] 右下角：X魂 (X为基础魂点数)
            base_soul = get_card_base_soul(card)
            self.canvas.create_text(
                x2 - pad_x, y2 - pad_y,
                text=f"{base_soul}魂",
                fill=accent_color,
                font=font_corner,
                anchor="se",
                justify="right",
                tags=("zone_elem", f"zone_{zone_name}")
            )

        # 绑定点击与 Hover 事件
        tag_name = f"zone_{zone_name}"
        self.canvas.tag_bind(tag_name, "<Button-1>", lambda e=None, zn=zone_name: self.on_zone_click(zn))
        self.canvas.tag_bind(tag_name, "<Enter>", lambda e=None, r=rect_id: self.canvas.itemconfig(r, fill=hover_bg_color))
        self.canvas.tag_bind(tag_name, "<Leave>", lambda e=None, r=rect_id, bg=(card_bg_color if card else empty_bg): self.canvas.itemconfig(r, fill=bg))

    def _redraw_grid(self, event=None):
        cw = event.width if event else self.canvas.winfo_width()
        if cw < 50:
            return

        # 动态清理旧的矢量槽位图形
        self.canvas.delete("zone_elem")

        mode_idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        card_bg_color = PALETTE["secondary"][mode_idx]
        card_border_color = PALETTE["card_border"][mode_idx]
        danger_color = PALETTE["danger"][mode_idx]    # 🌟 敌方前列红色描边
        success_color = PALETTE["success"][mode_idx]  # 🌟 我方前/后列绿色描边
        text_color = PALETTE["text_main"][mode_idx]

        padding_x = 12
        gap_x = max(2, int(cw * 0.006))
        gap_y = max(2, int(cw * 0.006))

        # -----------------------------------------------------------------
        # 1. 动态卡牌尺寸计算与 Margins 调整
        # -----------------------------------------------------------------
        card_v_w = max(20, int((cw - 2 * padding_x - 6 * gap_x) / 7.42))
        card_v_h = int(card_v_w * (88.0 / 63.0))

        card_h_w = card_v_h
        card_h_h = card_v_w

        # 顶部边距适配敌方顶部 Frame
        top_margin = card_v_h + 2 * gap_y + 60

        # -----------------------------------------------------------------
        # 2. X 轴定位计算
        # -----------------------------------------------------------------
        x_level_center = padding_x + card_h_w / 2
        x_level_right = padding_x + card_h_w

        x_clock1 = x_level_right + gap_x + card_v_w / 2
        x_clock2 = x_clock1 + card_v_w + gap_x
        x_clock3 = x_clock2 + card_v_w + gap_x
        x_clock4 = x_clock3 + card_v_w + gap_x
        x_clock5 = x_clock4 + card_v_w + gap_x
        x_clock6 = x_clock5 + card_v_w + gap_x

        x_stock_col_center = x_level_right + gap_x + card_h_w / 2
        x_stock = x_stock_col_center
        x_cx    = x_stock_col_center
        x_mem   = x_stock_col_center
        x_stock_col_right = x_level_right + gap_x + card_h_w

        x_front1 = x_stock_col_right + gap_x + card_v_w / 2
        x_front3 = x_clock5
        x_deck   = x_clock6

        x_front2 = (x_front1 + x_front3) / 2.0
        x_back1 = (x_front1 + x_front2) / 2.0
        x_back2 = (x_front2 + x_front3) / 2.0
        x_control = x_deck

        x_right_max = x_deck + card_v_w / 2
        x_stage_center = (padding_x + x_right_max) / 2.0

        # -----------------------------------------------------------------
        # 3. Y 轴定位与 gap_y 精确空隙计算
        # -----------------------------------------------------------------
        y_lvl4 = top_margin + card_h_h / 2
        y_lvl3 = y_lvl4 + card_h_h + gap_y
        y_lvl2 = y_lvl3 + card_h_h + gap_y
        y_lvl1 = y_lvl2 + card_h_h + gap_y

        y_stock = y_lvl4
        y_cx    = y_lvl3
        y_mem   = y_lvl2

        y_front = (y_lvl4 - card_h_h / 2) + card_v_h / 2
        y_back = y_front + card_v_h / 2 + gap_y + card_v_h / 2
        y_clock = (y_lvl1 - card_h_h / 2) + card_v_h / 2

        # 🌟 我方前列顶端
        y_top_front = y_front - card_v_h / 2

        # 🌟 分界线：离我方前列顶端正好有 gap_y 空隙
        y_divider1 = y_top_front - gap_y

        # 🌟 敌方前列：底端离分界线正好有 gap_y 空隙
        y_enemy = y_divider1 - gap_y - card_v_h / 2

        y_bottom_baseline = max(y_clock + card_v_h / 2, y_back + card_v_h / 2)
        y_hand = y_bottom_baseline + 28
        total_height = y_hand + 28

        self.canvas.configure(height=int(total_height))

        # -----------------------------------------------------------------
        # 4. 绘制红线与敌我顶部/底部标识栏定位
        # -----------------------------------------------------------------
        self.canvas.coords("divider_red", padding_x, y_divider1, x_right_max, y_divider1)

        # 🌟 敌方顶部标识栏定位 (与敌方前列上边缘拉开距离并居中)
        y_enemy_top = max(20, int((y_enemy - card_v_h / 2) / 2.0))
        self.canvas.coords(self.enemy_top_id, x_stage_center, y_enemy_top)

        # -----------------------------------------------------------------
        # 5. 敌方前列 1~3 (红色描边)
        # -----------------------------------------------------------------
        self._draw_single_card_zone("敌前列1", "敌前列 1", x_front1, y_enemy, card_v_w, card_v_h, border_col=danger_color)
        self._draw_single_card_zone("敌前列2", "敌前列 2", x_front2, y_enemy, card_v_w, card_v_h, border_col=danger_color)
        self._draw_single_card_zone("敌前列3", "敌前列 3", x_front3, y_enemy, card_v_w, card_v_h, border_col=danger_color)

        # -----------------------------------------------------------------
        # 7. 最左侧 Level 列 (默认灰色描边)
        # -----------------------------------------------------------------
        self._draw_single_card_zone("等级4", "等级 4", x_level_center, y_lvl4, card_h_w, card_h_h)
        self._draw_single_card_zone("等级3", "等级 3", x_level_center, y_lvl3, card_h_w, card_h_h)
        self._draw_single_card_zone("等级2", "等级 2", x_level_center, y_lvl2, card_h_w, card_h_h)
        self._draw_single_card_zone("等级1", "等级 1", x_level_center, y_lvl1, card_h_w, card_h_h)

        # -----------------------------------------------------------------
        # 8. 库存/高潮/思出列 (默认灰色描边)
        # -----------------------------------------------------------------
        self._draw_stat_zone("库存", x_stock, y_stock, card_h_w, card_h_h)
        self._draw_single_card_zone("CX", "高潮区", x_cx, y_cx, card_h_w, card_h_h)
        self._draw_stat_zone("思出", x_mem, y_mem, card_h_w, card_h_h)

        # -----------------------------------------------------------------
        # 9. 我方前列 1, 2, 3 (绿色描边) 与卡组 (默认灰色描边)
        # -----------------------------------------------------------------
        self._draw_single_card_zone("前列1", "前列 1", x_front1, y_front, card_v_w, card_v_h, border_col=success_color)
        self._draw_single_card_zone("前列2", "前列 2", x_front2, y_front, card_v_w, card_v_h, border_col=success_color)
        self._draw_single_card_zone("前列3", "前列 3", x_front3, y_front, card_v_w, card_v_h, border_col=success_color)
        self._draw_stat_zone("卡组", x_deck, y_front, card_v_w, card_v_h)

        # -----------------------------------------------------------------
        # 10. 我方后列 1, 2 (绿色描边) 与控制室 (默认灰色描边)
        # -----------------------------------------------------------------
        self._draw_single_card_zone("后列1", "后列 1", x_back1, y_back, card_v_w, card_v_h, border_col=success_color)
        self._draw_single_card_zone("后列2", "后列 2", x_back2, y_back, card_v_w, card_v_h, border_col=success_color)
        self._draw_stat_zone("控制室", x_control, y_back, card_v_w, card_v_h)

        # -----------------------------------------------------------------
        # 11. 计时区 1~6 (默认灰色描边)
        # -----------------------------------------------------------------
        for i in range(1, 7):
            zn = f"计时{i}"
            xc = eval(f"x_clock{i}")
            self._draw_single_card_zone(zn, f"计时 {i}", xc, y_clock, card_v_w, card_v_h)

        # -----------------------------------------------------------------
        # 12. 渲染顶部与底部控制栏尺寸配置
        # -----------------------------------------------------------------
        try:
            scale = ctk.get_widget_scaling(self)
        except Exception:
            scale = 1.0

        bottom_w = min(220, max(180, int((x_right_max - padding_x) * 0.5)))
        scaled_bottom_w = int(bottom_w / scale)

        # 同步敌方顶部与我方底部的面板宽度与高度
        self.enemy_top_frame.configure(width=scaled_bottom_w, height=34)

        self.canvas.coords(self.hand_bottom_id, x_stage_center, y_hand)
        self.hand_bottom_frame.configure(width=scaled_bottom_w, height=34)