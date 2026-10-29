local constants = require("src.core.constants")
local dice = require("src.core.dice")
local CombatLog = require("src.core.combat_log")
local positioning = require("src.core.positioning")

local CombatEngine = {}
CombatEngine.__index = CombatEngine

local function isMeleeLike(attack)
  return attack and (attack.attack_type == constants.AttackType.MELEE or
    attack.attack_type == constants.AttackType.NATURAL)
end

local function conditionsText(c)
  local list = c:getConditionList()
  if #list == 0 then return "" end
  local labels = {}
  for _, condition in ipairs(list) do
    labels[#labels + 1] = constants.Conditions[condition] and
      constants.Conditions[condition].label or condition
  end
  return table.concat(labels, ", ")
end

function CombatEngine.new(opts)
  opts = opts or {}
  local self = setmetatable({}, CombatEngine)
  self.combatants = {}
  self.log = opts.log or CombatLog.new()
  self.grid = opts.grid or { width = 20, height = 14, blocked = {} }
  self.grid.blocked = self.grid.blocked or {}
  self.initiative_order = {}
  self.initiative_table = {}
  self.current_round = 0
  self.current_turn_index = 0
  self.combat_active = false
  self.ended = false
  self.winner = nil
  self.is_surprise_round = false
  self.current = nil
  self.current_can_act = false
  self.provocation_counter = 0
  self.on_end = opts.on_end
  return self
end

function CombatEngine:setGrid(width, height, blocked)
  self.grid = {
    width = math.max(1, math.floor(width or 20)),
    height = math.max(1, math.floor(height or 14)),
    blocked = blocked or {},
  }
end

function CombatEngine:autoPlace(c)
  local width = self.grid and self.grid.width or 20
  local height = self.grid and self.grid.height or 14
  local sideIndex = 0
  for _, other in ipairs(self.combatants) do
    if other.is_pc == c.is_pc then sideIndex = sideIndex + 1 end
  end
  local prefX = c.is_pc and 2 or math.max(2, width - 3)
  local prefY = 2 + (sideIndex * 2) % math.max(2, height - 4)
  local x, y = positioning.findPlacement(c, self.combatants, self.grid, prefX, prefY)
  if x then
    c.position = { x = x, y = y }
  end
  return c.position
end

function CombatEngine:addCombatant(combatant, isAware, position)
  if not combatant then return nil end
  if isAware ~= nil then
    combatant.is_aware = isAware == true
  end
  combatant.is_flat_footed = not combatant.is_aware
  if position then
    combatant.position = { x = position.x, y = position.y }
  end
  self.combatants[#self.combatants + 1] = combatant
  if not combatant.position then
    self:autoPlace(combatant)
  end
  return combatant
end

function CombatEngine:removeCombatant(combatant)
  if not combatant then return false end
  local removed = false
  for i = #self.combatants, 1, -1 do
    if self.combatants[i] == combatant or self.combatants[i].id == combatant.id then
      table.remove(self.combatants, i)
      removed = true
    end
  end
  for i = #self.initiative_order, 1, -1 do
    if self.initiative_order[i] == combatant or self.initiative_order[i].id == combatant.id then
      table.remove(self.initiative_order, i)
    end
  end
  if self.current == combatant then
    self.current = nil
    self.current_can_act = false
  end
  return removed
end

function CombatEngine:getCombatantById(id)
  for _, c in ipairs(self.combatants) do
    if c.id == id then return c end
  end
  return nil
end

function CombatEngine:rollInitiative()
  local entries = {}
  for index, c in ipairs(self.combatants) do
    if not c:isDead() then
      c.initiative_roll = dice.d20()
      local bonus = c:getInitiativeBonus()
      if c:hasCondition("deafened") then bonus = bonus - 4 end
      c.initiative_total = c.initiative_roll + bonus
      entries[#entries + 1] = {
        combatant = c,
        total = c.initiative_total,
        bonus = bonus,
        roll = c.initiative_roll,
        index = index,
        tiebreak = nil,
      }
    end
  end

  table.sort(entries, function(a, b)
    if a.total ~= b.total then return a.total > b.total end
    if a.bonus ~= b.bonus then return a.bonus > b.bonus end
    if a.tiebreak == nil then a.tiebreak = dice.d20() end
    if b.tiebreak == nil then b.tiebreak = dice.d20() end
    if a.tiebreak ~= b.tiebreak then return a.tiebreak > b.tiebreak end
    return a.index < b.index
  end)

  self.initiative_order = {}
  self.initiative_table = entries
  local parts = {}
  for i, entry in ipairs(entries) do
    self.initiative_order[i] = entry.combatant
    parts[#parts + 1] = string.format("%s %d", entry.combatant.name, entry.total)
  end
  if #parts > 0 then
    self.log:add("Initiative order: " .. table.concat(parts, ", "), "system")
  end
  return self.initiative_order
end

function CombatEngine:startCombat()
  if #self.combatants == 0 then return false end
  self.ended = false
  self.winner = nil
  self.combat_active = true
  self.current = nil
  self.current_can_act = false
  self.is_surprise_round = false
  self.current_round = 1
  self.current_turn_index = 0
  self.provocation_counter = 0

  for _, c in ipairs(self.combatants) do
    c:resetForCombat()
    c.is_flat_footed = true
  end

  self.log:header("=== Combat begins ===")
  self:rollInitiative()

  local aware, unaware = 0, 0
  for _, c in ipairs(self.combatants) do
    if c.is_aware then aware = aware + 1 else unaware = unaware + 1 end
  end
  if aware > 0 and unaware > 0 then
    self.is_surprise_round = true
    self.log:add("Surprise round! Only aware combatants may act.", "system")
  elseif unaware > 0 then
    self.log:add("Nobody is aware of the ambush; everyone is flat-footed.", "system")
  end

  self:advanceTurn()
  return self.combat_active
end

function CombatEngine:roundLabel()
  local suffix = ""
  if self.is_surprise_round then suffix = " (Surprise)" end
  return string.format("Round %d%s", self.current_round, suffix)
end

function CombatEngine:_beginTurnFor(c)
  self.current = c
  c:resetForTurn()
  c.aoo_made_this_round = 0
  c.aoo_provocation_key = nil
  c.is_flat_footed = false

  self.log:header(string.format("%s  --  %s (HP %d/%d, AC %d)",
    self:roundLabel(), c.name, c.current_hp, c.max_hp, c:getAC("standard")))

  if c:isDying() then
    local result = c:stabilize()
    if result.success then
      self.log:add(string.format("%s stabilizes (Constitution check %d vs DC %d).",
        c.name, result.total, result.dc), "save")
    elseif result.death then
      self.log:add(string.format("%s succumbs to their wounds.", c.name), "death")
    else
      self.log:add(string.format("%s fails to stabilize (Constitution check %d vs DC %d, now at %d HP).",
        c.name, result.total, result.dc, c.current_hp), "save")
    end
    self:maybeEndCombat()
  end

  local able = c:canAct()
  self.current_can_act = able
  if not able and not c:isDead() then
    local cond = conditionsText(c)
    local reason = cond ~= "" and cond or c:getStatusLabel()
    self.log:add(string.format("%s cannot act (%s).", c.name, reason), "system")
  end

  if c:isDead() then
    self.current_can_act = false
  end

  return able
end

function CombatEngine:advanceTurn()
  if not self.combat_active then return nil end
  self:maybeEndCombat()
  if not self.combat_active then return nil end

  local n = #self.initiative_order
  if n == 0 then
    self:endCombat()
    return nil
  end

  local start = self.current_turn_index or 0
  local steps = 0
  while steps < n do
    steps = steps + 1
    local idx = start + steps
    if idx > n then
      idx = idx - n
      if self.current_round > 0 then
        self.current_round = self.current_round + 1
      end
      if self.is_surprise_round then
        self.is_surprise_round = false
      end
    end
    local c = self.initiative_order[idx]
    if c and not c:isDead() and (not self.is_surprise_round or c.is_aware) then
      self.current_turn_index = idx
      self:_beginTurnFor(c)
      return c
    end
  end

  self:endCombat()
  return nil
end

CombatEngine.endTurn = CombatEngine.advanceTurn

function CombatEngine:getCurrent()
  return self.current
end

function CombatEngine:getTurnLabel()
  if not self.combat_active then
    if self.ended and self.winner then
      return "Combat over - " .. self.winner .. " victorious"
    end
    return "No active combat"
  end
  if not self.current then return "Combat starting" end
  return self:roundLabel() .. " - " .. self.current.name
end

function CombatEngine:isCombatEffective(c)
  if c:isDead() or c:isDying() or c:isStable() then return false end
  if c:hasCondition("petrified") or c:hasCondition("unconscious") or
     c:hasCondition("helpless") then
    return false
  end
  return true
end

function CombatEngine:getSideCounts()
  local pcs, npcs = 0, 0
  for _, c in ipairs(self.combatants) do
    if self:isCombatEffective(c) then
      if c.is_pc then pcs = pcs + 1 else npcs = npcs + 1 end
    end
  end
  return pcs, npcs
end

function CombatEngine:isCombatOver()
  if #self.combatants < 2 then return false end
  local pcs, npcs = self:getSideCounts()
  return pcs == 0 or npcs == 0
end

function CombatEngine:maybeEndCombat()
  if self.combat_active and self:isCombatOver() then
    self:endCombat()
    return true
  end
  return false
end

function CombatEngine:endCombat()
  if self.ended then return end
  self.combat_active = false
  self.ended = true
  local pcs, npcs = self:getSideCounts()
  if pcs > 0 and npcs == 0 then
    self.winner = "PCs"
  elseif npcs > 0 and pcs == 0 then
    self.winner = "Monsters"
  elseif pcs == 0 and npcs == 0 then
    self.winner = "Draw"
  else
    self.winner = "Undecided"
  end
  local message
  if self.winner == "Draw" then
    message = "Combat over - everyone is down!"
  elseif self.winner == "Undecided" then
    message = "Combat ended."
  else
    message = "Combat over - " .. self.winner .. " are victorious!"
  end
  self.log:header("=== " .. message .. " ===")
  if self.on_end then self.on_end(self) end
end

function CombatEngine:getEnemies(combatant, includeDefeated)
  local list = {}
  for _, other in ipairs(self.combatants) do
    if other ~= combatant and other.is_pc ~= combatant.is_pc then
      if includeDefeated or not other:isDead() then
        list[#list + 1] = other
      end
    end
  end
  return list
end

function CombatEngine:getAllies(combatant, includeDefeated)
  local list = {}
  for _, other in ipairs(self.combatants) do
    if other ~= combatant and other.is_pc == combatant.is_pc then
      if includeDefeated or not other:isDead() then
        list[#list + 1] = other
      end
    end
  end
  return list
end

function CombatEngine:getValidTargets(combatant)
  local list = {}
  for _, enemy in ipairs(self:getEnemies(combatant)) do
    if enemy.current_hp > 0 and not enemy:isDead() then
      list[#list + 1] = enemy
    end
  end
  return list
end

function CombatEngine:getLivingCombatants()
  local list = {}
  for _, c in ipairs(self.combatants) do
    if not c:isDead() then list[#list + 1] = c end
  end
  return list
end

function CombatEngine:canMakeAoO(combatant)
  if not self.combat_active then return false end
  return combatant:canMakeAoO()
end

function CombatEngine:distanceBetween(a, b)
  return positioning.distanceBetween(a, b)
end

function CombatEngine:isInReach(attacker, target, attack)
  return positioning.attackThreatensCombatant(attacker, target, attack)
end

function CombatEngine:isThreatened(target)
  local threatening = {}
  for _, enemy in ipairs(self:getEnemies(target)) do
    if enemy.current_hp > 0 and not enemy:isDead() and
       positioning.threatensCombatant(enemy, target) then
      threatening[#threatening + 1] = enemy
    end
  end
  return threatening
end

function CombatEngine:getThreatenedCells(combatant)
  local set = {}
  for _, enemy in ipairs(self:getEnemies(combatant)) do
    if not enemy:isDead() then
      local cells = enemy:threatenedSquares(self.grid.width, self.grid.height)
      for key in pairs(cells) do set[key] = true end
    end
  end
  return set
end

function CombatEngine:selectAoOAttack(combatant)
  local best = nil
  for _, attack in ipairs(combatant.attacks) do
    if isMeleeLike(attack) then
      if not best or attack.reach > best.reach or
         (attack.reach == best.reach and attack.enhancement_bonus > best.enhancement_bonus) then
        best = attack
      end
    end
  end
  return best
end

function CombatEngine:makeAttack(attacker, target, attack, opts)
  opts = opts or {}
  if not attacker or not target then return nil end
  attack = attack or attacker:getPrimaryAttack()
  if not attack then
    self.log:add(attacker.name .. " has no attack available.", "system")
    return nil
  end
  if target:isDead() then
    self.log:add(target.name .. " is already dead.", "system")
    return nil
  end

  local isRanged = attack.attack_type == constants.AttackType.RANGED
  local attackNumber = opts.attackNumber or 0
  local bonus = attacker:getAttackBonus(attack, {
    attackNumber = attackNumber,
    fullAttack = opts.fullAttack,
    target = target,
    extraBonus = opts.extraBonus,
  })
  local roll = dice.d20()
  local total = roll + bonus

  local ac = target:getAC("standard")
  local acNotes = {}
  if target:hasCondition("prone") then
    if isRanged then
      ac = ac + 4
      acNotes[#acNotes + 1] = "+4 AC vs ranged (prone)"
    else
      ac = ac - 4
      acNotes[#acNotes + 1] = "-4 AC vs melee (prone)"
    end
  end

  local result = {
    attacker = attacker,
    target = target,
    attack = attack,
    roll = roll,
    attack_bonus = bonus,
    total = total,
    target_ac = ac,
    attack_number = attackNumber,
    is_hit = false,
    is_threat = false,
    confirmed = false,
    is_critical_hit = false,
    damage = 0,
    is_aoo = opts.isAoO == true,
    is_ranged = isRanged,
    ac_notes = acNotes,
  }

  local hit
  local autoNote = ""
  if roll == 1 then
    hit = false
    autoNote = " (natural 1)"
  elseif roll == 20 then
    hit = true
    autoNote = " (natural 20)"
  else
    hit = total >= ac
  end

  if hit and attacker:hasCondition("blinded") then
    local missRoll = dice.rollRange(1, 100)
    result.miss_chance_roll = missRoll
    if missRoll <= 50 then
      result.is_hit = false
      result.missed = true
      result.miss_reason = "concealment"
      self.log:add(string.format(
        "%s attacks %s with %s: would hit (AC %d), but is blinded - %d%% miss chance. MISS.",
        attacker.name, target.name, attack.name, ac, missRoll), "miss")
      return result
    end
  end

  result.is_hit = hit
  if not hit then
    local acSuffix = ""
    if #acNotes > 0 then acSuffix = " [" .. table.concat(acNotes, "; ") .. "]" end
    self.log:add(string.format(
      "%s attacks %s with %s: %d + %d = %d vs AC %d%s - MISS%s.",
      attacker.name, target.name, attack.name, roll, bonus, total, ac, acSuffix, autoNote), "miss")
    return result
  end

  local threat = false
  for _, value in ipairs(attack:get_threat_range()) do
    if roll == value then
      threat = true
      break
    end
  end
  result.is_threat = threat

  local crit = false
  if threat then
    local confirmRoll = dice.d20()
    local confirmTotal = confirmRoll + bonus
    local confirmed
    if confirmRoll == 20 then
      confirmed = true
    elseif confirmRoll == 1 then
      confirmed = false
    else
      confirmed = confirmTotal >= ac
    end
    result.confirm_roll = confirmRoll
    result.confirm_total = confirmTotal
    result.confirmed = confirmed
    crit = confirmed
    if confirmed then
      self.log:add(string.format(
        "  Critical threat! Confirmation %d + %d = %d vs AC %d - CONFIRMED!",
        confirmRoll, bonus, confirmTotal, ac), "crit")
    else
      self.log:add(string.format(
        "  Critical threat! Confirmation %d + %d = %d vs AC %d - not confirmed.",
        confirmRoll, bonus, confirmTotal, ac), "info")
    end
  end

  local damageRoll = attacker:rollDamage(attack, crit)
  local effective, info = target:takeDamage(damageRoll.total, attack.damage_type)
  result.damage = effective
  result.damage_roll = damageRoll
  result.damage_details = info
  result.is_critical_hit = crit

  local critNote = crit and " CRITICAL!" or ""
  local noteText = ""
  if info and info.notes and #info.notes > 0 then
    noteText = " [" .. table.concat(info.notes, ", ") .. "]"
  end
  local acSuffix = ""
  if #acNotes > 0 then acSuffix = " [" .. table.concat(acNotes, "; ") .. "]" end

  self.log:add(string.format(
    "%s attacks %s with %s: %d + %d = %d vs AC %d%s - HIT%s%s for %d %s damage. %s HP: %d/%d.",
    attacker.name, target.name, attack.name, roll, bonus, total, ac, acSuffix,
    autoNote, critNote, effective, attack.damage_type, target.name,
    target.current_hp, target.max_hp),
    crit and "crit" or "hit")

  if target:isDead() then
    self.log:add(target.name .. " is slain!", "death")
  elseif target:isDying() then
    self.log:add(target.name .. " is dying!", "death")
  elseif target:isDisabled() then
    self.log:add(target.name .. " is disabled (0 HP).", "system")
  end

  self:maybeEndCombat()
  return result
end

function CombatEngine:attackOfOpportunity(attacker, target, attack, opts)
  opts = opts or {}
  attack = attack or self:selectAoOAttack(attacker)
  if not attack then
    self.log:add(attacker.name .. " has no melee weapon for an attack of opportunity.", "system")
    return nil
  end
  self.log:add(string.format("%s takes an attack of opportunity against %s!",
    attacker.name, target.name), "aoo")
  opts.isAoO = true
  return self:makeAttack(attacker, target, attack, opts)
end

function CombatEngine:triggerAoOs(provoker, actionName, opts)
  opts = opts or {}
  local outcome = { results = {}, anyHit = false, interrupted = false, provocationId = nil }
  if not self.combat_active or not provoker or provoker:isDead() then
    return outcome
  end

  local provocationId = opts.provocationId
  if not provocationId then
    self.provocation_counter = self.provocation_counter + 1
    provocationId = "provoke_" .. self.provocation_counter
  end
  outcome.provocationId = provocationId

  for _, enemy in ipairs(self.combatants) do
    if enemy ~= provoker and enemy.is_pc ~= provoker.is_pc and not enemy:isDead() then
      if enemy.aoo_provocation_key ~= provocationId and enemy:canMakeAoO() then
        local threatened
        if opts.cell then
          local reachSquares = math.max(1, math.floor(enemy:getReachFeet() / 5))
          threatened = enemy:cellDistance(opts.cell.x, opts.cell.y) <= reachSquares
        else
          threatened = positioning.threatensCombatant(enemy, provoker)
        end
        if threatened then
          enemy.aoo_made_this_round = enemy.aoo_made_this_round + 1
          enemy.aoo_provocation_key = provocationId
          local result = self:attackOfOpportunity(enemy, provoker, nil, {
            provocationId = provocationId,
          })
          if result then
            outcome.results[#outcome.results + 1] = result
            if result.is_hit then outcome.anyHit = true end
            if provoker:isDead() or not provoker:canAct() then
              outcome.interrupted = true
            end
          end
        end
      end
    end
  end

  if outcome.interrupted then
    self.log:add(string.format("%s's %s is interrupted!", provoker.name,
      actionName or "action"), "system")
  end
  return outcome
end

function CombatEngine:checkMovementAoOs(mover, path, opts)
  opts = opts or {}
  path = path or {}
  local outcome = {
    moved = true, stopped = false, stopIndex = nil, results = {}, path = path,
    finalPosition = { x = mover.position.x, y = mover.position.y },
  }

  if #path == 0 then
    return outcome
  end

  if opts.isFiveFootStep then
    mover.position = { x = path[#path].x, y = path[#path].y }
    outcome.finalPosition = { x = mover.position.x, y = mover.position.y }
    return outcome
  end

  local provocationId = opts.provocationId
  if not provocationId then
    self.provocation_counter = self.provocation_counter + 1
    provocationId = "move_" .. self.provocation_counter
  end

  for i, cell in ipairs(path) do
    local skipAoo = opts.isWithdraw and i == 1
    if not skipAoo then
      local leaving = { x = mover.position.x, y = mover.position.y }
      local result = self:triggerAoOs(mover, "movement", {
        provocationId = provocationId,
        cell = leaving,
      })
      for _, r in ipairs(result.results) do
        outcome.results[#outcome.results + 1] = r
      end
      if result.interrupted then
        outcome.moved = false
        outcome.stopped = true
        outcome.stopIndex = i - 1
        outcome.finalPosition = { x = mover.position.x, y = mover.position.y }
        self.log:add(string.format("%s's movement stops at (%d, %d).",
          mover.name, mover.position.x, mover.position.y), "system")
        return outcome
      end
    end
    mover.position = { x = cell.x, y = cell.y }
  end

  outcome.finalPosition = { x = mover.position.x, y = mover.position.y }
  return outcome
end

function CombatEngine:moveCombatant(combatant, x, y, opts)
  opts = opts or {}
  if not combatant or not combatant.position then
    return { moved = false, reason = "no position" }
  end
  if not positioning.canStand(combatant, x, y, self.combatants, self.grid) then
    return { moved = false, reason = "blocked" }
  end
  local maxCost = opts.maxCost or 999
  local path, cost = positioning.findPath(combatant, self.combatants, self.grid, x, y, maxCost)
  if not path then
    return { moved = false, reason = "no path" }
  end
  if cost > maxCost then
    return { moved = false, reason = "too far" }
  end

  local outcome
  if opts.checkAoOs == false then
    combatant.position = { x = x, y = y }
    outcome = {
      moved = true, stopped = false, results = {}, path = path,
      finalPosition = { x = x, y = y },
    }
  else
    outcome = self:checkMovementAoOs(combatant, path, {
      isFiveFootStep = opts.isFiveFootStep,
      isWithdraw = opts.isWithdraw,
      provocationId = opts.provocationId,
    })
  end
  outcome.cost = cost
  outcome.path = path
  return outcome
end

return CombatEngine
