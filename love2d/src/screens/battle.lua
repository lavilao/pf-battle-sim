local theme = require("src.ui.theme")
local ui = require("src.ui.widgets")
local constants = require("src.core.constants")
local positioning = require("src.core.positioning")
local CombatEngine = require("src.core.combat_engine")
local ActionHandler = require("src.core.action_handler")
local AI = require("src.core.ai")

local BattleScreen = {}
BattleScreen.__index = BattleScreen

local TOP_H = 64
local GRID_X, GRID_Y, GRID_W, GRID_H = 312, 80, 732, 540
local INIT_X, INIT_Y, INIT_W, INIT_H = 16, 80, 280, 804
local ACTION_X, ACTION_Y, ACTION_W, ACTION_H = 312, 632, 732, 252
local DETAIL_X, DETAIL_Y, DETAIL_W, DETAIL_H = 1056, 80, 368, 396
local LOG_X, LOG_Y, LOG_W, LOG_H = 1056, 492, 368, 392
local INIT_ROW_H = 48
local INIT_ROWS_Y = 168
local INIT_VISIBLE = 12

local LOG_COLORS = {
  header = theme.colors.gold,
  crit = theme.colors.orange,
  hit = theme.colors.text,
  miss = theme.colors.textMuted,
  death = theme.colors.red,
  aoo = theme.colors.purple,
  heal = theme.colors.green,
  maneuver = theme.colors.blue,
  save = theme.colors.blue,
  system = theme.colors.textMuted,
  info = theme.colors.text,
}

local CONDITION_COLORS = {
  prone = theme.colors.orange,
  grappled = theme.colors.purple,
  pinned = theme.colors.purple,
  stunned = theme.colors.blue,
  dazed = theme.colors.blue,
  blinded = theme.colors.textMuted,
  dying = theme.colors.red,
  stable = theme.colors.green,
  disabled = theme.colors.red,
  frightened = theme.colors.orange,
  shaken = theme.colors.orange,
  sickened = theme.colors.green,
  entangled = theme.colors.green,
  fatigued = theme.colors.orange,
  exhausted = theme.colors.red,
  unconscious = theme.colors.red,
  helpless = theme.colors.red,
  charge = theme.colors.gold,
  ["flat-footed"] = theme.colors.textMuted,
}

local function clamp(value, low, high)
  if value < low then return low end
  if value > high then return high end
  return value
end

local function signed(value)
  local n = math.floor(tonumber(value) or 0)
  if n >= 0 then return "+" .. n end
  return tostring(n)
end

local function conditionLabel(key)
  local info = constants.Conditions[key]
  return info and info.label or tostring(key)
end

local function combatantAlive(c)
  return c ~= nil and not c:isDead()
end

function BattleScreen.new(app)
  local self = setmetatable({}, BattleScreen)
  self.app = app
  self.engine = nil
  self.handler = nil
  self.ai = nil
  self.config = nil
  self.selected = nil
  self.attackChoice = 1
  self.mode = nil
  self.moveCells = nil
  self.autoBattle = false
  self.paused = false
  self.resultVisible = false
  self.resultShown = false
  self.npcTimer = 0
  self.endTurnTimer = 1
  self.turnKey = nil
  self.message = nil
  self.messageTimer = 0
  self.messageKind = "info"
  self.banner = nil
  self.logLines = {}
  self.logVersion = -1
  self.logScroll = 0
  self.initScroll = 0
  self._map = nil
  self:_buildStaticWidgets()
  return self
end

