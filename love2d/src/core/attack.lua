local constants = require("src.core.constants")

local Attack = {}
Attack.__index = Attack

local function parseThreatRange(text)
  local s = tostring(text or "20"):gsub("%s", "")
  local low, high = s:match("^(%d+)%-(%d+)$")
  if low and high then
    local range = {}
    for i = tonumber(low), tonumber(high) do
      if i >= 1 and i <= 20 then range[#range + 1] = i end
    end
    if #range > 0 then return range end
  end
  local single = tonumber(s)
  if single and single >= 1 and single <= 20 then return { single } end
  return { 20 }
end

local function parseMultiplier(text)
  if type(text) == "number" then
    return math.max(2, math.floor(text))
  end
  local s = tostring(text or "x2"):lower():gsub("%s", "")
  local n = tonumber(s:match("^x?(%d+)$") or "")
  if n and n >= 2 then return n end
  return 2
end

function Attack.new(opts)
  opts = opts or {}
  local self = setmetatable({}, Attack)
  self.name = opts.name or "Unarmed Strike"
  self.damage_dice = opts.damage_dice or "1d3"
  self.critical_threat_range = tostring(opts.critical_threat_range or "20")
  self.critical_multiplier = tostring(opts.critical_multiplier or "x2")
  self.damage_type = opts.damage_type or constants.DamageType.BLUDGEONING
  self.attack_type = opts.attack_type or constants.AttackType.MELEE
  self.reach = tonumber(opts.reach) or 5
  self.associated_ability_for_attack = opts.associated_ability_for_attack or "str"
  self.associated_ability_for_damage = opts.associated_ability_for_damage or "str"
  self.is_primary_natural_attack = opts.is_primary_natural_attack ~= false
  self.special_qualities = opts.special_qualities or {}
  self.enhancement_bonus = tonumber(opts.enhancement_bonus) or 0
  self.two_handed = opts.two_handed == true
  self.off_hand = opts.off_hand == true
  self.damaged = opts.damaged == true
  self.natural = self.attack_type == constants.AttackType.NATURAL
  return self
end

function Attack:get_threat_range()
  return parseThreatRange(self.critical_threat_range)
end

function Attack:get_crit_multiplier()
  return parseMultiplier(self.critical_multiplier)
end

function Attack:isMeleeLike()
  return self.attack_type == constants.AttackType.MELEE or
    self.attack_type == constants.AttackType.NATURAL
end

function Attack:to_dict()
  return {
    name = self.name,
    damage_dice = self.damage_dice,
    critical_threat_range = self.critical_threat_range,
    critical_multiplier = self.critical_multiplier,
    damage_type = self.damage_type,
    attack_type = self.attack_type,
    reach = self.reach,
    associated_ability_for_attack = self.associated_ability_for_attack,
    associated_ability_for_damage = self.associated_ability_for_damage,
    is_primary_natural_attack = self.is_primary_natural_attack,
    special_qualities = self.special_qualities,
    enhancement_bonus = self.enhancement_bonus,
    two_handed = self.two_handed,
    off_hand = self.off_hand,
    damaged = self.damaged,
  }
end

function Attack.from_dict(data)
  if not data then return nil end
  return Attack.new(data)
end

Attack.parseThreatRange = parseThreatRange
Attack.parseMultiplier = parseMultiplier

return Attack
