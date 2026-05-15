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
    """Patch load_config：所有代码读取配置时自动包含覆盖字段"""
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

    override_cfg = load_override_config()
    if not override_cfg:
        return

    utils.load_config = _patched_load_config
    GetPixels.load_config = _patched_load_config
    class_names = {1: "战士", 2: "圣骑士", 3: "猎人", 4: "盗贼", 5: "牧师", 6: "死亡骑士",
                  7: "萨满", 8: "法师", 9: "术士", 10: "武僧", 11: "德鲁伊", 12: "恶魔猎手", 13: "唤魔师"}
    named_keys = [f"{class_names.get(k, k)}(ID:{k})" for k in override_cfg.keys()]
    print(f"[FuyutsuiTools] 已加载覆盖配置: {named_keys}")
    print(f"[FuyutsuiTools] 已加载覆盖模块: {[f.stem for f in _override_class_dir.glob('*_logic.py')]}")


def clear_merged_cache():
    """重载时清除合并缓存，使下次 load_config() 重新读取并合并"""
    global _cached_override_config
    _cached_override_config = None
    try:
        import utils
        utils.load_config._cache = {}
    except Exception:
        pass
