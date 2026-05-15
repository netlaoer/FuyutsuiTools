# -*- coding: utf-8 -*-
"""
通用 GUI：根据职业/专精自动适配显示。
使用 CustomTkinter，背景半透明，文字保持清晰。
"""
import threading
import time
import ctypes
import sys
import os
import shutil
import math
import json
from pathlib import Path
import customtkinter as ctk
import tkinter as tk

import importlib

# 检测是否是PyInstaller打包的exe运行时
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # 获取exe文件所在目录
    exe_dir = Path(sys.executable).parent
    # 将exe所在目录添加到sys.path，以便能够导入class目录下的模块
    if str(exe_dir) not in sys.path:
        sys.path.insert(0, str(exe_dir))

from utils import *
from GetPixels import get_info, scan_screen_data

# ── FuyutsuiTools 覆盖 ──
_override_base = Path(__file__).parent.parent.parent / "FuyutsuiTools" / "Fuyutsui"
if (_override_base / "overrides.py").is_file():
    sys.path.insert(0, str(_override_base))
    from overrides import import_with_override, apply_overrides, clear_merged_cache, print_loaded_info
    apply_overrides()
    # 更新局部 load_config 引用（from utils import * 创建的是模块级绑定）
    import utils
    load_config = utils.load_config
    _clear_merged_cache = clear_merged_cache
    _print_loaded_info = print_loaded_info
    del sys.path[0]

# ── 职业模块：从 config.yml 自动构建映射 + class/ 目录扫描补充 ──
_logic_modules = {}
_module_names = []
_CLASS_ID_TO_MODULE = {}
_class_dir = Path(__file__).parent / "class"


def _import_with_override(module_name: str):
    """优先从 FuyutsuiTools/class/ 加载同名模块（覆盖），找不到则回退到内置 class/"""
    try:
        return import_with_override(module_name)
    except Exception:
        return importlib.import_module(f"class.{module_name}")


def _build_class_module_map():
    """从 config.yml 的顶层 key(职业ID)+keymap 字段推导模块名，再扫描 class/ 补充"""
    global _CLASS_ID_TO_MODULE
    _CLASS_ID_TO_MODULE = {}
    # 1. 从 config.yml 读取：顶层 key=职业ID, keymap="warrior.yml" → "warrior_logic"
    try:
        config = load_config()
        for cid_str, cid_val in config.items():
            if not str(cid_str).isdigit():
                continue
            cid = int(cid_str)
            km = cid_val.get("keymap") if isinstance(cid_val, dict) else None
            if isinstance(km, str) and km.endswith(".yml"):
                mod_name = km[:-4] + "_logic"  # "warrior.yml" → "warrior_logic"
                if mod_name not in _CLASS_ID_TO_MODULE.values():
                    _CLASS_ID_TO_MODULE[cid] = mod_name
    except Exception:
        pass

    # 2. config.yml 中未配置 keymap 的职业，通过 class/ 目录扫描补充
    #    文件名去掉 "_logic" 后缀即为 keymap 名，反查 config 顶层 key 找不到的
    #    对已知职业 ID 做兜底映射（仅用于 config 中未配置的情况）
    _FALLBACK_ID = {
        "hunter_logic": 3, "rogue_logic": 4, "evoker_logic": 13,
    }
    for _f in sorted(_class_dir.glob("*_logic.py")):
        mod_name = _f.stem
        if mod_name in _CLASS_ID_TO_MODULE.values():
            continue
        if mod_name in _FALLBACK_ID:
            _CLASS_ID_TO_MODULE[_FALLBACK_ID[mod_name]] = mod_name


_build_class_module_map()

# 加载所有模块
for _name in _CLASS_ID_TO_MODULE.values():
    try:
        _logic_modules[_name] = _import_with_override(_name)
        _module_names.append(_name)
    except Exception:
        _logic_modules[_name] = None

# 扫描 class/ 目录，加载 config.yml 中未映射的模块
for _f in sorted(_class_dir.glob("*_logic.py")):
    _mod_name = _f.stem
    if _mod_name not in _logic_modules:
        try:
            _logic_modules[_mod_name] = _import_with_override(_mod_name)
            _module_names.append(_mod_name)
        except Exception:
            pass


def _load_logic_module(module_name: str):
    """从 _logic_modules 缓存中获取逻辑函数"""
    module = _logic_modules.get(module_name)
    if module is None:
        return None
    return getattr(module, f"run_{module_name.replace('_logic', '')}_logic")


def reload_logic_modules():
    """重新加载所有职业逻辑模块（重新构建映射 + reload）"""
    global LOGIC_FUNCS_BY_CLASS
    try:
        # 重新构建映射
        _build_class_module_map()

        # 重新导入所有已知模块（覆盖模块通过 _import_with_override 重新加载）
        for name in list(_logic_modules.keys()):
            try:
                _logic_modules[name] = _import_with_override(name)
            except Exception:
                _logic_modules[name] = None

        # 扫描并加载新模块
        for _f in sorted(_class_dir.glob("*_logic.py")):
            _mod_name = _f.stem
            if _mod_name not in _logic_modules:
                try:
                    _logic_modules[_mod_name] = _import_with_override(_mod_name)
                    _module_names.append(_mod_name)
                except Exception:
                    pass

        LOGIC_FUNCS_BY_CLASS = {cid: _load_logic_module(name) for cid, name in _CLASS_ID_TO_MODULE.items()}
        return True
    except Exception as e:
        print(f"重新加载模块失败: {e}")
        return False


TOGGLE_INTERVAL = 0.05
LOGIC_INTERVAL = 0.2
GUI_UPDATE_MS = 100

LOGIC_FUNCS_BY_CLASS = {cid: _load_logic_module(name) for cid, name in _CLASS_ID_TO_MODULE.items()}

def _default_logic(state_dict, spec_name):
    return None, "无逻辑定义", {}


_toggle_key_str = "XBUTTON1"
_toggle_vk = get_vk(_toggle_key_str)

# 发送按键模式：switch=开关(持续) / click=单击(一次) / hold=按住(按住持续)
_send_mode = "switch"

_state_lock = threading.Lock()
_logic_enabled = False
_click_pending = False
_state_dict = {}
_class_name = None
_class_id = None
_spec_name = None
_spec_id = None
_current_step = ""  # 当前行为，每次逻辑循环都会更新
_unit_info = {}  # 单位信息，供 GUI 显示
_scan_ms = 0.0   # 上一次 get_info() 的扫描耗时（毫秒）

_CONFIG_CACHE = None
_DEFAULT_STATUS_KEYS = ["生命值", "能量值", "有效性", "战斗", "移动", "施法", "引导"]


