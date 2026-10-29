local constants = require("src.core.constants")
local AbilityScores = require("src.core.ability_scores")
local ArmorClass = require("src.core.armor_class")
local SavingThrows = require("src.core.saving_throws")
local Attack = require("src.core.attack")
local dice = require("src.core.dice")

local Combatant = {}
Combatant.__index = Combatant

local nextId = 0

local TOKEN_PALETTE = {
  { 0.45, 0.65, 0.90 }, { 0.85, 0.52, 0.35 }, { 0.48, 0.75, 0.50 },
  { 0.72, 0.52, 0.86 }, { 0.86, 0.72, 0.38 }, { 0.42, 0.72, 0.75 },
  { 0.88, 0.48, 0.56 }, { 0.66, 0.66, 0.72 },
}

local function hashString(s)
  local h = 5381
  for i = 1, #s do
    h = (h * 33 + string.byte(s, i)) % 2147483647
  end
  return h
end

local function conditionSet(list)
  local set = {}
  for _, c in ipairs(list or {}) do set[c] = true end
  return set
end

local function sortedKeys(map)
  local keys = {}
  for k in pairs(map or {}) do keys[#keys + 1] = k end
  table.sort(keys)
  return keys
end

function Combatant.new(opts)
  opts = opts or {}
  local self = setmetatable({}, Combatant)
  nextId = nextId + 1
  self.id = opts.id or ("combatant_" .. nextId)
  self.name = opts.name or "Combatant"
  self.is_pc = opts.is_pc == true
  self.notes = opts.notes or ""

  self.max_hp = math.max(1, math.floor(tonumber(opts.max_hp) or 1))
  self.current_hp = tonumber(opts.current_hp) or self.max_hp
  self.temp_hp = tonumber(opts.temp_hp) or 0

  self.abilities = opts.abilities or AbilityScores.from_dict(opts.ability_scores)
  self.base_attack_bonus = tonumber(opts.base_attack_bonus) or 0

  self.attacks = {}
  local attackList = opts.attacks or {}
  for _, a in ipairs(attackList) do
    if getmetatable(a) == Attack then
      self.attacks[#self.attacks + 1] = a
    else
      self.attacks[#self.attacks + 1] = Attack.new(a)
    end
  end
  self.dropped_attacks = {}

  self.armor_class = opts.armor_class or ArmorClass.from_dict(opts.ac)
  if getmetatable(self.armor_class) ~= ArmorClass then
    self.armor_class = ArmorClass.from_dict(opts.armor_class)
  end

  self.damage_reduction = opts.damage_reduction or nil
  self.spell_resistance = tonumber(opts.spell_resistance) or 0
  self.energy_resistances = opts.energy_resistances or {}
  self.energy_immunities = conditionSet(opts.energy_immunities)
  self.energy_vulnerabilities = conditionSet(opts.energy_vulnerabilities)
  self.energy_immunity_list = opts.energy_immunities or {}
  self.energy_vulnerability_list = opts.energy_vulnerabilities or {}

  self.saving_throws = opts.saving_throws or SavingThrows.from_dict(opts.saves)
  if getmetatable(self.saving_throws) ~= SavingThrows then
    self.saving_throws = SavingThrows.from_dict(opts.saving_throws)
  end

  self.base_speed = tonumber(opts.base_speed) or 30
  self.size = opts.size or "Medium"
  self.creature_type = opts.creature_type or "Humanoid"
  self.subtypes = opts.subtypes or {}
  self.alignment = opts.alignment or "True Neutral"

  self.skills = opts.skills or {}
  self.feats = opts.feats or {}
  self.special_abilities = opts.special_abilities or {}
  self.healing_potions = tonumber(opts.healing_potions) or 0

  self.conditions = conditionSet(opts.conditions_list)
  self.is_flat_footed = opts.is_flat_footed ~= false
  self.is_aware = opts.is_aware ~= false

  self.position = opts.position
  self.aoo_made_this_round = 0
  self.initiative_roll = 0
  self.initiative_total = 0
  self.initiative_modifier = tonumber(opts.initiative_modifier)

  self.standard_used = false
  self.move_used = false
  self.five_foot_used = false
  self.full_round_used = false
  self.distance_moved = 0
  self.charge_penalty = 0
  self.total_defense_bonus = 0
  self.no_aoo_until_next_turn = false
  self.aid_bonuses = {}

  self.color = opts.color
  self.token_label = opts.token_label
  if not self.color then
    local palette = TOKEN_PALETTE[(hashString(self.name) % #TOKEN_PALETTE) + 1]
    self.color = { palette[1], palette[2], palette[3] }
  end
  if not self.token_label then
    self.token_label = self.name:sub(1, 1):upper()
  end

  return self
end

function Combatant:getAbilityModifier(ability)
  return self.abilities:get_modifier(ability)
end

function Combatant:getAbilityScore(ability)
  return self.abilities:get_total_score(ability)
end

function Combatant:hasFeat(name)
  local needle = tostring(name):lower()
  for _, feat in ipairs(self.feats) do
    local lower = feat:lower()
    if lower == needle or lower:find(needle, 1, true) then
      return true, feat
    end
  end
  return false
end

function Combatant:featMatchesWeapon(featName, attack)
  if not attack then
    return self:hasFeat(featName)
  end
  local needle = tostring(featName):lower()
  local weaponName = attack.name:lower():gsub("%s*%+%d+$", "")
  for _, feat in ipairs(self.feats) do
    local lower = feat:lower()
    if lower:find(needle, 1, true) then
      local spec = lower:match("%((.-)%)")
      if not spec then return true end
      if spec:find(weaponName, 1, true) or weaponName:find(spec, 1, true) then
        return true
      end
    end
  end
  return false
end

function Combatant:sizeData()
  return constants.sizeData(self.size)
end

function Combatant:getSizeModifier()
  return self:sizeData().attackMod
end

function Combatant:getSpaceSquares()
  return math.max(1, self:sizeData().space)
end

function Combatant:getReachFeet()
  local reach = 0
  for _, attack in ipairs(self.attacks) do
    if attack:isMeleeLike() and attack.reach > reach then
      reach = attack.reach
    end
  end
  if reach < 5 then
    reach = math.max(5, self:sizeData().reach)
  end
  return reach
end

function Combatant:getFootprint(origin)
  local pos = origin or self.position
  if not pos then return {} end
  local space = self:getSpaceSquares()
  local cells = {}
  for dx = 0, space - 1 do
    for dy = 0, space - 1 do
      cells[#cells + 1] = { x = pos.x + dx, y = pos.y + dy }
    end
  end
  return cells
end

function Combatant:occupiesCell(x, y, origin)
  local pos = origin or self.position
  if not pos then return false end
  local space = self:getSpaceSquares()
  return x >= pos.x and x < pos.x + space and y >= pos.y and y < pos.y + space
end

function Combatant:cellDistance(x, y, origin)
  local pos = origin or self.position
  if not pos then return 9999 end
  local space = self:getSpaceSquares()
  local dx = math.max(pos.x - x, x - (pos.x + space - 1), 0)
  local dy = math.max(pos.y - y, y - (pos.y + space - 1), 0)
  return math.max(dx, dy)
end

function Combatant:hasCondition(condition)
  return self.conditions[condition] == true
end

function Combatant:hasAnyCondition(list)
  for _, c in ipairs(list) do
    if self.conditions[c] then return true end
  end
  return false
end

function Combatant:addCondition(condition)
  self.conditions[condition] = true
  if condition == "unconscious" and self.current_hp > 0 then
    self.is_flat_footed = true
  end
end

function Combatant:removeCondition(condition)
  self.conditions[condition] = nil
end

function Combatant:getConditionList()
  local list = {}
  local known = {}
  for _, c in ipairs(constants.ConditionOrder) do
    known[c] = true
    if self.conditions[c] then list[#list + 1] = c end
  end
  for _, c in ipairs(sortedKeys(self.conditions)) do
    if not known[c] then list[#list + 1] = c end
  end
  return list
end

function Combatant:getStatus()
  if self:hasCondition("dead") or self.current_hp <= -self:getAbilityScore("constitution") then
    return "dead"
  elseif self.current_hp < 0 then
    if self:hasCondition("stable") then return "stable" end
    return "dying"
  elseif self.current_hp == 0 then
    return "disabled"
  elseif self:hasCondition("unconscious") then
    return "unconscious"
  end
  return "ok"
end

function Combatant:getStatusLabel()
  local status = self:getStatus()
  if status == "ok" then return "OK" end
  return constants.Conditions[status] and constants.Conditions[status].label or status
end

function Combatant:isDead()
  return self:getStatus() == "dead"
end

function Combatant:isDying()
  return self:getStatus() == "dying"
end

function Combatant:isStable()
  return self:getStatus() == "stable"
end

function Combatant:isDisabled()
  return self:getStatus() == "disabled"
end

function Combatant:isAlive()
  return self.current_hp > 0 and not self:hasCondition("dead")
end

function Combatant:canAct()
  if self:isDead() then return false end
  if self.current_hp < 0 then return false end
  for condition in pairs(constants.UnableConditions) do
    if self.conditions[condition] then return false end
  end
  return true
end

function Combatant:canMakeAoO()
  if self.no_aoo_until_next_turn then return false end
  if self.is_flat_footed and not self:hasFeat("Combat Reflexes") then return false end
  if not self:canAct() then return false end
  return self.aoo_made_this_round < self:getMaxAoO()
end

function Combatant:getMaxAoO()
  local max = 1
  if self:hasFeat("Combat Reflexes") then
    max = max + math.max(0, self:getAbilityModifier("dex"))
  end
  return max
end

function Combatant:getInitiativeBonus()
  local bonus = self:getAbilityModifier("dex")
  if self:hasFeat("Improved Initiative") then bonus = bonus + 4 end
  return bonus
end

local function abilityModWithConditions(self, ability)
  local name = AbilityScores.fullName(ability)
  local mod = self.abilities:get_modifier(name)
  if name == "strength" or name == "dexterity" then
    if self:hasCondition("exhausted") then
      mod = mod - 3
    elseif self:hasCondition("fatigued") then
      mod = mod - 1
    end
    if name == "dexterity" and self:hasCondition("entangled") then
      mod = mod - 2
    end
  end
  return mod
end

function Combatant:losesDexToAC()
  if self.is_flat_footed then return true end
  for condition in pairs(constants.LoseDexConditions) do
    if self.conditions[condition] then return true end
  end
  return false
end

function Combatant:getAC(acType)
  acType = acType or "standard"
  local dex = self:getAbilityModifier("dex")
  local lostDex = self:losesDexToAC()
  local ac
  if acType == "touch" then
    ac = self.armor_class:calculate_touch_ac(dex, lostDex)
  elseif acType == "flat_footed" then
    ac = self.armor_class:calculate_flat_footed_ac()
  else
    ac = self.armor_class:calculate_ac(dex, lostDex)
  end

  ac = ac + self:getSizeModifier() + (self.armor_class.size_modifier or 0)

  if not lostDex and self:hasFeat("Dodge") then
    ac = ac + 1
  end
  if self:hasCondition("blinded") then ac = ac - 2 end
  if self:hasCondition("cowering") then ac = ac - 2 end
  if self:hasCondition("helpless") then ac = ac - 4 end
  if self:hasCondition("pinned") then ac = ac - 4 end
  if self:hasCondition("stunned") then ac = ac - 2 end

  ac = ac + (self.total_defense_bonus or 0)
  ac = ac - (self.charge_penalty or 0)
  return math.max(0, ac)
end

function Combatant:getAttackBonus(attack, opts)
  opts = opts or {}
  local ability = attack.associated_ability_for_attack
  if self:hasFeat("Weapon Finesse") and attack.attack_type == "melee" then
    ability = "dex"
  end
  local abilityMod = abilityModWithConditions(self, ability)

  local bab = self.base_attack_bonus
  local attackNumber = opts.attackNumber or 0
  if opts.fullAttack and attackNumber > 0 then
    bab = bab - attackNumber * 5
  end

  local bonus = bab + abilityMod + self:getSizeModifier() + attack.enhancement_bonus
  if self:featMatchesWeapon("Weapon Focus", attack) then bonus = bonus + 1 end

  if self:hasCondition("dazzled") then bonus = bonus - 1 end
  if self:hasCondition("entangled") then bonus = bonus - 2 end
  if self:hasCondition("frightened") or self:hasCondition("shaken") then bonus = bonus - 2 end
  if self:hasCondition("grappled") then bonus = bonus - 2 end
  if self:hasCondition("sickened") then bonus = bonus - 2 end
  if self:hasCondition("prone") then
    if attack.attack_type == "melee" or attack.attack_type == "natural" then
      bonus = bonus - 4
    elseif attack.attack_type == "ranged" then
      bonus = bonus - 20
    end
  end
  if attack.damaged then bonus = bonus - 2 end

  if opts.extraBonus then bonus = bonus + opts.extraBonus end

  if opts.target then
    for _, aid in ipairs(self.aid_bonuses or {}) do
      if aid.target_id == opts.target.id and not aid.expired then
        bonus = bonus + aid.value
      end
    end
  end

  return bonus
end

function Combatant:getDamageBonus(attack)
  local ability = attack.associated_ability_for_damage
  local mod = abilityModWithConditions(self, ability)
  if AbilityScores.fullName(ability) == "strength" then
    if attack.off_hand and mod > 0 then
      mod = math.floor(mod / 2)
    elseif attack.two_handed and mod > 0 then
      mod = math.floor(mod * 1.5)
    end
  end
  local bonus = mod + attack.enhancement_bonus
  if self:featMatchesWeapon("Weapon Specialization", attack) then bonus = bonus + 2 end
  if self:hasCondition("sickened") then bonus = bonus - 2 end
  if attack.damaged then bonus = bonus - 2 end
  return bonus
end

function Combatant:rollDamage(attack, isCrit)
  local roll = dice.rollNotation(attack.damage_dice)
  local bonus = self:getDamageBonus(attack)
  local raw = roll.total + bonus
  local mult = 1
  if isCrit then
    mult = attack:get_crit_multiplier()
    raw = raw * mult
  end
  return {
    total = math.max(1, raw),
    raw = raw,
    base = roll.total,
    rolls = roll.rolls,
    bonus = bonus,
    multiplier = mult,
    notation = attack.damage_dice,
  }
end

local function drBypassed(dr, damageType)
  if not dr or not dr.type or dr.type == "" then return false end
  local drType = tostring(dr.type):lower()
  local dtype = tostring(damageType):lower()
  if drType == "magic" then return false end
  return drType == dtype or drType:find(dtype, 1, true) ~= nil or dtype:find(drType, 1, true) ~= nil
end

function Combatant:takeDamage(amount, damageType, opts)
  opts = opts or {}
  local dtype = tostring(damageType or "untyped"):lower()
  local dmg = math.max(0, math.floor(tonumber(amount) or 0))
  local original = dmg
  local notes = {}

  if constants.PhysicalDamage[dtype] and self.damage_reduction then
    local dr = self.damage_reduction
    if (dr.amount or 0) > 0 and not drBypassed(dr, dtype) then
      dmg = math.max(0, dmg - dr.amount)
      notes[#notes + 1] = "DR " .. dr.amount
    end
  end

  if self.energy_immunities[dtype] then
    dmg = 0
    notes[#notes + 1] = "immune"
  elseif self.energy_vulnerabilities[dtype] then
    dmg = dmg * 2
    notes[#notes + 1] = "vulnerable (x2)"
  end

  local resist = self.energy_resistances[dtype]
  if resist and resist > 0 then
    dmg = math.max(0, dmg - resist)
    notes[#notes + 1] = "resist " .. resist
  end

  local absorbed = 0
  if self.temp_hp > 0 and dmg > 0 then
    absorbed = math.min(self.temp_hp, dmg)
    self.temp_hp = self.temp_hp - absorbed
    dmg = dmg - absorbed
  end

  if dmg > 0 then
    if self.current_hp - dmg < 0 then
      self:removeCondition("stable")
    end
    self.current_hp = self.current_hp - dmg
  end

  local deathThreshold = -self:getAbilityScore("constitution")
  if self.current_hp <= deathThreshold then
    self.current_hp = deathThreshold
    self:addCondition("dead")
    self:removeCondition("dying")
    self:removeCondition("disabled")
    self:removeCondition("stable")
  elseif self.current_hp < 0 then
    self:addCondition("dying")
    self:removeCondition("disabled")
  elseif self.current_hp == 0 then
    if not self:hasCondition("dead") then
      self:addCondition("disabled")
      self:removeCondition("dying")
    end
  else
    self:removeCondition("disabled")
    self:removeCondition("dying")
  end

  return dmg, {
    original = original,
    absorbed = absorbed,
    notes = notes,
    damageType = dtype,
    target_hp = self.current_hp,
  }
end

function Combatant:heal(amount)
  amount = math.max(0, math.floor(tonumber(amount) or 0))
  local old = self.current_hp
  self.current_hp = math.min(self.max_hp, self.current_hp + amount)
  if self.current_hp > 0 then
    self:removeCondition("disabled")
    self:removeCondition("dying")
    self:removeCondition("stable")
    self:removeCondition("dead")
  elseif self.current_hp == 0 then
    self:addCondition("disabled")
    self:removeCondition("dying")
    self:removeCondition("stable")
  end
  return self.current_hp - old
end

function Combatant:getSaveBonus(saveType)
  local base = self.saving_throws:base(saveType)
  local ability = saveType == "fortitude" and "constitution" or
    (saveType == "reflex" and "dexterity" or "wisdom")
  local bonus = base + self:getAbilityModifier(ability)
  if self:hasCondition("shaken") or self:hasCondition("frightened") then
    bonus = bonus - 2
  end
  if self:hasCondition("sickened") then
    bonus = bonus - 2
  end
  return bonus
end

function Combatant:makeSavingThrow(saveType, dc)
  local bonus = self:getSaveBonus(saveType)
  local roll = dice.d20()
  local total = roll + bonus
  local success
  if roll == 1 then
    success = false
  elseif roll == 20 then
    success = true
  else
    success = total >= dc
  end
  return {
    saveType = saveType,
    roll = roll,
    bonus = bonus,
    total = total,
    dc = dc,
    success = success,
  }
end

function Combatant:stabilize()
  if not self:isDying() then
    return { success = false, reason = "not dying" }
  end
  local penalty = math.max(0, -self.current_hp)
  local dc = 10 + penalty
  local conMod = self:getAbilityModifier("con")
  local roll = dice.d20()
  local total = roll + conMod
  local success = roll == 20 or total >= dc

  local result = {
    roll = roll,
    bonus = conMod,
    total = total,
    dc = dc,
    success = success,
    death = false,
  }

  if success then
    self:addCondition("stable")
    self:removeCondition("dying")
  else
    self.current_hp = self.current_hp - 1
    local deathThreshold = -self:getAbilityScore("constitution")
    if self.current_hp <= deathThreshold then
      self.current_hp = deathThreshold
      self:addCondition("dead")
      self:removeCondition("dying")
      self:removeCondition("stable")
      result.death = true
    end
  end
  return result
end

function Combatant:calculateCMB()
  local bab = self.base_attack_bonus
  local abilityMod
  if self.size == "Fine" or self.size == "Diminutive" or self.size == "Tiny" then
    abilityMod = self:getAbilityModifier("dex")
  else
    abilityMod = self:getAbilityModifier("str")
  end
  return bab + abilityMod + self:sizeData().cmbMod
end

function Combatant:calculateCMD()
  local cmd = 10 + self.base_attack_bonus + self:getAbilityModifier("str") +
    self:getAbilityModifier("dex") + self:sizeData().cmbMod +
    (self.armor_class.deflection_bonus or 0) + (self.armor_class.dodge_bonus or 0)
  if self.is_flat_footed and self:getAbilityModifier("dex") > 0 then
    cmd = cmd - self:getAbilityModifier("dex")
  end
  if self:hasCondition("prone") then cmd = cmd - 4 end
  return cmd
end

function Combatant:threatenedSquares(gridWidth, gridHeight)
  local reachSquares = math.max(1, math.floor(self:getReachFeet() / 5))
  local own = {}
  local threatened = {}
  for _, cell in ipairs(self:getFootprint()) do
    own[cell.x .. "," .. cell.y] = true
  end
  for _, cell in ipairs(self:getFootprint()) do
    for dx = -reachSquares, reachSquares do
      for dy = -reachSquares, reachSquares do
        local x = cell.x + dx
        local y = cell.y + dy
        local dist = math.max(math.abs(dx), math.abs(dy))
        if dist >= 1 and dist <= reachSquares then
          if x >= 1 and y >= 1 and x <= (gridWidth or 100) and y <= (gridHeight or 100) then
            local key = x .. "," .. y
            if not own[key] then threatened[key] = true end
          end
        end
      end
    end
  end
  return threatened
end

function Combatant:canReach(target, attack)
  if not target or not target.position then return false end
  local reachSquares = math.ceil((attack and attack.reach or self:getReachFeet()) / 5)
  local targetCells = target:getFootprint()
  local best = 9999
  for _, cell in ipairs(targetCells) do
    local d = self:cellDistance(cell.x, cell.y)
    if d < best then best = d end
  end
  return best <= reachSquares
end

function Combatant:resetActions()
  self.standard_used = false
  self.move_used = false
  self.five_foot_used = false
  self.full_round_used = false
  self.distance_moved = 0
end

function Combatant:resetForTurn()
  self:resetActions()
  self.charge_penalty = 0
  self.total_defense_bonus = 0
  self.no_aoo_until_next_turn = false
  self:removeCondition("charge")
  for _, aid in ipairs(self.aid_bonuses) do
    if aid.expires_for_id == self.id then aid.expired = true end
  end
  local active = {}
  for _, aid in ipairs(self.aid_bonuses) do
    if not aid.expired then active[#active + 1] = aid end
  end
  self.aid_bonuses = active
end

function Combatant:resetForCombat()
  self.current_hp = self.max_hp
  self.temp_hp = 0
  self.conditions = {}
  self.is_flat_footed = true
  self.aoo_made_this_round = 0
  self.initiative_roll = 0
  self.initiative_total = 0
  self:resetActions()
  self.charge_penalty = 0
  self.total_defense_bonus = 0
  self.no_aoo_until_next_turn = false
  self.aid_bonuses = {}
  for _, attack in ipairs(self.dropped_attacks) do
    attack.damaged = false
    self.attacks[#self.attacks + 1] = attack
  end
  self.dropped_attacks = {}
  for _, attack in ipairs(self.attacks) do
    attack.damaged = false
  end
  self:removeCondition("disarmed")
  self:removeCondition("weapon-damaged")
end

function Combatant:dropWeapons()
  local kept = {}
  local dropped = {}
  for _, attack in ipairs(self.attacks) do
    if attack.attack_type == "natural" then
      kept[#kept + 1] = attack
    else
      dropped[#dropped + 1] = attack
    end
  end
  if #dropped == 0 then return false end
  self.attacks = kept
  for _, attack in ipairs(dropped) do
    self.dropped_attacks[#self.dropped_attacks + 1] = attack
  end
  self:addCondition("disarmed")
  return true
end

function Combatant:recoverWeapons()
  if #self.dropped_attacks == 0 then return false end
  for _, attack in ipairs(self.dropped_attacks) do
    self.attacks[#self.attacks + 1] = attack
  end
  self.dropped_attacks = {}
  self:removeCondition("disarmed")
  return true
end

function Combatant:getPrimaryAttack()
  return self.attacks[1]
end

function Combatant:getMeleeAttacks()
  local list = {}
  for _, attack in ipairs(self.attacks) do
    if attack:isMeleeLike() then list[#list + 1] = attack end
  end
  return list
end

function Combatant:to_dict()
  local attacks = {}
  for _, attack in ipairs(self.attacks) do
    attacks[#attacks + 1] = attack:to_dict()
  end
  local res = {}
  for k, v in pairs(self.energy_resistances) do res[k] = v end
  local conditions = {}
  for _, c in ipairs(self:getConditionList()) do
    if c ~= "dead" and c ~= "dying" and c ~= "disabled" and
       c ~= "stable" and c ~= "flat-footed" and c ~= "charge" then
      conditions[#conditions + 1] = c
    end
  end
  return {
    name = self.name,
    is_pc = self.is_pc,
    max_hp = self.max_hp,
    ability_scores = self.abilities:to_dict(),
    base_attack_bonus = self.base_attack_bonus,
    armor_class = self.armor_class:to_dict(),
    saving_throws = self.saving_throws:to_dict(),
    base_speed = self.base_speed,
    size = self.size,
    creature_type = self.creature_type,
    subtypes = self.subtypes,
    alignment = self.alignment,
    skills = self.skills,
    feats = self.feats,
    healing_potions = self.healing_potions,
    attacks = attacks,
    damage_reduction = self.damage_reduction,
    spell_resistance = self.spell_resistance,
    energy_resistances = res,
    energy_immunities = self.energy_immunity_list,
    energy_vulnerabilities = self.energy_vulnerability_list,
    notes = self.notes,
    color = self.color,
    token_label = self.token_label,
    conditions = conditions,
  }
end

function Combatant.from_dict(data)
  if not data then return nil end
  local attacks = {}
  for _, attackData in ipairs(data.attacks or {}) do
    attacks[#attacks + 1] = Attack.from_dict(attackData)
  end
  local opts = {
    name = data.name,
    is_pc = data.is_pc,
    max_hp = data.max_hp,
    ability_scores = data.ability_scores,
    base_attack_bonus = data.base_attack_bonus,
    armor_class = data.armor_class,
    saving_throws = data.saving_throws,
    base_speed = data.base_speed,
    size = data.size,
    creature_type = data.creature_type,
    subtypes = data.subtypes,
    alignment = data.alignment,
    skills = data.skills,
    feats = data.feats,
    healing_potions = data.healing_potions,
    attacks = attacks,
    damage_reduction = data.damage_reduction,
    spell_resistance = data.spell_resistance,
    energy_resistances = data.energy_resistances,
    energy_immunities = data.energy_immunities,
    energy_vulnerabilities = data.energy_vulnerabilities,
    notes = data.notes,
    color = data.color,
    token_label = data.token_label,
    conditions_list = data.conditions,
    initiative_modifier = data.initiative_modifier,
  }
  return Combatant.new(opts)
end

return Combatant
