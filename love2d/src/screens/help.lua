-- Scrollable field manual: controls, turn options, and simulator rules.
local theme = require("src.ui.theme")
local ui = require("src.ui.widgets")
local constants = require("src.core.constants")

local Screen = {}
Screen.__index = Screen

local VIEW = { x = 40, y = 162, w = 900, h = 700 }
local RAIL = { x = 968, y = 162, w = 410, h = 700 }
local SCROLLBAR = { x = 1392, y = 162, w = 8, h = 700 }
local TEXT_WIDTH = 900

local CONDITION_KEYS = {
  "prone", "grappled", "shaken", "sickened", "blinded", "stunned",
  "entangled", "fatigued", "disabled", "dying", "stable", "flat-footed",
}

local function conditionBullets()
  local items = {}
  for _, key in ipairs(CONDITION_KEYS) do
    local condition = constants.Conditions[key]
    if condition then
      items[#items + 1] = condition.label .. ": " .. condition.help
    end
  end
  return items
end

local SECTIONS = {
  {
    title = "Overview",
    blocks = {
      { type = "p", text = "Choose a prebuilt encounter from the main menu or assemble one in Setup. Combat runs on a square grid with Pathfinder 1e initiative, actions, attacks of opportunity, conditions, and dying." },
      { type = "p", text = "The battle screen can hand the monsters' turns to the AI or auto-resolve a fight. Turn AI control off to command both sides yourself." },
    },
  },
  {
    title = "Setup",
    blocks = {
      { type = "p", text = "Add heroes and monsters to either side, choose the grid size, toggle pillars and awareness, then start combat. Heroes can carry healing potions. Entries can be duplicated or removed before the first initiative roll." },
      { type = "bullets", items = {
        "Bestiary statblocks can be placed on either side. Custom monsters are built in the Creator.",
        "Pillars block squares and break movement. They do not grant cover in this simulator.",
        "If one side is unaware, the other may act in a surprise round.",
      } },
    },
  },
  {
    title = "Turn Controls",
    blocks = {
      { type = "p", text = "Click a token or an initiative entry to inspect or target a combatant. Choose the attack in the dropdown before using Attack or Full Attack. Hover over tokens, conditions, and buttons for tooltips." },
      { type = "bullets", items = {
        "Attack: one standard-action attack against the selected enemy.",
        "Full Attack: a full-round action using every iterative or natural attack.",
        "Move: click a green highlighted square. Step: click an adjacent square for a 5-foot step.",
        "Withdraw: retreat at double speed. The first square does not provoke.",
        "Charge: move in a straight line and strike with +2 attack and -2 AC.",
        "End Turn (N): pass to the next combatant. Escape opens the pause menu.",
      } },
      { type = "note", text = "Maneuvers: Trip, Disarm, Grapple, Bull Rush, and Sunder." },
      { type = "note", text = "Utility: Stand Up, Total Defense, Drink Potion, Draw Weapon, Stabilize, Aid Another, Escape Grapple, and Drop Prone." },
      { type = "note", text = "Keyboard: A Attack, F Full Attack, M Move, T 5-ft Step, W Withdraw, C Charge, 1-5 maneuvers, V Total Defense, U Stand Up, P Drink Potion, K Draw Weapon, G Aid Another, Z Stabilize, E Escape Grapple, X Drop Prone, N End Turn, Tab cycles attacks." },
      { type = "p", text = "Drink Potion consumes one of a hero's potions of cure light wounds (1d8+1). The combat log scrolls with the mouse wheel and records every roll, condition, and turn change." },
    },
  },
  {
    title = "Rules Notes",
    blocks = {
      { type = "p", text = "These are the Pathfinder 1e rules the simulator applies. Where a rule is not modeled, the note says so." },
      { type = "bullets", items = {
        "Attacks: d20 + BAB + ability and size modifiers versus AC. A natural 1 always misses; a natural 20 always hits.",
        "Critical hits: a roll inside the weapon's threat range threatens. A confirmation roll against AC decides whether damage is multiplied.",
        "Iteratives: BAB +6, +11, and +16 add attacks at -5, -10, and -15. Full Attack uses up to four attacks.",
        "Two-weapon fighting: off-hand attacks use half Strength on damage, and two-weapon penalties should be built into the statblock's attack entries. Multiple natural weapons are each used in a Full Attack.",
        "Damage reduction reduces physical damage unless the attack type bypasses it. Resistance, immunity, and vulnerability apply to typed energy damage.",
        "Ranged attacks provoke an attack of opportunity. Movement provokes once per provoking enemy per action, not once per square.",
        "A 5-foot step never provokes. The first square of a withdraw does not provoke either.",
        "Prone: -4 on melee attacks and -4 AC against melee, but +4 AC against ranged attacks. Standing up provokes.",
        "Cover is not modeled. Pillars simply block movement.",
        "Surprise: when awareness differs between sides, only aware creatures act in the surprise round. Everyone is flat-footed until their first turn.",
        "Dying: below 0 HP a creature is unconscious and dying. It dies when its negative HP reaches its Constitution score.",
        "Stabilization: a dying creature checks each turn with a Constitution check against DC 10 + its negative HP. Failure costs 1 HP; a natural 20 succeeds.",
        "Disabled: at exactly 0 HP a creature may take only one move or standard action, and a standard action costs 1 HP.",
        "Maneuvers: d20 + CMB versus CMD. A natural 20 succeeds and a natural 1 fails. Improved Trip, Disarm, Grapple, Bull Rush, and Sunder avoid the provoking attack.",
        "Attacks of opportunity: one per round by default. Combat Reflexes adds extra attacks equal to the Dexterity modifier. Flat-footed creatures cannot make them.",
        "Feats: Dodge adds +1 AC, Weapon Focus +1 attack, Weapon Finesse uses Dex for melee attacks, Weapon Specialization +2 damage, and Improved Initiative +4 initiative.",
      } },
    },
  },
  {
    title = "Conditions",
    blocks = {
      { type = "p", text = "The most common conditions are listed below. Exhausted, dazed, frightened, nauseated, paralyzed, and unconscious can also appear on statblocks." },
      { type = "bullets", items = conditionBullets() },
    },
  },
  {
    title = "Credits",
    blocks = {
      { type = "p", text = "Built with Love2D 11.5 and LuaJIT. Interface text uses the DejaVu font family, distributed under the Bitstream Vera license." },
      { type = "p", text = "Rules are inspired by the Pathfinder 1e System Reference Document and are summarized for this simulator. No copyrighted rulebook text is reproduced verbatim." },
    },
  },
}

local function clamp(value, low, high)
  if value < low then return low end
  if value > high then return high end
  return value
end

local function drawBackdrop()
  local bands = 32
  local bandHeight = theme.height / bands
  for i = 0, bands - 1 do
    local t = i / (bands - 1)
    theme.setColor({
      0.030 + 0.034 * t,
      0.036 + 0.040 * t,
      0.052 + 0.044 * t,
    })
    love.graphics.rectangle("fill", 0, i * bandHeight,
      theme.width, bandHeight + 1)
  end

  local strips = 18
  for i = 1, strips do
    local inset = (i - 1) * 10
    local strength = 1 - (i - 1) / strips
    theme.setColor(theme.colors.black, 0.030 * strength * strength)
    love.graphics.rectangle("fill", inset, inset,
      theme.width - inset * 2, 10)
    love.graphics.rectangle("fill", inset, theme.height - inset - 10,
      theme.width - inset * 2, 10)
  end

  theme.setColor(theme.colors.gold, 0.018)
  love.graphics.setLineWidth(1)
  for i = 0, 6 do
    love.graphics.line(0, 150 + i * 120, theme.width, 30 + i * 120)
  end
end

function Screen.new(app)
  local self = setmetatable({}, Screen)
  self.app = app
  self.scroll = 0
  self.layout = nil
  self._layoutWidth = nil
  self.contentHeight = 0

  self.backButton = ui.Button.new({
    x = 1232, y = 20, w = 176, h = 40,
    label = "Back to Menu", hotkey = "Esc",
    tooltip = "Return to the main menu. You can also press Escape.",
    onClick = function() app:showMenu() end,
  })
  return self
end

function Screen:enter(params)
  self.scroll = 0
  self:_ensureLayout()
  self.backButton._pressed = false
  self.backButton.hover = false
end

function Screen:leave()
end

function Screen:update(dt)
end

function Screen:_ensureLayout()
  if self.layout and self._layoutWidth == TEXT_WIDTH then return end

  local entries = {}
  local h3 = theme.getFont("h3")
  local body = theme.getFont("body")
  local small = theme.getFont("small")
  local h3Height = h3:getHeight()
  local bodyHeight = body:getHeight()
  local smallHeight = small:getHeight()
  local y = 4

  for index, section in ipairs(SECTIONS) do
    if index > 1 then
      entries[#entries + 1] = {
        kind = "separator", y = y + 16, height = 1,
      }
      y = y + 44
    end

    entries[#entries + 1] = {
      kind = "heading", text = section.title, y = y,
      font = h3, height = h3Height,
    }
    y = y + h3Height + 12

    for _, block in ipairs(section.blocks) do
      if block.type == "p" then
        local lines = theme.wrap(block.text, body, TEXT_WIDTH)
        local height = #lines * bodyHeight
        entries[#entries + 1] = {
          kind = "lines", y = y, lines = lines, font = body,
          color = theme.colors.text, lineHeight = bodyHeight, height = height,
        }
        y = y + height + 11
      elseif block.type == "bullets" then
        for _, text in ipairs(block.items) do
          local lines = theme.wrap(text, body, TEXT_WIDTH - 20)
          local height = #lines * bodyHeight
          entries[#entries + 1] = {
            kind = "bullet", y = y, lines = lines, font = body,
            color = theme.colors.text, lineHeight = bodyHeight, height = height,
          }
          y = y + height + 7
        end
        y = y + 3
      elseif block.type == "note" then
        local lines = theme.wrap(block.text, small, TEXT_WIDTH - 18)
        local height = #lines * smallHeight
        entries[#entries + 1] = {
          kind = "note", y = y, lines = lines, font = small,
          color = theme.colors.textMuted, lineHeight = smallHeight,
          height = height,
        }
        y = y + height + 9
      end
    end
  end

  self.layout = entries
  self._layoutWidth = TEXT_WIDTH
  self.contentHeight = y + 16
end

function Screen:_maxScroll()
  self:_ensureLayout()
  return math.max(0, self.contentHeight - VIEW.h)
end

function Screen:_drawTopBar()
  theme.setColor({ 0.040, 0.047, 0.064, 0.95 })
  love.graphics.rectangle("fill", 0, 0, theme.width, 80)
  theme.setColor(theme.colors.goldDark)
  love.graphics.rectangle("fill", 22, 18, 3, 32, 1, 1)
  theme.setColor(theme.colors.border, 0.6)
  love.graphics.line(0, 80.5, theme.width, 80.5)

  theme.drawText("How to Play", 36, 14, "h1", theme.colors.gold)
  theme.drawText("Controls, actions, and Pathfinder 1e rules used by the simulator",
    36, 52, "small", theme.colors.textMuted)
end

function Screen:_drawMainPanel()
  theme.drawPanel(16, 84, 1408, 800, {
    title = "Field Manual",
    padding = 18,
    fill = { 0.072, 0.081, 0.105, 0.97 },
    border = theme.colors.border,
  })

  theme.drawText(
    "Scroll with the mouse wheel or arrow keys. Home and End jump to the top or bottom.",
    VIEW.x, 132, "small", theme.colors.textMuted)
  theme.drawText("Esc returns to the menu", 1400, 132, "small",
    theme.colors.goldDark, "right")

  theme.setColor(theme.colors.border, 0.4)
  love.graphics.setLineWidth(1)
  love.graphics.line(VIEW.x, 154, 1400, 154)
end

function Screen:_drawQuickReference()
  local contentY = theme.drawPanel(RAIL.x, RAIL.y, RAIL.w, RAIL.h, {
    title = "Quick Reference",
    padding = 16,
    fill = { 0.078, 0.088, 0.113, 0.94 },
    border = theme.colors.border,
  })

  local left = RAIL.x + 18
  local innerWidth = RAIL.w - 36
  local cursor = contentY
  local muted = theme.colors.textMuted

  local function heading(text)
    theme.drawText(text, left, cursor, "smallBold", theme.colors.gold)
    cursor = cursor + 23
  end

  local function divider()
    theme.setColor(theme.colors.border, 0.45)
    love.graphics.line(left, cursor, RAIL.x + RAIL.w - 18, cursor)
    cursor = cursor + 11
  end

  local function row(text)
    theme.drawText(text, left, cursor, "small", theme.colors.text,
      "left", innerWidth)
    cursor = cursor + 21
  end

  heading("Controls")
  local controls = {
    { "Wheel", "Scroll this manual or the battle log." },
    { "N", "End the current turn." },
    { "Esc", "Pause battle or return to the menu." },
    { "Hover", "Show tooltips for tokens and controls." },
  }
  for _, item in ipairs(controls) do
    theme.drawPill(left, cursor, 56, 20, item[1], theme.colors.gold, "tiny")
    theme.drawText(item[2], left + 66, cursor + 1, "small",
      theme.colors.text, "left", innerWidth - 66)
    cursor = cursor + 26
  end

  divider()
  heading("Core Numbers")
  row("Attack: d20 + BAB + ability and size vs AC.")
  row("Saving throw: d20 + base save + ability vs DC.")
  row("CMB vs CMD: d20 + BAB + Str + size vs CMD.")
  row("Initiative: d20 + Dex (+4 Improved Initiative).")
  row("Critical: threaten, then confirm against AC.")
  row("Stabilize: d20 + Con vs DC 10 + negative HP.")

  divider()
  heading("Movement")
  row("5-foot step: one square, never provokes.")
  row("Withdraw: the first square does not provoke.")
  row("Movement: provokes once per enemy per action.")

  divider()
  heading("Actions")
  local actions = {
    { "Standard", theme.colors.gold },
    { "Move", theme.colors.blue },
    { "Swift", theme.colors.green },
    { "Full Round", theme.colors.purple },
  }
  local pillX = left
  local tiny = theme.fonts.tiny
  for _, action in ipairs(actions) do
    local pillWidth = tiny:getWidth(action[1]) + 14
    theme.drawPill(pillX, cursor, pillWidth, 20, action[1], action[2], "tiny")
    pillX = pillX + pillWidth + 6
  end
  cursor = cursor + 26

  divider()
  heading("At the Table")
  local tips = {
    "Focus fire: removing an enemy early deletes its turns.",
    "A 5-foot step keeps you in reach without provoking.",
    "Prone targets are easy to hit in melee, hard to shoot.",
  }
  for _, tip in ipairs(tips) do
    theme.setColor(theme.colors.goldDark)
    love.graphics.polygon("fill", left, cursor + 8, left + 3, cursor + 11,
      left, cursor + 14, left - 3, cursor + 11)
    local nextY = theme.drawText(tip, left + 12, cursor, "small", muted,
      "left", innerWidth - 12)
    cursor = nextY + 8
  end
end

function Screen:_drawContent()
  local maxScroll = self:_maxScroll()
  self.scroll = clamp(self.scroll, 0, maxScroll)

  love.graphics.setScissor(VIEW.x, VIEW.y, VIEW.w, VIEW.h)
  local originY = VIEW.y - self.scroll
  local clipTop = VIEW.y - 2
  local clipBottom = VIEW.y + VIEW.h + 2

  for _, entry in ipairs(self.layout) do
    local y = originY + entry.y
    if y + (entry.height or 0) >= clipTop and y <= clipBottom then
      if entry.kind == "heading" then
        theme.setColor(theme.colors.goldDark)
        love.graphics.polygon("fill",
          VIEW.x + 4, y + 10, VIEW.x + 9, y + 5,
          VIEW.x + 14, y + 10, VIEW.x + 9, y + 15)
        theme.drawText(entry.text, VIEW.x + 22, y, entry.font,
          theme.colors.gold)
      elseif entry.kind == "separator" then
        theme.setColor(theme.colors.border, 0.4)
        love.graphics.setLineWidth(1)
        love.graphics.line(VIEW.x, math.floor(y + 0.5),
          VIEW.x + VIEW.w, math.floor(y + 0.5))
      elseif entry.kind == "lines" then
        theme.setColor(entry.color)
        love.graphics.setFont(entry.font)
        for i, line in ipairs(entry.lines) do
          love.graphics.print(line, VIEW.x,
            math.floor(y + (i - 1) * entry.lineHeight + 0.5))
        end
      elseif entry.kind == "bullet" then
        theme.setColor(theme.colors.goldDark)
        local bx = VIEW.x + 7
        local by = y + entry.lineHeight * 0.5
        love.graphics.polygon("fill", bx, by - 3, bx + 3, by,
          bx, by + 3, bx - 3, by)
        theme.setColor(entry.color)
        love.graphics.setFont(entry.font)
        for i, line in ipairs(entry.lines) do
          love.graphics.print(line, VIEW.x + 20,
            math.floor(y + (i - 1) * entry.lineHeight + 0.5))
        end
      elseif entry.kind == "note" then
        theme.setColor(theme.colors.goldDark, 0.7)
        love.graphics.rectangle("fill", VIEW.x + 4, y + 2, 2,
          math.max(1, entry.height - 4), 1, 1)
        theme.setColor(entry.color)
        love.graphics.setFont(entry.font)
        for i, line in ipairs(entry.lines) do
          love.graphics.print(line, VIEW.x + 16,
            math.floor(y + (i - 1) * entry.lineHeight + 0.5))
        end
      end
    end
  end
  love.graphics.setScissor()
end

function Screen:_drawScrollbar()
  local maxScroll = self:_maxScroll()
  local thumbHeight = SCROLLBAR.h
  if self.contentHeight > VIEW.h then
    thumbHeight = math.max(40, SCROLLBAR.h * (VIEW.h / self.contentHeight))
  end

  theme.setColor(theme.colors.black, 0.30)
  love.graphics.rectangle("fill", SCROLLBAR.x, SCROLLBAR.y,
    SCROLLBAR.w, SCROLLBAR.h, 4, 4)

  local thumbY = SCROLLBAR.y
  if maxScroll > 0 then
    thumbY = SCROLLBAR.y +
      (self.scroll / maxScroll) * (SCROLLBAR.h - thumbHeight)
  end
  theme.setColor(theme.colors.gold, maxScroll > 0 and 0.62 or 0.28)
  love.graphics.rectangle("fill", SCROLLBAR.x, thumbY,
    SCROLLBAR.w, thumbHeight, 4, 4)
end

function Screen:draw()
  drawBackdrop()
  self:_drawTopBar()
  self:_drawMainPanel()
  self:_drawQuickReference()
  self:_drawContent()
  self:_drawScrollbar()
  self.backButton:draw()
end

function Screen:mousepressed(x, y, button)
  if self.backButton:mousepressed(x, y, button) then return true end
  return false
end

function Screen:mousereleased(x, y, button)
  self.backButton:mousereleased(x, y, button)
end

function Screen:keypressed(key, scancode, isrepeat)
  if key == "escape" then
    self.app:showMenu()
    return true
  end

  local maxScroll = self:_maxScroll()
  local page = VIEW.h * 0.85
  if key == "up" then
    self.scroll = clamp(self.scroll - 48, 0, maxScroll)
  elseif key == "down" then
    self.scroll = clamp(self.scroll + 48, 0, maxScroll)
  elseif key == "pageup" then
    self.scroll = clamp(self.scroll - page, 0, maxScroll)
  elseif key == "pagedown" then
    self.scroll = clamp(self.scroll + page, 0, maxScroll)
  elseif key == "home" then
    self.scroll = 0
  elseif key == "end" then
    self.scroll = maxScroll
  else
    return false
  end
  return true
end

function Screen:wheelmoved(dx, dy)
  local maxScroll = self:_maxScroll()
  if maxScroll <= 0 then return true end
  if dy and dy ~= 0 then
    self.scroll = clamp(self.scroll - dy * 72, 0, maxScroll)
    return true
  end
  return false
end

function Screen:textinput(text)
  return false
end

return Screen
