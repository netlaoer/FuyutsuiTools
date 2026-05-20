# FuyutsuiTools

**Fuyutsui 的功能扩展与数据覆盖模块**

<!-- AI_INSTRUCTION: 在修改此项目任何代码之前，请完整阅读本文件，了解架构、所有函数、编码约定和开发规范。完成代码修改后，必须同步更新本文件中对应的章节（函数列表、文件结构、数据结构等），保持文档与代码一致。 -->
<!-- AI: Before making any changes to this project, read this entire file first. After completing code changes, you MUST update the corresponding sections in this file (function lists, file structure, data structures, etc.) to keep documentation in sync with code. -->

> 用户使用说明：[使用说明.md](使用说明.md)

---

## 一、项目概述

**Fuyutsui（冬月）** 是一个魔兽世界（WoW）辅助决策系统，分为两层：

1. **WoW 插件层（Lua）**：在游戏内运行，将玩家/目标/队伍/法术等状态编码为屏幕顶部像素条的颜色值
2. **Python 决策层**：在外部运行，通过屏幕像素扫描读取游戏状态，根据职业逻辑做决策，通过后台按键（PostMessage）向游戏发送操作

**FuyutsuiTools** 是 Fuyutsui 的扩展插件，通过覆盖机制在不修改主插件代码的情况下扩展功能。

---

## 二、文件结构

### Fuyutsui（主插件）

```
Fuyutsui/
├── Fuyutsui.toc          # 插件描述 (v0.0.8, 接口 120000-120005)
├── embeds.xml            # Ace3 库嵌入
├── libs/                 # 第三方库（Ace3, LibRangeCheck-3.0）
│
├── core/                 # 核心模块
│   ├── core.lua          # 插件初始化、AceDB、52个事件注册、斜杠命令、开关切换
│   ├── config.lua        # spellsList(按职业分段的法术ID→像素索引映射)、
│   │                     #   events(事件枚举)、heroTalents(英雄天赋)、
│   │                     #   difficulty(难度ID)、actionbar(动作条)、
│   │                     #   keymap(按键映射)、classMap(职业映射)、
│   │                     #   bossID(Boss编号)、failed_spell_map(法术失败映射)
│   ├── block.lua         # 像素色条创建（255个色块 + 法术充能进度条）
│   ├── macro.lua         # 动态宏创建（队伍目标 @raid/party 智能切换）
│   ├── keybinds.lua      # 扫描动作条按键绑定（修饰键×基础键组合）
│   ├── auras.lua         # 逻辑光环状态机（按classId索引，追踪buff/debuff时间/层数）
│   ├── quickbutton.lua   # 快捷切换按钮（爆发/AOE/输出模式/药水）
│
├── class/                # 职业模块（定义各职业的像素块布局 ClassBlocks）
│   ├── Warrior.lua       # 战士 (classId=1)
│   ├── Paladin.lua       # 圣骑士 (classId=2)
│   ├── Hunter.lua        # 猎人 (classId=3)
│   ├── Rogue.lua         # 盗贼 (classId=4)
│   ├── Priest.lua        # 牧师 (classId=5)
│   ├── DeathKnight.lua   # 死亡骑士 (classId=6)
│   ├── Shaman.lua        # 萨满 (classId=7)
│   ├── Mage.lua          # 法师 (classId=8)
│   ├── Warlock.lua       # 术士 (classId=9)
│   ├── Monk.lua          # 武僧 (classId=10)
│   ├── Druid.lua         # 德鲁伊 (classId=11)
│   ├── DemonHunter.lua   # 恶魔猎手 (classId=12)
│   └── Evoker.lua        # 唤魔师 (classId=13)
│
├── main.lua              # 事件处理函数 + OnUpdate 帧循环（1723行）
├── gui.lua               # Ace3 配置界面（/fu gui 像素块调试/查看）
│
└── Fuyutsui/             # Python 决策层
    ├── logic_gui_laoer.py  # 主 GUI 入口（赛博朋克风格，按键检测+逻辑调度+状态显示）
    ├── logic_gui.py        # 备用 GUI 入口（简洁风格）
    ├── utils.py            # 核心工具库
    ├── GetPixels.py        # 屏幕像素扫描引擎
    ├── config.yml          # 像素块配置（state/spells/groups/auras 定义）
    ├── keymap.yml          # 默认按键映射
    ├── keymap/             # 按职业分目录的按键映射
    │
    ├── class/              # 职业逻辑模块（12个职业）
    │   ├── paladin_logic.py   # 圣骑士（三系）
    │   ├── priest_logic.py    # 牧师（三系）
    │   ├── deathknight_logic.py
    │   ├── druid_logic.py
    │   ├── shaman_logic.py
    │   ├── monk_logic.py
    │   ├── evoker_logic.py
    │   ├── mage_logic.py
    │   ├── warlock_logic.py
    │   ├── demonhunter_logic.py
    │   ├── hunter_logic.py
    │   ├── rogue_logic.py
    │   └── warrior_logic.py
    │
    └── other/              # 调试工具
        ├── GetInfo.py
        ├── GetRGB.py
        └── hex_to_decode.py
```

### FuyutsuiTools（扩展插件）

