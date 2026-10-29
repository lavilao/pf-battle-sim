local constants = require("src.core.constants")
local positioning = require("src.core.positioning")

local AI = {}
AI.__index = AI

function AI.new(engine, handler, opts)
  opts = opts or {}
  local self = setmetatable({}, AI)
  self.engine = engine
  self.handler = handler
  self.aggression = opts.aggression or 1
  return self
end

function AI:attackIndex(combatant, attack)
  for index, candidate in ipairs(combatant.attacks) do
    if candidate == attack then return index end
  end
  return 1
end

function AI:chooseTarget(combatant)
  local targets = self.engine:getValidTargets(combatant)
  if #targets == 0 then return nil end
  local best, bestDistance, bestHp = nil, 9999, 9999
  for _, target in ipairs(targets) do
    local distance = positioning.distanceBetween(combatant, target)
    if distance < bestDistance or
       (distance == bestDistance and target.current_hp < bestHp) then
      best = target
      bestDistance = distance
      bestHp = target.current_hp
    end
  end
  return best
end

function AI:prefersRanged(combatant)
  local primary = combatant.attacks[1]
  return primary ~= nil and primary.attack_type == constants.AttackType.RANGED
end

function AI:findRangedAttack(combatant)
  for _, attack in ipairs(combatant.attacks) do
    if attack.attack_type == constants.AttackType.RANGED then
      return attack
    end
  end
  return nil
end

function AI:isThreatened(combatant)
  return #self.engine:isThreatened(combatant) > 0
end

function AI:findRetreatCell(combatant)
  local enemies = self.engine:getEnemies(combatant)
  local candidates = positioning.cellsAround(combatant, 1)
  local best, bestScore = nil, -9999
  for _, cell in ipairs(candidates) do
    if positioning.canStand(combatant, cell.x, cell.y,
        self.engine.combatants, self.engine.grid) then
      local threatened = false
      for _, enemy in ipairs(enemies) do
        if not enemy:isDead() and positioning.threatensCell(enemy, cell.x, cell.y) then
          threatened = true
          break
        end
      end
      if not threatened then
        local score = 0
        for _, enemy in ipairs(enemies) do
          if not enemy:isDead() and enemy.position then
            score = score + enemy:cellDistance(cell.x, cell.y)
          end
        end
        if score > bestScore then
          best = cell
          bestScore = score
        end
      end
    end
  end
  return best
end

function AI:moveIntoReach(combatant, target, attack)
  local speedSquares = math.floor(combatant.base_speed / 5)
  local usedSquares = math.floor((combatant.distance_moved or 0) / 5)
  local remaining = speedSquares - usedSquares
  if remaining <= 0 then return false end

  local bfs = positioning.reachable(combatant, self.engine.combatants,
    self.engine.grid, remaining)
  local reachSquares = math.max(1, math.ceil((attack.reach or combatant:getReachFeet()) / 5))
  local targetCells = target:getFootprint()
  local best, bestCost = nil, nil
  local closest, closestDistance, closestCost = nil, 9999, 9999

  for key, cost in pairs(bfs.costs) do
    if cost > 0 then
      local cell = bfs.cells[key]
      local reaches = false
      local minDistance = 9999
      for _, targetCell in ipairs(targetCells) do
        local distance = positioning.chebyshev(cell.x, cell.y, targetCell.x, targetCell.y)
        if distance <= reachSquares then reaches = true end
        if distance < minDistance then minDistance = distance end
      end
      if reaches and (not bestCost or cost < bestCost) then
        best = cell
        bestCost = cost
      end
      if not reaches then
        local score = minDistance * 100 + cost
        if score < closestDistance then
          closest = cell
          closestDistance = score
          closestCost = cost
        end
      end
    end
  end

  if not best then
    best = closest
  end
  if not best then return false end

  local outcome = self.handler:takeMoveAction(combatant, best.x, best.y)
  if not outcome.success then
    return positioning.attackThreatensCombatant(combatant, target, attack)
  end
  return positioning.attackThreatensCombatant(combatant, target, attack)
end

function AI:chargeLanePossible(combatant, target)
  if not combatant.position or not target.position then return false end
  for _, cell in ipairs(target:getFootprint()) do
    if cell.x == combatant.position.x or cell.y == combatant.position.y then
      local distance = positioning.chebyshev(combatant.position.x, combatant.position.y,
        cell.x, cell.y)
      if distance >= 2 then return true end
    end
  end
  return false
end

function AI:tryRangedAttack(combatant, target, ranged)
  if self:isThreatened(combatant) and not combatant.five_foot_used and
     not combatant.move_used and not combatant.full_round_used then
    local retreat = self:findRetreatCell(combatant)
    if retreat then
      local step = self.handler:takeFiveFootStep(combatant, retreat.x, retreat.y)
      if step.success then
        self.engine.log:add(combatant.name .. " steps back to shoot.", "info")
      end
    end
  end
  if not self.handler:canTakeAction(combatant, "standard") then return nil end
  return self.handler:takeAttackAction(combatant, target,
    self:attackIndex(combatant, ranged))
