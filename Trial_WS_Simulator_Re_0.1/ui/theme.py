# ui/theme.py

# =====================================================================
# Geek Indigo 配色与字体全局规范 (GitHub 碳灰高对比度无障碍版)
# =====================================================================

# GitHub 配色体系 (元组格式: Light_Color, Dark_Color)
PALETTE = {
    "bg_main":         ("#E2E8F0", "#0D1117"),
    "panel_bg":        ("#F1F5F9", "#111827"),
    "card_bg":         ("#F8FAFC", "#161B22"),
    "card_border":     ("#CBD5E1", "#30363D"),  # 🌟 容器卡片 1px 描边
    "input_border":    ("#94A3B8", "#64748B"),  # 🌟 输入/下拉框 1.5px 高对比度描边 (#64748B 在暗色下极其清晰)
    "primary":         ("#2563EB", "#60A5FA"),
    "primary_hover":   ("#1D4ED8", "#3B82F6"),
    "secondary":       ("#E2E8F0", "#21262D"),
    "secondary_hover": ("#CBD5E1", "#30363D"),
    "text_main":       ("#0F172A", "#C9D1D9"),
    "text_sub":        ("#475569", "#8B949E"),
    "optimal":         ("#2563EB", "#60A5FA"),
    "success":         ("#059669", "#34D399"),
    "danger":          ("#DC2626", "#F87171"),
}

# 全局字体规范 (五号字：锁定绝对像素 -14px，彻底免疫 Windows 缩放干扰)
FONT_GLOBAL = ("微软雅黑", -14)
FONT_GLOBAL_BOLD = ("微软雅黑", -14, "bold")