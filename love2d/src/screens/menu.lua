-- Dark fantasy main menu: procedural backdrop, navigation cards, and rules.
local theme = require("src.ui.theme")
local ui = require("src.ui.widgets")
local constants = require("src.core.constants")

local Screen = {}
Screen.__index = Screen

local SPEED_LABELS = { "Slow", "Normal", "Fast" }
local SPEED_VALUES = { 0.66, 1, 1.5 }

local CARD_TOP = 260
local CARD_HEIGHT = 430
local LEFT_X, LEFT_W = 140, 520
local RIGHT_X, RIGHT_W = 740, 560

local function lerp(a, b, t)
  return a + (b - a) * t
end

local function speedLabelFor(value)
  local speed = tonumber(value) or 1
  local bestIndex = 2
  local bestDelta = math.huge
  for i = 1, #SPEED_VALUES do
    local delta = math.abs(speed - SPEED_VALUES[i])
    if delta < bestDelta then
      bestDelta = delta
      bestIndex = i
    end
  end
  return SPEED_LABELS[bestIndex]
end

local function speedValueFor(label)
  for i = 1, #SPEED_LABELS do
    if SPEED_LABELS[i] == label then return SPEED_VALUES[i] end
  end
  return 1
end

local function buildMotes(count)
  local motes = {}
  local seed = 7919
  local function nextRandom()
    seed = (seed * 16807) % 2147483647
    return seed / 2147483647
  end
  for i = 1, count do
    motes[i] = {
      x = 20 + nextRandom() * 1400,
      y = 10 + nextRandom() * 880,
      radius = 0.7 + nextRandom() * 1.2,
      speed = 4 + nextRandom() * 10,
      drift = 5 + nextRandom() * 14,
      phase = nextRandom() * math.pi * 2,
      alpha = 0.05 + nextRandom() * 0.10,
    }
  end
  return motes
end

local function drawBackdrop()
  local bands = 48
  local bandHeight = theme.height / bands
  for i = 0, bands - 1 do
    local t = i / (bands - 1)
    theme.setColor({
      lerp(0.030, 0.070, t),
      lerp(0.035, 0.082, t),
      lerp(0.050, 0.112, t),
    })
    love.graphics.rectangle("fill", 0, i * bandHeight,
      theme.width, bandHeight + 1)
  end

  local strips = 22
  for i = 1, strips do
    local inset = (i - 1) * 9
    local strength = 1 - (i - 1) / strips
    local alpha = 0.038 * strength * strength
    theme.setColor(theme.colors.black, alpha)
    love.graphics.rectangle("fill", inset, inset,
      theme.width - inset * 2, 9)
    love.graphics.rectangle("fill", inset, theme.height - inset - 9,
      theme.width - inset * 2, 9)
    love.graphics.rectangle("fill", inset, inset, 9,
      theme.height - inset * 2)
    love.graphics.rectangle("fill", theme.width - inset - 9, inset, 9,
      theme.height - inset * 2)
  end

  theme.setColor(theme.colors.border, 0.032)
  love.graphics.setLineWidth(1)
  for i = -1, 9 do
    local x = i * 190
    love.graphics.line(x, 0, x + 900, theme.height)
  end
end

local function drawTorchGlow(cx, cy, time, phase)
  local pulse = 0.82 + 0.12 * math.sin(time * 1.7 + phase) +
    0.06 * math.sin(time * 4.3 + phase * 2.1)

  love.graphics.setBlendMode("add")
  for i = 12, 1, -1 do
    local f = i / 12
    theme.setColor(theme.colors.orange, (0.006 + 0.014 * (1 - f)) * pulse)
    love.graphics.ellipse("fill", cx, cy, 40 + 130 * f, 28 + 100 * f)
  end
  theme.setColor(theme.colors.gold, 0.07 * pulse)
  love.graphics.ellipse("fill", cx, cy, 38, 42)
  love.graphics.setBlendMode("alpha")

  theme.setColor(theme.colors.orange, 0.85)
  love.graphics.ellipse("fill", cx, cy - 2, 5, 12)
  theme.setColor({ 1.0, 0.86, 0.55 }, 0.95)
  love.graphics.ellipse("fill", cx, cy, 2.4, 6)

  theme.setColor(theme.colors.border, 0.55)
  love.graphics.rectangle("fill", cx - 11, cy + 17, 22, 3, 1, 1)
  love.graphics.polygon("fill", cx - 8, cy + 20, cx + 8, cy + 20,
    cx + 3, cy + 30, cx - 3, cy + 30)
end

