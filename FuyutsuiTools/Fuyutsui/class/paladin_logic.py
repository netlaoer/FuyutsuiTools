# -*- coding: utf-8 -*-
"""FuyutsuiTools 覆盖：圣骑士逻辑（添加驱散开关支持 + 扩展功能）"""
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
    """覆盖：驱散开关关闭时，神圣天赋用目标类型判断直接目标驱散"""
    action_hotkey, current_step, unit_info = _orig_run(state_dict, spec_name)

    if spec_name == "神圣" and state_dict.get("驱散开关", 1) == 0:
        # 抑制原始的驱散单位自动驱散（只允许目标类型驱散）
        if current_step and "清毒术" in current_step and "目标" not in current_step:
            action_hotkey = None
            current_step = "无匹配技能"
        # 驱散当前目标
        spells = state_dict.get("spells") or {}
        清洁术CD = spells.get("清洁术", -1)
        目标类型 = state_dict.get("目标类型", 0)
        if 清洁术CD == 0 and 目标类型 in (12, 13, 15):
            current_step = "施放 清毒术 on 目标"
            action_hotkey = get_hotkey(0, "清毒术")

    return action_hotkey, current_step, unit_info

