# FuyutsuiTools

**Fuyutsui 的功能扩展与数据覆盖模块**

FuyutsuiTools 是 [Fuyutsui](https://github.com/waynebian01/Fuyutsui/) 的非侵入式扩展插件，在不修改父插件源码的前提下，通过覆盖机制添加新功能、定制职业行为。

## 功能特性

1. 需要将 [logic_gui_laoer.py] 放在 [主插件]`\Fuyutsui\Fuyutsui`下使用.

## 安装

1. 确保 [Fuyutsui](https://github.com/waynebian01/Fuyutsui/) 已正确安装
2. 将 `FuyutsuiTools` 文件夹复制到 `Interface/AddOns/` 目录
3. 确保目录结构为 `Interface/AddOns/FuyutsuiTools/FuyutsuiTools.toc`
4. 重载插件或重启游戏

### 驱散开关
为圣骑士三个专精添加驱散开关，可通过游戏内按钮一键切换：
- **开启**：按原始逻辑自动驱散队伍成员
- **关闭**：神圣圣骑士仅对当前目标施放清洁术（魔法/疾病/中毒）

### 四按钮控制面板
替代父插件原有的单按钮，提供可拖动的四按钮面板：

| 按钮 | 功能 |
|------|------|
| 爆发 | 切换爆发开关 |
| 自动/单体 | 切换 AOE 模式 |
| 逻辑/辅助 | 切换输出模式 |
| 驱散 | 切换驱散开关 |

支持快捷键绑定（右键点击按钮进入绑定模式）。

### 圣骑士逻辑定制
- 驱散开关关闭时，神圣专精仅对目标类型为魔法(12)、疾病(13)、中毒(15)的当前目标驱散
- 制裁之锤直接映射为固定按键

## 架构设计

采用**双层覆盖架构**，Lua 端和 Python 端各自独立扩展：

```
FuyutsuiTools/
├── FuyutsuiTools.toc        # 插件定义（依赖 Fuyutsui）
├── init.lua                 # 初始化钩子
├── core/
│   ├── core.lua             # 驱散开关逻辑
│   ├── config.lua           # 配置覆盖（占位）
│   └── quickbutton.lua      # 四按钮面板
├── class/
│   └── Paladin.lua          # 圣骑士数据块扩展
└── Fuyutsui/                # Python 端覆盖
    ├── overrides.py         # 覆盖加载引擎
    ├── config.yml           # 配置深度合并
    └── class/
        └── paladin_logic.py # 圣骑士逻辑覆盖
```

### Lua 端（游戏内）
- **初始化钩子**：包装 `OnEnable`，注入额外初始化逻辑
- **函数覆盖**：在 `Fuyutsui` 命名空间上定义同名函数，利用 Lua 运行时特性覆盖
- **数据扩展**：直接修改 `ClassBlocks` 表添加新的像素块

### Python 端（桌面端）
- **配置合并**：monkey-patch `utils.load_config`，自动深度合并覆盖配置
- **模块替换**：`import_with_override` 优先加载 Tools 目录下的同名逻辑模块
