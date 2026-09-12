# -*- coding: utf-8 -*-
"""
矩陣批量統計結果存檔持久化服務 (Batch Matrix Preset Service)
負責本地 batch_matrix_presets.json 文件的讀取、保存與具名存檔管理。
每筆存檔內容：{"var1", "var2", "range1", "range2", "winrate_matrix", "avg_dmg_matrix"}
"""

from services.preset_store import PresetStore

# 全局單例服務實例
batch_matrix_service = PresetStore("batch_matrix_presets.json")
