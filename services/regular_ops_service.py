# -*- coding: utf-8 -*-
"""
常規操作列表存檔持久化服務 (Regular Ops Preset Service)
負責本地 regular_ops_presets.json 文件的讀取、保存與具名存檔管理。
"""

from services.preset_store import PresetStore

# 全局單例服務實例
regular_ops_service = PresetStore("regular_ops_presets.json")
