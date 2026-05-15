if UnitClassBase("player") ~= "PALADIN" then return end

-- 为所有圣骑士专精添加驱散开关像素块（index 47）
if Fuyutsui.ClassBlocks then
    for spec = 1, 3 do
        if Fuyutsui.ClassBlocks[spec] then
            Fuyutsui.ClassBlocks[spec][47] = { type = "block", name = "驱散开关" }
        end
    end
end
