-- Bestiary browser: inspect, filter, edit, duplicate, delete, export, and
-- stage statblocks into the encounter builder. Layout targets 1440x900.
local theme = require("src.ui.theme")
local ui = require("src.ui.widgets")

local Screen = {}
Screen.__index = Screen

local LIST_X, LIST_Y, LIST_W, LIST_H = 16, 80, 560, 804
local DETAIL_X, DETAIL_Y, DETAIL_W, DETAIL_H = 592, 80, 832, 804
local LIST_ROWS_Y = LIST_Y + 74
local LIST_ROW_H = 62
local LIST_VISIBLE = 11
local DETAIL_CONTENT_TOP = DETAIL_Y + 76
local DETAIL_VIEW_H = DETAIL_Y + DETAIL_H - 56 - DETAIL_CONTENT_TOP

local NAME_X = LIST_X + 22
local NAME_W = 330
local HP_X = LIST_X + 380
local AC_X = LIST_X + 432
local TAG_X = LIST_X + 488
local TAG_W = 58

local FILTERS = {
  { key = "all", label = "All" },
  { key = "heroes", label = "Heroes" },
  { key = "monsters", label = "Monsters" },
  { key = "custom", label = "Custom" },
}

local ABILITIES = {
  { key = "str", label = "STR" },
  { key = "dex", label = "DEX" },
  { key = "con", label = "CON" },
  { key = "int", label = "INT" },
  { key = "wis", label = "WIS" },
  { key = "cha", label = "CHA" },
}

local function trim(text)
  return (tostring(text or ""):gsub("^%s+", ""):gsub("%s+$", ""))
end

local function signed(value)
  value = math.floor(tonumber(value) or 0)
  if value >= 0 then return "+" .. value end
  return tostring(value)
end

local function numberText(value)
  local n = tonumber(value) or 0
  if n == math.floor(n) then return string.format("%d", n) end
  return tostring(n)
end