function BattleScreen:_buildStaticWidgets()
  local function topButton(opts)
    local button = ui.Button.new(opts)
    self.topButtons[#self.topButtons + 1] = button
    return button
  end

  self.topButtons = {}
  self.topAutoNpc = topButton({
    x = 1020, y = 16, w = 138, h = 32,
    label = "AI Monsters: On", style = "default", font = "smallBold",
    tooltip = "Let the computer run monster turns. Toggle during battle if you want to take command.",
    onClick = function()
      self.app.settings.autoNpc = not self.app.settings.autoNpc
      if self.app.settings.autoNpc then
        self.npcTimer = math.min(self.npcTimer or 0.4, 0.4)
      end
    end,
  })
  self.topAutoBattle = topButton({
    x = 1164, y = 16, w = 134, h = 32,
    label = "Auto Battle: Off", style = "default", font = "smallBold",
    tooltip = "Let the AI run every combatant until the battle ends.",
    onClick = function()
      self.autoBattle = not self.autoBattle
      if self.autoBattle then
        self.npcTimer = math.min(self.npcTimer or 0.4, 0.4)
      end
    end,
  })
  self.topPause = topButton({
    x = 1304, y = 16, w = 120, h = 32,
    label = "Pause", style = "ghost", font = "smallBold",
    tooltip = "Pause the battle, restart it, or return to the menu.",
    onClick = function()
      if self.engine and self.engine.ended then
        self.resultVisible = true
      else
        self.paused = true
      end
    end,
  })

  self.actionButtons = {}
  self.actionButtonList = {}

  local ACTIONS = {
    { id = "attack", label = "Attack", x = 328, y = 704, h = 34,
      tooltip = "Standard action: attack the selected enemy with the chosen attack (A)." },
    { id = "full", label = "Full Attack", x = 445, y = 704, h = 34,
      tooltip = "Full-round action: use every iterative or natural attack (F)." },
    { id = "move", label = "Move", x = 562, y = 704, h = 34,
      tooltip = "Move action: choose a highlighted square (M)." },
    { id = "step", label = "5-ft Step", x = 679, y = 704, h = 34,
      tooltip = "Move exactly one square without provoking (T)." },
    { id = "withdraw", label = "Withdraw", x = 796, y = 704, h = 34,
      tooltip = "Full-round action: retreat at double speed; the first square does not provoke (W)." },
    { id = "charge", label = "Charge", x = 913, y = 704, h = 34,
      tooltip = "Full-round action: charge the selected enemy in a straight line (C)." },

    { id = "trip", label = "Trip", x = 328, y = 742, h = 34,
      tooltip = "Combat maneuver: knock the selected enemy prone (1)." },
    { id = "disarm", label = "Disarm", x = 445, y = 742, h = 34,
      tooltip = "Combat maneuver: knock a weapon from the selected enemy (2)." },
    { id = "grapple", label = "Grapple", x = 562, y = 742, h = 34,
      tooltip = "Combat maneuver: grapple the selected enemy (3)." },
    { id = "bull_rush", label = "Bull Rush", x = 679, y = 742, h = 34,
      tooltip = "Combat maneuver: push the selected enemy back (4)." },
    { id = "sunder", label = "Sunder", x = 796, y = 742, h = 34,
      tooltip = "Combat maneuver: damage the selected enemy's weapon (5)." },
    { id = "defense", label = "Total Defense", x = 913, y = 742, h = 34,
      tooltip = "Standard action: +4 dodge AC until your next turn (V)." },

    { id = "stand", label = "Stand Up", x = 328, y = 780, h = 34,
      tooltip = "Move action: stand from prone. This provokes attacks of opportunity (U)." },
    { id = "potion", label = "Drink Potion", x = 445, y = 780, h = 34,
      tooltip = "Standard action: drink a potion of cure light wounds. This provokes (P)." },
    { id = "draw", label = "Draw Weapon", x = 562, y = 780, h = 34,
      tooltip = "Move action: recover a dropped or disarmed weapon (K)." },
    { id = "aid", label = "Aid Another", x = 679, y = 780, h = 34,
      tooltip = "Standard action: grant an ally +2 against the selected enemy (G)." },
    { id = "stabilize", label = "Stabilize", x = 796, y = 780, h = 34,
      tooltip = "Standard action: attempt first aid on a selected dying ally (Z)." },
    { id = "escape", label = "Escape", x = 913, y = 780, h = 34,
      tooltip = "Standard action: break free of a grapple (E)." },

    { id = "drop", label = "Drop Prone", x = 328, y = 818, h = 34,
      tooltip = "Free action: drop to the ground (X)." },
    { id = "end", label = "End Turn", x = 445, y = 818, w = 230, h = 34,
      tooltip = "End the current turn and pass to the next combatant (N)." },
  }

  for _, def in ipairs(ACTIONS) do
    local button = ui.Button.new({
      x = def.x, y = def.y, w = def.w or 112, h = def.h,
      label = def.label,
      style = def.id == "end" and "primary" or (def.id == "attack" and "default" or "default"),
      font = "smallBold",
      tooltip = def.tooltip,
      onClick = function() self:_runAction(def.id) end,
    })
    self.actionButtons[def.id] = button
    self.actionButtonList[#self.actionButtonList + 1] = button
  end

  self.attackCycle = ui.Button.new({
    x = 668, y = 666, w = 352, h = 28,
    label = "Attack: none", style = "ghost", font = "smallBold",
    hotkey = "Tab",
    tooltip = "Cycle the weapon or natural attack used by Attack and Full Attack.",
    onClick = function() self:_cycleAttack() end,
  })

  self.pauseButtons = {}
  local function pauseButton(opts)
    local button = ui.Button.new(opts)
    self.pauseButtons[#self.pauseButtons + 1] = button
    return button
  end
  pauseButton({
    x = 520, y = 344, w = 400, h = 44, label = "Resume", style = "primary",
    font = "bodyBold", onClick = function() self.paused = false end,
  })
  pauseButton({
    x = 520, y = 400, w = 400, h = 44, label = "Restart Battle", style = "default",
    font = "bodyBold", onClick = function() self:_restartBattle() end,
  })
  pauseButton({
    x = 520, y = 456, w = 400, h = 44, label = "Encounter Setup", style = "default",
    font = "bodyBold", onClick = function() self.app:showSetup() end,
  })
  pauseButton({
    x = 520, y = 512, w = 400, h = 44, label = "Main Menu", style = "ghost",
    font = "bodyBold", onClick = function() self.app:showMenu() end,
  })

  self.resultButtons = {}
  local function resultButton(opts)
    local button = ui.Button.new(opts)
    self.resultButtons[#self.resultButtons + 1] = button
    return button
  end
  resultButton({
    x = 450, y = 520, w = 270, h = 46, label = "Rematch", style = "primary",
    font = "bodyBold", onClick = function() self:_restartBattle() end,
  })
  resultButton({
    x = 736, y = 520, w = 270, h = 46, label = "Review Field", style = "default",
    font = "bodyBold", onClick = function() self.resultVisible = false end,
  })
  resultButton({
    x = 450, y = 578, w = 270, h = 46, label = "Encounter Setup", style = "default",
    font = "bodyBold", onClick = function() self.app:showSetup() end,
  })
  resultButton({
    x = 736, y = 578, w = 270, h = 46, label = "Main Menu", style = "ghost",
    font = "bodyBold", onClick = function() self.app:showMenu() end,
  })
end

function BattleScreen:enter(config)
  self:_setupBattle(config)
end

function BattleScreen:leave()
end

function BattleScreen:_setupBattle(config)
  config = config or self.config or {}
  self.config = config
  self.autoBattle = config.autoBattle == true
  self.paused = false
  self.resultVisible = false
  self.resultShown = false
  self.selected = nil
  self.attackChoice = 1
  self.mode = nil
  self.moveCells = nil
  self.turnKey = nil
  self.npcTimer = 0
  self.endTurnTimer = 1
  self.message = nil
  self.messageTimer = 0
  self.banner = nil
  self.logLines = {}
  self.logVersion = -1
  self.logScroll = 0
  self.initScroll = 0

  local gridW = tonumber(config.gridW) or 20
  local gridH = tonumber(config.gridH) or 14
  local blocked = {}
  if config.pillars then
    local coords = {
      { math.floor(gridW * 0.35), math.floor(gridH * 0.30) },
      { math.floor(gridW * 0.35) + 1, math.floor(gridH * 0.30) },
      { math.floor(gridW * 0.65), math.floor(gridH * 0.68) },
      { math.floor(gridW * 0.65) + 1, math.floor(gridH * 0.68) },
      { math.floor(gridW * 0.50), math.floor(gridH * 0.48) },
      { math.floor(gridW * 0.50), math.floor(gridH * 0.78) },
    }
    for _, cell in ipairs(coords) do
      if cell[1] >= 1 and cell[1] <= gridW and cell[2] >= 1 and cell[2] <= gridH then
        blocked[cell[1] .. "," .. cell[2]] = true
      end
    end
  end

  local engine = CombatEngine.new({
    grid = { width = gridW, height = gridH, blocked = blocked },
  })
  local entries = config.entries
  if not entries or #entries == 0 then
    entries = self.app:makeDefaultRoster()
  end
  for _, entry in ipairs(entries) do
    local isPc = entry.side == "pc"
    local combatant = self.app.database:instantiate(entry.key, {
      is_pc = isPc,
      healing_potions = entry.potions or 0,
    })
    if combatant then
      local aware = isPc and config.pcsAware ~= false or config.npcsAware ~= false
      engine:addCombatant(combatant, aware)
    end
  end

  self.engine = engine
  self.handler = ActionHandler.new(engine)
  self.ai = AI.new(engine, self.handler)

  if #engine.combatants < 2 then
    self.message = { text = "Not enough combatants to start a battle.", kind = "error", timer = 5 }
  else
    engine:startCombat()
  end

  local current = engine:getCurrent()
  self.selected = current
  if current then
    self:_onTurnStart(current)
  else
    self:_checkEnd()
  end
end

function BattleScreen:_onTurnStart(combatant)
  if not combatant then return end
  self.turnKey = self:_turnKey(combatant)
  self.selected = combatant
  self.attackChoice = 1
  self.mode = nil
  self.moveCells = nil
  self.endTurnTimer = 1.1
  local speed = math.max(0.25, tonumber(self.app.settings.speed) or 1)
  self.npcTimer = 0.75 / speed
  self.banner = {
    text = string.format("%s  -  %s", self.engine:roundLabel(), combatant.name),
    timer = 1.7,
  }
end

function BattleScreen:_turnKey(combatant)
  if not combatant then return nil end
  return tostring(combatant.id) .. ":" .. tostring(self.engine.current_round) ..
    ":" .. tostring(self.engine.current_turn_index)
end

function BattleScreen:_isAIControlled(combatant)
  if not combatant then return false end
  if self.autoBattle then return true end
  if combatant.is_pc then return false end
  return self.app.settings.autoNpc == true
end

function BattleScreen:_canControlCurrent()
  if self.paused or self.resultVisible then return false end
  if not self.engine or not self.engine.combat_active then return false end
  local current = self.engine.current
  if not current then return false end
  return not self:_isAIControlled(current)
end

function BattleScreen:_msg(text, kind)
  self.message = { text = tostring(text or ""), kind = kind or "info", timer = 4 }
  self.messageTimer = 4
  self.messageKind = kind or "info"
end

function BattleScreen:_checkEnd()
  if self.engine and self.engine.ended and not self.resultShown then
    self.resultShown = true
    self.resultVisible = true
    self.paused = false
    self.mode = nil
    self.moveCells = nil
  end
end

function BattleScreen:_afterAction()
  self.mode = nil
  self.moveCells = nil
  self:_checkEnd()
end

function BattleScreen:update(dt)
  if self.messageTimer > 0 then
    self.messageTimer = math.max(0, self.messageTimer - dt)
  elseif self.message then
    self.message = nil
  end
  if self.banner then
    self.banner.timer = self.banner.timer - dt
    if self.banner.timer <= 0 then self.banner = nil end
  end

  if not self.engine then return end
  self:_checkEnd()
  if self.paused or self.resultVisible then return end
  if not self.engine.combat_active then return end

  local current = self.engine.current
  if not current then return end
  if self:_turnKey(current) ~= self.turnKey then
    self:_onTurnStart(current)
  end

  if self:_isAIControlled(current) then
    self.npcTimer = self.npcTimer - dt
    if self.npcTimer <= 0 then
      self.ai:takeTurn(current)
      self:_checkEnd()
      local nextCombatant = self.engine.current
      if nextCombatant and self.engine.combat_active then
        self:_onTurnStart(nextCombatant)
      end
      local speed = math.max(0.25, tonumber(self.app.settings.speed) or 1)
      self.npcTimer = 0.75 / speed
    end
    return
  end

  local outOfActions = current.full_round_used or
    (current.standard_used and current.move_used) or
    not current:canAct()
  if outOfActions then
    self.endTurnTimer = self.endTurnTimer - dt
    if self.endTurnTimer <= 0 then
      self:_endTurn()
    end
  else
    self.endTurnTimer = 1.0
  end
end

function BattleScreen:_endTurn()
  if not self.engine or not self.engine.combat_active then return end
  self.engine:advanceTurn()
  self.mode = nil
  self.moveCells = nil
  self:_checkEnd()
  if self.engine.combat_active then
    local current = self.engine:getCurrent()
    if current then self:_onTurnStart(current) end
  end
end

function BattleScreen:_restartBattle()
  self:_setupBattle(self.config)
end

function BattleScreen:_cycleAttack()
  local current = self.engine and self.engine.current
  if not current or #current.attacks == 0 then
    self:_msg("This combatant has no attacks.", "error")
    return
  end
  if not self:_canControlCurrent() then
    self:_msg("You are not controlling this turn.", "error")
    return
  end
  self.attackChoice = (self.attackChoice % #current.attacks) + 1
end

function BattleScreen:_selectedAttack()
  local current = self.engine and self.engine.current
  if not current or #current.attacks == 0 then return nil end
  if self.attackChoice < 1 or self.attackChoice > #current.attacks then
    self.attackChoice = 1
  end
  return current.attacks[self.attackChoice]
end

function BattleScreen:_findTarget()
  local current = self.engine and self.engine.current
  if not current then return nil end
  local valid = self.engine:getValidTargets(current)
  local selected = self.selected
  for _, target in ipairs(valid) do
    if target == selected then return target end
  end
  local best, bestDistance, bestHp = nil, 9999, 9999
  for _, target in ipairs(valid) do
    local distance = positioning.distanceBetween(current, target)
    if distance < bestDistance or
       (distance == bestDistance and target.current_hp < bestHp) then
      best, bestDistance, bestHp = target, distance, target.current_hp
    end
  end
  return best
end

function BattleScreen:_requireTurn()
  if not self:_canControlCurrent() then
    self:_msg("You are not controlling this turn.", "error")
    return false
  end
  return true
end

function BattleScreen:_inMeleeReach(actor, target)
  if not actor or not target then return false end
  return positioning.threatensCombatant(actor, target)
end

function BattleScreen:_runAction(id)
  if id == "attack" then return self:_attack(false) end
  if id == "full" then return self:_attack(true) end
  if id == "move" then return self:_beginMove("move") end
  if id == "step" then return self:_beginMove("step") end
  if id == "withdraw" then return self:_beginMove("withdraw") end
  if id == "charge" then return self:_charge() end
  if id == "trip" then return self:_maneuver("trip") end
  if id == "disarm" then return self:_maneuver("disarm") end
  if id == "grapple" then return self:_maneuver("grapple") end
  if id == "bull_rush" then return self:_maneuver("bull_rush") end
  if id == "sunder" then return self:_maneuver("sunder") end
  if id == "defense" then return self:_totalDefense() end
  if id == "stand" then return self:_standUp() end
  if id == "potion" then return self:_drinkPotion() end
  if id == "draw" then return self:_drawWeapon() end
  if id == "aid" then return self:_aidAnother() end
  if id == "stabilize" then return self:_stabilizeOther() end
  if id == "escape" then return self:_escapeGrapple() end
  if id == "drop" then return self:_dropProne() end
  if id == "end" then
    if not self:_requireTurn() then return end
    self:_endTurn()
  end
end

function BattleScreen:_attack(full)
  if not self:_requireTurn() then return end
  local actor = self.engine.current
  local target = self:_findTarget()
  local attack = self:_selectedAttack()
  if not attack then
    self:_msg("No attack is available.", "error")
    return
  end
  if not target then
    self:_msg("No enemy target is available.", "error")
    return
  end
  if attack:isMeleeLike() and not self:_inMeleeReach(actor, target) then
    self:_msg("The target is out of reach. Move closer first.", "error")
    return
  end

  local outcome
  if full then
    outcome = self.handler:takeFullAttackAction(actor, target, self.attackChoice)
  else
    outcome = self.handler:takeAttackAction(actor, target, self.attackChoice)
  end

  if not outcome.success then
    self:_msg(outcome.reason or "The attack could not be made.", "error")
  else
    local results = outcome.results or (outcome.result and { outcome.result }) or {}
    local hits, damage = 0, 0
    for _, result in ipairs(results) do
      if result.is_hit then hits = hits + 1 end
      damage = damage + (result.damage or 0)
    end
    if #results > 0 then
      self:_msg(string.format("%d attack%s, %d hit%s, %d damage.",
        #results, #results == 1 and "" or "s", hits, hits == 1 and "" or "s", damage), "info")
    end
    self.selected = target
  end
  self:_afterAction()
end

function BattleScreen:_maneuver(kind)
  if not self:_requireTurn() then return end
  local actor = self.engine.current
  local target = self:_findTarget()
  if not target then
    self:_msg("Select an enemy to target with the maneuver.", "error")
    return
  end
  if not self:_inMeleeReach(actor, target) then
    self:_msg("The target is out of reach for a combat maneuver.", "error")
    return
  end
  local outcome = self.handler:takeCombatManeuver(actor, target, kind)
  if outcome.reason then
    self:_msg(outcome.reason, "error")
  elseif not outcome.success then
    self:_msg("The maneuver fails.", "error")
  else
    self:_msg("The maneuver succeeds.", "success")
  end
  self:_afterAction()
end

function BattleScreen:_charge()
  if not self:_requireTurn() then return end
  local actor = self.engine.current
  local target = self:_findTarget()
  if not target then
    self:_msg("Select an enemy to charge.", "error")
    return
  end
  local outcome = self.handler:takeChargeAction(actor, target)
  if not outcome.success then
    self:_msg(outcome.reason or "The charge is not possible.", "error")
  else
    local damage = outcome.result and outcome.result.damage or 0
    self:_msg(string.format("Charge connects for %d damage.", damage), "success")
  end
  self:_afterAction()
end

function BattleScreen:_beginMove(kind)
  if not self:_requireTurn() then return end
  local current = self.engine.current
  local state = self.handler:getActionState(current)
  if kind == "step" then
    if not state.five_foot_step then
      self:_msg("A 5-foot step is not available (already moved or disabled).", "error")
      return
    end
  else
    local actionType = kind == "move" and "move" or "full_round"
    local allowed, reason = self.handler:canTakeAction(current, actionType)
    if not allowed then
      self:_msg(reason or "You cannot move right now.", "error")
      return
    end
  end

  self.mode = kind
  if kind == "step" then
    local cells = {}
    for _, cell in ipairs(positioning.cellsAround(current, 1)) do
      if positioning.canStand(current, cell.x, cell.y, self.engine.combatants, self.engine.grid) then
        cells[positioning.key(cell.x, cell.y)] = 1
      end
    end
    self.moveCells = cells
    self:_msg("Choose an adjacent square for your 5-foot step. Escape cancels.", "info")
    return
  end

  local speedSquares = math.floor(current.base_speed / 5)
  local maxSquares
  if kind == "move" then
    local used = math.floor((current.distance_moved or 0) / 5)
    maxSquares = speedSquares - used
  else
    maxSquares = speedSquares * 2
  end
  maxSquares = math.max(0, maxSquares)
  local bfs = positioning.reachable(current, self.engine.combatants, self.engine.grid, maxSquares)
  local cells = {}
  for key, cost in pairs(bfs.costs) do
    if cost > 0 then cells[key] = cost end
  end
  self.moveCells = cells
  if kind == "withdraw" then
    self:_msg("Choose a destination for a full withdrawal. Escape cancels.", "info")
  else
    self:_msg("Choose a highlighted square to move. Escape cancels.", "info")
  end
end

function BattleScreen:_moveTo(x, y)
  local current = self.engine.current
  if not current or not self.mode then return end
  local mode = self.mode
  self.mode = nil
  self.moveCells = nil

  local outcome
  if mode == "step" then
    outcome = self.handler:takeFiveFootStep(current, x, y)
  elseif mode == "withdraw" then
    outcome = self.handler:takeWithdrawAction(current, x, y)
  else
    outcome = self.handler:takeMoveAction(current, x, y)
  end

  if outcome.success then
    self:_msg(mode == "step" and "5-foot step taken." or "Movement complete.", "success")
  else
    self:_msg(outcome.reason or "The movement failed.", "error")
  end
  self:_afterAction()
end

function BattleScreen:_totalDefense()
  if not self:_requireTurn() then return end
  local outcome = self.handler:takeTotalDefenseAction(self.engine.current)
  self:_msg(outcome.success and "Total defense: +4 dodge AC until next turn."
    or (outcome.reason or "Cannot fight defensively now."), outcome.success and "success" or "error")
  self:_afterAction()
end

function BattleScreen:_standUp()
  if not self:_requireTurn() then return end
  local outcome = self.handler:takeStandUpAction(self.engine.current)
  self:_msg(outcome.success and "You stand up." or (outcome.reason or "You cannot stand up."),
    outcome.success and "success" or "error")
  self:_afterAction()
end

function BattleScreen:_drinkPotion()
  if not self:_requireTurn() then return end
  local outcome = self.handler:takeDrinkPotionAction(self.engine.current)
  if outcome.success then
    self:_msg(string.format("Potion heals %d HP.", outcome.healed or 0), "success")
  else
    self:_msg(outcome.reason or "No potion available.", "error")
  end
  self:_afterAction()
end

function BattleScreen:_drawWeapon()
  if not self:_requireTurn() then return end
  local outcome = self.handler:takeDrawWeaponAction(self.engine.current)
  self:_msg(outcome.success and "Weapon recovered." or (outcome.reason or "No weapon to draw."),
    outcome.success and "success" or "error")
  self:_afterAction()
end

function BattleScreen:_aidAnother()
  if not self:_requireTurn() then return end
  local actor = self.engine.current
  local target = self:_findTarget()
  if not target then
    self:_msg("Select the enemy the ally should be aided against.", "error")
    return
  end
  local ally = nil
  for _, candidate in ipairs(self.engine:getAllies(actor)) do
    if candidate.current_hp > 0 and not candidate:isDead() then
      ally = candidate
      break
    end
  end
  if not ally then
    self:_msg("There is no ally to aid.", "error")
    return
  end
  local outcome = self.handler:takeAidAnotherAction(actor, ally, target)
  self:_msg(outcome.success and ("Aid granted: " .. ally.name .. " gains +2 against " .. target.name .. ".")
    or (outcome.reason or "Aid Another fails."), outcome.success and "success" or "error")
  self:_afterAction()
end

function BattleScreen:_stabilizeOther()
  if not self:_requireTurn() then return end
  local actor = self.engine.current
  local target = self.selected
  if not target or target.is_pc ~= actor.is_pc then
    self:_msg("Select a dying ally to stabilize.", "error")
    return
  end
  if not target:isDying() then
    self:_msg("The selected ally is not dying.", "error")
    return
  end
  if positioning.distanceBetween(actor, target) > 1 then
    self:_msg("You must be adjacent to stabilize that ally.", "error")
    return
  end
  local outcome = self.handler:takeStabilizeOtherAction(actor, target)
  self:_msg(outcome.success and (target.name .. " is stabilized.")
    or "First aid fails.", outcome.success and "success" or "error")
  self:_afterAction()
end

function BattleScreen:_escapeGrapple()
  if not self:_requireTurn() then return end
  local actor = self.engine.current
  local grappler = nil
  for _, enemy in ipairs(self.engine:getEnemies(actor)) do
    if enemy:hasCondition("grappled") then
      grappler = enemy
      break
    end
  end
  local outcome = self.handler:takeEscapeGrappleAction(actor, grappler)
  self:_msg(outcome.success and "You break free!" or (outcome.reason or "You fail to break free."),
    outcome.success and "success" or "error")
  self:_afterAction()
end

function BattleScreen:_dropProne()
  if not self:_requireTurn() then return end
  local outcome = self.handler:takeDropProneAction(self.engine.current)
  self:_msg(outcome.success and "You drop prone." or (outcome.reason or "Cannot drop prone."),
    outcome.success and "success" or "error")
  self:_afterAction()
end

function BattleScreen:_refreshButtons()
  local current = self.engine and self.engine.current
  local state = { standard = false, move = false, full_round = false,
    five_foot_step = false, swift = false }
  if current and self.handler then
    state = self.handler:getActionState(current)
  end
  local canControl = self:_canControlCurrent()
  local ended = not self.engine or self.engine.ended or not self.engine.combat_active

  local function set(id, enabled)
    local button = self.actionButtons[id]
    if button then
      button:setEnabled(canControl and enabled and not ended)
    end
  end

  set("attack", state.standard)
  set("full", state.full_round)
  set("move", state.move)
  set("step", state.five_foot_step)
  set("withdraw", state.full_round)
  set("charge", state.full_round)
  set("trip", state.standard)
  set("disarm", state.standard)
  set("grapple", state.standard)
  set("bull_rush", state.standard)
  set("sunder", state.standard)
  set("defense", state.standard)
  set("stand", state.move)
  set("potion", state.standard and current ~= nil and (current.healing_potions or 0) > 0)
  set("draw", state.move)
  set("aid", state.standard)
  set("stabilize", state.standard)
  set("escape", state.standard)
  set("drop", current ~= nil and current:canAct())
  set("end", current ~= nil)

  local attack = current and current.attacks[self.attackChoice]
  if attack then
    self.attackCycle:setLabel("Attack: " .. attack.name)
  else
    self.attackCycle:setLabel("Attack: none")
  end
  self.attackCycle:setEnabled(canControl and attack ~= nil)

  self.topAutoNpc:setLabel("AI Monsters: " .. (self.app.settings.autoNpc and "On" or "Off"))
  self.topAutoBattle:setLabel("Auto Battle: " .. (self.autoBattle and "On" or "Off"))
  self.topPause:setLabel(self.engine and self.engine.ended and "Results" or "Pause")
end

function BattleScreen:_geometry()
  local grid = self.engine and self.engine.grid or { width = 20, height = 14 }
  local availW = GRID_W - 32
  local availH = GRID_H - 62
  local cs = math.floor(math.min(availW / grid.width, availH / grid.height))
  cs = clamp(cs, 12, 44)
  local mapW = grid.width * cs
  local mapH = grid.height * cs
  local ox = GRID_X + math.floor((GRID_W - mapW) / 2)
  local oy = GRID_Y + 8 + math.floor(math.max(0, availH - mapH) / 2)
  return cs, ox, oy
end

function BattleScreen:_cellAt(mouseX, mouseY)
  if not self.engine then return nil end
  local cs, ox, oy = self:_geometry()
  local grid = self.engine.grid
  local x = math.floor((mouseX - ox) / cs) + 1
  local y = math.floor((mouseY - oy) / cs) + 1
  if x < 1 or y < 1 or x > grid.width or y > grid.height then return nil end
  return x, y
end

function BattleScreen:_hitTestInitiative(x, y)
  if x < INIT_X or x > INIT_X + INIT_W or y < INIT_Y or y > INIT_Y + INIT_H then
    return nil
  end
  local order = self.engine.initiative_order
  local visibleIndex = math.floor((y - INIT_ROWS_Y) / INIT_ROW_H) + 1
  if visibleIndex < 1 or visibleIndex > INIT_VISIBLE then return nil end
  local index = visibleIndex + (self.initScroll or 0)
  if index >= 1 and index <= #order and y >= INIT_ROWS_Y then
    return order[index]
  end
  return nil
end

function BattleScreen:mousepressed(x, y, button)
  if self.resultVisible then
    for _, widget in ipairs(self.resultButtons) do
      if widget:mousepressed(x, y, button) then return true end
    end
    return true
  end
  if self.paused then
    for _, widget in ipairs(self.pauseButtons) do
      if widget:mousepressed(x, y, button) then return true end
    end
    return true
  end
  if not self.engine then return false end

  if button == 2 then
    if self.mode then
      self.mode = nil
      self.moveCells = nil
      self:_msg("Movement cancelled.", "info")
      return true
    end
    return false
  end
  if button ~= 1 then return false end

  self:_refreshButtons()

  for _, widget in ipairs(self.topButtons) do
    if widget:mousepressed(x, y, button) then return true end
  end
  if self.attackCycle:mousepressed(x, y, button) then return true end
  for _, widget in ipairs(self.actionButtonList) do
    if widget:mousepressed(x, y, button) then return true end
  end

  local combatant = self:_hitTestInitiative(x, y)
  if combatant then
    self.selected = combatant
    return true
  end

  if x >= GRID_X and x <= GRID_X + GRID_W and y >= GRID_Y and y <= GRID_Y + GRID_H then
    local cellX, cellY = self:_cellAt(x, y)
    if not cellX then return true end
    local atCell = positioning.combatantAt(self.engine.combatants, cellX, cellY)
    if self.mode and self:_canControlCurrent() then
      local key = positioning.key(cellX, cellY)
      if atCell then
        self.selected = atCell
        return true
      end
      if self.moveCells and self.moveCells[key] then
        self:_moveTo(cellX, cellY)
      elseif positioning.terrainBlocked(self.engine.grid, cellX, cellY) then
        self:_msg("That square is blocked by a pillar.", "error")
      elseif positioning.combatantAt(self.engine.combatants, cellX, cellY) then
        self:_msg("That square is occupied.", "error")
      else
        self:_msg("That square is out of movement range.", "error")
      end
      return true
    end
    if atCell then
      self.selected = atCell
      return true
    end
    return true
  end

  return false
end

function BattleScreen:mousereleased(x, y, button)
  local lists = { self.actionButtonList, self.topButtons, self.pauseButtons, self.resultButtons }
  for _, list in ipairs(lists) do
    for _, widget in ipairs(list) do
      if widget.mousereleased then widget:mousereleased(x, y, button) end
    end
  end
  if self.attackCycle.mousereleased then self.attackCycle:mousereleased(x, y, button) end
end

function BattleScreen:wheelmoved(dx, dy)
  if self.resultVisible or self.paused then return true end
  local mx, my = theme.mouseX or 0, theme.mouseY or 0
  if mx >= LOG_X and mx <= LOG_X + LOG_W and my >= LOG_Y and my <= LOG_Y + LOG_H then
    local font = theme.getFont("small")
    local visible = math.max(1, math.floor((LOG_H - 64) / font:getHeight()))
    local maxScroll = math.max(0, #self.logLines - visible)
    self.logScroll = clamp((self.logScroll or 0) + dy * 3, 0, maxScroll)
    return true
  end
  if mx >= INIT_X and mx <= INIT_X + INIT_W and my >= INIT_Y and my <= INIT_Y + INIT_H then
    local maxScroll = math.max(0, #self.engine.initiative_order - INIT_VISIBLE)
    self.initScroll = clamp((self.initScroll or 0) - dy, 0, maxScroll)
    return true
  end
  return false
end

function BattleScreen:keypressed(key)
  if self.resultVisible then
    if key == "escape" or key == "return" or key == "kpenter" then
      self.resultVisible = false
      return true
    end
    return false
  end
  if self.paused then
    if key == "escape" then
      self.paused = false
      return true
    end
    return false
  end
  if not self.engine then return false end

  if key == "escape" then
    if self.mode then
      self.mode = nil
      self.moveCells = nil
      self:_msg("Movement cancelled.", "info")
    elseif self.engine.ended then
      self.resultVisible = true
    else
      self.paused = true
    end
    return true
  elseif key == "tab" then
    self:_cycleAttack()
    return true
  elseif key == "a" then
    self:_runAction("attack")
    return true
  elseif key == "f" then
    self:_runAction("full")
    return true
  elseif key == "m" then
    self:_runAction("move")
    return true
  elseif key == "t" then
    self:_runAction("step")
    return true
  elseif key == "w" then
    self:_runAction("withdraw")
    return true
  elseif key == "c" then
    self:_runAction("charge")
    return true
  elseif key == "v" then
    self:_runAction("defense")
    return true
  elseif key == "u" then
    self:_runAction("stand")
    return true
  elseif key == "p" then
    self:_runAction("potion")
    return true
  elseif key == "k" then
    self:_runAction("draw")
    return true
  elseif key == "g" then
    self:_runAction("aid")
    return true
  elseif key == "z" then
    self:_runAction("stabilize")
    return true
  elseif key == "e" then
    self:_runAction("escape")
    return true
  elseif key == "x" then
    self:_runAction("drop")
    return true
  elseif key == "n" then
    self:_runAction("end")
    return true
  elseif key == "1" then
    self:_runAction("trip")
    return true
  elseif key == "2" then
    self:_runAction("disarm")
    return true
  elseif key == "3" then
    self:_runAction("grapple")
    return true
  elseif key == "4" then
    self:_runAction("bull_rush")
    return true
  elseif key == "5" then
    self:_runAction("sunder")
    return true
  end
  return false
end

function BattleScreen:textinput()
  return false
end

function BattleScreen:_syncLog()
  local log = self.engine and self.engine.log
  if not log then return end
  local size = log:size()
  if size == self.logVersion then return end
  self.logVersion = size

  local font = theme.getFont("small")
  local maxWidth = LOG_W - 40
  local lines = {}
  for _, entry in ipairs(log.entries) do
    local wrapped = theme.wrap(entry.text, font, maxWidth)
    local color = LOG_COLORS[entry.kind] or theme.colors.text
    for _, text in ipairs(wrapped) do
      lines[#lines + 1] = { text = text, color = color }
    end
  end
  self.logLines = lines

  local visible = math.max(1, math.floor((LOG_H - 64) / font:getHeight()))
  local maxScroll = math.max(0, #lines - visible)
  self.logScroll = clamp(self.logScroll or 0, 0, maxScroll)
  if size > 0 and self.logScroll == 0 then
    -- Stay pinned to the newest line when the reader is already at the bottom.
  end
end

function BattleScreen:_drawTopBar()
  local colors = theme.colors
  theme.setColor(colors.panel)
  love.graphics.rectangle("fill", 0, 0, 1440, TOP_H)
  theme.setColor(colors.black, 0.35)
  love.graphics.rectangle("fill", 0, TOP_H - 3, 1440, 3)
  theme.setColor(colors.border, 0.8)
  love.graphics.setLineWidth(1)
  love.graphics.line(0, TOP_H - 0.5, 1440, TOP_H - 0.5)

  theme.drawText("Battle", 24, 8, "h2", colors.gold)
  local roundLabel = self.engine and self.engine:roundLabel() or "No battle"
  theme.drawText(roundLabel, 24, 38, "small", colors.textMuted)

  local turnLabel = self.engine and self.engine:getTurnLabel() or "No active combat"
  theme.drawText(turnLabel, 720, 12, "h3", colors.text, "center")
  local pcs, npcs = 0, 0
  if self.engine then pcs, npcs = self.engine:getSideCounts() end
  theme.drawText(string.format("Heroes %d   |   Monsters %d", pcs, npcs),
    720, 40, "small", colors.textMuted, "center")

  for _, button in ipairs(self.topButtons) do
    button:draw()
  end
end

function BattleScreen:_drawInitiative()
  local colors = theme.colors
  theme.drawPanel(INIT_X, INIT_Y, INIT_W, INIT_H, { title = "Initiative", titleFont = "h3" })

  theme.drawText(self.engine:roundLabel(), INIT_X + 16, 136, "smallBold", colors.gold)
  local pcs, npcs = self.engine:getSideCounts()
  theme.drawText(string.format("%d vs %d", pcs, npcs),
    INIT_X + INIT_W - 16, 136, "small", colors.textMuted, "right")

  local order = self.engine.initiative_order
  local current = self.engine.current
  local mouseX, mouseY = theme.mouseX or 0, theme.mouseY or 0
  local scissorX, scissorY, scissorW, scissorH = love.graphics.getScissor()
  love.graphics.setScissor(INIT_X + 8, INIT_ROWS_Y, INIT_W - 16,
    INIT_VISIBLE * INIT_ROW_H + 4)

  for index = 1, #order do
    local visibleIndex = index - (self.initScroll or 0)
    if visibleIndex >= 1 and visibleIndex <= INIT_VISIBLE then
      local c = order[index]
      local rowY = INIT_ROWS_Y + (visibleIndex - 1) * INIT_ROW_H
      local rowX = INIT_X + 12
      local rowW = INIT_W - 30
      local isCurrent = c == current
      local isSelected = c == self.selected
      local hover = mouseX >= rowX and mouseX < rowX + rowW and
        mouseY >= rowY and mouseY < rowY + INIT_ROW_H - 5

      theme.setColor(isSelected and colors.panelLight or colors.panelAlt,
        hover and 1 or 0.72)
      love.graphics.rectangle("fill", rowX, rowY, rowW, INIT_ROW_H - 5, 5, 5)
      if isCurrent then
        theme.setColor(colors.gold)
        love.graphics.rectangle("fill", rowX, rowY, 3, INIT_ROW_H - 5, 1.5, 1.5)
      end
      theme.setColor(isSelected and colors.borderBright or colors.border,
        hover and 0.9 or 0.5)
      love.graphics.setLineWidth(1)
      love.graphics.rectangle("line", rowX + 0.5, rowY + 0.5, rowW - 1, INIT_ROW_H - 6, 4.5, 4.5)

      local dead = c:isDead()
      local nameColor = dead and colors.textMuted or colors.text
      if isCurrent then nameColor = colors.gold end
      local nameFont = theme.fonts.smallBold
      theme.drawText(theme.truncateText(c.name, nameFont, rowW - 92),
        rowX + 9, rowY + 5, "smallBold", nameColor)
      local hpColor = colors.green
      local frac = c.max_hp > 0 and clamp(c.current_hp / c.max_hp, 0, 1) or 0
      if frac <= 0.25 then hpColor = colors.red elseif frac <= 0.55 then hpColor = colors.orange end
      theme.drawText(string.format("%d/%d", c.current_hp, c.max_hp),
        rowX + rowW - 8, rowY + 6, "tiny",
        dead and colors.textMuted or colors.textMuted, "right")
      theme.drawBar(rowX + 9, rowY + 23, rowW - 18, 4, frac,
        dead and colors.textMuted or hpColor, { radius = 2 })

      local status = c:getStatusLabel()
      if status == "OK" then status = "" end
      local conditions = c:getConditionList()
      local conditionText = {}
      for _, condition in ipairs(conditions) do
        if condition ~= "flat-footed" and condition ~= "dead" and condition ~= "dying" and
           condition ~= "disabled" and condition ~= "stable" then
          conditionText[#conditionText + 1] = conditionLabel(condition)
        end
      end
      local line = status
      if #conditionText > 0 then
        if line ~= "" then line = line .. " | " end
        line = line .. table.concat(conditionText, ", ")
      end
      if line == "" and c.is_flat_footed then line = "Flat-footed" end
      if line ~= "" then
        theme.drawText(theme.truncateText(line, theme.fonts.tiny, rowW - 18),
          rowX + 9, rowY + 31, "tiny", colors.textMuted)
      end
    end
  end

  if scissorX then
    love.graphics.setScissor(scissorX, scissorY, scissorW, scissorH)
  else
    love.graphics.setScissor()
  end

  if #order > INIT_VISIBLE then
    local maxScroll = #order - INIT_VISIBLE
    local barH = math.max(24, (INIT_VISIBLE * INIT_ROW_H) *
      (INIT_VISIBLE / #order))
    local barY = INIT_ROWS_Y + ((INIT_VISIBLE * INIT_ROW_H) - barH) *
      ((self.initScroll or 0) / math.max(1, maxScroll))
    theme.setColor(colors.borderBright, 0.5)
    love.graphics.rectangle("fill", INIT_X + INIT_W - 12, barY, 3, barH, 1.5, 1.5)
  end

  theme.setColor(colors.border, 0.65)
  love.graphics.setLineWidth(1)
  love.graphics.line(INIT_X + 16, 754, INIT_X + INIT_W - 16, 754)

  theme.drawText(string.format("Heroes %d", pcs), INIT_X + 16, 766, "smallBold", colors.blue)
  theme.drawText(string.format("Monsters %d", npcs),
    INIT_X + INIT_W - 16, 766, "smallBold", colors.red, "right")

  local legend = {
    { colors.gold, "Gold: current turn" },
    { colors.green, "Green: reachable" },
    { colors.orange, "Orange: threatened" },
    { colors.blue, "Blue: hero / red: monster" },
  }
  for index, item in ipairs(legend) do
    local y = 790 + (index - 1) * 18
    theme.setColor(item[1], 0.9)
    love.graphics.circle("fill", INIT_X + 20, y + 6, 4)
    theme.drawText(item[2], INIT_X + 30, y, "tiny", colors.textMuted)
  end

  if self.engine.is_surprise_round then
    theme.drawText("Surprise round: only aware combatants act.",
      INIT_X + 16, 862, "tiny", colors.orange)
  end
end

function BattleScreen:_drawMap()
  local colors = theme.colors
  theme.drawPanel(GRID_X, GRID_Y, GRID_W, GRID_H, { radius = 8 })

  local grid = self.engine.grid
  local cs, ox, oy = self:_geometry()
  self._map = { cs = cs, ox = ox, oy = oy }

  local mapW, mapH = grid.width * cs, grid.height * cs
  theme.setColor(colors.black, 0.35)
  love.graphics.rectangle("fill", ox + 2, oy + 3, mapW, mapH, 3, 3)
  theme.setColor(0.075, 0.09, 0.085)
  love.graphics.rectangle("fill", ox, oy, mapW, mapH, 2, 2)

  for y = 1, grid.height do
    for x = 1, grid.width do
      local px = ox + (x - 1) * cs
      local py = oy + (y - 1) * cs
      local blocked = positioning.terrainBlocked(grid, x, y)
      if blocked then
        theme.setColor(0.16, 0.16, 0.17)
        love.graphics.rectangle("fill", px + 1, py + 1, cs - 2, cs - 2, 3, 3)
        theme.setColor(colors.borderBright, 0.55)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", px + 2.5, py + 2.5, cs - 5, cs - 5, 2, 2)
        theme.setColor(colors.black, 0.55)
        love.graphics.line(px + 5, py + 5, px + cs - 6, py + cs - 8)
        love.graphics.line(px + cs - 7, py + 5, px + 7, py + cs - 7)
      else
        local even = (x + y) % 2 == 0
        if even then
          theme.setColor(0.095, 0.115, 0.105)
        else
          theme.setColor(0.085, 0.102, 0.095)
        end
        love.graphics.rectangle("fill", px, py, cs, cs)
      end
      theme.setColor(colors.border, 0.30)
      love.graphics.setLineWidth(1)
      love.graphics.rectangle("line", px + 0.5, py + 0.5, cs - 1, cs - 1)
    end
  end

  if self.app.settings.showThreats and self.engine.combat_active and
     not self.engine.ended and self.engine.current then
    local threatened = self.engine:getThreatenedCells(self.engine.current)
    theme.setColor(colors.red, 0.10)
    for key in pairs(threatened) do
      local cell = positioning.parseKey(key)
      if cell then
        love.graphics.rectangle("fill", ox + (cell.x - 1) * cs,
          oy + (cell.y - 1) * cs, cs, cs)
      end
    end
  end

  if self.moveCells then
    for key, cost in pairs(self.moveCells) do
      local cell = positioning.parseKey(key)
      if cell then
        local px = ox + (cell.x - 1) * cs
        local py = oy + (cell.y - 1) * cs
        theme.setColor(colors.green, 0.20)
        love.graphics.rectangle("fill", px + 1, py + 1, cs - 2, cs - 2, 2, 2)
        theme.setColor(colors.green, 0.55)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", px + 1.5, py + 1.5, cs - 3, cs - 3, 2, 2)
        if cs >= 24 then
          theme.drawText(tostring(cost), px + cs - 4, py + cs - 14,
            "tiny", colors.green, "right")
        end
      end
    end
  end

  local hoverX, hoverY = self:_cellAt(theme.mouseX or 0, theme.mouseY or 0)
  if hoverX then
    theme.setColor(colors.white, 0.5)
    love.graphics.setLineWidth(1.5)
    love.graphics.rectangle("line", ox + (hoverX - 1) * cs + 1.5,
      oy + (hoverY - 1) * cs + 1.5, cs - 3, cs - 3, 2, 2)
  end

  local target = self:_findTarget()
  if target and target ~= self.engine.current and target.position then
    local space = target:getSpaceSquares()
    local cx = ox + (target.position.x + space / 2 - 0.5) * cs
    local cy = oy + (target.position.y + space / 2 - 0.5) * cs
    theme.setColor(colors.red, 0.75)
    love.graphics.setLineWidth(2)
    love.graphics.circle("line", cx, cy, space * cs * 0.52 + 4)
  end

  local drawList = {}
  local hovered
  for _, c in ipairs(self.engine.combatants) do
    local priority = 1
    if not c:isDead() then priority = 2 end
    if c == self.engine.current then priority = 3 end
    if c == self.selected then priority = 4 end
    drawList[#drawList + 1] = { c = c, priority = priority }
    if hoverX and c:occupiesCell(hoverX, hoverY) then hovered = c end
  end
  table.sort(drawList, function(a, b) return a.priority < b.priority end)

  for _, item in ipairs(drawList) do
    self:_drawToken(item.c, cs, ox, oy)
  end

  if hovered then
    local c = hovered
    local conditions = c:getConditionList()
    local labels = {}
    for _, condition in ipairs(conditions) do
      labels[#labels + 1] = conditionLabel(condition)
    end
    local status = c:getStatusLabel()
    local text = string.format("%s\nHP %d/%d   AC %d\n%s\n%s", c.name,
      c.current_hp, c.max_hp, c:getStatusLabel(),
      #labels > 0 and table.concat(labels, ", ") or "No conditions")
    if c.is_flat_footed then text = text .. "\nFlat-footed" end
    ui.queueTooltip(text, theme.mouseX or 0, theme.mouseY or 0)
  end

  local legend = {
    { colors.blue, "Hero" },
    { colors.red, "Monster" },
    { colors.gold, "Current" },
    { colors.green, "Reachable" },
    { colors.orange, "Threatened" },
  }
  local legendY = GRID_Y + GRID_H - 24
  local legendX = GRID_X + 24
  for index, item in ipairs(legend) do
    local x = legendX + (index - 1) * 132
    theme.setColor(item[1], 0.9)
    love.graphics.circle("fill", x, legendY + 6, 4)
    theme.drawText(item[2], x + 9, legendY, "tiny", colors.textMuted)
  end

  if self.banner and self.banner.timer > 0 then
    local alpha = clamp(self.banner.timer * 1.2, 0, 1)
    local font = theme.fonts.h3
    local width = math.min(GRID_W - 80, font:getWidth(self.banner.text) + 44)
    local bx = GRID_X + (GRID_W - width) / 2
    local by = GRID_Y + 16
    theme.setColor(colors.black, 0.55 * alpha)
    love.graphics.rectangle("fill", bx + 2, by + 2, width, 38, 6, 6)
    theme.setColor(colors.panelAlt, 0.92 * alpha)
    love.graphics.rectangle("fill", bx, by, width, 38, 6, 6)
    theme.setColor(colors.gold, 0.8 * alpha)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", bx + 0.5, by + 0.5, width - 1, 37, 5.5, 5.5)
    theme.drawText(theme.truncateText(self.banner.text, font, width - 24),
      bx + width / 2, by + (38 - font:getHeight()) / 2, font, colors.gold, "center")
  end
end

function BattleScreen:_drawToken(c, cs, ox, oy)
  if not c.position then return end
  local colors = theme.colors
  local space = c:getSpaceSquares()
  local cx = ox + (c.position.x + space / 2 - 0.5) * cs
  local cy = oy + (c.position.y + space / 2 - 0.5) * cs
  local radius = cs * (0.38 * space + 0.06)
  local dead = c:isDead()

  theme.setColor(colors.black, dead and 0.20 or 0.38)
  love.graphics.ellipse("fill", cx + 2, cy + 4, radius, radius * 0.72)

  local current = self.engine.current
  local isCurrent = c == current
  if isCurrent and not dead then
    local pulse = 0.5 + 0.5 * math.sin(love.timer.getTime() * 5)
    theme.setColor(colors.gold, 0.20 + pulse * 0.25)
    love.graphics.circle("fill", cx, cy, radius + 7)
  end

  theme.setColor(c.color or colors.panelLight, dead and 0.28 or 0.96)
  love.graphics.circle("fill", cx, cy, radius)

  local outline = c.is_pc and colors.blue or colors.red
  if isCurrent then outline = colors.gold end
  theme.setColor(outline, dead and 0.4 or 0.95)
  love.graphics.setLineWidth(isCurrent and 3 or 2)
  love.graphics.circle("line", cx, cy, radius)
  if c == self.selected then
    theme.setColor(colors.white, 0.9)
    love.graphics.setLineWidth(1.5)
    love.graphics.circle("line", cx, cy, radius + 3)
  end

  local label = c.token_label or "?"
  local font = theme.getFont(math.max(10, math.floor(cs * 0.42)))
  theme.setColor(dead and colors.panelAlt or colors.bg, dead and 0.7 or 0.92)
  love.graphics.setFont(font)
  local labelWidth = font:getWidth(label)
  love.graphics.print(label, math.floor(cx - labelWidth / 2),
    math.floor(cy - font:getHeight() / 2))

  local barW = math.max(22, radius * 1.75)
  local barX = cx - barW / 2
  local barY = cy + radius + 3
  local fraction = c.max_hp > 0 and clamp(c.current_hp / c.max_hp, 0, 1) or 0
  local hpColor = colors.green
  if fraction <= 0.25 then hpColor = colors.red
  elseif fraction <= 0.55 then hpColor = colors.orange end
  if dead then hpColor = colors.textMuted end
  theme.drawBar(barX, barY, barW, 4, fraction, hpColor, { radius = 2 })

  local nameFont = theme.fonts.tiny
  local name = theme.truncateText(c.name, nameFont, barW + 26)
  theme.drawText(name, cx, barY + 6, "tiny",
    dead and colors.textMuted or colors.text, "center")

  if dead then
    theme.setColor(colors.red, 0.85)
    love.graphics.setLineWidth(2)
    local r = radius * 0.72
    love.graphics.line(cx - r, cy - r, cx + r, cy + r)
    love.graphics.line(cx + r, cy - r, cx - r, cy + r)
    return
  end

  local conditions = c:getConditionList()
  local shown = 0
  for _, condition in ipairs(conditions) do
    if condition ~= "flat-footed" and condition ~= "charge" and shown < 3 then
      local color = CONDITION_COLORS[condition] or colors.textMuted
      theme.setColor(color, 0.95)
      love.graphics.circle("fill", cx - radius + 2, cy - radius + 4 + shown * 8, 3)
      shown = shown + 1
    end
  end
  if c.is_flat_footed and shown < 3 then
    theme.setColor(colors.textMuted, 0.8)
    love.graphics.circle("fill", cx - radius + 2, cy - radius + 4 + shown * 8, 3)
  end

  if c.temp_hp and c.temp_hp > 0 then
    theme.setColor(colors.blue, 0.9)
    love.graphics.rectangle("fill", barX, barY - 5, barW * clamp(c.temp_hp / c.max_hp, 0, 1), 2)
  end
end

function BattleScreen:_drawActionPanel()
  local colors = theme.colors
  theme.drawPanel(ACTION_X, ACTION_Y, ACTION_W, ACTION_H, { radius = 8 })

  local current = self.engine and self.engine.current
  local title
  if self.engine and self.engine.ended then
    title = "Battle over"
  elseif current then
    title = current.name .. "'s turn"
  else
    title = "Waiting for combat"
  end
  theme.drawText(theme.truncateText(title, theme.fonts.h3, 440),
    328, 646, "h3", colors.gold)

  if current then
    local state = self.handler:getActionState(current)
    local pills = {
      { "Std", state.standard, colors.gold },
      { "Move", state.move, colors.blue },
      { "Swift", state.swift, colors.purple },
      { "5-ft", state.five_foot_step, colors.green },
    }
    local px = 1012
    for index = #pills, 1, -1 do
      local pill = pills[index]
      local width = index == 1 and 42 or 48
      px = px - width
      local color = pill[2] and pill[3] or colors.textMuted
      theme.drawPill(px, 644, width, 18, pill[1],
        color, "tiny", { fill = pill[2] and colors.panelAlt or nil })
      px = px - 4
    end
  end

  local target = self:_findTarget()
  if current and target then
    local distance = positioning.distanceBetween(current, target)
    theme.drawText(string.format("Target: %s  (HP %d/%d, %d sq)",
      target.name, target.current_hp, target.max_hp, distance),
      328, 674, "small", target.is_pc and colors.blue or colors.red)
  else
    theme.drawText("Target: none", 328, 674, "small", colors.textMuted)
  end

  for _, button in ipairs(self.actionButtonList) do
    button:draw()
  end
  self.attackCycle:draw()

  local message = self.message
  if message and self.messageTimer > 0 then
    local color = colors.gold
    if message.kind == "error" then color = colors.red
    elseif message.kind == "success" then color = colors.green end
    theme.drawText(theme.truncateText(message.text, theme.fonts.small, 680),
      328, 860, "small", color)
  else
    theme.drawText("Hotkeys: A attack, F full, M move, T step, N end turn. Escape pauses.",
      328, 860, "tiny", colors.textMuted)
  end
end

function BattleScreen:_attackDescription(c, attack)
  local bonus = c:getAttackBonus(attack)
  local damageBonus = c:getDamageBonus(attack)
  local suffix = ""
  if damageBonus ~= 0 then suffix = string.format("%+d", damageBonus) end
  return string.format("%s: +%d, %s%s", attack.name, bonus, attack.damage_dice, suffix)
end

function BattleScreen:_drawDetails()
  local colors = theme.colors
  theme.drawPanel(DETAIL_X, DETAIL_Y, DETAIL_W, DETAIL_H, {
    title = "Combatant", titleFont = "h3",
  })

  local c = self.selected or (self.engine and self.engine.current)
  if not c then
    theme.drawText("Select a combatant to inspect.", DETAIL_X + 16, 150,
      "small", colors.textMuted)
    return
  end

  local x = DETAIL_X + 16
  local width = DETAIL_W - 32
  theme.drawText(theme.truncateText(c.name, theme.fonts.h3, width),
    x, 130, "h3", colors.gold)
  local typeLine = string.format("%s %s - %s", c.size or "Medium",
    c.creature_type or "Humanoid", c.alignment or "True Neutral")
  theme.drawText(theme.truncateText(typeLine, theme.fonts.tiny, width),
    x, 154, "tiny", colors.textMuted)

  local fraction = c.max_hp > 0 and clamp(c.current_hp / c.max_hp, 0, 1) or 0
  local hpColor = colors.green
  if fraction <= 0.25 then hpColor = colors.red
  elseif fraction <= 0.55 then hpColor = colors.orange end
  theme.drawBar(x, 180, width, 14, fraction, hpColor, { border = colors.border })
  theme.drawText(string.format("HP %d / %d", c.current_hp, c.max_hp),
    x + width / 2, 181, "tiny", colors.white, "center")

  theme.drawText(string.format("AC %d  |  Touch %d  |  Flat %d",
    c:getAC("standard"), c:getAC("touch"), c:getAC("flat_footed")),
    x, 204, "small", colors.text)
  theme.drawText(string.format("Fort %s   Ref %s   Will %s",
    signed(c:getSaveBonus("fortitude")), signed(c:getSaveBonus("reflex")),
    signed(c:getSaveBonus("will"))), x, 222, "small", colors.text)
  theme.drawText(string.format("CMB %s   CMD %d   BAB %s",
    signed(c:calculateCMB()), c:calculateCMD(), signed(c.base_attack_bonus)),
    x, 240, "small", colors.text)
  theme.drawText(string.format("Speed %d ft   Init %s   Reach %d ft",
    c.base_speed or 30, signed(c:getInitiativeBonus()), c:getReachFeet()),
    x, 258, "small", colors.text)

  local abilities = {
    { "STR", "strength" }, { "DEX", "dexterity" }, { "CON", "constitution" },
    { "INT", "intelligence" }, { "WIS", "wisdom" }, { "CHA", "charisma" },
  }
  local colWidth = width / 6
  for index, ability in ipairs(abilities) do
    local ax = x + (index - 1) * colWidth
    theme.drawText(ability[1], ax, 284, "tiny", colors.textMuted)
    local score = c:getAbilityScore(ability[2])
    local mod = c:getAbilityModifier(ability[2])
    theme.drawText(string.format("%d (%s)", score, signed(mod)),
      ax, 298, "smallBold", colors.text)
  end

  theme.setColor(colors.border, 0.6)
  love.graphics.setLineWidth(1)
  love.graphics.line(x, 320, x + width, 320)
  theme.drawText("Attacks", x, 326, "smallBold", colors.gold)

  local shown = 0
  for _, attack in ipairs(c.attacks) do
    if shown >= 3 then break end
    local y = 344 + shown * 17
    theme.drawText(theme.truncateText(attack.name, theme.fonts.small, 150),
      x, y, "small", colors.text)
    theme.drawText(self:_attackDescription(c, attack), x + width, y,
      "tiny", colors.textMuted, "right")
    shown = shown + 1
  end
  if #c.attacks == 0 then
    theme.drawText("Unarmed", x, 344, "small", colors.textMuted)
  elseif #c.attacks > shown then
    theme.drawText(string.format("+%d more attacks", #c.attacks - shown),
      x, 344 + shown * 17, "tiny", colors.textMuted)
  end

  theme.setColor(colors.border, 0.6)
  love.graphics.line(x, 400, x + width, 400)

  local conditionLabels = {}
  for _, condition in ipairs(c:getConditionList()) do
    conditionLabels[#conditionLabels + 1] = conditionLabel(condition)
  end
  if #conditionLabels == 0 then
    conditionLabels[1] = "None"
  end
  local conditionsText = "Conditions: " .. table.concat(conditionLabels, ", ")
  theme.drawText(theme.truncateText(conditionsText, theme.fonts.tiny, width),
    x, 408, "tiny", colors.textMuted)

  local defenses = {}
  if c.damage_reduction and (c.damage_reduction.amount or 0) > 0 then
    defenses[#defenses + 1] = string.format("DR %d/%s", c.damage_reduction.amount,
      c.damage_reduction.type or "-")
  end
  local immunityLabels = {}
  for _, dtype in ipairs(c.energy_immunity_list or {}) do
    immunityLabels[#immunityLabels + 1] = dtype
  end
  if #immunityLabels > 0 then
    defenses[#defenses + 1] = "Immune " .. table.concat(immunityLabels, "/")
  end
  local resistLabels = {}
  for dtype, amount in pairs(c.energy_resistances or {}) do
    resistLabels[#resistLabels + 1] = string.format("%s %d", dtype, amount)
  end
  table.sort(resistLabels)
  if #resistLabels > 0 then
    defenses[#defenses + 1] = "Resist " .. table.concat(resistLabels, ", ")
  end
  if (c.spell_resistance or 0) > 0 then
    defenses[#defenses + 1] = "SR " .. c.spell_resistance
  end
  local defenseText = #defenses > 0 and table.concat(defenses, " | ") or "No special defenses."
  theme.drawText(theme.truncateText(defenseText, theme.fonts.tiny, width),
    x, 428, "tiny", colors.textMuted)

  local notes = c.notes or ""
  if notes ~= "" then
    theme.drawText(theme.truncateText(notes, theme.fonts.tiny, width),
      x, 448, "tiny", colors.textMuted)
  end

  if c == (self.engine and self.engine.current) and self.engine.combat_active then
    theme.drawText("Acting now", x + width, 130, "tiny", colors.gold, "right")
  end
end

function BattleScreen:_drawLog()
  local colors = theme.colors
  theme.drawPanel(LOG_X, LOG_Y, LOG_W, LOG_H, {
    title = "Combat Log", titleFont = "h3",
  })

  local font = theme.fonts.small
  local lineHeight = font:getHeight()
  local innerX = LOG_X + 16
  local innerY = LOG_Y + 56
  local innerW = LOG_W - 32
  local visible = math.max(1, math.floor((LOG_H - 64) / lineHeight))
  local total = #self.logLines
  local maxScroll = math.max(0, total - visible)
  self.logScroll = clamp(self.logScroll or 0, 0, maxScroll)
  local startIndex = math.max(1, total - visible - self.logScroll + 1)

  theme.drawText(self.logScroll > 0 and string.format("Scroll: %d lines back", self.logScroll)
    or "Newest entries", LOG_X + LOG_W - 16, LOG_Y + 22, "tiny",
    colors.textMuted, "right")

  local sx, sy, sw, sh = love.graphics.getScissor()
  love.graphics.setScissor(innerX - 4, innerY - 2, innerW + 8, visible * lineHeight + 4)
  for index = startIndex, total do
    local line = self.logLines[index]
    if line then
      local y = innerY + (index - startIndex) * lineHeight
      theme.setColor(line.color)
      love.graphics.setFont(font)
      love.graphics.print(line.text, math.floor(innerX), math.floor(y))
    end
  end
  if sx then
    love.graphics.setScissor(sx, sy, sw, sh)
  else
    love.graphics.setScissor()
  end

  if total > visible then
    local barH = math.max(20, (visible * lineHeight) * (visible / total))
    local barY = innerY + ((visible * lineHeight) - barH) *
      ((total - visible - self.logScroll) / math.max(1, total - visible))
    theme.setColor(colors.borderBright, 0.5)
    love.graphics.rectangle("fill", LOG_X + LOG_W - 12, barY, 3, barH, 1.5, 1.5)
  end
end

function BattleScreen:_drawPauseOverlay()
  local colors = theme.colors
  ui._pendingTooltips = {}
  theme.setColor(colors.overlay)
  love.graphics.rectangle("fill", 0, 0, 1440, 900)
  theme.drawPanel(460, 280, 520, 300, { title = "Battle Paused", titleFont = "h2" })
  theme.drawText("Step away from the table. The initiative order will wait.",
    720, 312, "small", colors.textMuted, "center")
  for _, button in ipairs(self.pauseButtons) do
    button:draw()
  end
end

function BattleScreen:_drawResultOverlay()
  local colors = theme.colors
  ui._pendingTooltips = {}
  theme.setColor(colors.overlay)
  love.graphics.rectangle("fill", 0, 0, 1440, 900)

  local winner = self.engine and self.engine.winner or "Undecided"
  local title, subtitle
  if winner == "PCs" then
    title = "Victory"
    subtitle = "The heroes hold the field. The monsters are slain or broken."
  elseif winner == "Monsters" then
    title = "Defeat"
    subtitle = "The party has fallen. The dungeon claims another legend."
  elseif winner == "Draw" then
    title = "Mutual Destruction"
    subtitle = "Both sides lie broken on the battlefield."
  else
    title = "Battle Ended"
    subtitle = "The field falls silent."
  end

  theme.drawPanel(410, 230, 620, 430, { title = "Battle Report", titleFont = "h2" })
  theme.drawText(title, 720, 288, "title", colors.gold, "center")
  theme.drawText(subtitle, 720, 348, "small", colors.textMuted, "center")

  local rounds = self.engine and self.engine.current_round or 0
  local pcs, npcs = 0, 0
  if self.engine then pcs, npcs = self.engine:getSideCounts() end
  theme.drawText(string.format("Rounds fought: %d", rounds), 720, 382,
    "body", colors.text, "center")
  theme.drawText(string.format("Still standing: %d heroes  |  %d monsters", pcs, npcs),
    720, 408, "small", colors.textMuted, "center")
  theme.drawText(string.format("Winner: %s", winner), 720, 436,
    "smallBold", winner == "PCs" and colors.green or colors.red, "center")

  for _, button in ipairs(self.resultButtons) do
    button:draw()
  end
end

function BattleScreen:draw()
  if not self.engine then
    theme.drawText("No battle configured.", 720, 420, "h2", theme.colors.textMuted, "center")
    return
  end

  self:_syncLog()
  self:_checkEnd()
  self:_refreshButtons()
  self:_drawTopBar()
  self:_drawInitiative()
  self:_drawMap()
  self:_drawActionPanel()
  self:_drawDetails()
  self:_drawLog()

  if self.resultVisible then
    self:_drawResultOverlay()
  elseif self.paused then
    self:_drawPauseOverlay()
  end
end

return BattleScreen
