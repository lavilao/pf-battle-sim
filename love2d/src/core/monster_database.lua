local json = require("src.util.json")
local Combatant = require("src.core.combatant")

local MonsterDatabase = {}
MonsterDatabase.__index = MonsterDatabase

MonsterDatabase.BUNDLED = {
  "orc_warrior", "orc_barbarian", "goblin", "goblin_archer",
  "skeleton", "zombie", "wolf", "ogre", "bandit", "dire_rat",
  "sir_roderick", "shadowstep",
}

local ABILITIES = {
  "strength", "dexterity", "constitution",
  "intelligence", "wisdom", "charisma",
}

local function deepCopy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for key, val in pairs(value) do
    out[key] = deepCopy(val)
  end
  return out
end

local function readFile(path)
  if love and love.filesystem and love.filesystem.read then
    local contents = love.filesystem.read(path)
    if contents then return contents end
  end
  local file = io.open(path, "r")
  if not file then
    file = io.open("love2d/" .. path, "r")
  end
  if not file then return nil end
  local contents = file:read("*a")
  file:close()
  return contents
end

local function writeFile(path, contents)
  if love and love.filesystem and love.filesystem.write then
    local ok, err = love.filesystem.write(path, contents)
    return ok == true, err
  end
  local file, err = io.open(path, "w")
  if not file then return false, err end
  file:write(contents)
  file:close()
  return true
end

local function deleteFile(path)
  if love and love.filesystem and love.filesystem.remove then
    return love.filesystem.remove(path)
  end
  return os.remove(path) ~= nil
end