end

function AI:takeTurn(combatant)
  local summary = { actions = {} }
  if not self.engine.combat_active then return summary end

  if not combatant:canAct() then
    self.engine:advanceTurn()
    summary.ended = true
    return summary
  end

  local target = self:chooseTarget(combatant)
  if not target then
    self.engine:advanceTurn()
    summary.ended = true
    return summary
  end
  summary.target = target

  if (combatant.healing_potions or 0) > 0 and
     combatant.current_hp <= math.max(1, math.floor(combatant.max_hp * 0.35)) and
     self.handler:canTakeAction(combatant, "standard") then
    local potion = self.handler:takeDrinkPotionAction(combatant)
    summary.actions[#summary.actions + 1] = "potion"
    summary.potion = potion
    if not combatant:canAct() then
      self.engine:advanceTurn()
      summary.ended = true
      return summary
    end
  end

  if combatant:hasCondition("grappled") then
    if self.handler:canTakeAction(combatant, "standard") then
      summary.escape = self.handler:takeEscapeGrappleAction(combatant, target)
      summary.actions[#summary.actions + 1] = "escape"
    end
    self.engine:advanceTurn()
    summary.ended = true
    return summary
  end

  local melee = self.engine:selectAoOAttack(combatant)
  local ranged = self:findRangedAttack(combatant)
  local targetAdjacent = melee and
    positioning.attackThreatensCombatant(combatant, target, melee) or false

  if targetAdjacent then
    if melee then
      if combatant.base_attack_bonus >= 5 and
         self.handler:canTakeAction(combatant, "full_round") then
        summary.full_attack = self.handler:takeFullAttackAction(combatant, target,
          self:attackIndex(combatant, melee))
        summary.actions[#summary.actions + 1] = "full attack"
      else
        summary.attack = self.handler:takeAttackAction(combatant, target,
          self:attackIndex(combatant, melee))
        summary.actions[#summary.actions + 1] = "attack"
      end
    elseif ranged then
      local stepCell = self:findRetreatCell(combatant)
      if stepCell and not combatant.five_foot_used and not combatant.move_used then
        local step = self.handler:takeFiveFootStep(combatant, stepCell.x, stepCell.y)
        summary.step = step
        if step.success then summary.actions[#summary.actions + 1] = "5-foot step" end
      end
      if self.handler:canTakeAction(combatant, "standard") then
        summary.attack = self.handler:takeAttackAction(combatant, target,
          self:attackIndex(combatant, ranged))
        summary.actions[#summary.actions + 1] = "ranged attack"
      end
    end
    self.engine:advanceTurn()
    summary.ended = true
    return summary
  end

  local rangedPreferred = ranged and (not melee or self:prefersRanged(combatant))
  if rangedPreferred then
    summary.attack = self:tryRangedAttack(combatant, target, ranged)
    summary.actions[#summary.actions + 1] = "ranged attack"
    self.engine:advanceTurn()
    summary.ended = true
    return summary
  end

  if melee then
    local distance = positioning.distanceBetween(combatant, target)
    local maxCharge = math.floor(combatant.base_speed / 5) * 2
    if self.handler:canTakeAction(combatant, "full_round") and
       distance >= 2 and distance <= maxCharge and
       self:chargeLanePossible(combatant, target) then
      local charge = self.handler:takeChargeAction(combatant, target)
      summary.charge = charge
      summary.actions[#summary.actions + 1] = "charge"
      if charge.success then
        self.engine:advanceTurn()
        summary.ended = true
        return summary
      end
    end

    local moved = self:moveIntoReach(combatant, target, melee)
    summary.actions[#summary.actions + 1] = "move"
    if self.handler:canTakeAction(combatant, "standard") and
       positioning.attackThreatensCombatant(combatant, target, melee) then
      summary.attack = self.handler:takeAttackAction(combatant, target,
        self:attackIndex(combatant, melee))
      summary.actions[#summary.actions + 1] = "attack"
    end
    summary.moved = moved
  elseif ranged then
    summary.attack = self.handler:takeAttackAction(combatant, target,
      self:attackIndex(combatant, ranged))
    summary.actions[#summary.actions + 1] = "ranged attack"
  else
    self.engine.log:add(combatant.name .. " has no attacks and hesitates.", "system")
  end

  self.engine:advanceTurn()
  summary.ended = true
  return summary
end

function AI:autoResolve(maxTurns)
  local turns = 0
  local guard = 0
  maxTurns = maxTurns or 300
  while self.engine.combat_active and guard < maxTurns do
    guard = guard + 1
    local current = self.engine:getCurrent()
    if not current then
      if not self.engine:advanceTurn() then break end
    elseif current:canAct() then
      self:takeTurn(current)
      turns = turns + 1
    else
      self.engine:advanceTurn()
    end
  end
  return turns
end

return AI
