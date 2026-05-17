-- ============================================================================
-- 覆盖 Fuyutsui quickbutton.lua — 面板替代
-- ============================================================================

local F = Fuyutsui

local switchButtonRegistry = {}
local pendingBindButton = nil
local bindBtnRegistry = {}
local boundKeys = {}
local bindEditBox = nil

local function CharCfg()
    return F.db and F.db.char
end

local function updateSwitchButtons()
    for _, v in pairs(switchButtonRegistry) do
        local btn, opt = v.btn, v.opt
        local onText, offText = opt.onText or "ON", opt.offText or "OFF"
        local curState = opt.getter()
        if curState then
            btn:SetText(onText)
            if btn.Left then btn.Left:SetDesaturated(false) end
            if btn.Middle then btn.Middle:SetDesaturated(false) end
            if btn.Right then btn.Right:SetDesaturated(false) end
        else
            btn:SetText(offText)
            if btn.Left then btn.Left:SetDesaturated(true) end
            if btn.Middle then btn.Middle:SetDesaturated(true) end
            if btn.Right then btn.Right:SetDesaturated(true) end
        end
    end
end

local function createSwitchButton(opt)
    local name = opt.name
    local parent = opt.parent
    local onText, offText = opt.onText, opt.offText
    local w, h = opt.width or 60, opt.height or 20
    local anchor = opt.anchor
    local stateGet, stateSet = opt.getter, opt.setter

    local btn = CreateFrame("Button", name, parent, "UIPanelButtonTemplate")
    btn:SetWidth(w)
    btn:SetHeight(h)
    btn:SetPoint(unpack(anchor))
    btn:SetText(onText)
    btn:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    btn:SetScript("OnClick", function(self, mouseBtn)
        if mouseBtn == "RightButton" then
            pendingBindButton = name
            print("|cFFFFD700Fuyutsui|r: 按下要绑定的按键 (ESC取消), 不支持修饰键和组合")
            bindEditBox:Show()
            bindEditBox:SetFocus()
            return
        end
        local curState = stateGet()
        stateSet(not curState)
        updateSwitchButtons()
    end)

    local bindBtn = CreateFrame("Button", name .. "Bind")
    bindBtn:RegisterForClicks("AnyDown")
    bindBtn:SetScript("OnClick", function()
        local curState = stateGet()
        stateSet(not curState)
        updateSwitchButtons()
    end)
    bindBtnRegistry[name] = bindBtn
    switchButtonRegistry[name] = { btn = btn, opt = opt }

    if opt.tip then
        btn:SetScript("OnEnter", function(self)
            GameTooltip:SetOwner(self, "ANCHOR_TOPRIGHT")
            local tipText = opt.tip
            local savedKey = boundKeys[name]
            if savedKey then
                tipText = tipText .. "\n|cFFFFD700快捷键: " .. savedKey .. "|r"
            else
                tipText = tipText .. "\n|cFF888888右键点击绑定快捷键|r"
            end
            GameTooltip:AddLine(tipText)
            GameTooltip:Show()
        end)
        btn:SetScript("OnLeave", function(self)
            GameTooltip:Hide()
        end)
    end

    return btn
end

