# -*- coding: utf-8 -*-
"""FuyutsuiTools 覆盖：圣骑士逻辑（驱散开关支持）"""
import importlib
from utils import get_hotkey

_orig_mod = importlib.import_module("class.paladin_logic")
_orig_run = _orig_mod.run_paladin_logic

# 特殊技能按键（不走keymap，直接按指定键）
direct_key_map = {
    "制裁之锤": "x",
}

# 替换原始模块的 get_hotkey，使制裁之锤走固定按键
_orig_get_hotkey = _orig_mod.get_hotkey

def _patched_get_hotkey(unit, skill_name):
    if skill_name in direct_key_map:
        return direct_key_map[skill_name]
    return _orig_get_hotkey(unit, skill_name)

_orig_mod.get_hotkey = _patched_get_hotkey


def run_paladin_logic(state_dict, spec_name):
    """覆盖：驱散开关关闭时，抑制自动驱散（保留目标驱散）"""
    驱散开关 = state_dict.get("驱散开关", 1)
    removed_dispel = {}

    # 驱散开关关闭时，临时移除 group 中的驱散字段，使原始逻辑跳过队友驱散
    if 驱散开关 == 0:
        group = state_dict.get("group") or {}
        for key, data in group.items():
            if isinstance(data, dict) and "驱散" in data:
                removed_dispel[key] = data["驱散"]
                del data["驱散"]

    action_hotkey, current_step, unit_info = _orig_run(state_dict, spec_name)

    # 恢复被移除的驱散字段
    if removed_dispel:
        group = state_dict.get("group") or {}
        for key, val in removed_dispel.items():
            if isinstance(group.get(key), dict):
                group[key]["驱散"] = val

    return action_hotkey, current_step, unit_info



