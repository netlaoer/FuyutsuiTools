# -*- coding: utf-8 -*-
"""FuyutsuiTools 覆盖模块：config.yml 合并 + 职业逻辑覆盖加载"""
import sys
from pathlib import Path
import importlib
import importlib.util

# ── 路径 ──
_override_base = Path(__file__).parent
_override_config_path = _override_base / "config.yml"
_override_class_dir = _override_base / "class"


# ── config.yml deep merge ──
def _deep_merge(base, override):
    """递归合并 override 到 base（覆盖同名键，保留 base 其余键）"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


_cached_override_config = None


def load_override_config():
    """加载并缓存覆盖 config.yml"""
    global _cached_override_config
    if _cached_override_config is not None:
        return _cached_override_config
    try:
        import yaml
        with open(_override_config_path, "r", encoding="utf-8") as f:
            _cached_override_config = yaml.safe_load(f) or {}
    except Exception:
        _cached_override_config = {}
    return _cached_override_config


# ── 模块覆盖加载 ──
def import_with_override(module_name: str):
    """优先从 FuyutsuiTools/class/ 加载同名模块（覆盖），找不到则回退到内置 class/"""
    override_file = _override_class_dir / f"{module_name}.py"
    if override_file.is_file():
        spec = importlib.util.spec_from_file_location(f"_override.{module_name}", override_file)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"_override.{module_name}"] = mod
        spec.loader.exec_module(mod)
        return mod
    return importlib.import_module(f"class.{module_name}")


def apply_overrides():
    """Patch load_config / load_keymap：识别职业后首次调用时自动合并覆盖"""
    import utils
    import GetPixels

    original_load_config = utils.load_config

    def _patched_load_config():
        if not _patched_load_config._cache:
            config = original_load_config()
            cfg = load_override_config()
            if cfg:
                _deep_merge(config, cfg)
            _patched_load_config._cache.update(config)
        return _patched_load_config._cache

    _patched_load_config._cache = {}

    utils.load_config = _patched_load_config
    GetPixels.load_config = _patched_load_config

    # Patch load_keymap + select_keymap_for_class
    original_load_keymap = utils.load_keymap
    original_select_keymap = utils.select_keymap_for_class
    override_keymap_dir = _override_base / "keymap"
    if override_keymap_dir.is_dir():
        def _patched_load_keymap():
            if _patched_load_keymap._cache:
                return _patched_load_keymap._cache
            keymap = original_load_keymap()
            km_name = Path(utils.KEYMAP_PATH).name
            override_km = override_keymap_dir / km_name
            if override_km.is_file():
                import yaml
                with open(override_km, "r", encoding="utf-8") as f:
                    extra = yaml.safe_load(f) or []
                if isinstance(extra, dict):
                    extra = list(extra.values())
                if extra:
                    max_id = max((int(k) for k in keymap.keys() if str(k).isdigit()), default=0)
                    for entry in extra:
                        if isinstance(entry, dict):
                            max_id += 1
                            keymap[str(max_id)] = entry
                    print(f"[FuyutsuiTools] 已合并 keymap 覆盖: {km_name} (+{len(extra)} 条)")
            _patched_load_keymap._cache = keymap
            return keymap

        _patched_load_keymap._cache = None

        def _patched_select_keymap(class_id, *args, **kwargs):
            original_select_keymap(class_id, *args, **kwargs)
            _patched_load_keymap._cache = None

        utils.load_keymap = _patched_load_keymap
        utils.select_keymap_for_class = _patched_select_keymap


_CLASS_NAMES = {1: "战士", 2: "圣骑士", 3: "猎人", 4: "盗贼", 5: "牧师", 6: "死亡骑士",
               7: "萨满", 8: "法师", 9: "术士", 10: "武僧", 11: "德鲁伊", 12: "恶魔猎手", 13: "唤魔师"}
_printed = False


def print_loaded_info():
    """识别到职业后调用，打印覆盖加载信息（只打印一次）"""
    global _printed
    if _printed:
        return
    _printed = True
    cfg = load_override_config()
    if cfg:
        named_keys = [f"{_CLASS_NAMES.get(k, k)}(ID:{k})" for k in cfg.keys()]
        print(f"[FuyutsuiTools] 已加载覆盖配置: {named_keys}")
    modules = [f.stem for f in _override_class_dir.glob('*_logic.py')]
    if modules:
        print(f"[FuyutsuiTools] 已加载覆盖模块: {modules}")


def clear_merged_cache():
    """重载时清除合并缓存，使下次 load_config() 重新读取并合并"""
    global _cached_override_config, _printed
    _cached_override_config = None
    _printed = False
    try:
        import utils
        utils.load_config._cache = {}
        utils._keymap_cache = None
        utils._unit_spell_to_hotkey_cache = None
        if hasattr(utils.load_keymap, '_cache'):
            utils.load_keymap._cache = None
    except Exception:
        pass
