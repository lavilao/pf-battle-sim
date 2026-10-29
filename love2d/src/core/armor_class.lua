local ArmorClass = {}
ArmorClass.__index = ArmorClass

function ArmorClass.new(opts)
  opts = opts or {}
  local self = setmetatable({}, ArmorClass)
  self.armor_bonus = tonumber(opts.armor_bonus) or 0
  self.shield_bonus = tonumber(opts.shield_bonus) or 0
  self.natural_armor_bonus = tonumber(opts.natural_armor_bonus) or 0
  self.deflection_bonus = tonumber(opts.deflection_bonus) or 0
  self.dodge_bonus = tonumber(opts.dodge_bonus) or 0
  self.size_modifier = tonumber(opts.size_modifier) or 0
  self.max_dex_bonus_from_armor = tonumber(opts.max_dex_bonus_from_armor)
  return self
end

function ArmorClass:effective_dex(dex_modifier, lost_dex)
  if lost_dex then return 0 end
  local dex = dex_modifier
  if self.max_dex_bonus_from_armor and dex > self.max_dex_bonus_from_armor then
    dex = self.max_dex_bonus_from_armor
  end
  return dex
end

function ArmorClass:calculate_ac(dex_modifier, lost_dex)
  return 10 + self.armor_bonus + self.shield_bonus +
    self.natural_armor_bonus + self:effective_dex(dex_modifier, lost_dex) +
    self.size_modifier + self.deflection_bonus +
    (lost_dex and 0 or self.dodge_bonus)
end

function ArmorClass:calculate_touch_ac(dex_modifier, lost_dex)
  return 10 + self:effective_dex(dex_modifier, lost_dex) +
    self.size_modifier + self.deflection_bonus +
    (lost_dex and 0 or self.dodge_bonus)
end

function ArmorClass:calculate_flat_footed_ac()
  return 10 + self.armor_bonus + self.shield_bonus +
    self.natural_armor_bonus + self.size_modifier + self.deflection_bonus
end

function ArmorClass:to_dict()
  return {
    armor_bonus = self.armor_bonus,
    shield_bonus = self.shield_bonus,
    natural_armor_bonus = self.natural_armor_bonus,
    deflection_bonus = self.deflection_bonus,
    dodge_bonus = self.dodge_bonus,
    size_modifier = self.size_modifier,
    max_dex_bonus_from_armor = self.max_dex_bonus_from_armor,
  }
end

function ArmorClass.from_dict(data)
  return ArmorClass.new(data)
end

return ArmorClass
