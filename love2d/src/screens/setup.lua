local theme = require("src.ui.theme")
local ui = require("src.ui.widgets")
local constants = require("src.core.constants")

local SetupScreen = {}
SetupScreen.__index = SetupScreen

local PANEL_X, PANEL_Y = 16, 84
local ROSTER_W, PANEL_H = 860, 700
local COL_W = 400
local LEFT_X, RIGHT_X = 32, 460
local ADD_Y = 166
local LIST_Y = 210
local LIST_H = 550
local ROW_H = 56

local GRID_PRESETS = {
  { label = "Small (16 x 10)", w = 16, h = 10 },
  { label = "Standard (20 x 14)", w = 20, h = 14 },
  { label = "Large (28 x 18)", w = 28, h = 18 },
}

local function quickAC(data)
  local ac = data.armor_class or {}
  local dex = math.floor(((tonumber(data.ability_scores and data.ability_scores.dexterity) or 10) - 10) / 2)
  local size = constants.sizeData(data.size or "Medium")
  local total = 10 + dex + size.attackMod
  total = total + (tonumber(ac.armor_bonus) or 0)
  total = total + (tonumber(ac.shield_bonus) or 0)
  total = total + (tonumber(ac.natural_armor_bonus) or 0)
  total = total + (tonumber(ac.deflection_bonus) or 0)
  total = total + (tonumber(ac.dodge_bonus) or 0)
  total = total + (tonumber(ac.size_modifier) or 0)
  local maxDex = tonumber(ac.max_dex_bonus_from_armor)
  if maxDex and dex > maxDex then
    total = total - (dex - maxDex)
  end
  return total
end

local function copyRosterEntry(entry)
  return {
    key = entry.key,
    side = entry.side,
    potions = entry.potions,
  }
end

function SetupScreen.new(app)
  local self = setmetatable({}, SetupScreen)
  self.app = app
  self.roster = app:makeDefaultRoster()
  for _, entry in ipairs(self.roster) do
    if entry.side == "pc" then entry.potions = entry.potions or 2 end
  end
  self.gridW, self.gridH = 20, 14
  self.pillars = false
  self.pcsAware = true
  self.npcsAware = true
  self.scroll = { pc = 0, npc = 0 }
  self.addSelection = {}
  self.message = nil
  self.messageTimer = 0
  self.messageKind = "info"
  self._everEntered = false
  self:_buildWidgets()
  return self
end

