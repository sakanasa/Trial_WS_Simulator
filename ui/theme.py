# ui/theme.py

# =====================================================================
# Geek Indigo 配色與字體全局規範 (GitHub 碳灰高對比度無障礙版)
# =====================================================================

# GitHub 配色體系 (元組格式: Light_Color, Dark_Color)
PALETTE = {
    "bg_main":         ("#E2E8F0", "#0D1117"),
    "panel_bg":        ("#F1F5F9", "#111827"),
    "card_bg":         ("#F8FAFC", "#161B22"),
    "card_border":     ("#CBD5E1", "#30363D"),  # 🌟 容器卡片 1px 描邊
    "input_border":    ("#94A3B8", "#64748B"),  # 🌟 輸入/下拉框 1.5px 高對比度描邊 (#64748B 在暗色下極其清晰)
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

# 全局字體規範 (五號字：鎖定絕對像素 -14px，徹底免疫 Windows 縮放干擾)
FONT_GLOBAL = ("微軟雅黑", -14)
FONT_GLOBAL_BOLD = ("微軟雅黑", -14, "bold")