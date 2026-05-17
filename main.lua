-- ============================================================================
-- 实时血量更新：覆盖 OnUpdate，将血量加入高频轮询（0.1秒间隔）
-- ============================================================================

local F = Fuyutsui

local origOnUpdate = F.OnUpdate
local healthElapsed = 0
local HEALTH_INTERVAL = 0.2

function F:OnUpdate(elapsed)
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

    -- 调用原始 OnUpdate（施法、引导、光环等）
    origOnUpdate(self, elapsed)
end
