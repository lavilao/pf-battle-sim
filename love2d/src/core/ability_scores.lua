local AbilityScores = {}
AbilityScores.__index = AbilityScores

local ABILITIES = {
  strength = true,
  dexterity = true,
  constitution = true,
  intelligence = true,
  wisdom = true,
  charisma = true,
}

local SHORT = {
  str = "strength",
  dex = "dexterity",
  con = "constitution",
  int = "intelligence",
  wis = "wisdom",
  cha = "charisma",
  strength = "strength",
  dexterity = "dexterity",
  constitution = "constitution",
  intelligence = "intelligence",
  wisdom = "wisdom",
  charisma = "charisma",
}

local TEMP = {
  strength = "temp_str",
  dexterity = "temp_dex",
  constitution = "temp_con",
  intelligence = "temp_int",
  wisdom = "temp_wis",
  charisma = "temp_cha",
}

function AbilityScores.new(opts)
  opts = opts or {}
  local self = setmetatable({}, AbilityScores)
  for key in pairs(ABILITIES) do
    self[key] = tonumber(opts[key]) or 10
  end
  for _, key in pairs(TEMP) do
    self[key] = tonumber(opts[key]) or 0
  end
  return self
end

function AbilityScores.fullName(ability)
  return SHORT[tostring(ability):lower()] or tostring(ability):lower()
end

function AbilityScores:get_modifier(ability)
  local name = AbilityScores.fullName(ability)
  local score = self[name] or 10
  local temp = self[TEMP[name]] or 0
  return math.floor((score + temp - 10) / 2)
end

function AbilityScores:get_total_score(ability)
  local name = AbilityScores.fullName(ability)
  return (self[name] or 10) + (self[TEMP[name]] or 0)
end

function AbilityScores:set(ability, value)
  local name = AbilityScores.fullName(ability)
  if ABILITIES[name] then
    self[name] = tonumber(value) or 10
  end
end

function AbilityScores:to_dict()
  return {
    strength = self.strength,
    dexterity = self.dexterity,
    constitution = self.constitution,
    intelligence = self.intelligence,
    wisdom = self.wisdom,
    charisma = self.charisma,
    temp_str = self.temp_str,
    temp_dex = self.temp_dex,
    temp_con = self.temp_con,
    temp_int = self.temp_int,
    temp_wis = self.temp_wis,
    temp_cha = self.temp_cha,
  }
end

function AbilityScores.from_dict(data)
  return AbilityScores.new(data or {})
end

return AbilityScores