def _get_config_cached():
    """config.yml 缓存：避免 GUI 每帧都重复解析 YAML。"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = load_config()
    return _CONFIG_CACHE


def _get_class_spec_cfg(class_id, spec_id):
    """获取 config.yml 里指定 (class_id, spec_id) 的 spec 配置块。"""
    if class_id is None or spec_id is None:
        return {}
    config = _get_config_cached()
    class_dict = config.get(class_id) or config.get(str(class_id)) or {}
    if not isinstance(class_dict, dict):
        return {}
    return class_dict.get(spec_id) or class_dict.get(str(spec_id)) or {}


def get_group_config_for_class_spec(class_id, spec_id):
    """根据 config.yml 生成队伍字段表格配置 (num_units, fields)。"""
    spec_cfg = _get_class_spec_cfg(class_id, spec_id)
    group_cfg = spec_cfg.get("group") if isinstance(spec_cfg, dict) else None
    if not isinstance(group_cfg, dict):
        return (0, [])
    try:
        num_units = int(group_cfg.get("num", 0))
    except (TypeError, ValueError):
        num_units = 0
    fields = [k for k in group_cfg.keys() if k not in ("start", "num")]
    return (num_units, fields)


def get_class_spec_view_data(class_id, spec_id):
    """
    聚合生成 GUI 所需数据，避免同一 spec_cfg 被重复解析三次：
    返回 (status_keys, (num_units, fields), spells_list)
    """
    spec_cfg = _get_class_spec_cfg(class_id, spec_id)
    if not isinstance(spec_cfg, dict) or not spec_cfg:
        return list(_DEFAULT_STATUS_KEYS), (0, []), []

    extra_keys = [k for k in spec_cfg.keys() if k not in ("spells", "group", "keymap")]
    status_keys = list(_DEFAULT_STATUS_KEYS) + [k for k in extra_keys if k not in _DEFAULT_STATUS_KEYS]

    spells_cfg = spec_cfg.get("spells")
    spells_list = list(spells_cfg.keys()) if isinstance(spells_cfg, dict) else []

    group_cfg = spec_cfg.get("group")
    if not isinstance(group_cfg, dict):
        group_num = 0
        fields = []
    else:
        try:
            group_num = int(group_cfg.get("num", 0))
        except (TypeError, ValueError):
            group_num = 0
        fields = [k for k in group_cfg.keys() if k not in ("start", "num")]

    return status_keys, (group_num, fields), spells_list


def _key_detect_loop():
    """独立高频按键检测线程：50ms 轮询，不受逻辑执行耗时影响"""
    global _logic_enabled, _click_pending, _current_step
    prev_pressed = False
    prev_vk = _toggle_vk
    prev_pressed_x1 = False
    prev_pressed_x2 = False
    VK_XBUTTON1 = get_vk("XBUTTON1")
    VK_XBUTTON2 = get_vk("XBUTTON2")
    _hold_release_count = 0
    _HOLD_RELEASE_GRACE = 3
    KEY_POLL = 0.05  # 50ms 按键轮询

    while True:
        try:
            vk_now = _toggle_vk
            if vk_now is None:
                time.sleep(KEY_POLL)
                continue

            if vk_now != prev_vk:
                prev_pressed = False
                prev_vk = vk_now

            # 高 bit: 当前物理状态 / 低 bit: 自上次调用后是否被按下过
            raw = ctypes.windll.user32.GetAsyncKeyState(vk_now)
            current_pressed = (raw & 0x8000) != 0
            rising = (raw & 0x1) != 0 or (current_pressed and not prev_pressed)

            raw_x1 = ctypes.windll.user32.GetAsyncKeyState(VK_XBUTTON1)
            raw_x2 = ctypes.windll.user32.GetAsyncKeyState(VK_XBUTTON2)
            current_x1 = (raw_x1 & 0x8000) != 0
            current_x2 = (raw_x2 & 0x8000) != 0
            rising_x1 = (raw_x1 & 0x1) != 0 or (current_x1 and not prev_pressed_x1)
            rising_x2 = (raw_x2 & 0x1) != 0 or (current_x2 and not prev_pressed_x2)

            use_custom_bind = (_toggle_key_str != "XBUTTON1" and _toggle_vk is not None)
            mode = _send_mode

            if mode == "switch":
                if use_custom_bind:
                    if rising:
                        with _state_lock:
                            _logic_enabled = not _logic_enabled
                            _click_pending = False
                        _current_step = "逻辑 " + ("开启" if _logic_enabled else "关闭")
                else:
                    if rising_x1:
                        with _state_lock:
                            _logic_enabled = True
                            _click_pending = False
                        _current_step = "逻辑 开启"
                    elif rising_x2:
                        with _state_lock:
                            _logic_enabled = False
                            _click_pending = False
                        _current_step = "逻辑 关闭"
            elif mode == "click":
                if rising:
                    with _state_lock:
                        _logic_enabled = True
                        _click_pending = True
                    _current_step = "单击触发"
            elif mode == "hold":
                if current_pressed:
                    _hold_release_count = 0
                    with _state_lock:
                        _logic_enabled = True
                        _click_pending = False
                else:
                    _hold_release_count += 1
                    if _hold_release_count >= _HOLD_RELEASE_GRACE:
                        with _state_lock:
                            was_enabled = _logic_enabled
                            _logic_enabled = False
                            _click_pending = False
                        if was_enabled:
                            _current_step = "按住结束"
            else:
                if rising:
                    with _state_lock:
                        _logic_enabled = not _logic_enabled
                        _click_pending = False
                    _current_step = "逻辑 " + ("开启" if _logic_enabled else "关闭")

            prev_pressed = current_pressed
            prev_pressed_x1 = current_x1
            prev_pressed_x2 = current_x2
        except Exception as e:
            print(f"[key_detect] error: {e}")
        time.sleep(KEY_POLL)





def _run_logic_loop():
    """逻辑执行循环：读取游戏状态并执行职业逻辑，开关由 _key_detect_loop 控制"""
    global _state_dict, _class_name, _class_id, _spec_name, _spec_id, _current_step, _unit_info, _logic_enabled, _click_pending, _scan_ms
    last_logic_time = 0.0

    while True:
        try:
            now = time.time()
            if now - last_logic_time >= LOGIC_INTERVAL:
                last_logic_time = now
                _t0 = time.perf_counter()
                state_dict = get_info()
                _scan_ms = (time.perf_counter() - _t0) * 1000
                class_name, spec_name = None, None
                class_id, spec_id = None, None
                if state_dict:
                    class_id = state_dict.get("职业")
                    spec_id = state_dict.get("专精")
                    config = load_config()
                    class_name, spec_name = get_class_and_spec_name(config, class_id, spec_id)
                    select_keymap_for_class(class_id)
                    try:
                        _print_loaded_info()
                        utils.load_keymap()
                    except Exception:
                        pass


                with _state_lock:
                    _state_dict = state_dict or {}
                    _class_name = class_name
                    _class_id = class_id
                    _spec_name = spec_name
                    _spec_id = spec_id

            if not _logic_enabled:
                time.sleep(TOGGLE_INTERVAL)
                continue

            sd = _state_dict
            if not sd or not sd.get("有效性"):
                _current_step = "等待游戏状态"
                time.sleep(TOGGLE_INTERVAL)
                continue

            spec_name = _spec_name
            class_id = _class_id
            action_hotkey = None
            _current_step = "无操作"

            logic_func = LOGIC_FUNCS_BY_CLASS.get(class_id, _default_logic)
            action_hotkey, _current_step, unit_info_update = logic_func(sd, spec_name)
            if unit_info_update:
                with _state_lock:
                    _unit_info = unit_info_update

            # 根据发送模式处理发送逻辑
            mode = _send_mode
            if mode == "click":
                with _state_lock:
                    pending = _click_pending
                if pending:
                    if action_hotkey:
                        send_key_to_wow(action_hotkey)
                    with _state_lock:
                        _logic_enabled = False
                        _click_pending = False
            else:
                if action_hotkey:
                    send_key_to_wow(action_hotkey)
        except Exception as e:
            print(f"[logic_loop] error: {e}")
        time.sleep(TOGGLE_INTERVAL)

# ═══════════════════════════════════════════
#  配色 / HUD 风格
# ═══════════════════════════════════════════
BG_DARK = "#0a0e17"        # 深邃暗色背景
BG_FRAME = "#111827"        # 面板背景
BG_BTN = "#0f172a"          # 按钮背景
FG_LIGHT = "#e2e8f0"        # 主文字
FG_DIM = "#b0bec5"          # 暗淡文字
FG_ACCENT = "#38bdf8"       # 蓝色强调
CYAN = "#00f0ff"            # 青色高亮
GREEN = "#00ff88"           # 霓虹绿
RED = "#ff3366"             # 霓虹红
BORDER_COLOR = "#1e3a5f"    # 面板边框色
BORDER_ACCENT = "#0ea5e9"   # 强调边框色
WINDOW_ALPHA = 0.85


def _hsv_to_rgb(h, s, v):
    """HSV→RGB (h∈[0,1], s∈[0,1], v∈[0,1]) → (r,g,b) ∈ [0,1]"""
    if s == 0.0:
        return v, v, v
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i %= 6
    if i == 0: return v, t, p
    if i == 1: return q, v, p
    if i == 2: return p, v, t
    if i == 3: return p, q, v
    if i == 4: return t, p, v
    return v, p, q


def _hex_to_rgb(hex_color):
    """'#RRGGBB' → (r, g, b) int tuple"""
    return int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)


def _rgb_to_hex(r, g, b):
    """(r, g, b) → '#RRGGBB'"""
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _mix_colors(c1, c2, t):
    """线性混合两个 hex 颜色，t∈[0,1]，0=全c1，1=全c2"""
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def _create_glow_panel(parent, corner_radius=8, accent=False):
    """创建带发光边框的面板"""
    border_color = BORDER_ACCENT if accent else BORDER_COLOR
    outer = ctk.CTkFrame(parent, fg_color=border_color, corner_radius=corner_radius)
    inner = ctk.CTkFrame(outer, fg_color=BG_FRAME, corner_radius=max(corner_radius - 1, 0))
    inner.pack(fill="both", expand=True, padx=1.5, pady=1.5)
    return outer, inner


# 职业名称颜色（霓虹增强版）
CLASS_NAME_COLORS = {
    "战士": "#C79C6E",
    "圣骑士": "#F58CBA",
    "猎人": "#ABD473",
    "盗贼": "#FFF569",
    "潜行者": "#FFF569",
    "牧师": "#FFFFFF",
    "萨满": "#00BFFF",
    "法师": "#69CCF0",
    "术士": "#B388FF",
    "武僧": "#00FF96",
    "德鲁伊": "#FF7D0A",
    "死亡骑士": "#FF4444",
    "恶魔猎手": "#C040FF",
    "唤魔师": "#33FFCC",
}

def _disable_ime_for_hwnd(hwnd: int):
    """
    尽量关闭指定窗口的 IME，避免窗口获取焦点后弹出输入法候选/输入窗口。
    Windows IME 相关接口有兼容性差异，所以做了多种 best-effort。
    """
    try:
        imm32 = ctypes.windll.imm32
        hIMC = imm32.ImmGetContext(hwnd)
        if hIMC:
            # 0=关闭 IME 打开状态
            imm32.ImmSetOpenStatus(hIMC, 0)
            imm32.ImmReleaseContext(hwnd, hIMC)
            return True
    except Exception:
        pass

    # 兜底：不同系统/签名可能导致 ImmDisableIME 行为不一致
    try:
        ctypes.windll.imm32.ImmDisableIME(0)
        return True
    except Exception:
        return False


def _load_window_state():
    """从 gui_window_state.json 读取窗口状态"""
    state_file = Path(__file__).parent / "gui_window_state.json"
    try:
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_window_state(data):
    """保存窗口状态到 gui_window_state.json（合并更新）"""
    state_file = Path(__file__).parent / "gui_window_state.json"
    try:
        existing = {}
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        existing.update(data)
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def create_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    try:
        hwnd = root.winfo_id()
        _disable_ime_for_hwnd(hwnd)
        root.after(200, lambda: _disable_ime_for_hwnd(root.winfo_id()))
    except Exception:
        pass
    root.title("神经链接控制台")
    root.geometry("365x350")
    # 窗口大小配置（正常 / 缩小）
    normal_geometry = "365x350"
    small_geometry = "365x160"
    # 从 JSON 恢复窗口位置
    _saved_state = _load_window_state()
    _saved_geo = _saved_state.get("geometry", "")
    if _saved_geo and "+" in _saved_geo:
        _pos_parts = _saved_geo.split("+")
        if len(_pos_parts) >= 3:
            root.geometry(f"{normal_geometry}+{_pos_parts[-2]}+{_pos_parts[-1]}")
    root.resizable(True, True)
    root.attributes("-topmost", True)
    root.configure(fg_color=BG_DARK)
    root.attributes("-alpha", 0.85)
    root.overrideredirect(True)  # 移除系统窗口边框

    # overrideredirect(True) 会导致窗口不在任务栏显示，需要手动修复
    try:
        _GWL_EXSTYLE = -20
        _WS_EX_APPWINDOW = 0x00040000
        _WS_EX_TOOLWINDOW = 0x00000080
        hwnd = int(root.frame(), 16)
        # 移除 WS_EX_TOOLWINDOW（overrideredirect 自动加的），添加 WS_EX_APPWINDOW
        style = ctypes.windll.user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        style = (style & ~_WS_EX_TOOLWINDOW) | _WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, style)
        # 刷新任务栏
        root.after(100  , lambda: (
            ctypes.windll.user32.ShowWindow(hwnd, 0),  # SW_HIDE
            ctypes.windll.user32.ShowWindow(hwnd, 1),  # SW_SHOW
        ))
    except Exception:
        pass

    # 设置任务栏图标（overrideredirect 下必须用 Win32 API，且需延迟+刷新）
    _icon_path = Path(__file__).parent / "other" / "icon.ico"
    if getattr(sys, 'frozen', False):
        # 打包模式：从 _MEIPASS 释放 icon.ico 到 exe 同目录的 other/
        _bundled_icon = Path(sys._MEIPASS) / "other" / "icon.ico"
        _exe_icon_dir = Path(sys.executable).parent / "other"
        _exe_icon_dir.mkdir(exist_ok=True)
        _exe_dir_icon = _exe_icon_dir / "icon.ico"
        if _bundled_icon.exists() and not _exe_dir_icon.exists():
            shutil.copy2(str(_bundled_icon), str(_exe_dir_icon))
        _icon_path = _exe_dir_icon

    def _apply_icon():
        if not root.winfo_exists() or not _icon_path.exists():
            return
        try:
            hwnd = int(root.frame(), 16)
            # LoadImageW: hinst=0 时必须用绝对路径
            h_icon = ctypes.windll.user32.LoadImageW(
                0, str(_icon_path.resolve()), 1, 0, 0, 0x00000050  # IMAGE_ICON=1, LR_LOADFROMFILE|LR_DEFAULTSIZE
            )
            if h_icon:
                # ICON_SMALL=0, ICON_BIG=1, WM_SETICON=0x0080
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, h_icon)
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, h_icon)
                # 刷新任务栏：先隐藏再显示，让 Windows 重新读取图标
                ctypes.windll.user32.ShowWindow(hwnd, 0)
                ctypes.windll.user32.ShowWindow(hwnd, 1)
        except Exception:
            pass

    root.after(200, _apply_icon)

    # 背景呼吸脉冲（标题栏 + root 间隙区域同步）
    _bg_base = (10, 14, 23)  # BG_DARK RGB
    def _pulse_bg():
        if not root.winfo_exists():
            return
        t = time.time()
        offset = int(3 * math.sin(t * 0.8))
        r, g, b = [max(0, min(255, c + offset)) for c in _bg_base]
        color = f"#{r:02x}{g:02x}{b:02x}"
        root.configure(fg_color=color)
        title_bar.configure(bg=color)
        root.after(60, _pulse_bg)
    root.after(300, _pulse_bg)

    # ════════════════════════════════════════
    #   动态美化：边框流光 + 文字呼吸 + 扫描线
    # ════════════════════════════════════════

    # --- 1. 面板边框流光动画 ---
    _glow_phase = [0.0]

    def _animate_panel_glow():
        """accent面板边框颜色沿色相环缓慢流动"""
        if not root.winfo_exists():
            return
        _glow_phase[0] = (_glow_phase[0] + 0.008) % 1.0
        # 在青蓝-蓝色-紫色之间循环
        hue = 0.55 + 0.12 * math.sin(_glow_phase[0] * 2 * math.pi)
        r, g, b = _hsv_to_rgb(hue, 0.7, 0.95)
        glow_color = _rgb_to_hex(r * 255, g * 255, b * 255)
        try:
            if top_outer.winfo_exists():
                top_outer.configure(fg_color=glow_color)
        except Exception:
            pass
        root.after(50, _animate_panel_glow)

    # --- 2. 标题栏文字闪烁光效 ---
    _title_shimmer = [0.0]

    def _animate_title_shimmer():
        """标题文字做微妙的高光扫过效果（通过调整color）"""
        if not root.winfo_exists() or not title_bar.winfo_exists():
            return
        _title_shimmer[0] += 0.03
        t = _title_shimmer[0]
        # 周期性亮度变化：大部分时间暗淡，偶尔闪亮
        brightness = 0.7 + 0.3 * max(0, math.sin(t * 1.5)) ** 4
        shimmer_color = _rgb_to_hex(int(0x00 * brightness), int(0xf0 * brightness), int(0xff * brightness))
        try:
            for item_id in title_bar.find_all():
                tags = title_bar.gettags(item_id)
                if "ctxt" not in tags and "minline" not in tags:
                    title_bar.itemconfigure(item_id, fill=shimmer_color)
                    break
        except Exception:
            pass
        root.after(80, _animate_title_shimmer)

    # --- 4. 状态区域边框微光 ---
    _status_glow_phase = [0.0]

    def _animate_status_border():
        """状态面板和冷却面板的边框做极微弱的透明度脉动"""
        if not root.winfo_exists():
            return
        _status_glow_phase[0] = (_status_glow_phase[0] + 0.01) % 1.0
        alpha = 0.4 + 0.25 * math.sin(_status_glow_phase[0] * math.pi * 2)
        mixed = _mix_colors(BORDER_COLOR, BORDER_ACCENT, alpha)
        try:
            if 'status_outer' in dir() and status_outer.winfo_exists():
                status_outer.configure(fg_color=mixed)
            if 'cooldown_outer' in dir() and cooldown_outer.winfo_exists():
                cooldown_outer.configure(fg_color=mixed)
        except Exception:
            pass
        root.after(70, _animate_status_border)

    # --- 5. 缩放按钮动态箭头 ---
    _resize_arrow_tick = [0.0]

    def _animate_resize_btn():
        """缩放按钮箭头做微弱的上下浮动提示"""
        if not root.winfo_exists() or resize_btn is None or not resize_btn.winfo_exists():
            return
        _resize_arrow_tick[0] += 0.08
        # 通过改变text_color亮度来模拟"呼吸"
        factor = 0.5 + 0.5 * (math.sin(_resize_arrow_tick[0]) ** 2)
        bright = _rgb_to_hex(*[min(255, c + 40) for c in _hex_to_rgb(FG_DIM)])
        btn_color = _mix_colors(FG_DIM, bright, factor)
        try:
            resize_btn.configure(text_color=btn_color)
        except Exception:
            pass
        root.after(90, _animate_resize_btn)


    # 启动所有动画
    root.after(500, _animate_panel_glow)
    root.after(700, _animate_title_shimmer)
    root.after(800, _animate_status_border)
    root.after(900, _animate_resize_btn)

    # ════════════════════════════════════════














    # ════════════════════════════════════════
    #  自定义 HUD 标题栏（顶层，可交互）
    # ════════════════════════════════════════
    _drag_offset = [0, 0]

    title_bar = tk.Canvas(root, height=28, bg=BG_DARK, highlightthickness=0, bd=0)
    title_bar.place(x=1, y=1, relwidth=1, width=-2)

    def _on_title_press(event):
        _drag_offset[0] = event.x
        _drag_offset[1] = event.y

    def _on_title_drag(event):
        x = root.winfo_x() + (event.x - _drag_offset[0])
        y = root.winfo_y() + (event.y - _drag_offset[1])
        root.geometry(f"+{x}+{y}")

    title_bar.bind("<ButtonPress-1>", _on_title_press)
    title_bar.bind("<B1-Motion>", _on_title_drag)

    def _on_title_release(event):
        _save_window_state({"geometry": root.geometry()})

    title_bar.bind("<ButtonRelease-1>", _on_title_release)

    # ════════════════════════════════════════
    #  自定义边框拖拽缩放（右下角）
    # ════════════════════════════════════════
    _resize_corner = tk.Frame(root, bg=BORDER_ACCENT, cursor="sizing")
    _resize_corner.place(relx=1.0, rely=1.0, x=-5, y=-5, width=8, height=8)

    _resize_origin = [0, 0]
    _resize_geo = [0, 0]

    def _on_resize_press(event):
        _resize_origin[0] = event.x_root
        _resize_origin[1] = event.y_root
        _resize_geo[0] = root.winfo_width()
        _resize_geo[1] = root.winfo_height()

    def _on_resize_corner(event):
        dx = event.x_root - _resize_origin[0]
        dy = event.y_root - _resize_origin[1]
        w = max(300, _resize_geo[0] + dx)
        h = max(200, _resize_geo[1] + dy)
        root.geometry(f"{w}x{h}")

    _resize_corner.bind("<ButtonPress-1>", _on_resize_press)
    _resize_corner.bind("<B1-Motion>", _on_resize_corner)
    _resize_corner.bind("<ButtonRelease-1>", lambda e: _save_window_state({"geometry": root.geometry()}))

    def _draw_title_bar():
        if not title_bar.winfo_exists():
            return
        title_bar.delete("all")
        w = title_bar.winfo_width()
        h = title_bar.winfo_height()
        # 标题文字
        title_bar.create_text(w // 2, h // 2 - 5, text="赛博义体 // 神经链接控制台",
                              fill=CYAN, font=("Consolas", 10, "bold"))
        # 最小化按钮 — 横线
        mx = w - 40
        title_bar.create_line(mx - 5, h // 2 - 3, mx + 5, h // 2 - 3,
                              fill=FG_ACCENT, width=2, tags="minline")
        title_bar.tag_bind("minline", "<ButtonPress-1>", lambda e: ctypes.windll.user32.ShowWindow(
            int(root.frame(), 16), 6))
        title_bar.tag_bind("minline", "<Enter>", lambda e: title_bar.itemconfigure("minline", fill=CYAN))
        title_bar.tag_bind("minline", "<Leave>", lambda e: title_bar.itemconfigure("minline", fill=FG_ACCENT))
        # 关闭按钮
        bx = w - 14
        title_bar.create_text(bx, h // 2 - 4, text="✕", fill=RED,
                              font=("Consolas", 9, "bold"), tags="ctxt")
        title_bar.tag_bind("ctxt", "<ButtonPress-1>", lambda e: (_save_window_state({"geometry": root.geometry()}), root.destroy()))
        title_bar.tag_bind("ctxt", "<Enter>", lambda e: title_bar.itemconfigure("ctxt", fill="#ff6688"))
        title_bar.tag_bind("ctxt", "<Leave>", lambda e: title_bar.itemconfigure("ctxt", fill=RED))

    title_bar.bind("<Configure>", lambda e: _draw_title_bar())

    main_frame = ctk.CTkFrame(root, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=10, pady=(20, 0))

    # ---- 1. 职业/专精 + 开关 ----
    top_outer, top_frame = _create_glow_panel(main_frame, accent=True)
    top_outer.pack(fill="x", pady=(0, 6))

    inner_top = ctk.CTkFrame(top_frame, fg_color="transparent")
    inner_top.pack(fill="x", padx=12, pady=(10, 4))

    class_prefix_label = ctk.CTkLabel(inner_top, text="⟐ 职业:", font=("Microsoft YaHei", 13, "bold"), text_color=FG_ACCENT)
    class_prefix_label.pack(side="left", padx=(4, 0))
    class_name_label = ctk.CTkLabel(inner_top, text="-", font=("Consolas", 15, "bold"), text_color=CYAN)
    class_name_label.pack(side="left", padx=(4, 0), pady=(2, 0))
    spec_label = ctk.CTkLabel(inner_top, text="专精: -", font=("Microsoft YaHei", 13, "bold"), text_color=FG_LIGHT)
    spec_label.pack(side="left", padx=(12, 0))

    toggle_row = ctk.CTkFrame(top_frame, fg_color="transparent")
    toggle_row.pack(fill="x", padx=12, pady=(0, 10))

    # ---- 绑定开关按钮 ----
    _binding_active = [False]  # 是否正在等待用户按键
    _is_custom_bound = [False]  # 是否已自定义绑定

    def _restore_default():
        """恢复默认 XBUTTON1/XBUTTON2 绑定"""
        global _toggle_vk, _toggle_key_str
        _toggle_key_str = "XBUTTON1"
        _toggle_vk = get_vk(_toggle_key_str)
        _is_custom_bound[0] = False
        bind_btn.configure(text="绑定", text_color=FG_ACCENT)
        bound_key_label.configure(text="默认:X1开 X2关", text_color=FG_DIM)
        status_label.configure(text="已恢复默认", text_color=CYAN)
        _status_freeze_until[0] = time.time() + 1.0
        root.after(1000, lambda: _status_freeze_until.__setitem__(0, 0.0))

    def on_bind_toggle():
        """点击后进入按键监听模式，等待用户按下新按键；已绑定时恢复默认"""
        if _is_custom_bound[0]:
            _restore_default()
            return
        if _binding_active[0]:
            return
        _binding_active[0] = True
        bind_btn.configure(text="等待按键...", text_color="#ffaa00")
        bound_key_label.configure(text="请按下新按键...", text_color="#ffaa00")

        def _listen_key():
            nonlocal _binding_active
            if not root.winfo_exists():
                return
            import utils as _u
            # 检查 XBUTTON1/XBUTTON2（普通 GetAsyncKeyState 对它们也有效）
            special_keys = {
                "XBUTTON1": _u._get_vk("XBUTTON1") if _u._get_vk("XBUTTON1") else -1,
                "XBUTTON2": _u._get_vk("XBUTTON2") if _u._get_vk("XBUTTON2") else -1,
            }
            # 扫描所有可能的虚拟键
            checked = set()
            found_key = None
            found_vk = None
            while root.winfo_exists() and _binding_active[0]:
                for vk in list(range(1, 256)):
                    if vk in checked:
                        continue
                    if ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
                        checked.add(vk)
                        # 跳过鼠标左键(1)、右键(2)、中键(4)
                        if vk in (1, 2, 4):
                            continue
                        # 匹配特殊键名
                        matched_name = None
                        for sk_name, sk_vk in special_keys.items():
                            if sk_vk != -1 and vk == sk_vk:
                                matched_name = sk_name
                                break
                        if matched_name:
                            found_key = matched_name
                            found_vk = sk_vk
                        else:
                            # 普通按键：尝试从 _VK 反查名称
                            matched_name = None
                            if hasattr(_u, '_VK'):
                                for name, code in _u._VK.items():
                                    if code == vk:
                                        matched_name = name
                                        break
                            if matched_name:
                                found_key = matched_name
                                found_vk = vk
                            else:
                                # 尝试单字符
                                try:
                                    ch = chr(vk)
                                    if ch.isprintable():
                                        found_key = ch
                                        found_vk = vk
                                except:
                                    pass
                        if found_key:
                            break
                    else:
                        checked.discard(vk)
                if found_key:
                    break
                time.sleep(0.03)

            _binding_active[0] = False
            if not root.winfo_exists():
                return

            if found_key and found_vk:
                global _toggle_vk, _toggle_key_str
                _toggle_key_str = found_key
                _toggle_vk = found_vk
                _is_custom_bound[0] = True
                bind_btn.configure(text="恢复默认", text_color="#ffaa00")
                bound_key_label.configure(text=f"绑定:{found_key}开/关", text_color=GREEN)
                # 短暂高亮
                status_label.configure(text=f"已绑定 {found_key}", text_color=GREEN)
                _status_freeze_until[0] = time.time() + 1.0
                root.after(1000, lambda: _status_freeze_until.__setitem__(0, 0.0))
            else:
                bind_btn.configure(text="绑定", text_color=FG_ACCENT)
                bound_key_label.configure(text="默认:X1开 X2关", text_color=FG_DIM)

        threading.Thread(target=_listen_key, daemon=True).start()

    # ---- 按钮公共样式 ----
    _BTN_STYLE = dict(
        fg_color=BG_BTN, hover_color="#1e293b",
        corner_radius=6, border_width=1, border_color=BORDER_COLOR,
    )

    bind_btn = ctk.CTkButton(
        toggle_row, text="绑定", command=on_bind_toggle,
        font=("Microsoft YaHei", 11), width=65, text_color=FG_ACCENT, **_BTN_STYLE,
    )
    bind_btn.pack(side="left", padx=(0, 6))

    # 添加刷新逻辑按钮
    _status_freeze_until = [0.0]

    def on_refresh_logic():
        # 重新加载Python模块
        success = reload_logic_modules()
        
        # 清除配置文件缓存（包括config.yml和keymap/*.yml）
        global _CONFIG_CACHE
        _CONFIG_CACHE = None
        
        # 清除keymap缓存（需要在utils模块中清除）
        try:
            import utils
            # 清除keymap相关缓存
            if hasattr(utils, '_keymap_cache'):
                utils._keymap_cache = None
            if hasattr(utils, '_unit_spell_to_hotkey_cache'):
                utils._unit_spell_to_hotkey_cache = None
            if hasattr(utils, '_current_keymap_class'):
                utils._current_keymap_class = None
        except:
            pass

        # 清除 GetPixels.py 中的 config 缓存
        try:
            import GetPixels
            GetPixels.load_config._cache = None
        except:
            pass

        # 清除 FuyutsuiTools 合并缓存，重载后重新读取覆盖配置
        try:
            _clear_merged_cache()
        except:
            pass
        
        freeze_until = time.time() + 1.0
        _status_freeze_until[0] = freeze_until
        _dot_prev_state[0] = "freeze"  # 标记冻结，让 _animate_dot 立即切蓝
        _dot_last_toggle[0] = 0.0
        if success:
            status_label.configure(text="已重载", text_color=CYAN)
        else:
            status_label.configure(text="ERROR", text_color=RED)
        root.after(1000, lambda: _status_freeze_until.__setitem__(0, 0.0))

    refresh_btn = ctk.CTkButton(
        toggle_row, text="重载", command=on_refresh_logic,
        font=("Microsoft YaHei", 11), width=65, **_BTN_STYLE,
    )
    refresh_btn.pack(side="left", padx=(0, 6))

    bound_key_label = ctk.CTkLabel(
        toggle_row,
        text="默认:X1开 X2关",
        font=("Microsoft YaHei", 12),
        text_color=FG_DIM,
    )
    bound_key_label.pack(side="left")


    # 动态状态指示灯
    _status_dot_canvas = tk.Canvas(toggle_row, width=14, height=14,
                                    bg=BG_FRAME, highlightthickness=0, bd=0)
    _status_dot_canvas.pack(side="right", padx=(0, 6))
    _dot_id = _status_dot_canvas.create_oval(3, 3, 11, 11, fill=RED, outline="")

    status_label = ctk.CTkLabel(
        toggle_row,
        text="已停止-ms",
        font=("Consolas", 12, "bold"),
        text_color=RED,
    )
    status_label.pack(side="right")

    _dot_last_toggle = [0.0]
    _dot_prev_state = [None]
    _DOT_BLINK_INTERVAL = 0.25  # 闪烁切换间隔（秒）

    def _animate_dot():
        if not root.winfo_exists():
            return
        now = time.time()
        # 重载冻结期间，立即变蓝，然后蓝色呼吸
        if now < _status_freeze_until[0]:
            cur = _status_dot_canvas.itemcget(_dot_id, "fill")
            if CYAN not in cur and FG_ACCENT not in cur:
                _status_dot_canvas.itemconfig(_dot_id, fill=CYAN)
            elif now - _dot_last_toggle[0] >= _DOT_BLINK_INTERVAL:
                _dot_last_toggle[0] = now
                _status_dot_canvas.itemconfig(_dot_id, fill=FG_ACCENT if cur == CYAN else CYAN)
            root.after(100, _animate_dot)
            return
        # 刚退出冻结，立即恢复状态色
        if _dot_prev_state[0] == "freeze":
            _dot_prev_state[0] = None
            with _state_lock:
                is_on = _logic_enabled and bool(_state_dict.get("有效性"))
            bright = GREEN if is_on else RED
            _status_dot_canvas.itemconfig(_dot_id, fill=bright)
            _dot_last_toggle[0] = now
            root.after(100, _animate_dot)
            return
        with _state_lock:
            is_on = _logic_enabled and bool(_state_dict.get("有效性"))
        # 状态变化时立即切换颜色，不等待闪烁间隔
        if _dot_prev_state[0] != is_on:
            _dot_prev_state[0] = is_on
            _dot_last_toggle[0] = now
            bright = GREEN if is_on else RED
            _status_dot_canvas.itemconfig(_dot_id, fill=bright)
            root.after(100, _animate_dot)
            return
        if is_on:
            bright = GREEN
            dim = "#00b368"
            if now - _dot_last_toggle[0] >= _DOT_BLINK_INTERVAL:
                _dot_last_toggle[0] = now
                cur = _status_dot_canvas.itemcget(_dot_id, "fill")
                _status_dot_canvas.itemconfig(_dot_id, fill=dim if cur == bright else bright)
        root.after(100, _animate_dot)

    root.after(100, _animate_dot)

    # ---- 3. 显示队伍（弹窗）----
    def open_team_window():
        with _state_lock:
            spec_snapshot = _spec_name
            class_snapshot = _class_name
            spec_id_snapshot = _spec_id
            class_id_snapshot = _class_id

        # 专精未知时不显示弹窗内容（也不弹窗）
        if spec_snapshot is None:
            return

        team_window = ctk.CTkToplevel(root)
        team_window.title("队伍信息 // TEAM MONITOR")
        team_window.geometry("580x620")
        team_window.resizable(True, True)
        team_window.attributes("-topmost", True)
        team_window.configure(fg_color=BG_DARK)
        try:
            team_window.attributes("-alpha", WINDOW_ALPHA)
        except Exception:
            pass

        header_outer, header_frame = _create_glow_panel(team_window, accent=True)
        header_outer.pack(fill="x", padx=12, pady=(12, 8))
        header_label = ctk.CTkLabel(
            header_frame,
            text=f"队伍信息  职业: {class_snapshot or '-'} / 专精: {spec_snapshot or '-'}",
            font=("Consolas", 12, "bold"),
            text_color=CYAN,
            anchor="w",
        )
        header_label.pack(fill="x", padx=12, pady=10)

        body_frame = ctk.CTkFrame(team_window, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        team_text = ctk.CTkTextbox(
            body_frame,
            wrap="none",
            font=("Consolas", 11),
            corner_radius=8,
        )
        team_text.pack(fill="both", expand=True)
        team_text.configure(state="disabled")

        def format_value(v):
            if v is None:
                return "-"
            if isinstance(v, bool):
                return "是" if v else "否"
            return str(v)

        def build_team_text(sd, spec_name, class_id, spec_id, unit_info):
            if spec_name is None:
                return ""

            group = sd.get("group") or {}
            if not group:
                return "未检测到队伍数据（请确认游戏窗口存在且扫描成功）。\n"

            # group keys 理论上是 "1".."30"
            unit_keys = sorted(
                group.keys(),
                key=lambda x: int(x) if str(x).isdigit() else 10**9,
            )

            # 字段排序：优先使用当前专精在主界面显示的字段顺序，其余字段按字母排序补齐
            ordered_fields = []
            if spec_name and class_id is not None and spec_id is not None:
                try:
                    _, fields_for_spec = get_group_config_for_class_spec(class_id, spec_id)
                    ordered_fields.extend([f for f in fields_for_spec if f not in ordered_fields])
                except Exception:
                    pass

            rest_fields = set()
            for uk in unit_keys:
                unit_data = group.get(uk) or {}
                for f in unit_data.keys():
                    if f not in ordered_fields:
                        rest_fields.add(f)

            ordered_fields.extend(sorted(rest_fields))

            lines = []
            lines.append(f"单位总数: {len(unit_keys)}")
            lines.append(f"字段数: {len(ordered_fields)}")
            lines.append("")

            for uk in unit_keys:
                unit_data = group.get(uk) or {}
                # 每个单位严格一行：字段之间用分隔符拼接，避免多行导致滚动成本过高
                field_parts = []
                for f in ordered_fields:
                    field_parts.append(f"{f}={format_value(unit_data.get(f))}")
                lines.append(f"Unit {uk}: " + " | ".join(field_parts))

            if unit_info:
                lines.append("")
                lines.append("逻辑推荐/目标单位（unit_info）")
                for k in sorted(unit_info.keys()):
                    lines.append(f"  {k}: {format_value(unit_info.get(k))}")

            return "\n".join(lines) + "\n"

        # 自动刷新：让弹窗能跟随实时状态变化
        def refresh():
            if not team_window.winfo_exists():
                return

            with _state_lock:
                sd_now = dict(_state_dict)
                spec_now = _spec_name
                class_now = _class_name
                spec_id_now = _spec_id
                class_id_now = _class_id
                unit_info_now = dict(_unit_info)

            # 更新顶部标题（职业/专精可能在首次打开后发生变化）
            if spec_now is None:
                header_label.configure(
                    text=f"队伍信息（职业: {class_now or '-'} / 专精: -）"
                )
                team_text.configure(state="normal")
                team_text.delete("1.0", "end")
                team_text.configure(state="disabled")
            else:
                header_label.configure(
                    text=f"队伍信息（职业: {class_now or '-'} / 专精: {spec_now or '-'})"
                )

                team_text.configure(state="normal")
                team_text.delete("1.0", "end")
                team_text.insert("end", build_team_text(sd_now, spec_now, class_id_now, spec_id_now, unit_info_now))
                team_text.configure(state="disabled")

            TEAM_WINDOW_REFRESH_MS = 500
            team_window.after(TEAM_WINDOW_REFRESH_MS, refresh)

        refresh()

    # 顶部新增按钮：点击弹窗展示所有单位信息
    is_small = False

    resize_btn = None

    def toggle_window_size():
        nonlocal is_small, resize_btn
        is_small = not is_small
        x, y = root.winfo_x(), root.winfo_y()
        root.geometry(f"{small_geometry if is_small else normal_geometry}+{x}+{y}")
        # 同步按钮图标：当前为缩小状态时显示"▲"表示可恢复
        if resize_btn is not None:
            resize_btn.configure(text=("▲" if is_small else "▼"))
        _save_window_state({"geometry": root.geometry()})

    resize_btn = ctk.CTkButton(
        inner_top, text="▼", command=toggle_window_size,
        font=("Consolas", 11), width=28,
        text_color=FG_DIM, **_BTN_STYLE,
    )
    resize_btn.pack(side="right", padx=(0, 8))

    ctk.CTkButton(
        inner_top, text="队伍", command=open_team_window,
        font=("Microsoft YaHei", 11), width=80, text_color=FG_ACCENT, **_BTN_STYLE,
    ).pack(side="right", padx=(8, 0))

    # ---- 2. 状态区域（未检测到职业时不显示）----
    content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")

    status_outer, status_frame = _create_glow_panel(content_frame)
    status_outer.pack(fill="both", expand=True, pady=(0, 6))

    status_header = ctk.CTkFrame(status_frame, fg_color="transparent")
    status_header.pack(fill="x", padx=12, pady=(2, 2))
    ctk.CTkLabel(status_header, text="▸ 实时状态", font=("Microsoft YaHei", 12, "bold"), text_color=CYAN).pack(side="left")

    action_label = ctk.CTkLabel(status_header, text="行为: -", font=("Consolas", 12, "bold"), text_color=FG_LIGHT)
    action_label.pack(side="left", padx=(5, 0))

    lowest_health_label = ctk.CTkLabel(status_header, text="对象: 等待匹配", font=("Microsoft YaHei", 12, "bold"), text_color="#ff69b4")
    lowest_health_label.pack(side="right", padx=(0, 0), pady=(2, 0))

    status_grid = ctk.CTkFrame(status_frame, fg_color="transparent")
    status_grid.pack(fill="x", padx=12, pady=4)

    status_vars = {}

    def update_status_display(keys):
        for w in status_grid.winfo_children():
            w.destroy()
        status_vars.clear()
        for c in range(6):
            status_grid.grid_columnconfigure(c, weight=0)
        for i, k in enumerate(keys):
            row, col = i // 3, (i % 3) * 2
            ctk.CTkLabel(status_grid, text=k + ":", font=("Microsoft YaHei", 11), text_color=FG_DIM).grid(
                row=row, column=col, sticky="w", padx=(0, 4), pady=1)
            # 用 tk.Label 固定 7 字符宽度，防止数值变化导致列宽抖动
            lbl = tk.Label(status_grid, text="-", font=("Consolas", 11, "bold"), fg="#00f0ff",
                           bg=BG_FRAME, width=5, anchor="w", bd=0, highlightthickness=0)
            lbl.grid(row=row, column=col + 1, sticky="w", padx=(0, 16), pady=1)
            status_vars[k] = lbl


    # ---- 技能冷却 ----
    cooldown_outer, cooldown_frame = _create_glow_panel(content_frame)
    cooldown_outer.pack(fill="x", pady=(0, 6))
    cooldown_header = ctk.CTkFrame(cooldown_frame, fg_color="transparent")
    cooldown_header.pack(fill="x", padx=12, pady=(10, 2))
    ctk.CTkLabel(cooldown_header, text="▸ 技能冷却", font=("Microsoft YaHei", 12, "bold"), text_color=CYAN).pack(side="left")
    cooldown_grid = ctk.CTkFrame(cooldown_frame, fg_color="transparent")
    cooldown_grid.pack(fill="x", padx=12, pady=(4, 10))
    cooldown_vars = {}

    COOLDOWN_PER_ROW = 3

    def update_cooldown_display(spell_list):
        """根据专精技能列表重建冷却显示，每行 3 个技能"""
        for w in cooldown_grid.winfo_children():
            w.destroy()
        cooldown_vars.clear()
        if not spell_list:
            return
        for c in range(6):
            cooldown_grid.grid_columnconfigure(c, weight=0)
        for i, name in enumerate(spell_list):
            row = i // COOLDOWN_PER_ROW
            col = (i % COOLDOWN_PER_ROW) * 2
            ctk.CTkLabel(cooldown_grid, text=name + ":", font=("Microsoft YaHei", 11), text_color=FG_DIM).grid(
                row=row, column=col, sticky="w", padx=(0, 4), pady=1)
            lbl = tk.Label(cooldown_grid, text="-", font=("Consolas", 11, "bold"), fg="#00f0ff",
                           bg=BG_FRAME, width=5, anchor="w", bd=0, highlightthickness=0)
            lbl.grid(row=row, column=col + 1, sticky="w", padx=(0, 16), pady=1)
            cooldown_vars[name] = lbl

    last_cooldown_spells = [None]

    last_status_keys = [None]

    def update_display():
        nonlocal lowest_health_label
        with _state_lock:
            sd = dict(_state_dict)
            enabled = _logic_enabled
            mode = _send_mode
            class_name = _class_name
            spec = _spec_name
            class_id = _class_id
            spec_id = _spec_id

        class_name_label.configure(
            text=class_name or "-",
            text_color=CLASS_NAME_COLORS.get(class_name, CYAN),
        )
        spec_label.configure(text=f"专精: {spec or '-'}")

        # 状态显示：无数据时显示无信号，否则不管
        scan_text = f"{_scan_ms:5.1f}"
        if not sd:
            status_label.configure(text=f"无信号{scan_text}", text_color=FG_DIM)
        elif enabled:
            status_label.configure(text=f"运行中{scan_text}", text_color=GREEN)
        else:
            status_label.configure(text=f"已停止{scan_text}", text_color=RED)

        if spec is None:
            if content_frame.winfo_ismapped():
                content_frame.pack_forget()
            root.after(GUI_UPDATE_MS, update_display)
            return
        if not content_frame.winfo_ismapped():
            content_frame.pack(fill="both", expand=True, pady=(0, 6))

        # 重载后 1 秒内不覆盖状态标签
        if time.time() < _status_freeze_until[0]:
            root.after(GUI_UPDATE_MS, update_display)
            return


        current_status_keys, _, current_cooldown_spells = get_class_spec_view_data(class_id, spec_id)
        if last_status_keys[0] != current_status_keys:
            last_status_keys[0] = current_status_keys
            update_status_display(current_status_keys)

        if last_cooldown_spells[0] != current_cooldown_spells:
            last_cooldown_spells[0] = current_cooldown_spells
            update_cooldown_display(current_cooldown_spells)

        spells_data = sd.get("spells") or {}
        for name, lbl in cooldown_vars.items():
            val = spells_data.get(name)
            if val is None:
                lbl.configure(text="-", text_color=FG_DIM)
            else:
                lbl.configure(text=str(int(val)), fg=CYAN if val == 0 else FG_LIGHT)

        for k in status_vars:
            v = sd.get(k)
            txt = str(v) if v is not None else "-"
            status_vars[k].configure(text=txt, fg=GREEN if v is True else (RED if v is False else CYAN))

        action_label.configure(text=f"行为:{_current_step}",
                               text_color=GREEN if _logic_enabled else FG_LIGHT)

        # 更新最低生命值显示
        with _state_lock:
            unit_info = dict(_unit_info)
        lowest_unit = unit_info.get("最低单位") or unit_info.get("lowest_unit")
        lowest_unit_pct = unit_info.get("最低生命值") or unit_info.get("lowest_unit_pct")
        if lowest_unit is not None and lowest_unit_pct is not None:
            lowest_health_label.configure(text=f"对象:unit {lowest_unit} ({lowest_unit_pct}%)", text_color=RED)
        else:
            lowest_health_label.configure(text="对象: 等待匹配", text_color="#ff69b4")


        root.after(GUI_UPDATE_MS, update_display)

    default_keys, _, _ = get_class_spec_view_data(None, None)
    update_status_display(default_keys)
    last_status_keys[0] = default_keys
    root.after(0, update_display)

    def start_workers():
        threading.Thread(target=_key_detect_loop, daemon=True).start()
        try:
            _run_logic_loop()
        except Exception as e:
            print("Logic worker error:", e)

    worker = threading.Thread(target=start_workers, daemon=True)
    worker.start()

    root.mainloop()


if __name__ == "__main__":
    # 打包环境变量检测：避免 PyInstaller 构建过程中误启动 GUI
    if os.environ.get("CYBER_LIMB_BUILDING"):
        print("[BUILD] 打包模式，跳过 GUI 启动")
        sys.exit(0)
    create_gui()