```
FuyutsuiTools/
├── FuyutsuiTools.toc     # 依赖 Fuyutsui
├── init.lua              # 覆盖 OnEnable，进入世界时重新初始化
├── main.lua              # 覆盖 OnUpdate，血量高频轮询（0.2秒，团本除外）
├── logic_gui_laoer.py    # 独立 GUI 入口（需放入主插件 Fuyutsui/Fuyutsui/ 目录使用）
├── README.md             # 项目说明
│
├── core/
│   ├── core.lua          # 驱散开关（SwitchDispel、updatePlayerConfig 覆盖）
│   ├── config.lua        # 占位（空文件）
│   ├── quickbutton.lua   # 四按钮可拖拽面板（爆发/AOE/逻辑/驱散）
│
├── class/
│   └── Paladin.lua       # 神圣专精添加"驱散开关"像素块
│
├── iMorph/               # 预留空目录
│
└── Fuyutsui/             # Python 覆盖层
    ├── overrides.py      # config 深度合并 + 职业逻辑模块覆盖加载
    └── class/
        └── paladin_logic.py  # 覆盖圣骑士逻辑（驱散开关 + 制裁之锤固定按键）
```

> **注意**：`logic_gui_laoer.py` 不是放在 FuyutsuiTools 目录运行，而是复制到主插件 `Fuyutsui/Fuyutsui/` 下替换原版 GUI 入口。

---

## 三、加载顺序

### Lua 端

WoW 按 TOC 文件中的 `## Dependencies` 和文件列表顺序加载。Fuyutsui 先加载，FuyutsuiTools 后加载。

**Fuyutsui 加载顺序**：
1. `embeds.xml` + `Libs/LibRangeCheck-3.0`
2. `core/core.lua` → `core/quickbutton.lua` → `core/config.lua` → `core/block.lua` → `core/macro.lua` → `core/keybinds.lua` → `core/auras.lua`
3. 13 个 `class/*.lua` 文件
4. `main.lua` → `gui.lua`

**FuyutsuiTools 加载顺序**（在 Fuyutsui 之后）：
1. `init.lua` — 覆盖 OnEnable
2. `main.lua` — 覆盖 OnUpdate
3. `core\core.lua` — 驱散开关
4. `class\Paladin.lua` — 圣骑士数据块扩展
5. `core\config.lua` — 占位
6. `core\quickbutton.lua` — 四按钮面板

### Python 端

`logic_gui_laoer.py` 是入口，启动时：
1. `from utils import *` — 加载工具库
2. `from GetPixels import get_info, scan_screen_data` — 加载扫描引擎
3. 检测 `../FuyutsuiTools/Fuyutsui/overrides.py`，存在则 `apply_overrides()` — monkey-patch
4. `_build_class_module_map()` — 从 config.yml + class/ 目录构建职业模块映射
5. `create_gui()` — 创建 GUI，启动按键检测线程和逻辑执行线程

---

