if UnitClassBase("player") ~= "PALADIN" then return end

-- 为所有圣骑士专精添加驱散开关像素块（index 47）
if Fuyutsui.ClassBlocks then
    for spec = 1, 3 do
        if Fuyutsui.ClassBlocks[spec] then
            Fuyutsui.ClassBlocks[spec][47] = { type = "block", name = "驱散开关" }
        end
    end
end
-- 驱散宏（unit 0 直接对当前目标施放）
if Fuyutsui.MacrosList then
    Fuyutsui.MacrosList.staticSpells[41] = "清毒术"
end