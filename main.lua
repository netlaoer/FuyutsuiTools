-- ============================================================================
-- 实时血量更新：覆盖 OnUpdate，将血量加入高频轮询（0.2秒间隔）
-- 仅在大秘境/5人本/单人场景下轮询；团本使用事件驱动更新
-- ============================================================================

local F = Fuyutsui

local origOnUpdate = F.OnUpdate
local healthElapsed = 0
local HEALTH_INTERVAL = 0.2

-- 缓存实例类型，避免每帧调用 GetInstanceInfo
local pollHealth = true

local function UpdatePollState()
    local _, instanceType = GetInstanceInfo()
    -- raid 时禁用轮询，依赖事件驱动；其余场景（party/none/pvp/arena）启用
    pollHealth = (instanceType ~= "raid")
end

-- 区域切换时刷新缓存
local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
eventFrame:RegisterEvent("ZONE_CHANGED_NEW_AREA")
eventFrame:SetScript("OnEvent", UpdatePollState)

-- 初始化
UpdatePollState()

function F:OnUpdate(elapsed)
    if pollHealth then
        healthElapsed = healthElapsed + elapsed
        if healthElapsed >= HEALTH_INTERVAL then
            healthElapsed = 0
            self:updatePlayerHealth()
            self:updateTargetHealth()
            if self.blocks and self.blocks.groups then
                for unit in pairs(self.group or {}) do
                    self:updateUnitHealthInfo(unit)
                end
            end
        end
    else
        -- 团本：重置计时器，避免切回5人本时立即触发大量更新
        healthElapsed = 0
    end

    -- 调用原始 OnUpdate（施法、引导、光环等）
    origOnUpdate(self, elapsed)
end