## 四、核心数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                     WoW 游戏客户端                               │
│                                                                 │
│  游戏事件 → Fuyutsui Lua 插件 → 更新状态变量 → 编码为像素颜色     │
│  (UNIT_HEALTH, SPELL_UPDATE_COOLDOWN, etc.)                    │
│                                                                 │
│  屏幕顶部 255 个像素色块 (FuyutsuiColorBars)                    │
│  屏幕第二行充能进度条 (FuyutsuiCountBars)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ 像素颜色 (RGB)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Python 决策层                                │
│                                                                 │
│  GetPixels.py 扫描屏幕 → 构建 state_dict (字典)                  │
│       │                                                        │
│       ▼                                                        │
│  职业逻辑 class/*_logic.py                                      │
│  run_xxx_logic(state_dict, spec_name)                          │
│       │                                                        │
│       ▼                                                        │
│  返回 (action_hotkey, current_step, unit_info)                  │
│       │                                                        │
│       ▼                                                        │
│  utils.send_key_to_wow() → PostMessage 后台按键发送到 WoW 窗口   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、像素编码原理

### 顶部长条（FuyutsuiColorBars）

- **255 个像素**，每个像素宽度 = 屏幕宽度 / 255，高度 2px
- 颜色编码：`RGB = (0, index/255, value/255)`
  - **G 通道** = 索引号（1~255），标识这个像素代表什么数据
  - **B 通道** = 数值（0~1），通过颜色曲线映射实现非线性编码
- 索引由 `config.yml` 中 `blocks.state`、`blocks.spells`、`blocks.auras` 等定义

### 颜色曲线（ColorCurve）

- 使用 WoW API `C_CurveUtil.CreateColorCurve` 创建
- 核心函数 `creatColorCurveScaling(b)` 在 main.lua 中
  - b > 100：线性映射 `b/255`
  - b <= 100：三段折线（`0→黑色`，`1/255→目标`，`b/255→更高`）
- 缓存在 `curveCache` 中避免重复创建
- 另有 `creatColorCurve(point, b)` 在 core.lua 中创建简单线性曲线

### 法术冷却编码

- `blocks.spells[spellID]` 定义了每个法术的 index
- 冷却值 0 = 就绪，255 = 不可用/不存在
- 中间值通过颜色曲线 API 映射

### 充能进度条（FuyutsuiCountBars）

- 第二行，255 个像素宽度，高度 20px
- 使用 `CreateAutoLayoutBar()` 创建 StatusBar 显示充能/使用次数
- 自动布局，spellId 去重

### 左边界标记

- 充能进度条左边界有一对红/白标记像素
- Python 扫描时通过这对标记定位进度条的起始位置

---

## 六、Lua 端核心机制

### core.lua — 初始化与事件注册

**全局表**：
```lua
Fuyutsui.state       -- 玩家状态 (classId, className, classFilename, specName, specID, ...)
Fuyutsui.blocks      -- 当前加载的像素块配置
Fuyutsui.target      -- 目标信息
Fuyutsui.nameplate   -- 姓名版信息
Fuyutsui.group       -- 队伍单位信息 { [unit] = { index, healthPercent, role, dispel, curve, ... } }
Fuyutsui.groupList   -- 队伍单位列表
Fuyutsui.defaults    -- AceDB 默认值
Fuyutsui.keybindings -- 按键绑定映射
Fuyutsui.timeElapsed -- OnUpdate 计时器
```

**AceDB 保存变量**（`FuyutsuiADB`）：
```lua
char = { level, aoeMode(0=自动/1=单体), cooldowns(爆发), dpsMode(0=官方一键辅助/1=手动逻辑),
         delay, potion, quickButtonCX, quickButtonCY, quickButtonShow }
```

**关键函数**：

| 函数 | 说明 |
|------|------|
| `F:OnInitialize()` | AceDB 初始化，注册斜杠命令 `/fu` |
| `F:OnEnable()` | 获取专精信息、加载 blocks、读取按键绑定、注册 52 个事件 |
| `F:SwitchCooldown()` | 切换爆发开关 |
| `F:SwitchAoeMode()` | 切换 AOE 模式 |
| `F:SwitchDpsMode()` | 切换输出模式 |
| `F:SwitchDelay()` | 更新延迟标志像素 |
| `F:SwitchPotion()` | 切换药水开关 |
| `F:SlashCommand(input)` | 斜杠命令分发（cd/aoemode/dpsmode/potion/delay/help/config/gui 等） |
| `F:IterateGroupMembers(reversed, forceParty)` | 迭代队伍成员的迭代器 |
| `F:creatColorCurve(point, b)` | 创建线性颜色曲线 |
| `SetTestSecret(set)` | 全局函数，设置秘密值限制的 CVars |

**斜杠命令**：`/fu` 或 `/Fuyutsui`
- `cd [on/off]` — 爆发开关
- `aoemode [auto/aoe]` — AOE 模式
- `dpsmode [manual/assistant]` — 输出模式
- `potion [on/off]` — 药水开关
- `delay [秒]` — 延迟值
- `help` — 帮助信息
- `options` / `config` — 打开配置面板
- `gui` — 打开像素块调试界面
- `enable` / `disable` — 启用/禁用插件
- `message [文本]` — 显示聊天消息

### main.lua — 事件处理与帧循环

**注册的 52 个事件**：
`ZONE_CHANGED`, `ZONE_CHANGED_INDOORS`, `PLAYER_ENTERING_WORLD`, `PLAYER_TALENT_UPDATE`, `PLAYER_DEAD`, `PLAYER_ALIVE`, `PLAYER_UNGHOST`, `PLAYER_MOUNT_DISPLAY_CHANGED`, `PLAYER_REGEN_DISABLED`, `PLAYER_REGEN_ENABLED`, `PLAYER_STARTED_MOVING`, `PLAYER_STOPPED_MOVING`, `UNIT_SPELLCAST_SENT`, `UNIT_SPELLCAST_START`, `UNIT_SPELLCAST_STOP`, `UNIT_SPELLCAST_CHANNEL_START`, `UNIT_SPELLCAST_CHANNEL_STOP`, `UNIT_SPELLCAST_EMPOWER_START`, `UNIT_SPELLCAST_EMPOWER_STOP`, `UNIT_SPELLCAST_SUCCEEDED`, `UNIT_SPELLCAST_FAILED`, `UNIT_POWER_UPDATE`, `UNIT_HEALTH`, `UNIT_MAXHEALTH`, `UNIT_HEAL_ABSORB_AMOUNT_CHANGED`, `UNIT_HEAL_PREDICTION`, `SPELL_UPDATE_USES`, `GROUP_ROSTER_UPDATE`, `UNIT_DIED`, `SPELL_RANGE_CHECK_UPDATE`, `ACTION_RANGE_CHECK_UPDATE`, `UI_ERROR_MESSAGE`, `PLAYER_TARGET_CHANGED`, `NAME_PLATE_UNIT_ADDED`, `NAME_PLATE_UNIT_REMOVED`, `UPDATE_SHAPESHIFT_FORM`, `UPDATE_SHAPESHIFT_FORMS`, `ENCOUNTER_START`, `ENCOUNTER_END`, `UNIT_AURA`, `SPELL_UPDATE_COOLDOWN`, `SPELL_UPDATE_ICON`, `COOLDOWN_VIEWER_SPELL_OVERRIDE_UPDATED`, `SPELL_ACTIVATION_OVERLAY_GLOW_SHOW`, `SPELL_ACTIVATION_OVERLAY_GLOW_HIDE`, `SPELL_ACTIVATION_OVERLAY_SHOW`, `SPELL_ACTIVATION_OVERLAY_HIDE`, `UPDATE_BINDINGS`, `SPELLS_CHANGED`, `ACTIONBAR_HIDEGRID`, `ACTIONBAR_SHOWGRID`, `SPELL_UPDATE_CHARGES`

**关键事件处理函数**：

| 事件 | 函数 | 说明 |
|------|------|------|
| `UNIT_HEALTH` | `F:UNIT_HEALTH(_, unit)` | 玩家/目标/队伍血量更新 |
| `UNIT_MAXHEALTH` | `F:UNIT_MAXHEALTH(_, unit)` | 最大血量变化时更新 |
| `SPELL_UPDATE_COOLDOWN` | 遍历 spells 表 | 法术冷却更新 |
| `SPELL_UPDATE_CHARGES` | 遍历 spells 表 | 法术充能更新 |
| `SPELL_UPDATE_USES` | 遍历 spells 表 | 法术使用次数更新 |
| `UNIT_SPELLCAST_START` | `F:updatePlayerCastingInfo()` | 施法信息 |
| `UNIT_SPELLCAST_CHANNEL_START` | `F:updatePlayerChannelingInfo()` | 引导信息 |
| `UNIT_SPELLCAST_EMPOWER_START` | `F:updatePlayerEmpowerInfo()` | 蓄力信息 |
| `UNIT_SPELLCAST_SUCCEEDED` | `F:UNIT_SPELLCAST_SUCCEEDED()` | 施法成功处理 |
| `UNIT_SPELLCAST_FAILED` | `F:UNIT_SPELLCAST_FAILED()` | 施法失败处理 |
| `UNIT_AURA` | `F:UNIT_AURA(_, unit)` | 队伍成员光环变化 |
| `GROUP_ROSTER_UPDATE` | `F:GROUP_ROSTER_UPDATE()` | 队伍成员变化 |
| `PLAYER_TARGET_CHANGED` | `F:PLAYER_TARGET_CHANGED()` | 目标切换 |
| `PLAYER_REGEN_DISABLED/ENABLED` | 战斗状态更新 | 进出战斗 |
| `PLAYER_ENTERING_WORLD` | `F:PLAYER_ENTERING_WORLD()` | 进入世界初始化 |
| `PLAYER_DEAD/ALIVE/UNGHOST` | 死亡状态更新 | 死亡/复活 |
| `PLAYER_STARTED/STOPPED_MOVING` | 移动状态更新 | |
| `PLAYER_MOUNT_DISPLAY_CHANGED` | 坐骑状态更新 | |
| `UPDATE_SHAPESHIFT_FORM` | `F:UPDATE_SHAPESHIFT_FORM()` | 形态切换 |
| `ENCOUNTER_START/END` | Boss 战更新 | |
| `ZONE_CHANGED*` | `F:ZONE_CHANGED()` | 区域变化 |

**OnUpdate 帧循环**（`F:OnUpdate(elapsed)`）：

每帧执行（高频）：
- `updatePlayerCastingInfo()` — 施法信息（倒计时）
- `updatePlayerChannelingInfo()` — 引导信息（倒计时）
- `updatePlayerEmpowerInfo()` — 蓄力信息（层数）
- `updateGroupInRange()` — 队伍距离
- `updateAura()` — 光环剩余时间倒计时（遍历所有追踪的光环）

每 0.2 秒执行（低频，通过 `timeElapsed` 累加控制）：
- `updateSpellCooldown()` — 法术冷却
- `updateAuraBlocks()` — 光环像素更新
- `updatePlayerAssistant()` — 一键辅助
- `updateRune()` — 符文（死亡骑士）
- `updateTargetRangeBlock()` — 目标距离
- `updateEnemyCount()` — 敌人数量
- `updateItemCoolDown()` — 物品冷却

**其他关键函数**（main.lua）：

| 函数 | 说明 |
|------|------|
| `updatePlayerHealth()` | 更新玩家血量像素（通过 UnitHealthPercent + CreatTexture） |
| `updateTargetHealth()` | 更新目标血量像素 |
| `updateUnitHealthInfo(unit)` | 更新队伍成员血量（含 inComingHeals 和 healAbsorb 曲线） |
| `updateUnitDeathByHealthInfo(unit)` | 根据血量判断队伍成员死亡状态 |
| `CreatTexture(block, value)` | 将数值写入像素块（设置颜色） |
| `creatColorCurveScaling(b)` | 创建非线性颜色曲线（核心编码函数） |
| `GetCharacterSpecInfo()` | 获取角色专精信息 |
| `updateSpellKnown()` | 更新法术已知状态 |
| `updatePlayerBlocks()` | 更新玩家像素块布局 |
| `updateAuraIconByEnteringWorld()` | 进入世界时刷新光环 |

### config.lua — 配置数据

**核心数据表**：
- `Fuyutsui.spellsList` — 法术 ID → `{ index, failed?, name }` 映射，按职业分段
- `Fuyutsui.events` — 事件名称枚举
- `Fuyutsui.heroTalents` — 英雄天赋 `{ 1="名称A", 2="名称B", 3="名称C" }`
- `Fuyutsui.difficulty` — 难度 ID 映射
- `Fuyutsui.actionbar` — 动作条配置
- `Fuyutsui.keymap` — 按键映射表
- `Fuyutsui.classMap` — 职业名称/ID 映射
- `Fuyutsui.bossID` — Boss 编号映射（0=无, 1-13=团本, 51-79=大秘）
- `Fuyutsui.failed_spell_map` — 法术失败编码映射

### block.lua — 像素块创建

- `updatePlayerBlocks()` — 根据 config.yml 创建玩家状态像素块
- 创建 `FuyutsuiColorBars` Frame（255 个 2px 高的色块）
- 创建 `FuyutsuiCountBars` Frame（充能进度条）
- `CreateAutoLayoutBar()` — 自动布局法术充能/使用次数 StatusBar

### macro.lua — 宏系统

- 为每个技能创建带目标条件判断的动态宏
- 支持 `@raid`、`@party`、`@nogroup` 三种模式自动切换
- 斗篷状态变化时重建所有宏
- 斜杠命令 `/fu macro rebuild` 手动重建

### keybinds.lua — 按键绑定

- 扫描所有动作条的按键绑定
- 支持修饰键组合（CTRL/ALT/SHIFT × 36 个基础键）
- 生成 `Fuyutsui.keybindings` 表供 Python 端读取

### auras.lua — 光环状态机

- 按 `classId` 索引的光环定义表
- 每个光环追踪：`remaining`、`duration`、`expirationTime`、`count`、`countMin`、`countMax`
- 触发事件映射：`addAuras`、`updateAuras`、`removeAuras`
- 6 种事件类型：法术冷却、施法成功、图标改变、法术覆盖、屏幕提示显示/隐藏
- `updateAura()` 在 OnUpdate 中每帧倒计时
- `updateAuraBlocks()` 每 0.2 秒更新光环像素

### quickbutton.lua — 快捷按钮

- `InitQuickToggleButton()` — 创建单个切换按钮（原始实现）
- 点击切换爆发/AOE/输出模式
- 位置持久化到 SavedVariables

### gui.lua — 配置界面

- Ace3 AceConfigDialog 驱动
- `/fu gui` 打开像素块调试界面
- 显示所有像素索引对应的名称和当前值

### class/*.lua — 职业像素块布局

- 每个文件定义 `Fuyutsui.ClassBlocks[classId]` 表
- 表结构：`{ state = {...}, auras = {...}, spells = {...}, groups = {...} }`
- 定义了该职业需要编码到像素的所有状态、法术、光环、队伍信息

---

## 七、Python 端核心机制

### logic_gui_laoer.py — 主 GUI + 调度核心（1431 行）

**全局变量**：
- `_logic_modules` — 模块缓存 dict
- `_CLASS_ID_TO_MODULE` — 职业ID → 模块名映射
- `LOGIC_FUNCS_BY_CLASS` — 职业ID → 逻辑函数引用
- `TOGGLE_INTERVAL` = 0.05 — 按键检测休眠间隔（秒）
- `LOGIC_INTERVAL` = 0.2 — 状态扫描间隔（秒）
- `GUI_UPDATE_MS` = 100 — GUI 刷新间隔（毫秒）
- `_toggle_key_str` — 当前绑定按键（默认 "XBUTTON1"）
- `_send_mode` — 发送模式（switch/click/hold）
- `_state_lock` — 线程锁
- `_state_dict` — 最新游戏状态字典

**关键函数**：

| 函数 | 说明 |
|------|------|
| `_build_class_module_map()` | 从 config.yml + class/ 目录构建职业ID→模块名映射 |
| `_load_logic_module(name)` | 从缓存获取模块中的逻辑函数 |
| `reload_logic_modules()` | 热重载所有逻辑模块 |
| `_default_logic(state_dict, spec_name)` | 默认空逻辑（无匹配职业时使用） |
| `_get_config_cached()` | 缓存加载 config.yml |
| `get_group_config_for_class_spec(class_id, spec_id)` | 获取队伍表格配置 |
| `get_class_spec_view_data(class_id, spec_id)` | 聚合返回状态/队伍/法术配置 |
| `create_gui()` | **主函数**：创建 GUI，启动所有线程，进入 mainloop |

**线程模型**：
1. **按键检测线程** `_key_detect_loop()`：50ms 轮询，检测绑定按键状态
2. **逻辑执行线程** `_run_logic_loop()`：200ms 间隔，扫描状态→调用职业逻辑→发送按键
3. **主线程**：GUI mainloop，100ms 刷新状态面板

**GUI 结构**：
- 自定义标题栏（赛博朋克风格）
- 顶部面板：职业名称、专精、绑定按钮、重载按钮
- 状态面板：根据 config 动态生成键值对网格
- 冷却面板：根据 config spells 动态生成
- 队伍弹窗：Toplevel 窗口显示 group 数据
- 动画系统：背景呼吸、面板流光、标题闪烁

### GetPixels.py — 屏幕像素扫描引擎

**核心函数**：

| 函数 | 说明 |
|------|------|
| `get_info()` | 单次扫描，返回完整 state_dict |
| `scan_screen_data()` | 扫描指定区域像素数据 |

**扫描流程**：
1. 使用 `mss` 库截取屏幕顶部区域
2. 扫描顶部长条：逐像素读取 RGB 值
3. G 通道 = 索引，B 通道 = 数值（反算颜色曲线）
4. 扫描第二行充能进度条
5. 扫描左边界标记（红/白起始对）定位 bar 数据
6. 按 `config.yml` 定义的结构组装为 `state_dict`

### utils.py — 核心工具库

**配置函数**：

| 函数 | 说明 |
|------|------|
| `load_config()` | 加载 config.yml（会被 overrides.py monkey-patch） |
| `load_keymap()` | 加载按键映射 yml |
| `get_config_cached()` | 缓存版 load_config |

**查询函数**：

| 函数 | 说明 |
|------|------|
| `get_hotkey(unit, spell)` | 查找 (单位, 技能) 对应的按键 |
| `get_lowest_health_unit(state_dict, threshold)` | 找血量最低的队友 |
| `get_unit_with_dispel_type(state_dict, dispel_type)` | 找需要驱散的队友 |
| `count_units_below_health(state_dict, threshold)` | 统计低血量人数 |
| `get_group_config()` | 获取队伍配置 |
| `get_class_id()` | 获取当前职业 ID |

**按键函数**：

| 函数 | 说明 |
|------|------|
| `send_key_to_wow(hotkey, mode)` | 发送按键到 WoW（PostMessage） |
| `get_vk_by_name(key_str)` | 按键名称转虚拟键码 |
| `find_wow_hwnd()` | 查找 WoW 窗口句柄 |

**按键映射优先级**（高→低）：
1. FuyutsuiTools 的 `keymap.yml`
2. FuyutsuiTools 的 `keymap/<className>/` 目录
3. Fuyutsui 的 `keymap.yml`
4. Fuyutsui 的 `keymap/<className>/` 目录

### 职业逻辑模块统一接口

```python
def run_xxx_logic(state_dict: dict, spec_name: str) -> tuple:
    """
    参数:
        state_dict: 游戏状态字典（完整字段见第八节）
        spec_name: 专精名称 ("神圣", "防护", "惩戒", etc.)
    返回:
        action_hotkey: 要发送的按键字符串，或 None 表示无操作
        current_step: 当前步骤描述字符串（用于 GUI 显示）
        unit_info: 附加信息字典（用于 GUI 显示）
    """
```

所有 12 个职业逻辑文件都遵循此接口。内部通常使用 `if/elif` 优先级链：
1. 检查死亡/聊天框打开/坐骑等跳过条件
2. 检查爆发/AOE/驱散等高优先级操作
3. 检查目标条件（距离、类型）
4. 按优先级匹配法术（通过 `spells["法术名"] == 0` 判断就绪）
5. 使用 `get_hotkey(单位, 法术名)` 获取按键

---

## 八、状态数据结构

### Lua 端全局表

```lua
Fuyutsui.state = { classId, className, classFilename, specName, specID, ... }

Fuyutsui.blocks = {
    state = { ["生命值"] = index, ["爆发开关"] = index, ... },    -- 玩家状态像素索引
    auras = { [slotIndex] = { auraName, showKey } },              -- 光环像素索引
    spells = { [spellID] = { index, name, charge, inSpellBook } }, -- 法术冷却像素索引
    groups = { start, num, healthPercent, role, dispel, auras },   -- 队伍像素布局
}

Fuyutsui.target = { healthPercent, ... }
Fuyutsui.group = { [unit] = { index, healthPercent, role, dispel, curve, ... } }
```

### Python 端 state_dict（扫描结果）

```python
state_dict = {
    "职业": int,          # 职业ID (1=战士, 2=圣骑士, ..., 13=唤魔师)
    "专精": str,          # 专精名称
    "生命值": float,      # 玩家血量百分比
    "能量值": float,      # 玩家能量百分比
    "战斗": bool,         # 是否在战斗
    "移动": bool,         # 是否在移动
    "施法": int,          # 施法状态 (0=未施法, >0=施法中)
    "引导": int,          # 引导状态
    "蓄力": int,          # 蓄力层数
    "目标类型": int,      # 0=无目标, 1-3=敌对, 12-15=友方可驱散
    "目标距离": int,      # 到目标距离（码）
    "目标生命值": float,  # 目标血量百分比
    "爆发开关": int,      # 0/1
    "AOE开关": int,       # 0=自动, 1=单体
    "输出模式": int,      # 0=一键辅助, 1=手写逻辑
    "延迟": int,          # 逻辑延迟标志
    "敌人人数": int,      # 周围敌人数量
    "队伍类型": int,      # 0=单人, 1-40=团本, 46=大秘
    "队伍人数": int,
    "首领战": int,        # Boss ID
    "难度": int,          # 副本难度
    "英雄天赋": int,      # 英雄天赋编号
    "一键辅助": int,
    "法术失败": int,      # 0=无失败, 1~N=对应 failed_spell_map
    "spells": { "法术名": 冷却值 },  # 0=就绪, >0=冷却中
    "驱散开关": int,      # 0=关闭, 1=开启 (FuyutsuiTools 扩展)
    "group": {
        "1": { "生命值": float, "驱散": int, "角色": int, ... },
        ...
    }
}
```

---

## 九、关键约定

1. **像素索引**：config.yml 中定义的索引直接对应屏幕顶部第 N 个像素的 G 通道值
2. **法术失败**：`法术失败` 状态值 1~N 对应 `failed_spell_map` 表中的法术，值为 0 表示无失败
3. **目标类型**编码：
   - 0 = 无目标
   - 1~3 = 敌对（可攻击）
   - 12 = 友方有魔法 debuff
   - 13 = 友方有疾病 debuff
   - 14 = 诅咒（视职业而定）
   - 15 = 友方有毒素 debuff
4. **队伍类型**编码：0=单人, 1-40=团本(人数), 46=大秘
5. **冷却值**：0 = 就绪，1~254 = 冷却中（近似秒数），255 = 不存在/不可用
6. **英雄天赋**：1/2/3 对应三个英雄天赋树（具体名称见 config.lua 的 `heroTalents` 表）
7. **Boss ID**：0 = 未战斗，1~13 = 团本Boss，51~79 = 大秘Boss
8. **职业ID**：1=战士, 2=圣骑士, 3=猎人, 4=盗贼, 5=牧师, 6=死亡骑士, 7=萨满, 8=法师, 9=术士, 10=武僧, 11=德鲁伊, 12=恶魔猎手, 13=唤魔师

---

## 十、FuyutsuiTools 覆盖机制

### Lua 端覆盖

FuyutsuiTools 的 Lua 文件在主插件之后加载，通过以下方式覆盖：

1. **保存原始函数引用**：`local origOnUpdate = F.OnUpdate`
2. **覆盖函数**：`function F:OnUpdate(elapsed) ... origOnUpdate(self, elapsed) end`
3. **调用原始函数**：在覆盖函数末尾调用 `origXxx(self, ...)`

已实现的覆盖：

| 文件 | 覆盖函数 | 说明 |
|------|---------|------|
| `init.lua` | `F:OnEnable` | 进入世界时重新初始化（守卫防重复，仅执行一次） |
| `main.lua` | `F:OnUpdate` | 血量实时轮询（0.2秒，非团本时启用） |
| `core\core.lua` | `F:SwitchDispel` | 驱散开关切换（0/1，写入 db.char.dispel + 像素） |
| `core\core.lua` | `F:updatePlayerConfig` | 初始化时读取并显示驱散开关状态 |
| `core\quickbutton.lua` | `F:InitQuickToggleButton` | 隐藏原按钮，创建四按钮可拖拽面板 |

### Python 端覆盖

通过 `overrides.py` 实现：

1. **模块级替换**：`import_with_override(module_name)` 优先从 FuyutsuiTools 加载同名模块
2. **配置深度合并**：Monkey-patch `utils.load_config()` 和 `utils.load_keymap()`
3. **逻辑包装**：覆盖模块先 `importlib.import_module` 加载原始模块，包装后暴露同名函数

已实现的覆盖：

| 文件 | 覆盖内容 |
|------|---------|
| `overrides.py` | config 深度合并 + keymap 合并 + 模块覆盖加载 |
| `class/paladin_logic.py` | 驱散开关（临时移除驱散字段）+ 制裁之锤固定按键 |

---

## 十一、驱散开关机制详解

FuyutsuiTools 新增的驱散开关是跨越 Lua/Python 双层的功能：

### Lua 端（存储 + 显示）
- `class/Paladin.lua`：在神圣专精的 `ClassBlocks` 中添加 `"驱散开关"` 像素块
- `core/core.lua`：
  - `SwitchDispel()` — 切换 0/1，写入 `db.char.dispel`，更新像素块
  - `updatePlayerConfig()` — 覆盖原函数，初始化时读取并显示
- `core/quickbutton.lua`：四按钮面板中添加"驱散"按钮

### Python 端（决策拦截）
- `FuyutsuiTools/Fuyutsui/class/paladin_logic.py`：
  - 覆盖 `run_paladin_logic`
  - 驱散开关关闭时，**调用前**临时移除 `group` 中所有单位的 `"驱散"` 字段
  - 原始逻辑中 `get_unit_with_dispel_type()` 找不到可驱散单位 → `elif` 链自然跳过队友驱散
  - 调用完原始逻辑后，恢复被移除的驱散字段
  - **目标驱散不受影响**（只依赖 `目标类型`，不依赖 group 数据）

---

## 十二、四按钮面板（quickbutton.lua 覆盖）

覆盖 `F:InitQuickToggleButton`，隐藏原始单按钮，创建可拖拽四按钮面板：

| 按钮 | 功能 | 对应函数 |
|------|------|---------|
| 爆发 | 切换爆发开关 | `F:SwitchCooldown()` |
| 自动/单体 | 切换 AOE 模式 | `F:SwitchAoeMode()` |
| 逻辑/辅助 | 切换输出模式 | `F:SwitchDpsMode()` |
| 驱散 | 切换驱散开关 | `F:SwitchDispel()` |

特性：
- 可拖拽，位置持久化到 `db.char.quickButtonCX/Y`
- 右键点击按钮进入按键绑定模式
- `switchButtonRegistry` 表管理所有按钮

---

## 十三、血量实时轮询（main.lua 覆盖）

覆盖 `F:OnUpdate`，添加血量高频轮询：

- **间隔**：0.2 秒（`HEALTH_INTERVAL`）
- **范围**：非团本时启用（`pollHealth = (instanceType ~= "raid")`）
- **更新内容**：`updatePlayerHealth()` + `updateTargetHealth()` + 遍历 `self.group` 更新队伍
- **团本时**：禁用轮询，依赖原始 `UNIT_HEALTH` 事件驱动，节省性能
- **区域切换**：监听 `PLAYER_ENTERING_WORLD` 和 `ZONE_CHANGED_NEW_AREA` 刷新 `pollHealth`

---

## 十四、按键发送机制

Python 通过 `PostMessage(WM_KEYDOWN/WM_KEYUP)` 向 WoW 窗口发送按键：

| 模式 | 说明 |
|------|------|
| `switch` | 模拟按键按下+释放（默认） |
| `click` | 模拟鼠标点击 |
| `hold` | 按住不放（用于持续施法） |

按键映射查找：`get_hotkey(unit, spell)` → 从合并后的 keymap 中查找 `(单位, 技能)` 对应的按键字符串。

---

## 十五、添加新职业逻辑的步骤

### Lua 端

1. 创建 `class/NewClass.lua`，定义 `Fuyutsui.ClassBlocks[classId]` 表
2. 在 `Fuyutsui.toc` 中添加 `class\NewClass.lua`
3. 在 `core\config.lua` 的 `spellsList` 中添加该职业的法术 ID → index 映射
4. 在 `core\config.lua` 的 `heroTalents` 中添加英雄天赋映射

### Python 端

1. 创建 `Fuyutsui/class/newclass_logic.py`，实现 `run_newclass_logic(state_dict, spec_name)`
2. 按 config.yml 自动发现（或手动在 `_build_class_module_map` 中注册）
3. 在 `Fuyutsui/class/` 目录创建 `config.yml`（定义该职业的像素块配置）

### FuyutsuiTools 端（可选）

1. 创建 `FuyutsuiTools/class/NewClass.lua` 扩展像素块
2. 创建 `FuyutsuiTools/Fuyutsui/class/newclass_logic.py` 覆盖逻辑

---

## 十六、开发规范（必读）

> 以下规则在 FuyutsuiTools 中添加任何新功能时**必须遵守**。

### 通用规则

1. **不修改主插件源码**：所有功能通过覆盖机制实现，绝不直接编辑 `Fuyutsui/` 下的文件
2. **中文命名**：像素块名称、状态字段、GUI 文本统一使用中文（如 `"驱散开关"`、`"生命值"`）
3. **保存原始引用**：覆盖任何函数前必须先保存：`local origXxx = F.Xxx`
4. **调用原始函数**：覆盖函数末尾必须调用 `origXxx(self, ...)` 保留原有行为
5. **新功能放 main.lua**：帧循环相关的覆盖统一放在 `main.lua`，不要塞进 `core.lua`

### Lua 端规则

```lua
-- 正确的覆盖模板：
local F = Fuyutsui
local origXxx = F.Xxx      -- 1. 保存原始引用

function F:Xxx(...)         -- 2. 覆盖函数
    -- 新逻辑写在这里
    return origXxx(self, ...)  -- 3. 调用原始函数
end
```

- **像素块写入**：使用 `self:CreatTexture(block, value)`，value 范围 0~1
- **SavedVariables**：新增持久化数据放在 `F.db.char` 下，需在 `core/core.lua` 中 `RegisterDefaults`
- **像素索引分配**：新增像素块时索引不能与 config.yml 中已有的冲突，建议从 150+ 开始
- **TOC 加载顺序**：`init.lua` 最先（覆盖 OnEnable）→ `main.lua`（覆盖 OnUpdate）→ `core/*.lua` → `class/*.lua`

### Python 端规则

```python
# 正确的覆盖模板：
import importlib
_orig = importlib.import_module(f"class.paladin_logic")
_orig_run = _orig.run_paladin_logic

def run_paladin_logic(state_dict, spec_name):
    # 新逻辑（拦截/修改/扩展）
    result = _orig_run(state_dict, spec_name)
    return result
```

- **配置合并**：FuyutsuiTools 的 `config.yml` 会自动与主插件深度合并，只需写差异部分
- **按键映射**：FuyutsuiTools 的 `keymap.yml` 优先级高于主插件
- **职业逻辑返回值**：必须返回 `(action_hotkey, current_step, unit_info)` 三元组，无操作时 `action_hotkey = None`
- **工具函数**：优先使用 `utils.py` 中的 `get_hotkey()`、`get_lowest_health_unit()` 等，不要重复造轮子

### 添加新功能的检查清单

| 步骤 | 说明 |
|------|------|
| 1 | 读 README.md 了解完整架构 |
| 2 | 确定是纯 Lua 功能还是需要 Lua + Python 双端配合 |
| 3 | 纯 Lua：按覆盖模板写代码，放入对应文件（帧相关→main.lua，初始化→init.lua，开关→core/core.lua） |
| 4 | 双端：Lua 端添加像素块编码，Python 端在 `overrides.py` 注册覆盖模块 |
| 5 | 更新 `FuyutsuiTools.toc`（如新增文件） |
| 6 | 更新本 README.md 对应章节 |

### 常见陷阱

- **elif 链无法回退**：原始职业逻辑的 `if/elif` 是一次性执行的，事后修改返回值无法让逻辑继续走下一个分支。如需跳过某个优先级，必须在调用前修改 `state_dict` 中的数据
- **线程安全**：Python 端按键检测和逻辑执行在不同线程，访问 `_state_dict` 时注意 `_state_lock`
- **团本性能**：遍历队伍成员的轮询逻辑在 40 人团时开销大，建议加实例类型判断（`instanceType ~= "raid"`）
- **WoW API 限制**：`UnitHealthPercent` 等查询 API 有客户端频率限制，不适合每帧调用，应使用 `OnUpdate` + 时间累加器节流

---

## 十七、调试技巧

- **Lua 像素调试**：`/fu gui` 打开像素块调试界面，查看所有像素索引的名称和当前值
- **Lua 斜杠命令**：`/fu message 测试消息` — 向聊天框发送测试文本
- **Lua 秘密值**：`/script SetTestSecret(0)` 关闭秘密值限制
- **Python 像素颜色**：`other/GetRGB.py` 获取鼠标位置像素 RGB 值
- **Python 热重载**：GUI 中的"重载"按钮重新加载所有模块
- **Python 信息调试**：`other/GetInfo.py` 获取完整 state_dict
