-- ============================================================================
-- 覆盖 Fuyutsui 核心逻辑
-- ============================================================================

local F = Fuyutsui

-- 注册驱散开关默认值
if F.db then
    F.db:RegisterDefaults({
        char = {
            dispel = 1,
        }
    })
end

-- 覆盖 SwitchDispel：驱散开关（主插件无此函数，纯扩展）
function F:SwitchDispel()
    local c = self.db and self.db.char
    if not c then return end
    if c.dispel == 0 then
        print("|cff00ff00[Fuyutsui]|r 驱散已|cffff0000关闭|r")
    else
        print("|cff00ff00[Fuyutsui]|r 驱散已|cff00ff00开启|r")
    end
    -- 同步到像素条，供 Python 端读取
    if self.blocks and self.blocks.state and self.blocks.state["驱散开关"] then
        self:CreatTexture(self.blocks.state["驱散开关"], (c.dispel or 1) / 255)
    end
end

-- 覆盖 updatePlayerConfig：初始化时也写入驱散开关像素
local origUpdatePlayerConfig = F.updatePlayerConfig
function F:updatePlayerConfig()
    origUpdatePlayerConfig(self)
    local c = self.db and self.db.char
    if not c or not self.blocks then return end
    if self.blocks.state["驱散开关"] then
        self:CreatTexture(self.blocks.state["驱散开关"], (c.dispel or 1) / 255)
    end
end