local function listJsonFiles(dir)
  local keys = {}
  if love and love.filesystem and love.filesystem.getDirectoryItems then
    for _, item in ipairs(love.filesystem.getDirectoryItems(dir)) do
      local stem = item:match("^(.+)%.json$")
      if stem then keys[#keys + 1] = stem end
    end
  else
    local pipe = io.popen(string.format("ls %q 2>/dev/null", dir))
    if pipe then
      for line in pipe:lines() do
        local stem = line:match("^(.+)%.json$")
        if stem then keys[#keys + 1] = stem end
      end
      pipe:close()
    end
  end
  table.sort(keys)
  return keys
end

function MonsterDatabase.slug(name)
  local slug = tostring(name or "monster"):lower()
  slug = slug:gsub("[^%w]+", "_"):gsub("^_+", ""):gsub("_+$", "")
  if slug == "" then slug = "monster" end
  return slug
end

function MonsterDatabase.validate(data)
  if type(data) ~= "table" then
    return false, "statblock must be an object"
  end
  if type(data.name) ~= "string" or data.name:match("^%s*$") then
    return false, "name is required"
  end
  if tonumber(data.max_hp) == nil or tonumber(data.max_hp) < 1 then
    return false, "max_hp must be a positive number"
  end
  if data.ability_scores ~= nil and type(data.ability_scores) ~= "table" then
    return false, "ability_scores must be an object"
  end
  if data.attacks ~= nil and type(data.attacks) ~= "table" then
    return false, "attacks must be an array"
  end
  return true
end

local function normalize(data)
  local out = deepCopy(data)
  out.name = tostring(out.name)
  out.max_hp = math.max(1, math.floor(tonumber(out.max_hp) or 1))
  out.is_pc = out.is_pc == true
  out.ability_scores = out.ability_scores or {}
  for _, ability in ipairs(ABILITIES) do
    local value = tonumber(out.ability_scores[ability])
    out.ability_scores[ability] = value and math.floor(value) or 10
  end
  out.base_attack_bonus = math.floor(tonumber(out.base_attack_bonus) or 0)
  out.armor_class = out.armor_class or {}
  out.saving_throws = out.saving_throws or {}
  out.attacks = out.attacks or {}
  out.feats = out.feats or {}
  out.skills = out.skills or {}
  out.base_speed = math.floor(tonumber(out.base_speed) or 30)
  out.size = out.size or "Medium"
  out.creature_type = out.creature_type or "Humanoid"
  out.subtypes = out.subtypes or {}
  out.alignment = out.alignment or "True Neutral"
  out.energy_resistances = out.energy_resistances or {}
  out.energy_immunities = out.energy_immunities or {}
  out.energy_vulnerabilities = out.energy_vulnerabilities or {}
  out.notes = out.notes or ""
  return out
end

function MonsterDatabase.new(opts)
  opts = opts or {}
  local self = setmetatable({}, MonsterDatabase)
  self.customDir = opts.customDir or "custom_monsters"
  self.noDisk = opts.noDisk == true
  self.entries = {}
  self.errors = {}
  self:_loadBundled()
  self:_loadCustom()
  return self
end

function MonsterDatabase:_loadBundled()
  for _, key in ipairs(MonsterDatabase.BUNDLED) do
    local text = readFile("data/monsters/" .. key .. ".json")
    if text then
      local ok, data = pcall(json.decode, text)
      if ok and data then
        local valid, err = MonsterDatabase.validate(data)
        if valid then
          self.entries[key] = { key = key, data = normalize(data), custom = false }
        else
          self.errors[#self.errors + 1] = key .. ": " .. tostring(err)
        end
      else
        self.errors[#self.errors + 1] = key .. ": invalid JSON"
      end
    else
      self.errors[#self.errors + 1] = key .. ": file not found"
    end
  end
end

function MonsterDatabase:_loadCustom()
  for _, stem in ipairs(listJsonFiles(self.customDir)) do
    local text = readFile(self.customDir .. "/" .. stem .. ".json")
    if text then
      local ok, data = pcall(json.decode, text)
      if ok and data then
        local valid = MonsterDatabase.validate(data)
        if valid then
          self.entries[stem] = { key = stem, data = normalize(data), custom = true }
        else
          self.errors[#self.errors + 1] = stem .. ": invalid statblock"
        end
      else
        self.errors[#self.errors + 1] = stem .. ": invalid JSON"
      end
    end
  end
end

function MonsterDatabase:reload()
  self.entries = {}
  self.errors = {}
  self:_loadBundled()
  self:_loadCustom()
  return self:getDefinitions()
end

function MonsterDatabase:getDefinitions()
  local list = {}
  for _, entry in pairs(self.entries) do
    list[#list + 1] = entry
  end
  table.sort(list, function(a, b)
    local nameA = a.data.name:lower()
    local nameB = b.data.name:lower()
    if nameA == nameB then return a.key < b.key end
    return nameA < nameB
  end)
  return list
end

function MonsterDatabase:getEntry(key)
  return self.entries[key]
end

function MonsterDatabase:get(key)
  local entry = self.entries[key]
  return entry and entry.data or nil
end

function MonsterDatabase:findByName(name)
  local needle = tostring(name or ""):lower()
  for _, entry in pairs(self.entries) do
    if entry.data.name:lower() == needle then return entry end
  end
  return nil
end

function MonsterDatabase:instantiate(keyOrData, opts)
  opts = opts or {}
  local data
  if type(keyOrData) == "table" then
    data = keyOrData
  else
    local entry = self.entries[keyOrData]
    if not entry then return nil end
    data = entry.data
  end
  local copy = deepCopy(data)
  if opts.is_pc ~= nil then copy.is_pc = opts.is_pc end
  if opts.name then copy.name = opts.name end
  local combatant = Combatant.from_dict(copy)
  if combatant then
    if opts.position then
      combatant.position = { x = opts.position.x, y = opts.position.y }
    end
    if opts.healing_potions then
      combatant.healing_potions = opts.healing_potions
    end
    if opts.is_aware ~= nil then
      combatant.is_aware = opts.is_aware
    end
  end
  return combatant
end

function MonsterDatabase:addCustom(data)
  local valid, err = MonsterDatabase.validate(data)
  if not valid then
    return nil, err
  end
  local normalized = normalize(data)
  normalized.is_pc = false
  local baseKey = "custom_" .. MonsterDatabase.slug(normalized.name)
  local key = baseKey
  local counter = 2
  while self.entries[key] do
    key = baseKey .. "_" .. counter
    counter = counter + 1
  end
  normalized._key = nil
  self.entries[key] = { key = key, data = normalized, custom = true }
  if not self.noDisk then
    local ok, writeErr = writeFile(self.customDir .. "/" .. key .. ".json",
      json.encode(normalized, true))
    if not ok then
      return key, writeErr
    end
  end
  return key
end

function MonsterDatabase:updateCustom(key, data)
  local entry = self.entries[key]
  if not entry or not entry.custom then
    return false, "not a custom monster"
  end
  local valid, err = MonsterDatabase.validate(data)
  if not valid then return false, err end
  local normalized = normalize(data)
  normalized.is_pc = entry.data.is_pc
  entry.data = normalized
  if not self.noDisk then
    writeFile(self.customDir .. "/" .. key .. ".json", json.encode(normalized, true))
  end
  return true
end

function MonsterDatabase:removeCustom(key)
  local entry = self.entries[key]
  if not entry then return false end
  if not entry.custom then
    return false, "bundled monsters cannot be deleted"
  end
  self.entries[key] = nil
  if not self.noDisk then
    deleteFile(self.customDir .. "/" .. key .. ".json")
  end
  return true
end

function MonsterDatabase:exportKey(key)
  local entry = self.entries[key]
  if not entry then return nil, "monster not found" end
  return json.encode(entry.data, true)
end

function MonsterDatabase:importJSON(text)
  local ok, data = pcall(json.decode, text)
  if not ok or not data then
    return nil, "invalid JSON"
  end
  if data.is_pc == nil then data.is_pc = false end
  return self:addCustom(data)
end

function MonsterDatabase:createBlank()
  return {
    name = "New Monster",
    is_pc = false,
    max_hp = 10,
    ability_scores = {
      strength = 10, dexterity = 10, constitution = 10,
      intelligence = 10, wisdom = 10, charisma = 10,
    },
    base_attack_bonus = 0,
    armor_class = {
      armor_bonus = 0, shield_bonus = 0, natural_armor_bonus = 0,
      deflection_bonus = 0, dodge_bonus = 0, size_modifier = 0,
      max_dex_bonus_from_armor = nil,
    },
    saving_throws = { fortitude_base = 0, reflex_base = 0, will_base = 0 },
    base_speed = 30,
    size = "Medium",
    creature_type = "Humanoid",
    subtypes = {},
    alignment = "True Neutral",
    skills = {},
    feats = {},
    attacks = {
      {
        name = "Slam",
        damage_dice = "1d6",
        critical_threat_range = "20",
        critical_multiplier = "x2",
        damage_type = "bludgeoning",
        attack_type = "melee",
        reach = 5,
        associated_ability_for_attack = "str",
        associated_ability_for_damage = "str",
        enhancement_bonus = 0,
      },
    },
    energy_resistances = {},
    energy_immunities = {},
    energy_vulnerabilities = {},
    notes = "",
  }
end

MonsterDatabase.deepCopy = deepCopy

return MonsterDatabase
