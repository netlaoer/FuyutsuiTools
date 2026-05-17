if UnitClassBase("player") ~= "PALADIN" then return end

-- 为所有圣骑士专精添加驱散开关像素块
if Fuyutsui.ClassBlocks then
    local steps = { [1] = 48, [2] = 51, [3] = 48 }
    for spec = 1, 3 do
        if Fuyutsui.ClassBlocks[spec] then
            Fuyutsui.ClassBlocks[spec][steps[spec]] = { type = "block", name = "驱散开关" }
        end
    end
end
