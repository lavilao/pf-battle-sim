local constants = require("src.core.constants")
local dice = require("src.core.dice")
local positioning = require("src.core.positioning")

local ActionHandler = {}
ActionHandler.__index = ActionHandler

local function sign(n)
  if n > 0 then return 1 end
  if n < 0 then return -1 end
  return 0
end

local function pluralSquares(n)
  return n == 1 and "square" or "squares"
end

function ActionHandler.new(engine)
  local self = setmetatable({}, ActionHandler)
  self.engine = engine
  return self
end

function ActionHandler:log()
  return self.engine.log
end

function ActionHandler:canTakeAction(combatant, actionType)
  if not combatant then return false, "no combatant" end
  if not self.engine.combat_active then return false, "combat is not active" end
  if not combatant:canAct() then return false, "cannot act" end
  if combatant:hasCondition("nauseated") and actionType ~= "move" then
    return false, "nauseated (move actions only)"
  end
  if combatant.full_round_used then return false, "full-round action already used" end

  local limited = combatant:isDisabled() or combatant:hasCondition("staggered")
  if actionType == "full_round" then
    if limited then return false, "staggered/disabled (single action only)" end
    if combatant.standard_used or combatant.move_used then
      return false, "already acted this turn"
    end
    return true
  elseif actionType == "standard" then
    if combatant.standard_used then return false, "standard action already used" end
    if limited and combatant.move_used then
      return false, "staggered/disabled (already used move action)"
    end
    return true
  elseif actionType == "move" then
    if combatant.move_used then return false, "move action already used" end
    if limited and combatant.standard_used then
      return false, "staggered/disabled (already used standard action)"
    end
    return true
  elseif actionType == "swift" then
    if combatant.swift_used then return false, "swift action already used" end
    return true
  end
  return true
end

function ActionHandler:_applyDisabledStrain(combatant)
  if combatant:isDisabled() then
    combatant:takeDamage(1, "untyped")
    self:log():add(string.format(
      "%s pushes through the pain while disabled and takes 1 damage (HP %d).",
      combatant.name, combatant.current_hp), "system")
    if combatant:isDying() then
      self:log():add(combatant.name .. " collapses, dying!", "death")
    end
    self.engine:maybeEndCombat()
  end
end

function ActionHandler:_selectAttack(combatant, attackIndex)
  if not combatant or #combatant.attacks == 0 then return nil end
  local index = attackIndex or 1
  return combatant.attacks[index] or combatant.attacks[1]
end

function ActionHandler:_rangedProvocation(attacker)
  if not attacker.position then return { interrupted = false, results = {} } end
  return self.engine:triggerAoOs(attacker, "ranged attack")
end

function ActionHandler:takeAttackAction(attacker, target, attackIndex, opts)
  opts = opts or {}
  local allowed, reason = self:canTakeAction(attacker, "standard")
  if not allowed then
    return { success = false, reason = reason }
  end
  local attack = self:_selectAttack(attacker, attackIndex)
  if not attack then
    return { success = false, reason = "no attack" }
  end
  if not target or target:isDead() then
    return { success = false, reason = "no valid target" }
  end

  attacker.standard_used = true

  local outcome = { success = false, attack = attack }
  if attack.attack_type == constants.AttackType.RANGED then
    local aoo = self:_rangedProvocation(attacker)
    outcome.aoo = aoo
    if aoo.interrupted then
      outcome.reason = "interrupted by attack of opportunity"
      self:_applyDisabledStrain(attacker)
      return outcome
    end
  end

  local result = self.engine:makeAttack(attacker, target, attack, {
    attackNumber = 0,
    extraBonus = opts.extraBonus,
  })
  outcome.result = result
  outcome.success = result ~= nil
  self:_applyDisabledStrain(attacker)
  return outcome
end