function SetupScreen:enter(params)
  if not self._everEntered then
    self._everEntered = true
    self.pillars = self.app.settings.pillars == true
  end
  if params and params.entries then
    self.roster = {}
    for _, entry in ipairs(params.entries) do
      self.roster[#self.roster + 1] = copyRosterEntry(entry)
    end
  end
  self:_buildWidgets()
end

function SetupScreen:leave()
end

function SetupScreen:update(dt)
  if self.messageTimer > 0 then
    self.messageTimer = math.max(0, self.messageTimer - dt)
    if self.messageTimer == 0 then self.message = nil end
  end
end

function SetupScreen:_notify(text, kind)
  self.message = text
  self.messageKind = kind or "info"
  self.messageTimer = 4
end

function SetupScreen:_definitionNames()
  local names = {}
  for _, entry in ipairs(self.app.database:getDefinitions()) do
    names[#names + 1] = entry.data.name
  end
  return names
end

function SetupScreen:_gridLabel()
  for _, preset in ipairs(GRID_PRESETS) do
    if preset.w == self.gridW and preset.h == self.gridH then
      return preset.label
    end
  end
  return string.format("%d x %d", self.gridW, self.gridH)
end

function SetupScreen:_addButton(opts)
  local button = ui.Button.new(opts)
  self.buttons[#self.buttons + 1] = button
  return button
end

function SetupScreen:_addDropdown(opts)
  local dropdown = ui.Dropdown.new(opts)
  self.dropdowns[#self.dropdowns + 1] = dropdown
  return dropdown
end

function SetupScreen:_buildWidgets()
  self.buttons = {}
  self.dropdowns = {}

  local names = self:_definitionNames()

  local function buildColumn(side, colX, title, sideLabel)
    local addWidth = 246
    local dropdown = self:_addDropdown({
      x = colX, y = ADD_Y, w = addWidth, h = 32,
      items = names,
      value = self.addSelection[side],
      placeholder = "No statblocks available",
      font = "small",
      onChange = function(value) self.addSelection[side] = value end,
      tooltip = "Choose a statblock, then add it to this side.",
    })
    if not dropdown:getValue() and #names > 0 then
      dropdown:setValue(names[1])
      self.addSelection[side] = names[1]
    end
    self:_addButton({
      x = colX + 254, y = ADD_Y, w = 146, h = 32,
      label = "Add " .. sideLabel,
      style = "default",
      font = "smallBold",
      enabled = #names > 0,
      onClick = function()
        local name = dropdown:getValue()
        if not name then
          self:_notify("No statblock selected.", "error")
          return
        end
        self:_addEntry(side, name)
      end,
    })

    local entries = {}
    for _, entry in ipairs(self.roster) do
      if entry.side == side then entries[#entries + 1] = entry end
    end
    local offset = self.scroll[side] or 0
    for index, entry in ipairs(entries) do
      local rowY = LIST_Y + (index - 1) * ROW_H - offset
      if rowY >= LIST_Y and rowY + ROW_H <= LIST_Y + LIST_H then
        local data = self.app.database:get(entry.key)
        if data and entry.potions == nil and side == "pc" then
          entry.potions = 0
        end

        local buttonY = rowY + 15
        local right = colX + COL_W - 8
        self:_addButton({
          x = right - 26, y = buttonY, w = 24, h = 26,
          compact = true, label = "X", style = "ghost", font = "smallBold",
          tooltip = "Remove this combatant from the roster.",
          onClick = function() self:_removeEntry(entry) end,
        })
        right = right - 30
        self:_addButton({
          x = right - 26, y = buttonY, w = 24, h = 26,
          compact = true, label = "D", style = "ghost", font = "smallBold",
          tooltip = "Duplicate this roster entry.",
          onClick = function() self:_duplicateEntry(entry) end,
        })
        if side == "pc" then
          right = right - 30
          self:_addButton({
            x = right - 24, y = buttonY, w = 22, h = 26,
            compact = true, label = "+", style = "ghost", font = "smallBold",
            tooltip = "Add one healing potion.",
            onClick = function() self:_changePotions(entry, 1) end,
          })
          right = right - 26
          self:_addButton({
            x = right - 24, y = buttonY, w = 22, h = 26,
            compact = true, label = "-", style = "ghost", font = "smallBold",
            tooltip = "Remove one healing potion.",
            onClick = function() self:_changePotions(entry, -1) end,
          })
        end
      end
    end

    return #entries
  end

  local pcCount = buildColumn("pc", LEFT_X, "Heroes", "Hero")
  local npcCount = buildColumn("npc", RIGHT_X, "Monsters", "Monster")
  self.pcCount, self.npcCount = pcCount, npcCount

  self.gridDropdown = self:_addDropdown({
    x = 908, y = 166, w = 300, h = 34,
    items = (function()
      local labels = {}
      for _, preset in ipairs(GRID_PRESETS) do labels[#labels + 1] = preset.label end
      return labels
    end)(),
    value = self:_gridLabel(),
    font = "small",
    tooltip = "Battle grid dimensions. Each square is 5 feet.",
    onChange = function(value)
      for _, preset in ipairs(GRID_PRESETS) do
        if preset.label == value then
          self.gridW, self.gridH = preset.w, preset.h
          return
        end
      end
    end,
  })

  self.pillarsBox = ui.Checkbox.new({
    x = 908, y = 218, size = 20,
    label = "Scatter stone pillars (blocked squares)",
    checked = self.pillars,
    font = "small",
    onChange = function(value)
      self.pillars = value
      self.app.settings.pillars = value
    end,
  })
  self.pcAwareBox = ui.Checkbox.new({
    x = 908, y = 252, size = 20,
    label = "Heroes are aware (no surprise)",
    checked = self.pcsAware,
    font = "small",
    onChange = function(value) self.pcsAware = value end,
  })
  self.npcAwareBox = ui.Checkbox.new({
    x = 908, y = 286, size = 20,
    label = "Monsters are aware (no surprise)",
    checked = self.npcsAware,
    font = "small",
    onChange = function(value) self.npcsAware = value end,
  })
  self.autoNpcBox = ui.Checkbox.new({
    x = 908, y = 320, size = 20,
    label = "AI controls monsters in battle",
    checked = self.app.settings.autoNpc,
    font = "small",
    onChange = function(value) self.app.settings.autoNpc = value end,
  })

  self:_addButton({
    x = 672, y = 822, w = 116, h = 40,
    label = "Main Menu", style = "ghost", font = "smallBold",
    onClick = function() self.app:showMenu() end,
  })
  self:_addButton({
    x = 800, y = 822, w = 128, h = 40,
    label = "Bestiary", style = "default", font = "smallBold",
    tooltip = "Browse and edit statblocks.",
    onClick = function() self.app:showBestiary("setup") end,
  })
  self:_addButton({
    x = 940, y = 822, w = 148, h = 40,
    label = "New Monster", style = "default", font = "smallBold",
    tooltip = "Create a custom statblock for this encounter.",
    onClick = function() self.app:showCreator({ returnTo = "setup" }) end,
  })
  self:_addButton({
    x = 1100, y = 822, w = 136, h = 40,
    label = "Reset", style = "default", font = "smallBold",
    tooltip = "Restore the default roster.",
    onClick = function() self:_resetRoster() end,
  })
  self:_addButton({
    x = 1248, y = 822, w = 160, h = 40,
    label = "Start Battle", style = "primary", font = "bodyBold",
    onClick = function() self:_startBattle() end,
  })
end

function SetupScreen:_addEntry(side, name)
  local found = self.app.database:findByName(name)
  if not found then
    self:_notify("Statblock not found: " .. tostring(name), "error")
    return
  end
  local entry = {
    key = found.key,
    side = side,
    potions = side == "pc" and 2 or 0,
  }
  self.roster[#self.roster + 1] = entry
  local entries = 0
  for _, e in ipairs(self.roster) do
    if e.side == side then entries = entries + 1 end
  end
  local maxScroll = math.max(0, entries * ROW_H - LIST_H)
  self.scroll[side] = maxScroll
  self:_buildWidgets()
  self:_notify(found.data.name .. " added to the " .. (side == "pc" and "heroes." or "monsters."), "info")
end

function SetupScreen:_duplicateEntry(entry)
  local copy = copyRosterEntry(entry)
  self.roster[#self.roster + 1] = copy
  self:_buildWidgets()
  self:_notify("Roster entry duplicated.", "info")
end

function SetupScreen:_removeEntry(entry)
  for index, candidate in ipairs(self.roster) do
    if candidate == entry then
      table.remove(self.roster, index)
      break
    end
  end
  self:_clampScroll()
  self:_buildWidgets()
end

function SetupScreen:_changePotions(entry, delta)
  entry.potions = math.max(0, math.min(9, (entry.potions or 0) + delta))
end

function SetupScreen:_clampScroll()
  for _, side in ipairs({ "pc", "npc" }) do
    local count = 0
    for _, entry in ipairs(self.roster) do
      if entry.side == side then count = count + 1 end
    end
    local maxScroll = math.max(0, count * ROW_H - LIST_H)
    self.scroll[side] = math.max(0, math.min(self.scroll[side] or 0, maxScroll))
  end
end

function SetupScreen:_resetRoster()
  self.roster = self.app:makeDefaultRoster()
  for _, entry in ipairs(self.roster) do
    if entry.side == "pc" then entry.potions = entry.potions or 2 end
  end
  self.scroll = { pc = 0, npc = 0 }
  self:_buildWidgets()
  self:_notify("Default roster restored.", "info")
end

function SetupScreen:_startBattle()
  local pcs, npcs = 0, 0
  local entries = {}
  for _, entry in ipairs(self.roster) do
    if self.app.database:get(entry.key) then
      entries[#entries + 1] = copyRosterEntry(entry)
      if entry.side == "pc" then pcs = pcs + 1 else npcs = npcs + 1 end
    end
  end
  if pcs == 0 or npcs == 0 then
    self:_notify("Add at least one hero and one monster before starting.", "error")
    return
  end
  self.app.settings.pillars = self.pillars
  self.app:showBattle({
    entries = entries,
    gridW = self.gridW,
    gridH = self.gridH,
    pillars = self.pillars,
    pcsAware = self.pcsAware,
    npcsAware = self.npcsAware,
    autoBattle = false,
  })
end

function SetupScreen:mousepressed(x, y, button)
  if button ~= 1 then return false end
  for _, dropdown in ipairs(self.dropdowns) do
    if dropdown:mousepressed(x, y, button) then return true end
  end
  for _, widget in ipairs({ self.pillarsBox, self.pcAwareBox, self.npcAwareBox, self.autoNpcBox }) do
    if widget:mousepressed(x, y, button) then return true end
  end
  for _, widget in ipairs(self.buttons) do
    if widget:mousepressed(x, y, button) then return true end
  end
  return false
end

function SetupScreen:mousereleased(x, y, button)
  for _, widget in ipairs(self.buttons) do
    widget:mousereleased(x, y, button)
  end
end

function SetupScreen:wheelmoved(dx, dy)
  if dy == 0 then return false end
  local mx, my = theme.mouseX or 0, theme.mouseY or 0
  if my >= LIST_Y and my <= LIST_Y + LIST_H then
    local side
    if mx >= LEFT_X and mx <= LEFT_X + COL_W then side = "pc" end
    if mx >= RIGHT_X and mx <= RIGHT_X + COL_W then side = "npc" end
    if side then
      local count = 0
      for _, entry in ipairs(self.roster) do
        if entry.side == side then count = count + 1 end
      end
      local maxScroll = math.max(0, count * ROW_H - LIST_H)
      self.scroll[side] = math.max(0, math.min(maxScroll,
        (self.scroll[side] or 0) - dy * ROW_H))
      self:_buildWidgets()
      return true
    end
  end
  return false
end

function SetupScreen:keypressed(key)
  if key == "escape" then
    self.app:showMenu()
    return true
  elseif key == "return" or key == "kpenter" then
    self:_startBattle()
    return true
  elseif key == "b" then
    self.app:showBestiary("setup")
    return true
  elseif key == "c" then
    self.app:showCreator({ returnTo = "setup" })
    return true
  end
  return false
end

function SetupScreen:textinput()
  return false
end

function SetupScreen:_summary()
  local pcHp, npcHp = 0, 0
  local pcAc, npcAc, pcN, npcN = 0, 0, 0, 0
  for _, entry in ipairs(self.roster) do
    local data = self.app.database:get(entry.key)
    if data then
      local hp = tonumber(data.max_hp) or 0
      local ac = quickAC(data)
      if entry.side == "pc" then
        pcHp, pcAc, pcN = pcHp + hp, pcAc + ac, pcN + 1
      else
        npcHp, npcAc, npcN = npcHp + hp, npcAc + ac, npcN + 1
      end
    end
  end
  return {
    pcHp = pcHp, npcHp = npcHp,
    pcAc = pcN > 0 and pcAc / pcN or 0,
    npcAc = npcN > 0 and npcAc / npcN or 0,
    pcN = pcN, npcN = npcN,
  }
end

function SetupScreen:_drawColumn(side, colX, title, count)
  local colors = theme.colors
  theme.drawText(title, colX, 138, "h3", colors.gold)
  theme.drawText(tostring(count) .. (count == 1 and " entry" or " entries"),
    colX + COL_W, 142, "tiny", colors.textMuted, "right")

  love.graphics.setColor(colors.border, 0.65)
  love.graphics.setLineWidth(1)
  love.graphics.line(colX, 158, colX + COL_W, 158)

  local sx, sy, sw, sh = love.graphics.getScissor()
  love.graphics.setScissor(colX - 4, LIST_Y, COL_W + 8, LIST_H)

  local entries = {}
  for _, entry in ipairs(self.roster) do
    if entry.side == side then entries[#entries + 1] = entry end
  end
  local offset = self.scroll[side] or 0
  local mouseX, mouseY = theme.mouseX or 0, theme.mouseY or 0

  for index, entry in ipairs(entries) do
    local rowY = LIST_Y + (index - 1) * ROW_H - offset
    if rowY > LIST_Y - ROW_H and rowY < LIST_Y + LIST_H then
      local data = self.app.database:get(entry.key)
      local rowX = colX
      local rowW = COL_W
      local hover = mouseX >= rowX and mouseX < rowX + rowW and
        mouseY >= rowY and mouseY < rowY + ROW_H - 4

      theme.setColor(index % 2 == 0 and colors.panelAlt or colors.panel, hover and 0.98 or 0.75)
      love.graphics.rectangle("fill", rowX, rowY, rowW, ROW_H - 4, 5, 5)
      theme.setColor(hover and colors.borderBright or colors.border, hover and 0.9 or 0.5)
      love.graphics.setLineWidth(1)
      love.graphics.rectangle("line", rowX + 0.5, rowY + 0.5, rowW - 1, ROW_H - 5, 4.5, 4.5)

      local name = data and data.name or "Missing statblock"
      local detail = "This entry could not be loaded."
      local nameColor = data and colors.text or colors.red
      if data then
        local kinds = tostring(data.size or "Medium") .. " " ..
          tostring(data.creature_type or "Humanoid")
        if side == "pc" then
          detail = string.format("HP %d | AC %d | %s | %d potions",
            tonumber(data.max_hp) or 0, quickAC(data),
            tostring(data.creature_type or "Humanoid"), entry.potions or 0)
        else
          detail = string.format("HP %d | AC %d | %s", tonumber(data.max_hp) or 0,
            quickAC(data), kinds)
        end
      end
      theme.drawText(theme.truncateText(name, theme.fonts.smallBold, rowW - 150),
        rowX + 10, rowY + 7, "smallBold", nameColor)
      theme.drawText(theme.truncateText(detail, theme.fonts.tiny, rowW - 150),
        rowX + 10, rowY + 30, "tiny", colors.textMuted)
    end
  end

  if #entries == 0 then
    theme.drawText("No combatants yet. Add one above.", colX + COL_W / 2,
      LIST_Y + 48, "small", colors.textMuted, "center")
  elseif #entries * ROW_H > LIST_H then
    local maxScroll = #entries * ROW_H - LIST_H
    local barH = math.max(24, LIST_H * (LIST_H / (#entries * ROW_H)))
    local barY = LIST_Y + (LIST_H - barH) * (offset / math.max(1, maxScroll))
    theme.setColor(colors.borderBright, 0.55)
    love.graphics.rectangle("fill", colX + COL_W + 3, barY, 3, barH, 1.5, 1.5)
  end

  if sx then
    love.graphics.setScissor(sx, sy, sw, sh)
  else
    love.graphics.setScissor()
  end
end

function SetupScreen:draw()
  local colors = theme.colors

  theme.drawText("Encounter Builder", 32, 22, "h1", colors.gold)
  theme.drawText("Assemble both sides, set the field, and roll initiative.",
    34, 60, "small", colors.textMuted)

  theme.drawPanel(PANEL_X, PANEL_Y, ROSTER_W, PANEL_H, {
    title = "Roster",
    titleFont = "h3",
  })
  self:_drawColumn("pc", LEFT_X, "Heroes", self.pcCount or 0)
  self:_drawColumn("npc", RIGHT_X, "Monsters", self.npcCount or 0)

  theme.drawPanel(892, PANEL_Y, 532, PANEL_H, {
    title = "Battlefield",
    titleFont = "h3",
  })

  theme.drawText("Grid size", 908, 143, "smallBold", colors.text)
  theme.drawText("Terrain", 908, 202, "smallBold", colors.text)

  love.graphics.setColor(colors.border, 0.6)
  love.graphics.setLineWidth(1)
  love.graphics.line(908, 360, 1408, 360)
  theme.drawText("Encounter Summary", 908, 374, "h3", colors.gold)

  local summary = self:_summary()
  local totalHp = math.max(1, summary.pcHp + summary.npcHp)
  theme.drawText(string.format("Heroes: %d    Monsters: %d", summary.pcN, summary.npcN),
    908, 408, "body", colors.text)

  theme.drawText(string.format("Hero hit points: %d", summary.pcHp),
    908, 440, "small", colors.textMuted)
  theme.drawBar(908, 460, 480, 12, summary.pcHp / totalHp, colors.green,
    { border = colors.border })
  theme.drawText(string.format("Monster hit points: %d", summary.npcHp),
    908, 482, "small", colors.textMuted)
  theme.drawBar(908, 502, 480, 12, summary.npcHp / totalHp, colors.red,
    { border = colors.border })

  theme.drawText(string.format("Average AC  Heroes %.1f   Monsters %.1f",
    summary.pcAc, summary.npcAc), 908, 526, "small", colors.text)

  local balance
  if summary.pcHp == 0 or summary.npcHp == 0 then
    balance = "Add combatants to both sides to begin."
  elseif summary.pcHp > summary.npcHp * 1.6 then
    balance = "The heroes hold a clear advantage in staying power."
  elseif summary.npcHp > summary.pcHp * 1.6 then
    balance = "The monsters look considerably tougher."
  else
    balance = "Both sides look closely matched."
  end
  theme.drawText(balance, 908, 552, "small", colors.goldDark, nil, 480)

  love.graphics.setColor(colors.border, 0.6)
  love.graphics.line(908, 582, 1408, 582)
  theme.drawText("Awareness", 908, 596, "smallBold", colors.text)
  theme.drawText(
    "If one side is unaware and the other is not, combat opens with a surprise round. " ..
    "Unaware combatants are flat-footed until their first turn. Awareness is set per side here; " ..
    "custom scenarios can still vary individual combatants.",
    908, 618, "small", colors.textMuted, nil, 480)
  theme.drawText(
    "Pillars block movement, line of sight, and charges; the map stays open on the " ..
    "other squares so battles can flow around them.",
    908, 704, "small", colors.textMuted, nil, 480)

  self.pillarsBox:draw()
  self.pcAwareBox:draw()
  self.npcAwareBox:draw()
  self.autoNpcBox:draw()

  theme.drawPanel(16, 800, 1408, 84, { radius = 8 })
  theme.drawText("Tip: click Start Battle when both sides have at least one combatant.",
    34, 824, "small", colors.textMuted)
  theme.drawText("Enter starts the fight. Hotkeys: B bestiary, C new monster, Esc menu.",
    34, 848, "tiny", colors.textMuted)

  for _, widget in ipairs(self.buttons) do
    widget:draw()
  end

  self.gridDropdown:draw()
  for _, dropdown in ipairs(self.dropdowns) do
    if dropdown ~= self.gridDropdown then dropdown:draw() end
  end

  if self.message and self.messageTimer > 0 then
    local alpha = math.min(1, self.messageTimer * 2)
    local font = theme.fonts.small
    local width = font:getWidth(self.message) + 32
    local x = (1440 - width) / 2
    local y = 768
    theme.setColor(colors.black, 0.65 * alpha)
    love.graphics.rectangle("fill", x + 2, y + 2, width, 30, 6, 6)
    theme.setColor(colors.panelAlt, alpha)
    love.graphics.rectangle("fill", x, y, width, 30, 6, 6)
    theme.setColor(self.messageKind == "error" and colors.red or colors.gold, alpha)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", x + 0.5, y + 0.5, width - 1, 29, 5.5, 5.5)
    theme.drawText(self.message, 720, y + 7, "small",
      self.messageKind == "error" and colors.red or colors.text, "center")
  end
end

return SetupScreen