local function drawDust(motes, time)
  love.graphics.setBlendMode("add")
  for i = 1, #motes do
    local mote = motes[i]
    local y = (mote.y - time * mote.speed) % 920
    local x = mote.x + math.sin(time * 0.45 + mote.phase) * mote.drift
    local shimmer = 0.55 + 0.45 * math.sin(time * 1.2 + mote.phase)
    theme.setColor(theme.colors.gold, mote.alpha * shimmer)
    love.graphics.circle("fill", x, y - 10, mote.radius)
  end
  love.graphics.setBlendMode("alpha")
end

local function drawTracked(text, centerX, y, fontName, color, tracking)
  local font = theme.getFont(fontName)
  local total = 0
  for i = 1, #text do
    total = total + font:getWidth(text:sub(i, i))
  end
  total = total + tracking * math.max(0, #text - 1)

  local x = centerX - total / 2
  theme.setColor(color)
  love.graphics.setFont(font)
  for i = 1, #text do
    local ch = text:sub(i, i)
    love.graphics.print(ch, math.floor(x + 0.5), math.floor(y + 0.5))
    x = x + font:getWidth(ch) + tracking
  end
end

local function drawRule(cx, y, halfWidth, color, alpha, diamond)
  local d = diamond or 6
  local gap = d + 11
  theme.setColor(color, alpha or 1)
  love.graphics.setLineWidth(1)
  love.graphics.line(cx - halfWidth, y, cx - gap, y)
  love.graphics.line(cx + gap, y, cx + halfWidth, y)
  love.graphics.polygon("fill", cx, y - d, cx + d, y, cx, y + d, cx - d, y)
  if halfWidth > d + 6 then
    love.graphics.polygon("fill",
      cx - halfWidth - 3, y, cx - halfWidth, y - 2,
      cx - halfWidth + 3, y, cx - halfWidth, y + 2)
    love.graphics.polygon("fill",
      cx + halfWidth - 3, y, cx + halfWidth, y - 2,
      cx + halfWidth + 3, y, cx + halfWidth, y + 2)
  end
end

local function drawCornerBrackets(x, y, w, h, length, color, alpha)
  theme.setColor(color, alpha)
  love.graphics.setLineWidth(2)
  love.graphics.line(x, y + length, x, y, x + length, y)
  love.graphics.line(x + w - length, y, x + w, y, x + w, y + length)
  love.graphics.line(x, y + h - length, x, y + h, x + length, y + h)
  love.graphics.line(x + w - length, y + h, x + w, y + h, x + w, y + h - length)
  love.graphics.setLineWidth(1)
end

function Screen.new(app)
  local self = setmetatable({}, Screen)
  self.app = app
  self.time = 0
  self.motes = buildMotes(48)
  self.rosterEntries = {}
  self.pcCount = 0
  self.npcCount = 0

  self.aiCheckbox = ui.Checkbox.new({
    x = RIGHT_X + 20, y = 318, size = 20,
    label = "AI controls monsters",
    checked = app.settings.autoNpc,
    tooltip = "Let the AI run every monster turn. Uncheck to command both sides.",
    onChange = function(checked) app.settings.autoNpc = checked == true end,
  })
  self.threatCheckbox = ui.Checkbox.new({
    x = RIGHT_X + 20, y = 382, size = 20,
    label = "Show threatened squares",
    checked = app.settings.showThreats,
    tooltip = "Tint squares that enemies threaten with attacks of opportunity.",
    onChange = function(checked) app.settings.showThreats = checked == true end,
  })
  self.pillarCheckbox = ui.Checkbox.new({
    x = RIGHT_X + 20, y = 446, size = 20,
    label = "Pillars on battlefield",
    checked = app.settings.pillars,
    tooltip = "Scatter blocked pillars across the Quick Battle grid.",
    onChange = function(checked) app.settings.pillars = checked == true end,
  })
  self.checkboxes = { self.aiCheckbox, self.threatCheckbox, self.pillarCheckbox }

  self.speedDropdown = ui.Dropdown.new({
    x = RIGHT_X + 340, y = 512, w = 200, h = 32,
    items = SPEED_LABELS,
    value = speedLabelFor(app.settings.speed),
    placeholder = "Normal",
    font = "body",
    tooltip = "Delay between AI actions. Normal is recommended.",
    onChange = function(label)
      app.settings.speed = speedValueFor(label)
    end,
  })

  self.buttons = {
    ui.Button.new({
      x = 180, y = 316, w = 440, h = 52,
      label = "Quick Battle", style = "primary", hotkey = "Q",
      icon = ">",
      tooltip = "Deploy the default party against the default monsters.",
      onClick = function() app:startQuickBattle({}) end,
    }),
    ui.Button.new({
      x = 180, y = 380, w = 440, h = 52,
      label = "Build Encounter", hotkey = "B",
      tooltip = "Choose combatants, grid size, pillars, and awareness.",
      onClick = function() app:showSetup() end,
    }),
    ui.Button.new({
      x = 180, y = 444, w = 440, h = 52,
      label = "Bestiary", hotkey = "L",
      tooltip = "Inspect every hero and monster statblock.",
      onClick = function() app:showBestiary("menu") end,
    }),
    ui.Button.new({
      x = 180, y = 508, w = 440, h = 52,
      label = "Create Monster", hotkey = "C",
      tooltip = "Build a custom statblock and save it to the Bestiary.",
      onClick = function() app:showCreator({ returnTo = "menu" }) end,
    }),
    ui.Button.new({
      x = 180, y = 572, w = 440, h = 52,
      label = "How to Play", hotkey = "H",
      tooltip = "Controls, turn options, and the rules used by the simulator.",
      onClick = function() app:showHelp() end,
    }),
    ui.Button.new({
      x = 280, y = 640, w = 240, h = 32,
      label = "Quit", style = "ghost",
      onClick = function() love.event.quit() end,
    }),
  }
  return self
end

function Screen:_buildRoster()
  local entries = {}
  local pcs, npcs = 0, 0
  local roster = {}
  if self.app.makeDefaultRoster then
    roster = self.app:makeDefaultRoster() or {}
  end
  for _, item in ipairs(roster) do
    local data = self.app.database and self.app.database:get(item.key)
    local isPC = item.side == "pc"
    entries[#entries + 1] = {
      name = data and data.name or tostring(item.key),
      isPC = isPC,
    }
    if isPC then
      pcs = pcs + 1
    else
      npcs = npcs + 1
    end
  end
  self.rosterEntries = entries
  self.pcCount = pcs
  self.npcCount = npcs
end

function Screen:enter(params)
  self.time = 0
  self.speedDropdown:close()
  self.speedDropdown:setValue(speedLabelFor(self.app.settings.speed))
  self.aiCheckbox.checked = self.app.settings.autoNpc == true
  self.threatCheckbox.checked = self.app.settings.showThreats == true
  self.pillarCheckbox.checked = self.app.settings.pillars == true
  for _, button in ipairs(self.buttons) do
    button._pressed = false
    button.hover = false
  end
  self:_buildRoster()
end

function Screen:leave()
  self.speedDropdown:close()
end

function Screen:update(dt)
  self.time = self.time + (dt or 0)
end

function Screen:_drawTitle()
  theme.drawText("PATHFINDER", 722, 66, "title", { 0, 0, 0, 0.6 }, "center")
  theme.drawText("PATHFINDER", 720, 64, "title", theme.colors.gold, "center")
  drawTracked("BATTLE SIMULATOR", 720, 122, "h2", theme.colors.textMuted, 5)
  drawRule(720, 166, 250, theme.colors.goldDark, 0.9, 6)
  theme.drawText("Initiative, steel, and the dice decide.", 720, 180,
    "italic", { 0.60, 0.62, 0.68, 0.9 }, "center")
end

function Screen:_drawPanels()
  theme.drawPanel(LEFT_X, CARD_TOP, LEFT_W, CARD_HEIGHT, {
    title = "The Adventurer's Path",
    fill = { 0.072, 0.080, 0.104, 0.96 },
    border = theme.colors.border,
  })
  drawCornerBrackets(LEFT_X + 5, CARD_TOP + 5, LEFT_W - 10, CARD_HEIGHT - 10,
    16, theme.colors.goldDark, 0.55)

  theme.drawPanel(RIGHT_X, CARD_TOP, RIGHT_W, CARD_HEIGHT, {
    title = "Table Rules",
    fill = { 0.072, 0.080, 0.104, 0.96 },
    border = theme.colors.border,
  })
  drawCornerBrackets(RIGHT_X + 5, CARD_TOP + 5, RIGHT_W - 10, CARD_HEIGHT - 10,
    16, theme.colors.goldDark, 0.55)

  local left = RIGHT_X + 20
  local width = RIGHT_W - 40
  local muted = theme.colors.textMuted

  theme.drawText("Monsters act on their own. Uncheck to command both sides yourself.",
    left, 344, "small", muted, "left", width)
  theme.drawText("Tint squares enemies threaten. Useful for avoiding attacks of opportunity.",
    left, 408, "small", muted, "left", width)
  theme.drawText("Add blocked stone pillars to the battlefield. Cover is not modeled.",
    left, 472, "small", muted, "left", width)

  theme.drawText("AI speed", left, 519, "bodyBold", theme.colors.text)
  theme.drawText("Delay between AI actions. Normal is recommended.",
    left, 552, "small", muted, "left", width)

  self:_drawDefaultEncounter()
end

function Screen:_drawDefaultEncounter()
  local x, y, w, h = 760, 578, 520, 96
  theme.drawPanel(x, y, w, h, {
    fill = { 0.108, 0.120, 0.148, 0.82 },
    border = theme.colors.border,
    radius = 6,
    shadow = false,
  })

  theme.drawText("Default encounter", x + 16, 586, "smallBold", theme.colors.gold)

  local tiny = theme.fonts.tiny
  local pcText = string.format("PCs %d", self.pcCount)
  local npcText = string.format("Monsters %d", self.npcCount)
  local pcW = tiny:getWidth(pcText) + 14
  local npcW = tiny:getWidth(npcText) + 14
  local right = x + w - 16
  theme.drawPill(right - npcW, 583, npcW, 20, npcText, theme.colors.red, "tiny")
  theme.drawPill(right - npcW - 6 - pcW, 583, pcW, 20, pcText,
    theme.colors.green, "tiny")

  local pillX = x + 16
  local maxX = x + w - 16
  local shown = 0
  for _, entry in ipairs(self.rosterEntries) do
    local pillW = tiny:getWidth(entry.name) + 14
    if pillX + pillW > maxX then break end
    theme.drawPill(pillX, 612, pillW, 22, entry.name,
      entry.isPC and theme.colors.green or theme.colors.red, "tiny")
    pillX = pillX + pillW + 6
    shown = shown + 1
  end

  local extra = #self.rosterEntries - shown
  if extra > 0 then
    local label = "+" .. extra .. " more"
    local pillW = tiny:getWidth(label) + 14
    if pillX + pillW <= maxX then
      theme.drawPill(pillX, 612, pillW, 22, label,
        theme.colors.textMuted, "tiny")
    end
  end

  if #self.rosterEntries == 0 then
    theme.drawText("No roster available.", x + 16, 614, "small",
      theme.colors.textMuted)
  end

  theme.drawText("Quick Battle deploys this roster on a 20 x 14 grid.",
    x + 16, 645, "tiny", theme.colors.textMuted)
end

function Screen:_drawFooter()
  theme.setColor(theme.colors.border, 0.4)
  love.graphics.setLineWidth(1)
  love.graphics.line(LEFT_X, 836, RIGHT_X + RIGHT_W, 836)

  local version = constants.VERSION or "1.0.0"
  theme.drawText("v" .. tostring(version), LEFT_X, 848, "small",
    theme.colors.textMuted)
  theme.drawText("Pathfinder 1e tabletop ruleset", RIGHT_X + RIGHT_W, 848,
    "small", theme.colors.textMuted, "right")

  theme.drawText("The dice are neutral. The dungeon is not.", 720, 742,
    "italic", { 0.55, 0.58, 0.65, 0.78 }, "center")
  drawRule(720, 782, 130, theme.colors.goldDark, 0.4, 4)
end

function Screen:draw()
  drawBackdrop()
  drawTorchGlow(120, 100, self.time, 0)
  drawTorchGlow(1320, 100, self.time, 2.2)
  drawDust(self.motes, self.time)

  self:_drawTitle()
  self:_drawPanels()

  for _, checkbox in ipairs(self.checkboxes) do
    checkbox:draw()
  end
  for _, button in ipairs(self.buttons) do
    button:draw()
  end

  self:_drawFooter()
  self.speedDropdown:draw()
end

function Screen:mousepressed(x, y, button)
  if self.speedDropdown:mousepressed(x, y, button) then return true end
  for _, checkbox in ipairs(self.checkboxes) do
    if checkbox:mousepressed(x, y, button) then return true end
  end
  for _, button in ipairs(self.buttons) do
    if button:mousepressed(x, y, button) then return true end
  end
  return false
end

function Screen:mousereleased(x, y, button)
  for _, button in ipairs(self.buttons) do
    button:mousereleased(x, y, button)
  end
end

function Screen:keypressed(key, scancode, isrepeat)
  if self.speedDropdown.open and key == "escape" then
    self.speedDropdown:close()
    return true
  end
  key = tostring(key or ""):lower()
  if key == "q" then
    self.app:startQuickBattle({})
  elseif key == "b" then
    self.app:showSetup()
  elseif key == "l" then
    self.app:showBestiary("menu")
  elseif key == "c" then
    self.app:showCreator({ returnTo = "menu" })
  elseif key == "h" then
    self.app:showHelp()
  else
    return false
  end
  return true
end

function Screen:wheelmoved(dx, dy)
  return false
end

function Screen:textinput(text)
  return false
end

return Screen