function ActionHandler:takeFullAttackAction(attacker, target, attackIndex)
  local allowed, reason = self:canTakeAction(attacker, "full_round")
  if not allowed then
    return { success = false, reason = reason }
  end
  local attack = self:_selectAttack(attacker, attackIndex)
  if not attack then
    return { success = false, reason = "no attack" }
  end
  if not target or target:isDead() then
    return { success = false, reason = "no valid target" }
  end

  attacker.full_round_used = true
  attacker.standard_used = true
  attacker.move_used = true

  local outcome = { success = true, results = {}, attack = attack }
  if attack.attack_type == constants.AttackType.RANGED then
    local aoo = self:_rangedProvocation(attacker)
    outcome.aoo = aoo
    if aoo.interrupted then
      outcome.success = false
      outcome.reason = "interrupted by attack of opportunity"
      return outcome
    end
  end

  local naturalAttacks = {}
  for _, candidate in ipairs(attacker.attacks) do
    if candidate.attack_type == constants.AttackType.NATURAL then
      naturalAttacks[#naturalAttacks + 1] = candidate
    end
  end

  if attack.attack_type == constants.AttackType.NATURAL and #naturalAttacks > 1 then
    self:log():add(string.format("%s unleashes a full attack with %d natural weapons.",
      attacker.name, #naturalAttacks), "info")
    for _, natural in ipairs(naturalAttacks) do
      local result = self.engine:makeAttack(attacker, target, natural, {
        attackNumber = 0,
        fullAttack = true,
      })
      if result then outcome.results[#outcome.results + 1] = result end
      if target:isDead() then
        outcome.target_down = true
        break
      end
    end
    return outcome
  end

  local iterations = math.min(4, math.floor(attacker.base_attack_bonus / 5) + 1)
  for i = 0, iterations - 1 do
    local result = self.engine:makeAttack(attacker, target, attack, {
      attackNumber = i,
      fullAttack = true,
    })
    if result then outcome.results[#outcome.results + 1] = result end
    if target:isDead() then
      outcome.target_down = true
      break
    end
  end
  return outcome
end

function ActionHandler:takeMoveAction(combatant, x, y, opts)
  opts = opts or {}
  local allowed, reason = self:canTakeAction(combatant, "move")
  if not allowed then
    return { success = false, reason = reason }
  end
  if not combatant.position then
    return { success = false, reason = "no position" }
  end

  local speedSquares = math.floor(combatant.base_speed / 5)
  local usedSquares = math.floor((combatant.distance_moved or 0) / 5)
  local remaining = speedSquares - usedSquares
  if remaining <= 0 then
    return { success = false, reason = "no movement left" }
  end

  local outcome = self.engine:moveCombatant(combatant, x, y, {
    maxCost = remaining,
    checkAoOs = opts.checkAoOs ~= false,
    provocationId = opts.provocationId,
  })
  if not outcome.moved and outcome.stopped then
    combatant.move_used = true
    combatant.distance_moved = combatant.distance_moved +
      math.min(remaining, (outcome.cost or 0)) * 5
    outcome.success = false
    outcome.reason = "movement interrupted"
    return outcome
  end
  if not outcome.moved then
    return { success = false, reason = outcome.reason or "cannot move there" }
  end

  combatant.move_used = true
  combatant.distance_moved = combatant.distance_moved + (outcome.cost or 0) * 5
  outcome.success = true
  if outcome.stopped then
    outcome.success = false
    outcome.reason = "movement interrupted"
  end
  return outcome
end

function ActionHandler:takeFiveFootStep(combatant, x, y)
  if not self.engine.combat_active then
    return { success = false, reason = "combat is not active" }
  end
  if not combatant:canAct() then
    return { success = false, reason = "cannot act" }
  end
  if combatant.five_foot_used then
    return { success = false, reason = "5-foot step already used" }
  end
  if combatant.move_used or combatant.full_round_used then
    return { success = false, reason = "already moved this turn" }
  end
  if combatant:hasCondition("staggered") or combatant:isDisabled() then
    return { success = false, reason = "staggered/disabled" }
  end
  if not combatant.position then
    return { success = false, reason = "no position" }
  end
  local distance = positioning.chebyshev(combatant.position.x, combatant.position.y, x, y)
  if distance ~= 1 then
    return { success = false, reason = "a 5-foot step moves exactly one square" }
  end
  if not positioning.canStand(combatant, x, y, self.engine.combatants, self.engine.grid) then
    return { success = false, reason = "square is blocked" }
  end

  combatant.position = { x = x, y = y }
  combatant.five_foot_used = true
  combatant.move_used = true
  self:log():add(string.format("%s takes a 5-foot step to (%d, %d).",
    combatant.name, x, y), "info")
  return { success = true }
end

function ActionHandler:takeWithdrawAction(combatant, x, y)
  local allowed, reason = self:canTakeAction(combatant, "full_round")
  if not allowed then
    return { success = false, reason = reason }
  end
  if not combatant.position then
    return { success = false, reason = "no position" }
  end
  local speedSquares = math.floor(combatant.base_speed / 5) * 2
  local outcome = self.engine:moveCombatant(combatant, x, y, {
    maxCost = speedSquares,
    isWithdraw = true,
  })
  combatant.full_round_used = true
  combatant.move_used = true
  combatant.distance_moved = speedSquares * 5
  if not outcome.moved and not outcome.stopped then
    return { success = false, reason = outcome.reason or "cannot withdraw there" }
  end
  outcome.success = true
  if outcome.stopped then
    self:log():add(combatant.name .. "'s withdraw is cut short.", "system")
  else
    self:log():add(string.format("%s withdraws to (%d, %d).",
      combatant.name, combatant.position.x, combatant.position.y), "info")
  end
  return outcome
end

function ActionHandler:takeStandUpAction(combatant)
  local allowed, reason = self:canTakeAction(combatant, "move")
  if not allowed then
    return { success = false, reason = reason }
  end
  if not combatant:hasCondition("prone") then
    return { success = false, reason = "not prone" }
  end
  local aoo = self.engine:triggerAoOs(combatant, "standing up")
  combatant.move_used = true
  if aoo.interrupted then
    return { success = false, reason = "interrupted", aoo = aoo }
  end
  combatant:removeCondition("prone")
  self:log():add(combatant.name .. " stands up.", "info")
  return { success = true, aoo = aoo }
end

function ActionHandler:takeDropProneAction(combatant)
  if not combatant:canAct() then
    return { success = false, reason = "cannot act" }
  end
  if combatant:hasCondition("prone") then
    return { success = false, reason = "already prone" }
  end
  combatant:addCondition("prone")
  self:log():add(combatant.name .. " drops prone.", "info")
  return { success = true }
end

function ActionHandler:takeTotalDefenseAction(combatant)
  local allowed, reason = self:canTakeAction(combatant, "standard")
  if not allowed then
    return { success = false, reason = reason }
  end
  combatant.standard_used = true
  combatant.total_defense_bonus = 4
  self:log():add(string.format("%s fights defensively (+4 dodge AC until next turn).",
    combatant.name), "info")
  return { success = true }
end

function ActionHandler:takeDrawWeaponAction(combatant)
  local allowed, reason = self:canTakeAction(combatant, "move")
  if not allowed then
    return { success = false, reason = reason }
  end
  if combatant:hasCondition("disarmed") or #combatant.dropped_attacks > 0 then
    combatant:recoverWeapons()
    combatant.move_used = true
    self:log():add(combatant.name .. " recovers a weapon.", "info")
    return { success = true }
  end
  return { success = false, reason = "no weapon to draw" }
end

function ActionHandler:takeSheatheWeaponAction(combatant)
  local allowed, reason = self:canTakeAction(combatant, "move")
  if not allowed then
    return { success = false, reason = reason }
  end
  local aoo = self.engine:triggerAoOs(combatant, "sheathing a weapon")
  combatant.move_used = true
  if aoo.interrupted then
    return { success = false, reason = "interrupted", aoo = aoo }
  end
  if combatant:dropWeapons() then
    self:log():add(combatant.name .. " sheathes a weapon.", "info")
    return { success = true, aoo = aoo }
  end
  return { success = false, reason = "no weapon to sheathe" }
end

function ActionHandler:takeDrinkPotionAction(combatant)
  local allowed, reason = self:canTakeAction(combatant, "standard")
  if not allowed then
    return { success = false, reason = reason }
  end
  if (combatant.healing_potions or 0) <= 0 then
    return { success = false, reason = "no potions left" }
  end
  combatant.standard_used = true
  local aoo = self.engine:triggerAoOs(combatant, "drinking a potion")
  if aoo.interrupted then
    return { success = false, reason = "interrupted", aoo = aoo }
  end
  combatant.healing_potions = combatant.healing_potions - 1
  local roll = dice.rollNotation("1d8+1")
  local healed = combatant:heal(roll.total)
  self:log():add(string.format("%s drinks a potion of cure light wounds and heals %d HP (now %d/%d). %d potion(s) left.",
    combatant.name, healed, combatant.current_hp, combatant.max_hp, combatant.healing_potions), "heal")
  return { success = true, healed = healed, aoo = aoo }
end

function ActionHandler:takeStabilizeOtherAction(helper, target)
  local allowed, reason = self:canTakeAction(helper, "standard")
  if not allowed then
    return { success = false, reason = reason }
  end
  if not target or not target:isDying() then
    return { success = false, reason = "target is not dying" }
  end
  helper.standard_used = true
  local skill = helper.skills and helper.skills.Heal or 0
  local roll = dice.d20()
  local total = roll + skill
  local success = total >= 15
  self:log():add(string.format("%s attempts first aid on %s: Heal %d + %d = %d vs DC 15 - %s.",
    helper.name, target.name, roll, skill, total, success and "success" or "failure"), "save")
  if success then
    target:addCondition("stable")
    target:removeCondition("dying")
    self:log():add(target.name .. " is stabilized.", "heal")
  end
  return { success = success, roll = roll, total = total }
end

function ActionHandler:takeAidAnotherAction(helper, ally, enemy)
  local allowed, reason = self:canTakeAction(helper, "standard")
  if not allowed then
    return { success = false, reason = reason }
  end
  if not ally or not enemy then
    return { success = false, reason = "missing ally or enemy" }
  end
  helper.standard_used = true
  local attack = self:_selectAttack(helper, 1)
  if not attack then
    return { success = false, reason = "no attack" }
  end
  local bonus = helper:getAttackBonus(attack, { target = enemy })
  local roll = dice.d20()
  local total = roll + bonus
  local success = total >= 10
  self:log():add(string.format("%s tries to aid %s: attack roll %d + %d = %d vs AC 10 - %s.",
    helper.name, ally.name, roll, bonus, total, success and "success" or "failure"), "info")
  if success then
    ally.aid_bonuses[#ally.aid_bonuses + 1] = {
      target_id = enemy.id,
      target_name = enemy.name,
      value = 2,
      expires_for_id = helper.id,
      expired = false,
    }
    self:log():add(string.format("%s gains +2 on attacks against %s.", ally.name, enemy.name), "info")
  end
  return { success = success }
end

function ActionHandler:takeCombatManeuver(attacker, target, maneuver)
  local allowed, reason = self:canTakeAction(attacker, "standard")
  if not allowed then
    return { success = false, reason = reason }
  end
  if not target or target:isDead() then
    return { success = false, reason = "no valid target" }
  end
  if not attacker.position or not target.position then
    return { success = false, reason = "positioning required" }
  end

  maneuver = maneuver or "trip"
  local labels = {
    trip = "Trip", bull_rush = "Bull Rush", disarm = "Disarm",
    sunder = "Sunder", grapple = "Grapple",
  }
  local label = labels[maneuver] or maneuver
  attacker.standard_used = true

  local aoo = nil
  local improved = attacker:hasFeat("Improved " .. label)
  if not improved and (maneuver == "trip" or maneuver == "bull_rush" or
      maneuver == "disarm" or maneuver == "sunder" or maneuver == "grapple") then
    aoo = self.engine:triggerAoOs(attacker, label .. " attempt")
    if aoo.interrupted then
      return { success = false, reason = "interrupted", aoo = aoo }
    end
  end

  local cmb = attacker:calculateCMB()
  local cmd = target:calculateCMD()
  local roll = dice.d20()
  local total = roll + cmb
  local success = roll == 20 or (roll ~= 1 and total >= cmd)

  self:log():add(string.format("%s attempts a %s against %s: CMB %d + %d = %d vs CMD %d - %s.",
    attacker.name, label:lower(), target.name, roll, cmb, total, cmd,
    success and "success" or "failure"), "maneuver")

  if success then
    if maneuver == "trip" then
      target:addCondition("prone")
      self:log():add(target.name .. " is knocked prone.", "maneuver")
    elseif maneuver == "bull_rush" then
      local dx = sign(target.position.x - attacker.position.x)
      local dy = sign(target.position.y - attacker.position.y)
      if dx ~= 0 and dy ~= 0 then
        if math.abs(target.position.x - attacker.position.x) >=
           math.abs(target.position.y - attacker.position.y) then
          dy = 0
        else
          dx = 0
        end
      end
      local nx, ny = target.position.x + dx, target.position.y + dy
      if (dx ~= 0 or dy ~= 0) and
         positioning.canStand(target, nx, ny, self.engine.combatants, self.engine.grid) then
        target.position = { x = nx, y = ny }
        self:log():add(string.format("%s is pushed to (%d, %d).", target.name, nx, ny), "maneuver")
      else
        self:log():add(target.name .. " cannot be pushed any farther.", "info")
      end
    elseif maneuver == "disarm" then
      if target:dropWeapons() then
        self:log():add(target.name .. " is disarmed!", "maneuver")
      else
        self:log():add(target.name .. " has no weapon to disarm.", "info")
      end
    elseif maneuver == "sunder" then
      local weapon = target:getPrimaryAttack()
      if weapon then
        weapon.damaged = true
        target:addCondition("weapon-damaged")
        self:log():add(string.format("%s's %s is damaged (-2 on attacks and damage).",
          target.name, weapon.name), "maneuver")
      end
    elseif maneuver == "grapple" then
      attacker:addCondition("grappled")
      target:addCondition("grappled")
      self:log():add(string.format("%s grapples %s!", attacker.name, target.name), "maneuver")
    end
  end

  return {
    success = success, roll = roll, cmb = cmb, cmd = cmd, total = total,
    maneuver = maneuver, aoo = aoo,
  }
end

function ActionHandler:takeEscapeGrappleAction(combatant, grappler)
  local allowed, reason = self:canTakeAction(combatant, "standard")
  if not allowed then
    return { success = false, reason = reason }
  end
  if not combatant:hasCondition("grappled") then
    return { success = false, reason = "not grappled" }
  end
  combatant.standard_used = true
  local cmb = combatant:calculateCMB()
  local cmd = grappler and grappler:calculateCMD() or 15
  local roll = dice.d20()
  local total = roll + cmb
  local success = roll == 20 or (roll ~= 1 and total >= cmd)
  self:log():add(string.format("%s attempts to escape the grapple: CMB %d + %d = %d vs CMD %d - %s.",
    combatant.name, roll, cmb, total, cmd, success and "success" or "failure"), "maneuver")
  if success then
    combatant:removeCondition("grappled")
    if grappler then grappler:removeCondition("grappled") end
    self:log():add(combatant.name .. " breaks free!", "maneuver")
  end
  return { success = success }
end

function ActionHandler:takeChargeAction(attacker, target)
  local allowed, reason = self:canTakeAction(attacker, "full_round")
  if not allowed then
    return { success = false, reason = reason }
  end
  if not target or target:isDead() then
    return { success = false, reason = "no valid target" }
  end
  if not attacker.position or not target.position then
    return { success = false, reason = "positioning required" }
  end
  local attack = nil
  for _, candidate in ipairs(attacker.attacks) do
    if candidate:isMeleeLike() then
      attack = candidate
      break
    end
  end
  if not attack then
    return { success = false, reason = "no melee attack" }
  end

  local maxSquares = math.floor(attacker.base_speed / 5) * 2
  local candidates = {}
  local seen = {}
  for _, cell in ipairs(target:getFootprint()) do
    for dx = -1, 1 do
      for dy = -1, 1 do
        if dx ~= 0 or dy ~= 0 then
          local x, y = cell.x + dx, cell.y + dy
          local key = positioning.key(x, y)
          if not seen[key] and not target:occupiesCell(x, y) then
            seen[key] = true
            candidates[#candidates + 1] = { x = x, y = y }
          end
        end
      end
    end
  end

  local best = nil
  local bestDistance = 9999
  for _, candidate in ipairs(candidates) do
    local dx = candidate.x - attacker.position.x
    local dy = candidate.y - attacker.position.y
    if dx == 0 or dy == 0 then
      local distance = math.max(math.abs(dx), math.abs(dy))
      if distance >= 2 and distance <= maxSquares and distance < bestDistance then
        local path = positioning.straightCells(attacker.position.x, attacker.position.y,
          candidate.x, candidate.y)
        local clear = path ~= nil
        if clear then
          for _, step in ipairs(path) do
            if not positioning.canStand(attacker, step.x, step.y,
                self.engine.combatants, self.engine.grid) then
              clear = false
              break
            end
          end
        end
        if clear then
          best = { cell = candidate, path = path, distance = distance }
          bestDistance = distance
        end
      end
    end
  end

  if not best then
    return { success = false, reason = "no straight-line charge lane" }
  end

  attacker.full_round_used = true
  attacker.standard_used = true
  attacker.move_used = true

  local moveOutcome = self.engine:checkMovementAoOs(attacker, best.path, {
    isFiveFootStep = false,
    isWithdraw = false,
  })
  if moveOutcome.stopped then
    self:log():add(attacker.name .. "'s charge is interrupted!", "system")
    return { success = false, reason = "charge interrupted", moved = moveOutcome }
  end

  attacker.charge_penalty = 2
  attacker:addCondition("charge")
  attacker.distance_moved = best.distance * 5
  self:log():add(string.format("%s charges %d %s at %s! (+2 attack, -2 AC)",
    attacker.name, best.distance, pluralSquares(best.distance), target.name), "info")

  local result = self.engine:makeAttack(attacker, target, attack, {
    extraBonus = 2,
    isCharge = true,
  })
  return {
    success = result ~= nil,
    moved = moveOutcome,
    result = result,
    distance = best.distance,
  }
end

function ActionHandler:getActionState(combatant)
  local canStandard = self:canTakeAction(combatant, "standard")
  local canMove = self:canTakeAction(combatant, "move")
  local canFull = self:canTakeAction(combatant, "full_round")
  local canFiveFoot = combatant and combatant:canAct() and
    not combatant.five_foot_used and not combatant.move_used and
    not combatant.full_round_used and
    not combatant:hasCondition("staggered") and not combatant:isDisabled()
  return {
    standard = canStandard,
    move = canMove,
    full_round = canFull,
    five_foot_step = canFiveFoot,
    swift = self:canTakeAction(combatant, "swift"),
  }
end

return ActionHandler