-- 覆盖 InitQuickToggleButton：隐藏原按钮，创建新面板
function F:InitQuickToggleButton()
    -- 注册面板位置字段到 AceDB，确保重载后持久化
    if self.db then
        self.db:RegisterDefaults({
            char = {
                panelPoint = nil,
                panelRelPoint = nil,
                panelX = nil,
                panelY = nil,
                dispel = 1,
            }
        })
    end

    -- 隐藏原 quickbutton
    if self.quickToggleFrame then
        self.quickToggleFrame:Hide()
        self.quickToggleFrame:SetScript("OnShow", nil)
    end
    if FuyutsuiQuickToggle then FuyutsuiQuickToggle:Hide() end
    -- 如果已创建过就不再重复创建
    if self._panelFrame then return end

    -- 面板
    local panelFrame = CreateFrame("Frame", "FuyutsuiPanel", UIParent, BackdropTemplateMixin and "BackdropTemplate")
    panelFrame:SetSize(130, 52)

    -- 恢复保存的位置
    local c = CharCfg()
    if c and c.panelPoint and c.panelX and c.panelY then
        panelFrame:SetPoint(c.panelPoint, UIParent, c.panelRelPoint or c.panelPoint, c.panelX, c.panelY)
    else
        panelFrame:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
    end

    panelFrame:SetBackdrop({
        bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true, tileSize = 16, edgeSize = 12,
        insets = { left = 2, right = 2, top = 2, bottom = 2 }
    })
    panelFrame:SetBackdropColor(0, 0, 0, 0.5)
    panelFrame:SetBackdropBorderColor(0.3, 0.3, 0.3, 0.8)
    panelFrame:SetMovable(true)
    panelFrame:SetClampedToScreen(true)
    panelFrame:SetFrameStrata("LOW")

    local function SavePanelPosition()
        local ch = CharCfg()
        if not ch then return end
        local p, _, rp, x, y = panelFrame:GetPoint(1)
        if p and x and y then
            ch.panelPoint = p
            ch.panelRelPoint = rp or p
            ch.panelX = x
            ch.panelY = y
        end
    end

    panelFrame:SetScript("OnMouseDown", function() panelFrame:StartMoving() end)
    panelFrame:SetScript("OnMouseUp", function()
        panelFrame:StopMovingOrSizing()
        SavePanelPosition()
    end)

    -- 显示/隐藏按钮
    local controlButton = CreateFrame("Button", "FuyutsuiControlButton", UIParent, "UIPanelButtonTemplate")
    controlButton:SetSize(30, 18)
    controlButton:SetPoint("TOP", panelFrame, "BOTTOM", 0, 0)
    controlButton:SetFrameStrata("LOW")
    controlButton:SetText("隐")
    controlButton:SetNormalFontObject("GameFontNormalSmall")
    controlButton:SetHighlightFontObject("GameFontHighlightSmall")
    controlButton:SetScript("OnClick", function()
        if panelFrame:IsShown() then
            panelFrame:Hide()
            controlButton:SetText("显")
        else
            panelFrame:Show()
            controlButton:SetText("隐")
        end
    end)
    panelFrame:Show()

    -- 快捷键绑定 EditBox
    bindEditBox = CreateFrame("EditBox", "FuyutsuiBindEditBox", UIParent)
    bindEditBox:Hide()
    bindEditBox:SetAutoFocus(false)
    bindEditBox:SetWidth(0)
    bindEditBox:SetHeight(0)
    bindEditBox:SetScript("OnKeyDown", function(self, key)
        if not pendingBindButton then
            self:ClearFocus()
            self:Hide()
            return
        end
        if key == "LSHIFT" or key == "RSHIFT" or key == "LCTRL" or key == "RCTRL"
            or key == "LALT" or key == "RALT" then
            print("|cFFFFD700Fuyutsui|r: 不支持修饰键，请只按普通键")
            return
        end
        if IsShiftKeyDown() or IsControlKeyDown() or IsAltKeyDown() then
            print("|cFFFFD700Fuyutsui|r: 不支持修饰键组合，请只按普通键")
            return
        end
        local btnName = pendingBindButton
        pendingBindButton = nil
        self:ClearFocus()
        self:Hide()
        local bindBtn = bindBtnRegistry[btnName]
        if key == "ESCAPE" then
            if bindBtn then ClearOverrideBindings(bindBtn) end
            boundKeys[btnName] = nil
            print("|cFFFFD700Fuyutsui|r: 快捷键已清除")
            return
        end
        if not bindBtn then return end
        ClearOverrideBindings(bindBtn)
        SetOverrideBindingClick(bindBtn, false, key, btnName .. "Bind", "LeftButton")
        boundKeys[btnName] = key
        print("|cFFFFD700Fuyutsui|r: " .. key .. " 已绑定")
    end)
    bindEditBox:SetScript("OnEscapePressed", function(self)
        if pendingBindButton then
            local btnName = pendingBindButton
            pendingBindButton = nil
            self:ClearFocus()
            self:Hide()
            local bindBtn = bindBtnRegistry[btnName]
            if bindBtn then ClearOverrideBindings(bindBtn) end
            boundKeys[btnName] = nil
            print("|cFFFFD700Fuyutsui|r: 快捷键已清除")
        end
    end)

    -- 三个按钮
    local btnCD = createSwitchButton({
        name = "FuyutsuiCDButton",
        parent = panelFrame,
        onText = "爆发",
        offText = "爆发",
        width = 60, height = 20,
        anchor = { "TOPLEFT", panelFrame, "TOPLEFT", 4, -4 },
        tip = "切换爆发开关",
        getter = function() return (CharCfg().cooldowns or 0) == 1 end,
        setter = function(v)
            CharCfg().cooldowns = v and 1 or 0
            F:SwitchCooldown()
        end,
    })

    createSwitchButton({
        name = "FuyutsuiAOEButton",
        parent = panelFrame,
        onText = "自动",
        offText = "单体",
        width = 60, height = 20,
        anchor = { "LEFT", btnCD, "RIGHT", 0, 0 },
        tip = "切换AOE/单体模式",
        getter = function() return (CharCfg().aoeMode or 0) == 0 end,
        setter = function(v)
            CharCfg().aoeMode = v and 0 or 1
            F:SwitchAoeMode()
        end,
    })

    createSwitchButton({
        name = "FuyutsuiDPSButton",
        parent = panelFrame,
        onText = "逻辑",
        offText = "辅助",
        width = 60, height = 20,
        anchor = { "TOPLEFT", btnCD, "BOTTOMLEFT", 0, -2 },
        tip = "切换逻辑/辅助输出模式",
        getter = function() return (CharCfg().dpsMode or 0) == 1 end,
        setter = function(v)
            CharCfg().dpsMode = v and 1 or 0
            F:SwitchDpsMode()
        end,
    })

    createSwitchButton({
        name = "FuyutsuiDispelButton",
        parent = panelFrame,
        onText = "驱散",
        offText = "驱散",
        width = 60, height = 20,
        anchor = { "LEFT", btnCD, "RIGHT", 0, -22 },
        tip = "切换驱散开关",
        getter = function() return (CharCfg().dispel or 1) == 1 end,
        setter = function(v)
            CharCfg().dispel = v and 1 or 0
            F:SwitchDispel()
        end,
    })

    self._panelFrame = panelFrame

    -- 每 0.5s 刷新按钮状态
    local monitorFrame = CreateFrame("Frame")
    monitorFrame:SetScript("OnUpdate", function(self, elapsed)
        self.elapsed = (self.elapsed or 0) + elapsed
        if self.elapsed >= 0.5 then
            self.elapsed = 0
            updateSwitchButtons()
        end
    end)
end
