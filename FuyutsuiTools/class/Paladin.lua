if UnitClassBase("player") ~= "PALADIN" then return end

-- 仅神圣专精添加驱散开关像素块
if Fuyutsui.ClassBlocks and Fuyutsui.ClassBlocks[1] then
    Fuyutsui.ClassBlocks[1][48] = { type = "block", name = "驱散开关" }
end
