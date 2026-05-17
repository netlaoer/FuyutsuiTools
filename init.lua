local F = Fuyutsui

local origOnEnable = F.OnEnable
local overrideApplied = false

function F:OnEnable(...)
    origOnEnable(self, ...)
    if overrideApplied then return end
    overrideApplied = true
    self:GetCharacterSpecInfo()
    self:updateSpellKnown()
    self:updatePlayerBlocks()
    self:updateAuraIconByEnteringWorld()
end