local function sortedKeys(map)
  local keys = {}
  for key in pairs(map or {}) do keys[#keys + 1] = key end
  table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
  return keys
end

local function drawSectionLabel(x, y, w, title)
  theme.drawText(title, x, y, "smallBold", theme.colors.gold)
  local width = theme.fonts.smallBold:getWidth(title)
  theme.setColor(theme.colors.border, 0.75)
  love.graphics.setLineWidth(1)
  love.graphics.line(math.floor(x + width + 12), math.floor(y + 9),
    math.floor(x + w), math.floor(y + 9))
  return y + 24
end

local function drawScrollbar(x, y, h, count, visible, offset)
  if count <= visible then return end
  theme.setColor(theme.colors.panelAlt)
  love.graphics.rectangle("fill", x, y, 4, h, 2, 2)
  local thumbH = math.max(26, h * visible / count)
  local maxOffset = count - visible
  local ratio = maxOffset > 0 and math.max(0, math.min(1, offset / maxOffset)) or 0
  theme.setColor(theme.colors.goldDark)
  love.graphics.rectangle("fill", x, y + (h - thumbH) * ratio, 4, thumbH, 2, 2)
end

function Screen.new(app)
  local self = setmetatable({}, Screen)
  self.app = app
  self.filter = "all"
  self.search = ""
  self.selectionKey = nil
  self.listScroll = 0
  self.detailScroll = 0
  self._contentHeight = 0
  self._previewKey = nil
  self._preview = nil
  self.message = nil
  self.messageKind = "info"
  self.messageTimer = 0
  self.confirmDelete = nil
  self.returnTo = "menu"
  self:_buildWidgets()
  self:_refresh(true)
  return self
end

function Screen:_buildWidgets()
  self.widgets = {}
  self.topWidgets = {}
  self.detailWidgets = {}
  self.modalWidgets = {}

  local function addWidget(group, widget)
    group[#group + 1] = widget
    self.widgets[#self.widgets + 1] = widget
    return widget
  end

  local function addButton(group, opts)
    return addWidget(group, ui.Button.new(opts))
  end

  self.searchInput = addWidget(self.topWidgets, ui.TextInput.new({
    x = 330, y = 15, w = 280, h = 34,
    value = self.search,
    placeholder = "Search name, type, alignment...",
    tooltip = "Filter statblocks by name, type, size, or alignment.",
    onChange = function(value)
      self.search = value
      self:_refresh(false)
    end,
    onSubmit = function()
      self:_refresh(false)
    end,
  }))

  self.filterButtons = {}
  for index, filter in ipairs(FILTERS) do
    local item = filter
    self.filterButtons[item.key] = addButton(self.topWidgets, {
      x = 628 + (index - 1) * 88, y = 16, w = 82, h = 32,
      label = item.label, font = "smallBold", style = "ghost",
      onClick = function()
        if self.filter ~= item.key then
          self.filter = item.key
          self:_refresh(false)
        end
      end,
    })
  end

  self.newButton = addButton(self.topWidgets, {
    x = 988, y = 16, w = 148, h = 34,
    label = "New Monster", style = "primary", font = "smallBold",
    hotkey = "N",
    tooltip = "Create a new custom statblock.",
    onClick = function() self:_newStatblock() end,
  })

  addButton(self.topWidgets, {
    x = 1292, y = 16, w = 132, h = 34,
    label = "Back", font = "smallBold", hotkey = "Esc",
    tooltip = "Return to the previous screen.",
    onClick = function() self:_back() end,
  })

  self.addButton = addButton(self.detailWidgets, {
    x = 982, y = DETAIL_Y + 18, w = 156, h = 32,
    label = "Add to Encounter", style = "primary", font = "smallBold",
    tooltip = "Add this statblock to the current encounter roster.",
    onClick = function() self:_addSelectedToEncounter() end,
  })
  self.editButton = addButton(self.detailWidgets, {
    x = 1146, y = DETAIL_Y + 18, w = 72, h = 32,
    label = "Edit", font = "smallBold",
    tooltip = "Open this statblock in the editor.",
    onClick = function() self:_editSelected() end,
  })
  self.duplicateButton = addButton(self.detailWidgets, {
    x = 1226, y = DETAIL_Y + 18, w = 92, h = 32,
    label = "Duplicate", font = "smallBold",
    tooltip = "Copy this statblock into a new custom monster.",
    onClick = function() self:_duplicateSelected() end,
  })
  self.deleteButton = addButton(self.detailWidgets, {
    x = 1326, y = DETAIL_Y + 18, w = 78, h = 32,
    label = "Delete", style = "danger", font = "smallBold",
    tooltip = "Delete this custom statblock.",
    onClick = function() self:_openDeleteConfirm() end,
  })
  self.exportButton = addButton(self.detailWidgets, {
    x = 616, y = DETAIL_Y + DETAIL_H - 46, w = 132, h = 30,
    label = "Export JSON", style = "ghost", font = "smallBold",
    tooltip = "Copy this statblock's JSON to the clipboard.",
    onClick = function() self:_exportSelected() end,
  })
end

function Screen:_instantiate(key)
  local database = self.app and self.app.database
  if not database then return nil end
  local ok, combatant = pcall(function() return database:instantiate(key) end)
  if ok then return combatant end
  return nil
end

function Screen:_selectedEntry()
  if not self.selectionKey then return nil end
  for _, entry in ipairs(self.filtered or {}) do
    if entry.key == self.selectionKey then return entry end
  end
  return nil
end

function Screen:_select(key)
  if self.selectionKey == key then return end
  self.selectionKey = key
  self._previewKey = nil
  self._preview = nil
  self.detailScroll = 0
end

function Screen:_refresh(keepScroll)
  self.entries = self.app.database:getDefinitions()
  local query = trim(self.search):lower()
  local filtered = {}
  for _, entry in ipairs(self.entries) do
    local data = entry.data or {}
    local matches = true
    if self.filter == "heroes" then
      matches = data.is_pc == true
    elseif self.filter == "monsters" then
      matches = data.is_pc ~= true
    elseif self.filter == "custom" then
      matches = entry.custom == true
    end
    if matches and query ~= "" then
      local subtypes = type(data.subtypes) == "table" and table.concat(data.subtypes, " ") or ""
      local haystack = table.concat({
        tostring(data.name or ""),
        tostring(data.creature_type or ""),
        tostring(data.size or ""),
        tostring(data.alignment or ""),
        subtypes,
        tostring(data.notes or ""),
      }, " "):lower()
      matches = haystack:find(query, 1, true) ~= nil
    end
    if matches then filtered[#filtered + 1] = entry end
  end
  self.filtered = filtered

  self.rowStats = {}
  for _, entry in ipairs(filtered) do
    local stats = { hp = entry.data.max_hp or 1, ac = nil }
    local combatant = self:_instantiate(entry.key)
    if combatant then
      stats.hp = combatant.max_hp
      stats.ac = combatant:getAC()
    end
    self.rowStats[entry.key] = stats
  end

  local present = false
  for _, entry in ipairs(filtered) do
    if entry.key == self.selectionKey then present = true break end
  end
  if not present then
    self.selectionKey = filtered[1] and filtered[1].key or nil
    self._previewKey = nil
    self._preview = nil
    self.detailScroll = 0
  end
  if not keepScroll then
    self.listScroll = 0
  end
  self:_clampListScroll()
end

function Screen:_clampListScroll()
  local count = #(self.filtered or {})
  local maxOffset = math.max(0, count - LIST_VISIBLE)
  if self.listScroll < 0 then self.listScroll = 0 end
  if self.listScroll > maxOffset then self.listScroll = maxOffset end
end

function Screen:_previewCombatant()
  local key = self.selectionKey
  if not key then return nil end
  if self._previewKey == key then return self._preview end
  self._previewKey = key
  self._preview = self:_instantiate(key)
  return self._preview
end

function Screen:_notify(text, kind)
  self.message = text
  self.messageKind = kind or "info"
  self.messageTimer = 4
end

function Screen:enter()
  local target = self.app.bestiaryReturn or "menu"
  if target == "bestiary" then
    target = self._lastReturn or "menu"
  else
    self._lastReturn = target
  end
  self.returnTo = target
  self.confirmDelete = nil
  self.modalWidgets = {}
  if self.searchInput then self.searchInput:blur() end
  self:_refresh(true)
end

function Screen:leave()
  if self.searchInput then self.searchInput:blur() end
  self.confirmDelete = nil
  self.modalWidgets = {}
end

function Screen:update(dt)
  if self.messageTimer > 0 then
    self.messageTimer = math.max(0, self.messageTimer - dt)
    if self.messageTimer == 0 then self.message = nil end
  end
end

function Screen:_back()
  if self.returnTo == "setup" then
    self.app:showSetup()
  else
    self.app:showMenu()
  end
end

function Screen:_openCreator(opts)
  opts = opts or {}
  opts.returnTo = "bestiary"
  self.app:showCreator(opts)
end

function Screen:_newStatblock()
  self:_openCreator({})
end

function Screen:_editSelected()
  local entry = self:_selectedEntry()
  if not entry then return end
  if entry.custom then
    self:_openCreator({ key = entry.key })
  else
    self:_openCreator({ data = entry.data })
  end
end

function Screen:_duplicateSelected()
  local entry = self:_selectedEntry()
  if not entry then return end
  self:_openCreator({ data = entry.data })
end

function Screen:_exportSelected()
  local entry = self:_selectedEntry()
  if not entry then return end
  local text = self.app.database:exportKey(entry.key)
  if not text then
    self:_notify("Export failed: statblock not found.", "error")
    return
  end
  if love and love.system and love.system.setClipboardText then
    love.system.setClipboardText(text)
    self:_notify("Statblock JSON copied to the clipboard.", "info")
    return
  end
  if love and love.filesystem and love.filesystem.write then
    local name = "export_" .. entry.key .. ".json"
    local ok = love.filesystem.write(name, text)
    if ok then
      self:_notify("Exported to the save directory as " .. name .. ".", "info")
    else
      self:_notify("Export failed: could not write the file.", "error")
    end
    return
  end
  self:_notify("Export unavailable on this system.", "error")
end

function Screen:_addSelectedToEncounter()
  local entry = self:_selectedEntry()
  if not entry then return end
  local setup = self.app.screens.setup
  local entries = {}
  for _, rosterEntry in ipairs(setup and setup.roster or {}) do
    entries[#entries + 1] = {
      key = rosterEntry.key,
      side = rosterEntry.side,
      potions = rosterEntry.potions,
    }
  end
  local isHero = entry.data.is_pc == true
  entries[#entries + 1] = {
    key = entry.key,
    side = isHero and "pc" or "npc",
    potions = isHero and 2 or 0,
  }
  self.app:showSetup({ entries = entries })
end

function Screen:_openDeleteConfirm()
  local entry = self:_selectedEntry()
  if not entry or not entry.custom then return end
  self.confirmDelete = entry.key
  self.confirmName = entry.data.name or entry.key
  self.confirmError = nil
  self.modalWidgets = {
    ui.Button.new({
      x = 610, y = 438, w = 140, h = 34,
      label = "Cancel", tooltip = "Keep this statblock.",
      onClick = function() self:_closeDeleteConfirm() end,
    }),
    ui.Button.new({
      x = 770, y = 438, w = 140, h = 34,
      label = "Delete", style = "danger",
      tooltip = "Permanently delete this custom statblock.",
      onClick = function() self:_confirmDelete() end,
    }),
  }
end

function Screen:_closeDeleteConfirm()
  self.confirmDelete = nil
  self.confirmName = nil
  self.confirmError = nil
  self.modalWidgets = {}
end

function Screen:_confirmDelete()
  local key = self.confirmDelete
  if not key then return end
  local ok, err = self.app.database:removeCustom(key)
  if not ok then
    self.confirmError = tostring(err or "This statblock could not be deleted.")
    return
  end
  if self.selectionKey == key then
    self.selectionKey = nil
    self._previewKey = nil
    self._preview = nil
    self.detailScroll = 0
  end
  self:_closeDeleteConfirm()
  self:_refresh(true)
  self:_notify("Custom statblock deleted.", "info")
end

function Screen:_moveSelection(delta)
  local list = self.filtered or {}
  if #list == 0 then return end
  local index = 1
  for i, entry in ipairs(list) do
    if entry.key == self.selectionKey then index = i break end
  end
  index = math.max(1, math.min(#list, index + delta))
  self:_select(list[index].key)
  if index <= self.listScroll then
    self.listScroll = index - 1
  elseif index > self.listScroll + LIST_VISIBLE then
    self.listScroll = index - LIST_VISIBLE
  end
  self:_clampListScroll()
end

function Screen:mousepressed(x, y, button)
  if button ~= 1 then return false end
  if self.confirmDelete then
    for _, widget in ipairs(self.modalWidgets) do
      if widget:contains(x, y) then
        widget:mousepressed(x, y, button)
        return true
      end
    end
    return true
  end
  for _, widget in ipairs(self.widgets) do
    if widget.contains and widget:contains(x, y) then
      if widget:mousepressed(x, y, button) ~= false then return true end
    end
  end
  if x >= LIST_X and x < LIST_X + LIST_W and
     y >= LIST_ROWS_Y and y < LIST_ROWS_Y + LIST_VISIBLE * LIST_ROW_H then
    local index = math.floor((y - LIST_ROWS_Y) / LIST_ROW_H) + 1 + self.listScroll
    local entry = self.filtered and self.filtered[index]
    if entry then self:_select(entry.key) end
    return true
  end
  return false
end

function Screen:mousereleased(x, y, button)
  for _, widget in ipairs(self.widgets) do
    if widget.mousereleased then widget:mousereleased(x, y, button) end
  end
  for _, widget in ipairs(self.modalWidgets or {}) do
    if widget.mousereleased then widget:mousereleased(x, y, button) end
  end
  return false
end

function Screen:wheelmoved(dx, dy)
  if self.confirmDelete then return true end
  local mx, my = theme.mouseX or -100, theme.mouseY or -100
  if mx >= DETAIL_X and mx < DETAIL_X + DETAIL_W and
     my >= DETAIL_CONTENT_TOP and my < DETAIL_CONTENT_TOP + DETAIL_VIEW_H then
    local maxScroll = math.max(0, (self._contentHeight or 0) - DETAIL_VIEW_H)
    self.detailScroll = math.max(0, math.min(maxScroll, self.detailScroll - dy * 64))
    return true
  end
  if mx >= LIST_X and mx < LIST_X + LIST_W and
     my >= LIST_ROWS_Y and my < LIST_ROWS_Y + LIST_VISIBLE * LIST_ROW_H then
    self.listScroll = self.listScroll - dy
    self:_clampListScroll()
    return true
  end
  return false
end

function Screen:textinput(text)
  if self.searchInput and self.searchInput:focused() then
    return self.searchInput:textinput(text)
  end
  return false
end

function Screen:keypressed(key)
  if self.confirmDelete then
    if key == "escape" then self:_closeDeleteConfirm() end
    return true
  end
  if self.searchInput and self.searchInput:focused() then
    if self.searchInput:keypressed(key) then return true end
    if key ~= "up" and key ~= "down" then return false end
  end
  if key == "escape" then
    self:_back()
  elseif key == "up" then
    self:_moveSelection(-1)
  elseif key == "down" then
    self:_moveSelection(1)
  elseif key == "n" then
    self:_newStatblock()
  elseif key == "e" then
    self:_editSelected()
  elseif key == "d" then
    self:_duplicateSelected()
  elseif key == "delete" then
    self:_openDeleteConfirm()
  elseif key == "/" then
    self.searchInput:focus()
  elseif key == "return" or key == "kpenter" then
    self:_addSelectedToEncounter()
  else
    return false
  end
  return true
end

function Screen:_drawTopBar()
  local colors = theme.colors
  love.graphics.setColor(colors.panel)
  love.graphics.rectangle("fill", 0, 0, theme.width, 64)
  theme.setColor(colors.border, 0.9)
  love.graphics.setLineWidth(1)
  love.graphics.line(0, 64.5, theme.width, 64.5)

  theme.drawText("Bestiary", 24, 12, "h1", colors.gold)
  local total = #(self.entries or {})
  local shown = #(self.filtered or {})
  theme.drawText(string.format("%d of %d statblocks", shown, total),
    24, 45, "small", colors.textMuted)

  for _, filter in ipairs(FILTERS) do
    local button = self.filterButtons[filter.key]
    if button then
      button.style = (self.filter == filter.key) and "default" or "ghost"
    end
  end
  theme.drawText(string.format("%d entries", total), 1150, 27,
    "small", colors.textMuted, "right", 130)
  for _, widget in ipairs(self.topWidgets) do widget:draw() end
end

function Screen:_drawList()
  local colors = theme.colors
  theme.drawPanel(LIST_X, LIST_Y, LIST_W, LIST_H, { padding = 0, radius = 8 })

  theme.drawText("STATBLOCKS", LIST_X + 20, LIST_Y + 16, "smallBold", colors.gold)
  theme.drawText(string.format("%d shown", #(self.filtered or {})),
    LIST_X + LIST_W - 20, LIST_Y + 18, "small", colors.textMuted, "right", 160)

  local headerY = LIST_Y + 46
  theme.drawText("NAME", NAME_X, headerY, "tiny", colors.textMuted)
  theme.drawText("HP", HP_X, headerY, "tiny", colors.textMuted)
  theme.drawText("AC", AC_X, headerY, "tiny", colors.textMuted)
  theme.drawText("TAG", TAG_X, headerY, "tiny", colors.textMuted)

  theme.setColor(colors.border, 0.7)
  love.graphics.setLineWidth(1)
  love.graphics.line(LIST_X + 16, LIST_Y + 66.5, LIST_X + LIST_W - 16, LIST_Y + 66.5)

  if #(self.filtered or {}) == 0 then
    theme.drawText("No statblocks match the current filters.",
      LIST_X + 22, LIST_ROWS_Y + 24, "body", colors.textMuted, "left", LIST_W - 44)
    return
  end

  local sx, sy, sw, sh = love.graphics.getScissor()
  love.graphics.setScissor(LIST_X + 1, LIST_ROWS_Y, LIST_W - 2,
    LIST_VISIBLE * LIST_ROW_H)

  local mouseX, mouseY = theme.mouseX or -100, theme.mouseY or -100
  for slot = 1, LIST_VISIBLE do
    local index = slot + self.listScroll
    local entry = self.filtered[index]
    if entry then
      local data = entry.data or {}
      local rowY = LIST_ROWS_Y + (slot - 1) * LIST_ROW_H
      local rowX = LIST_X + 8
      local rowW = LIST_W - 16
      local selected = entry.key == self.selectionKey
      local hovered = mouseX >= rowX and mouseX < rowX + rowW and
        mouseY >= rowY and mouseY < rowY + LIST_ROW_H

      if selected then
        theme.setColor(colors.panelLight, 0.95)
        love.graphics.rectangle("fill", rowX, rowY, rowW, LIST_ROW_H, 6, 6)
      elseif hovered then
        theme.setColor(colors.panelAlt, 0.85)
        love.graphics.rectangle("fill", rowX, rowY, rowW, LIST_ROW_H, 6, 6)
      end
      if selected then
        theme.setColor(colors.gold)
        love.graphics.rectangle("fill", rowX, rowY + 4, 3, LIST_ROW_H - 8, 2, 2)
      end

      local stats = (self.rowStats or {})[entry.key] or {}
      local nameColor = selected and colors.gold or colors.text
      local name = theme.truncateText(tostring(data.name or entry.key),
        theme.fonts.bodyBold, NAME_W)
      theme.drawText(name, NAME_X, rowY + 9, "bodyBold", nameColor)

      local subtypeText = ""
      if type(data.subtypes) == "table" and #data.subtypes > 0 then
        subtypeText = " (" .. table.concat(data.subtypes, ", ") .. ")"
      end
      local subtitle = string.format("%s %s%s", tostring(data.size or "Medium"),
        tostring(data.creature_type or "Creature"), subtypeText)
      theme.drawText(theme.truncateText(subtitle, theme.fonts.small, NAME_W),
        NAME_X, rowY + 32, "small", colors.textMuted)

      theme.drawText(numberText(stats.hp or data.max_hp), HP_X, rowY + 21,
        "smallBold", colors.text)
      local ac = stats.ac and numberText(stats.ac) or "-"
      theme.drawText(ac, AC_X, rowY + 21, "smallBold", colors.text)

      if data.is_pc == true then
        theme.drawPill(TAG_X, rowY + 21, TAG_W, 20, "HERO", colors.blue, "tiny")
      elseif entry.custom then
        theme.drawPill(TAG_X, rowY + 21, TAG_W, 20, "CUSTOM", colors.gold, "tiny")
      end

      if slot < LIST_VISIBLE and self.filtered[index + 1] then
        theme.setColor(colors.border, 0.35)
        love.graphics.line(LIST_X + 18, rowY + LIST_ROW_H - 0.5,
          LIST_X + LIST_W - 18, rowY + LIST_ROW_H - 0.5)
      end
    end
  end

  love.graphics.setScissor(sx, sy, sw, sh)

  drawScrollbar(LIST_X + LIST_W - 9, LIST_ROWS_Y, LIST_VISIBLE * LIST_ROW_H,
    #self.filtered, LIST_VISIBLE, self.listScroll)

  theme.drawText("Wheel or Up/Down to browse  ·  Enter adds to the encounter",
    LIST_X + 20, LIST_Y + LIST_H - 34, "small", colors.textMuted,
    "left", LIST_W - 40)
end

function Screen:_drawDetailHeader(entry)
  local colors = theme.colors
  local data = entry.data or {}
  theme.drawText(theme.truncateText(tostring(data.name or entry.key),
    theme.fonts.h1, 350), DETAIL_X + 24, DETAIL_Y + 12, "h1", colors.gold)

  local source = entry.custom and "Custom statblock" or "Bundled statblock"
  local subtypeText = ""
  if type(data.subtypes) == "table" and #data.subtypes > 0 then
    subtypeText = " (" .. table.concat(data.subtypes, ", ") .. ")"
  end
  local subtitle = string.format("%s  ·  %s %s%s  ·  %s", source,
    tostring(data.size or "Medium"), tostring(data.creature_type or "Creature"),
    subtypeText, tostring(data.alignment or "True Neutral"))
  theme.drawText(theme.truncateText(subtitle, theme.fonts.small, 620),
    DETAIL_X + 24, DETAIL_Y + 48, "small", colors.textMuted)

  theme.setColor(colors.border, 0.7)
  love.graphics.setLineWidth(1)
  love.graphics.line(DETAIL_X + 20, DETAIL_Y + 66.5, DETAIL_X + DETAIL_W - 20, DETAIL_Y + 66.5)

  if entry.custom then
    self.editButton.tooltip = "Open this custom statblock in the editor."
  else
    self.editButton.tooltip = "Base a new custom statblock on this one."
  end
  self.editButton:setLabel(entry.custom and "Edit" or "Customize")
  self.deleteButton:setEnabled(entry.custom == true)
  self.addButton:setEnabled(true)
  self.exportButton:setEnabled(true)
  for _, widget in ipairs(self.detailWidgets) do widget:draw() end
end

function Screen:_defenseLines(data)
  local lines = {}
  local dr = data.damage_reduction
  if type(dr) == "table" and (tonumber(dr.amount) or 0) > 0 then
    local dtype = dr.type and tostring(dr.type) or ""
    lines[#lines + 1] = "Damage reduction " .. numberText(dr.amount) ..
      (dtype ~= "" and ("/" .. dtype) or "")
  elseif type(dr) == "number" and dr > 0 then
    lines[#lines + 1] = "Damage reduction " .. numberText(dr)
  end
  local sr = tonumber(data.spell_resistance) or 0
  if sr > 0 then lines[#lines + 1] = "Spell resistance " .. numberText(sr) end
  local resist = data.energy_resistances
  if type(resist) == "table" then
    for _, key in ipairs(sortedKeys(resist)) do
      local value = tonumber(resist[key])
      if value and value > 0 then
        lines[#lines + 1] = "Resist " .. tostring(key):lower() .. " " .. numberText(value)
      end
    end
  end
  local function energyLine(label, list)
    if type(list) ~= "table" then return end
    local names = {}
    for _, value in ipairs(list) do names[#names + 1] = tostring(value):lower() end
    if #names > 0 then
      lines[#lines + 1] = label .. " " .. table.concat(names, ", ")
    end
  end
  energyLine("Immune to", data.energy_immunities)
  energyLine("Vulnerable to", data.energy_vulnerabilities)
  return lines
end

function Screen:_skillFeatLines(data)
  local lines = {}
  local skills = data.skills
  if type(skills) == "table" then
    local parts = {}
    for _, key in ipairs(sortedKeys(skills)) do
      local value = tonumber(skills[key])
      if value then
        parts[#parts + 1] = tostring(key) .. " " .. signed(value)
      else
        parts[#parts + 1] = tostring(key) .. " " .. tostring(skills[key])
      end
    end
    if #parts > 0 then lines[#lines + 1] = "Skills: " .. table.concat(parts, ", ") end
  end
  local feats = data.feats
  if type(feats) == "table" and #feats > 0 then
    local names = {}
    for _, feat in ipairs(feats) do names[#names + 1] = tostring(feat) end
    lines[#lines + 1] = "Feats: " .. table.concat(names, ", ")
  end
  return lines
end

function Screen:_specialLines(data)
  local special = data.special_abilities
  local lines = {}
  if type(special) ~= "table" then return lines end
  if #special > 0 then
    for _, item in ipairs(special) do lines[#lines + 1] = tostring(item) end
  else
    for _, key in ipairs(sortedKeys(special)) do
      local value = special[key]
      if type(value) == "table" then
        local parts = {}
        for _, item in ipairs(value) do parts[#parts + 1] = tostring(item) end
        lines[#lines + 1] = tostring(key) .. ": " .. table.concat(parts, ", ")
      else
        lines[#lines + 1] = tostring(key) .. ": " .. tostring(value)
      end
    end
  end
  return lines
end

function Screen:_drawDetailContent(entry, combatant)
  local colors = theme.colors
  local data = entry.data or {}
  local contentX = DETAIL_X + 24
  local contentW = DETAIL_W - 48
  local cursor = DETAIL_CONTENT_TOP - self.detailScroll
  local startY = DETAIL_CONTENT_TOP

  local ac = combatant and combatant:getAC("standard") or 10
  local touch = combatant and combatant:getAC("touch") or 10
  local flat = combatant and combatant:getAC("flat_footed") or 10
  local fort = combatant and combatant:getSaveBonus("fortitude") or 0
  local reflex = combatant and combatant:getSaveBonus("reflex") or 0
  local will = combatant and combatant:getSaveBonus("will") or 0
  local cmb = combatant and combatant:calculateCMB() or 0
  local cmd = combatant and combatant:calculateCMD() or 10
  local bab = combatant and combatant.base_attack_bonus or 0
  local speed = data.base_speed or 30
  local reach = combatant and combatant:getReachFeet() or 5
  local initiative = combatant and combatant:getInitiativeBonus() or 0
  local maxHp = combatant and combatant.max_hp or (data.max_hp or 1)

  local col1 = contentX
  local col2 = contentX + 270
  local col3 = contentX + 520

  theme.drawText("HIT POINTS", col1, cursor, "tiny", colors.textMuted)
  theme.drawText(string.format("%d / %d", maxHp, maxHp), col1, cursor + 14,
    "h2", colors.text)
  theme.drawBar(col1, cursor + 44, 246, 10, 1, colors.hp,
    { border = colors.border })
  theme.drawText("CMB " .. signed(cmb) .. "   ·   CMD " .. numberText(cmd),
    col1, cursor + 62, "small", colors.textMuted)

  theme.drawText("ARMOR CLASS", col2, cursor, "tiny", colors.textMuted)
  theme.drawText(numberText(ac), col2, cursor + 12, "h2", colors.text)
  theme.drawText("Touch " .. numberText(touch), col2 + 46, cursor + 18,
    "small", colors.text)
  theme.drawText("Flat-footed " .. numberText(flat), col2 + 46, cursor + 34,
    "small", colors.textMuted)
  theme.drawText(string.format("Saves  F %s · R %s · W %s",
    signed(fort), signed(reflex), signed(will)),
    col2, cursor + 62, "small", colors.textMuted)

  theme.drawText("COMBAT", col3, cursor, "tiny", colors.textMuted)
  local combatLines = {
    "BAB " .. signed(bab),
    "Speed " .. numberText(speed) .. " ft.",
    "Reach " .. numberText(reach) .. " ft.",
    "Initiative " .. signed(initiative),
  }
  for index, line in ipairs(combatLines) do
    theme.drawText(line, col3, cursor + 14 + (index - 1) * 18, "small", colors.text)
  end
  cursor = cursor + 98

  cursor = drawSectionLabel(contentX, cursor, contentW, "ABILITY SCORES")
  local cellW, cellGap = 122, 8
  for index, ability in ipairs(ABILITIES) do
    local x = contentX + (index - 1) * (cellW + cellGap)
    theme.setColor(colors.panelAlt)
    love.graphics.rectangle("fill", x, cursor, cellW, 46, 6, 6)
    theme.setColor(colors.border, 0.8)
    love.graphics.rectangle("line", x + 0.5, cursor + 0.5, cellW - 1, 45, 6, 6)
    theme.drawText(ability.label, x + 10, cursor + 5, "tiny", colors.textMuted)
    local score = combatant and combatant:getAbilityScore(ability.key) or 10
    local mod = combatant and combatant:getAbilityModifier(ability.key) or 0
    theme.drawText(numberText(score), x + 10, cursor + 18, "bodyBold", colors.text)
    theme.drawText(signed(mod), x + cellW - 10, cursor + 22, "small",
      colors.gold, "right")
  end
  cursor = cursor + 62

  cursor = drawSectionLabel(contentX, cursor, contentW, "ATTACKS")
  local attacks = combatant and combatant.attacks or {}
  if #attacks == 0 then
    theme.drawText("No attacks defined.", contentX, cursor, "small", colors.textMuted)
    cursor = cursor + 20
  else
    for index = 1, math.min(#attacks, 6) do
      local attack = attacks[index]
      local hit = combatant:getAttackBonus(attack, {})
      local damageBonus = combatant:getDamageBonus(attack)
      local damage = tostring(attack.damage_dice) ..
        (damageBonus ~= 0 and signed(damageBonus) or "")
      theme.drawText(theme.truncateText(tostring(attack.name), theme.fonts.bodyBold, 196),
        contentX, cursor, "bodyBold", colors.text)
      local detail = string.format("%s  ·  %s  ·  %s/%s  ·  %s  ·  %s, reach %s ft.",
        signed(hit), damage, tostring(attack.critical_threat_range),
        tostring(attack.critical_multiplier), tostring(attack.damage_type),
        tostring(attack.attack_type), numberText(attack.reach))
      theme.drawText(theme.truncateText(detail, theme.fonts.small, contentW - 210),
        contentX + 210, cursor + 1, "small", colors.textMuted)
      cursor = cursor + 24
    end
    if #attacks > 6 then
      theme.drawText(string.format("... and %d more attacks", #attacks - 6),
        contentX + 210, cursor, "small", colors.textMuted)
      cursor = cursor + 22
    end
    if bab >= 6 then
      local iteratives = {}
      local number = 1
      while bab - number * 5 >= 0 and number <= 4 do
        iteratives[#iteratives + 1] = signed(bab - number * 5)
        number = number + 1
      end
      if #iteratives > 1 then
        theme.drawText("Full attack: " .. table.concat(iteratives, " / "),
          contentX, cursor, "small", colors.gold)
        cursor = cursor + 20
      end
    end
  end
  cursor = cursor + 12

  cursor = drawSectionLabel(contentX, cursor, contentW, "DEFENSES")
  local defenseLines = self:_defenseLines(data)
  if #defenseLines == 0 then defenseLines = { "No special defenses noted." } end
  for _, line in ipairs(defenseLines) do
    cursor = theme.drawText(line, contentX, cursor, "small", colors.text,
      "left", contentW)
    cursor = cursor + 2
  end
  cursor = cursor + 14

  cursor = drawSectionLabel(contentX, cursor, contentW, "SKILLS & FEATS")
  local skillFeatLines = self:_skillFeatLines(data)
  if #skillFeatLines == 0 then
    theme.drawText("No listed skills or feats.", contentX, cursor, "small", colors.textMuted)
    cursor = cursor + 20
  else
    for _, line in ipairs(skillFeatLines) do
      cursor = theme.drawText(line, contentX, cursor, "small", colors.text,
        "left", contentW)
      cursor = cursor + 2
    end
  end
  cursor = cursor + 14

  local specialLines = self:_specialLines(data)
  if #specialLines > 0 then
    cursor = drawSectionLabel(contentX, cursor, contentW, "SPECIAL ABILITIES")
    for _, line in ipairs(specialLines) do
      cursor = theme.drawText(line, contentX, cursor, "small", colors.text,
        "left", contentW)
      cursor = cursor + 2
    end
    cursor = cursor + 14
  end

  local notes = trim(data.notes)
  if notes ~= "" then
    cursor = drawSectionLabel(contentX, cursor, contentW, "NOTES")
    cursor = theme.drawText(notes, contentX, cursor, "small", colors.textMuted,
      "left", contentW)
    cursor = cursor + 4
  end

  self._contentHeight = cursor + self.detailScroll - startY
end

function Screen:_drawDetail()
  local colors = theme.colors
  theme.drawPanel(DETAIL_X, DETAIL_Y, DETAIL_W, DETAIL_H, { padding = 0, radius = 8 })

  local entry = self:_selectedEntry()
  if not entry then
    theme.drawText("No statblock selected", DETAIL_X + 24, DETAIL_Y + 24,
      "h2", colors.textMuted)
    theme.drawText("Choose a statblock from the list, or create a new one.",
      DETAIL_X + 24, DETAIL_Y + 56, "small", colors.textMuted)
    self.addButton:setEnabled(false)
    self.editButton:setEnabled(false)
    self.duplicateButton:setEnabled(false)
    self.deleteButton:setEnabled(false)
    self.exportButton:setEnabled(false)
    for _, widget in ipairs(self.detailWidgets) do widget:draw() end
    return
  end

  self.duplicateButton:setEnabled(true)
  self.editButton:setEnabled(true)
  self:_drawDetailHeader(entry)

  local combatant = self:_previewCombatant()

  local sx, sy, sw, sh = love.graphics.getScissor()
  love.graphics.setScissor(DETAIL_X + 16, DETAIL_CONTENT_TOP,
    DETAIL_W - 32, DETAIL_VIEW_H)
  self:_drawDetailContent(entry, combatant)
  love.graphics.setScissor(sx, sy, sw, sh)

  local maxScroll = math.max(0, (self._contentHeight or 0) - DETAIL_VIEW_H)
  if self.detailScroll > maxScroll then self.detailScroll = maxScroll end
  drawScrollbar(DETAIL_X + DETAIL_W - 10, DETAIL_CONTENT_TOP, DETAIL_VIEW_H,
    math.ceil(self._contentHeight or 0), DETAIL_VIEW_H,
    self.detailScroll)

  theme.setColor(colors.border, 0.7)
  love.graphics.setLineWidth(1)
  love.graphics.line(DETAIL_X + 20, DETAIL_Y + DETAIL_H - 56.5,
    DETAIL_X + DETAIL_W - 20, DETAIL_Y + DETAIL_H - 56.5)

  if self.message then
    local color = self.messageKind == "error" and colors.red or colors.green
    theme.drawText(theme.truncateText(self.message, theme.fonts.small, 620),
      760, DETAIL_Y + DETAIL_H - 42, "small", color)
  end
end

function Screen:_drawDeleteConfirm()
  if not self.confirmDelete then return end
  local colors = theme.colors
  love.graphics.setColor(colors.overlay)
  love.graphics.rectangle("fill", 0, 0, theme.width, theme.height)

  local x, y, w, h = 490, 330, 460, 200
  theme.drawPanel(x, y, w, h, { padding = 0, radius = 10 })
  theme.drawText("Delete statblock?", x + 24, y + 20, "h2", colors.gold)
  theme.drawText("This permanently removes the custom statblock \"" ..
    tostring(self.confirmName or "") .. "\" from the bestiary.",
    x + 24, y + 58, "small", colors.text, "left", w - 48)
  theme.drawText("Bundled statblocks cannot be deleted.",
    x + 24, y + 96, "small", colors.textMuted, "left", w - 48)
  if self.confirmError then
    theme.drawText(self.confirmError, x + 24, y + 118, "small", colors.red,
      "left", w - 48)
  end
  for _, widget in ipairs(self.modalWidgets) do widget:draw() end
end

function Screen:draw()
  self:_drawTopBar()
  self:_drawList()
  self:_drawDetail()
  self:_drawDeleteConfirm()
end

return Screen
