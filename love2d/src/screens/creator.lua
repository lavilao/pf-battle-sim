-- Custom monster creator/editor. Layout is tuned for the 1440x900 canvas.
local theme = require("src.ui.theme")
local ui = require("src.ui.widgets")
local constants = require("src.core.constants")
local json = require("src.util.json")
local Screen = {}
Screen.__index = Screen
local LEFT_TOP, LEFT_STEP, INPUT_DY, INPUT_H = 140, 43, 13, 30
local COL_X, COL_W = { 32, 312 }, 248
local ATTACK_TOP, ATTACK_STEP, ATTACK_H = 162, 68, 30
local ABILITY_ITEMS = { "str", "dex", "con", "int", "wis", "cha" }
local ABILITY_SET = { str = true, dex = true, con = true, int = true, wis = true, cha = true }
local ABILITY_FULL = {
  strength = "str", dexterity = "dex", constitution = "con",
  intelligence = "int", wisdom = "wis", charisma = "cha",
}
local ATTACK_HEADERS = {
  { "Name", 608 }, { "Damage dice", 806 }, { "Threat", 894 }, { "Mult", 972 },
  { "Damage type", 1040 }, { "Attack type", 1198 }, { "Action", 1326 },
}
local ATTACK_SUBLABELS = {
  { "Reach", 608 }, { "Enh", 714 }, { "Atk ability", 818 }, { "Dmg ability", 1028 },
}
local function deepCopy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for key, val in pairs(value) do out[key] = deepCopy(val) end
  return out
end
local function trim(text)
  return (tostring(text or ""):gsub("^%s+", ""):gsub("%s+$", ""))
end
local function asText(value, fallback)
  if type(value) == "string" then return value end
  if type(value) == "number" or type(value) == "boolean" then return tostring(value) end
  return fallback or ""
end
local function textOr(value, fallback)
  local text = asText(value, fallback)
  if text == "" then return fallback or "" end
  return text
end
local function numberText(value, fallback)
  local number = tonumber(value)
  if number == nil then
    if fallback == nil then return "" end
    return tostring(fallback)
  end
  if number == math.floor(number) and math.abs(number) < 1e15 then
    return string.format("%d", number)
  end
  return tostring(number)
end
local function splitList(text)
  local list = {}
  for part in tostring(text or ""):gmatch("[^,]+") do
    local item = trim(part)
    if item ~= "" then list[#list + 1] = item end
  end
  return list
end
local function parsePairs(text, numbersOnly)
  local out = {}
  for part in tostring(text or ""):gmatch("[^,]+") do
    local key, raw = part:match("^%s*(.-)%s*:%s*(.-)%s*$")
    if key and key ~= "" then
      local number = tonumber(raw)
      if number ~= nil then out[key] = number
      elseif not numbersOnly and trim(raw) ~= "" then out[key] = trim(raw) end
    end
  end
  return out
end
local function formatList(value)
  if type(value) == "string" then return value end
  if type(value) ~= "table" then return "" end
  local list = {}
  for i = 1, #value do
    local item = value[i]
    if type(item) == "string" or type(item) == "number" then
      list[#list + 1] = tostring(item)
    end
  end
  if #list == 0 then
    for _, item in pairs(value) do
      if type(item) == "string" or type(item) == "number" then
        list[#list + 1] = tostring(item)
      end
    end
    table.sort(list)
  end
  return table.concat(list, ", ")
end
local function formatPairs(value)
  if type(value) ~= "table" then return "" end
  local parts = {}
  for key, val in pairs(value) do
    if type(key) ~= "number" and (type(val) == "number" or type(val) == "string") then
      parts[#parts + 1] = tostring(key) .. ":" .. tostring(val)
    end
  end
  table.sort(parts)
  return table.concat(parts, ", ")
end
local function withValue(items, value)
  local out = {}
  for i = 1, #(items or {}) do out[i] = items[i] end
  if value ~= nil and value ~= "" then
    local found = false
    for _, item in ipairs(out) do
      if item == value then found = true; break end
    end
    if not found then out[#out + 1] = value end
  end
  return out
end
local function abilityShort(value)
  local key = tostring(value or ""):lower()
  if ABILITY_SET[key] then return key end
  return ABILITY_FULL[key] or "str"
end
local function defaultAttack()
  return {
    name = "Slam", damage_dice = "1d6", critical_threat_range = "20",
    critical_multiplier = "x2", damage_type = "bludgeoning",
    attack_type = "melee", reach = 5, enhancement_bonus = 0,
    associated_ability_for_attack = "str", associated_ability_for_damage = "str",
  }
end
local function attackValues(base)
  if type(base) ~= "table" then base = {} end
  return {
    name = asText(base.name, ""),
    damage_dice = textOr(base.damage_dice, "1d6"),
    threat = textOr(base.critical_threat_range, "20"),
    mult = textOr(base.critical_multiplier, "x2"),
    damage_type = textOr(base.damage_type, "bludgeoning"),
    attack_type = textOr(base.attack_type, "melee"),
    reach = numberText(base.reach, 5),
    enhancement = numberText(base.enhancement_bonus, 0),
    atk_ability = abilityShort(base.associated_ability_for_attack),
    dmg_ability = abilityShort(base.associated_ability_for_damage),
  }
end
local function appendAll(destination, source)
  for i = 1, #(source or {}) do destination[#destination + 1] = source[i] end
end
function Screen.new(app)
  local self = setmetatable({}, Screen)
  self.app = app
  self.returnTo = "bestiary"
  self.originalData = {}
  self:_resetState()
  return self
end
function Screen:_resetState()
  self.labels, self.fields, self.attacks, self.extraAttacks = {}, {}, {}, {}
  self.leftInputs, self.leftDropdowns, self.leftCheckboxes = {}, {}, {}
  self.attackInputs, self.attackDropdowns, self.attackButtons = {}, {}, {}
  self.navButtons, self.addButton = {}, nil
  self.inputs, self.dropdowns, self.buttons = {}, {}, {}
  self.errorMessage = nil
end
function Screen:_blurOwnedInput()
  local focused = ui._focusedInput
  if not focused then return end
  for _, widget in ipairs(self.inputs or {}) do
    if widget == focused then
      if focused.blur then focused:blur() end
      return
    end
  end
end
function Screen:enter(opts)
  opts = type(opts) == "table" and opts or {}
  self:_blurOwnedInput()
  self:_resetState()
  self.returnTo = asText(opts.returnTo, "bestiary")
  if self.returnTo == "" then self.returnTo = "bestiary" end
  local database = self.app and self.app.database
  local function blank()
    if database and database.createBlank then
      local data = database:createBlank()
      if type(data) == "table" then return data end
    end
    return {}
  end
  local source
  self.editingKey = nil
  if opts.key ~= nil and database and database.get then
    local existing = database:get(opts.key)
    if type(existing) == "table" then
      source = deepCopy(existing)
      self.editingKey = opts.key
    end
  end
  if not source then
    if type(opts.data) == "table" then source = deepCopy(opts.data) else source = blank() end
  end
  if type(source) ~= "table" then source = blank() end
  self.originalData = deepCopy(source)
  self:_buildLeftForm(source)
  self:_buildTopButtons()
  self:_buildAttacks(source)
  self:_refreshLists()
  self:_refreshAddButton()
end
function Screen:_buildTopButtons()
  self.navButtons = {
    ui.Button.new({ x = 1170, y = 16, w = 110, h = 38, label = "Back",
      font = "smallBold", tooltip = "Return without saving (Esc).",
      onClick = function() self:_navigate() end }),
    ui.Button.new({ x = 1292, y = 16, w = 132, h = 38, label = "Save",
      style = "primary", font = "smallBold", tooltip = "Validate and save this statblock.",
      onClick = function() self:_save() end }),
  }
  self.addButton = ui.Button.new({ x = 608, y = 574, w = 144, h = 32,
    label = "Add Attack", font = "smallBold", tooltip = "Add another attack row (maximum 6).",
    onClick = function() self:_addAttack() end })
end
function Screen:_buildLeftForm(data)
  local ac = type(data.armor_class) == "table" and data.armor_class or {}
  local saves = type(data.saving_throws) == "table" and data.saving_throws or {}
  local scores = type(data.ability_scores) == "table" and data.ability_scores or {}
  local dr = type(data.damage_reduction) == "table" and data.damage_reduction or nil
  local function addLabel(text, x, y) self.labels[#self.labels + 1] = { text = text, x = x, y = y } end
  local function field(col, row, key, text, value, tip, ph, numeric, max)
    local x = COL_X[col]
    local top = LEFT_TOP + (row - 1) * LEFT_STEP
    addLabel(text, x, top)
    local widget = ui.TextInput.new({ x = x, y = top + INPUT_DY, w = COL_W, h = INPUT_H,
      value = value or "", placeholder = ph or "", numeric = numeric == true,
      maxLength = max, font = "small", tooltip = tip })
    self.leftInputs[#self.leftInputs + 1] = widget
    self.fields[key] = widget
  end
  local function dropdown(col, row, key, text, items, value, tip)
    local x = COL_X[col]
    local top = LEFT_TOP + (row - 1) * LEFT_STEP
    addLabel(text, x, top)
    local widget = ui.Dropdown.new({ x = x, y = top + INPUT_DY, w = COL_W, h = INPUT_H,
      items = withValue(items, value), value = value, font = "small",
      placeholder = "Select...", tooltip = tip })
    self.leftDropdowns[#self.leftDropdowns + 1] = widget
    self.fields[key] = widget
  end
  field(1, 1, "name", "Name", asText(data.name, ""),
    "Name shown in the bestiary and encounter builder.", "Monster name", false, 80)
  field(2, 1, "alignment", "Alignment", textOr(data.alignment, "True Neutral"),
    nil, "True Neutral", false, 40)
  field(1, 2, "max_hp", "Max HP", numberText(data.max_hp, 10),
    "Maximum hit points; must be at least 1.", "10", true, 8)
  field(2, 2, "base_speed", "Base speed", numberText(data.base_speed, 30),
    "Base speed in feet per round.", "30", true, 8)
  dropdown(1, 3, "size", "Size", constants.Sizes, textOr(data.size, "Medium"),
    "Size category; modifies AC and attack rolls.")
  field(2, 3, "creature_type", "Creature type", textOr(data.creature_type, "Humanoid"),
    nil, "Humanoid", false, 40)
  local hero = ui.Checkbox.new({ x = 32, y = LEFT_TOP + 3 * LEFT_STEP + 18, size = 18,
    label = "Hero (PC)", checked = data.is_pc == true, font = "small",
    tooltip = "Mark this statblock as a hero instead of a monster." })
  self.leftCheckboxes[#self.leftCheckboxes + 1] = hero
  self.fields.is_pc = hero
  addLabel("Hero", 32, LEFT_TOP + 3 * LEFT_STEP)
  field(2, 4, "bab", "BAB", numberText(data.base_attack_bonus, 0),
    "Base attack bonus before ability and size modifiers.", "0", true, 8)
  local abilities = {
    { "str", "Strength", 5, scores.strength, "Strength: melee attack and damage bonuses." },
    { "dex", "Dexterity", 5, scores.dexterity, "Dexterity: AC, Reflex saves, and ranged attacks." },
    { "con", "Constitution", 6, scores.constitution, "Constitution: hit points and Fortitude saves." },
    { "int", "Intelligence", 6, scores.intelligence, "Intelligence: skill points and knowledge." },
    { "wis", "Wisdom", 7, scores.wisdom, "Wisdom: Will saves and perception." },
    { "cha", "Charisma", 7, scores.charisma, "Charisma: force of personality and social skills." },
  }
  for i, ability in ipairs(abilities) do
    field(i % 2 == 1 and 1 or 2, ability[3], ability[1], ability[2],
      numberText(ability[4], 10), ability[5], "10", true, 5)
  end
  local acFields = {
    { "ac_armor", "Armor bonus", 8, 1, ac.armor_bonus, "Armor bonus to AC; not applied to touch AC." },
    { "ac_shield", "Shield bonus", 8, 2, ac.shield_bonus, "Shield bonus to AC; not applied to touch AC." },
    { "ac_natural", "Natural armor", 9, 1, ac.natural_armor_bonus, "Natural armor bonus to AC." },
    { "ac_deflection", "Deflection", 9, 2, ac.deflection_bonus, "Deflection bonus to AC." },
    { "ac_dodge", "Dodge bonus", 10, 1, ac.dodge_bonus, "Dodge bonus to AC; lost when denied Dexterity." },
    { "ac_size", "Size modifier", 10, 2, ac.size_modifier, "Size modifier to AC." },
  }
  for _, f in ipairs(acFields) do
    field(f[4], f[3], f[1], f[2], numberText(f[5], 0), f[6], "0", true, 6)
  end
  field(1, 11, "fort", "Fort base", numberText(saves.fortitude_base, 0),
    "Base Fortitude save before ability modifiers.", "0", true, 6)
  field(2, 11, "ref", "Ref base", numberText(saves.reflex_base, 0),
    "Base Reflex save before ability modifiers.", "0", true, 6)
  field(1, 12, "will", "Will base", numberText(saves.will_base, 0),
    "Base Will save before ability modifiers.", "0", true, 6)
  field(2, 12, "potions", "Healing potions", numberText(data.healing_potions, 0),
    "Healing potions carried into battle.", "0", true, 5)
  field(1, 13, "dr_amount", "DR amount", numberText(dr and dr.amount, ""),
    "Damage reduction amount, for example 5 for DR 5/bludgeoning.", "0", true, 6)
  field(2, 13, "dr_type", "DR type", dr and asText(dr.type, "") or "",
    "Damage reduction bypass, such as bludgeoning or silver.", "bludgeoning", false, 40)
  field(1, 14, "sr", "Spell resistance", numberText(data.spell_resistance, 0),
    "Spell resistance; 0 means none.", "0", true, 6)
  field(1, 15, "feats", "Feats", formatList(data.feats),
    "Comma-separated feat names.", "Dodge, Toughness", false, 240)
  field(2, 15, "skills", "Skills", formatPairs(data.skills),
    "Comma-separated Name:bonus pairs.", "Heal:4, Stealth:8", false, 240)
  field(1, 16, "resistances", "Resistances", formatPairs(data.energy_resistances),
    "Comma-separated type:amount resistances.", "fire:5, cold:5", false, 240)
  field(2, 16, "immunities", "Immunities", formatList(data.energy_immunities),
    "Comma-separated damage or energy immunities.", "cold, fear", false, 240)
  field(1, 17, "vulnerabilities", "Vulnerabilities", formatList(data.energy_vulnerabilities),
    "Comma-separated damage or energy vulnerabilities.", "silver", false, 240)
  local notes = asText(data.notes, ""):gsub("[\r\n]+", " ")
  field(2, 17, "notes", "Notes", notes, "A single-line note shown in the bestiary.",
    "Short note for the bestiary", false, 240)
end
function Screen:_buildAttacks(data)
  local raw = type(data.attacks) == "table" and data.attacks or {}
  self.attacks, self.extraAttacks = {}, {}
  for i = 1, math.min(#raw, 6) do
    if type(raw[i]) == "table" then
      self.attacks[#self.attacks + 1] = { base = deepCopy(raw[i]) }
    end
  end
  if #self.attacks == 0 then self.attacks[1] = { base = defaultAttack() } end
  for i = 7, #raw do
    if type(raw[i]) == "table" then
      self.extraAttacks[#self.extraAttacks + 1] = deepCopy(raw[i])
    end
  end
  for i, row in ipairs(self.attacks) do self:_createAttackRow(row, i) end
end
function Screen:_createAttackRow(row, index, values)
  values = values or attackValues(row.base)
  local y = ATTACK_TOP + (index - 1) * ATTACK_STEP
  local y2 = y + 32
  local inputs, dropdowns = {}, {}
  local function input(key, x, w, value, top, tip, ph, numeric, max)
    local widget = ui.TextInput.new({ x = x, y = top, w = w, h = ATTACK_H,
      value = value or "", placeholder = ph or "", numeric = numeric == true,
      maxLength = max, font = "small", tooltip = tip })
    inputs[key] = widget
    self.attackInputs[#self.attackInputs + 1] = widget
  end
  local function dropdown(key, x, w, top, items, value, tip)
    local widget = ui.Dropdown.new({ x = x, y = top, w = w, h = ATTACK_H,
      items = withValue(items, value), value = value, font = "small", tooltip = tip })
    dropdowns[key] = widget
    self.attackDropdowns[#self.attackDropdowns + 1] = widget
  end
  input("name", 608, 190, values.name, y, nil, "Attack name", false, 60)
  input("damage_dice", 806, 80, values.damage_dice, y,
    "Damage dice such as 1d6 or 2d4+1.", "1d6", false, 20)
  input("threat", 894, 70, values.threat, y,
    "Critical threat range, such as 20 or 18-20.", "20", false, 10)
  input("mult", 972, 60, values.mult, y,
    "Critical multiplier, such as x2 or x3.", "x2", false, 6)
  dropdown("damage_type", 1040, 150, y, constants.DamageTypes, values.damage_type,
    "Damage type dealt by this attack.")
  dropdown("attack_type", 1198, 120, y, constants.AttackTypes, values.attack_type,
    "Melee, ranged, or natural attack.")
  input("reach", 648, 58, values.reach, y2, "Reach in feet.", "5", true, 6)
  input("enhancement", 752, 58, values.enhancement, y2,
    "Enhancement bonus to attack and damage.", "0", true, 6)
  dropdown("atk_ability", 894, 126, y2, ABILITY_ITEMS, values.atk_ability,
    "Ability modifier applied to the attack roll.")
  dropdown("dmg_ability", 1110, 126, y2, ABILITY_ITEMS, values.dmg_ability,
    "Ability modifier applied to damage.")
  local removeButton = ui.Button.new({ x = 1326, y = y, w = 82, h = ATTACK_H,
    label = "Remove", style = "danger", font = "small", tooltip = "Remove this attack.",
    onClick = function() self:_removeAttack(row) end })
  self.attackButtons[#self.attackButtons + 1] = removeButton
  row.inputs, row.dropdowns, row.removeButton, row.values = inputs, dropdowns, removeButton, values
end
function Screen:_refreshLists()
  self.inputs = {}
  appendAll(self.inputs, self.leftInputs)
  appendAll(self.inputs, self.attackInputs)
  self.dropdowns = {}
  appendAll(self.dropdowns, self.leftDropdowns)
  appendAll(self.dropdowns, self.attackDropdowns)
  self.buttons = {}
  appendAll(self.buttons, self.navButtons)
  if self.addButton then self.buttons[#self.buttons + 1] = self.addButton end
  appendAll(self.buttons, self.attackButtons)
end
function Screen:_refreshAddButton()
  if self.addButton then self.addButton:setEnabled(#self.attacks < 6) end
end
function Screen:_readAttackRow(row)
  local inputs, dropdowns = row.inputs or {}, row.dropdowns or {}
  local function input(key)
    local widget = inputs[key]
    return widget and widget.value or ""
  end
  local function dropdown(key)
    local widget = dropdowns[key]
    return widget and widget.value or nil
  end
  return {
    name = input("name"), damage_dice = input("damage_dice"),
    threat = input("threat"), mult = input("mult"),
    damage_type = dropdown("damage_type") or "bludgeoning",
    attack_type = dropdown("attack_type") or "melee",
    reach = input("reach"), enhancement = input("enhancement"),
    atk_ability = dropdown("atk_ability") or "str",
    dmg_ability = dropdown("dmg_ability") or "str",
  }
end
function Screen:_syncAttackValues(row)
  if row.inputs then row.values = self:_readAttackRow(row) end
end
function Screen:_clearAttackWidgets()
  self.attackInputs, self.attackDropdowns, self.attackButtons = {}, {}, {}
  for _, row in ipairs(self.attacks) do
    row.inputs, row.dropdowns, row.removeButton = nil, nil, nil
  end
end
function Screen:_addAttack()
  if #self.attacks >= 6 then return end
  local row = { base = defaultAttack() }
  self.attacks[#self.attacks + 1] = row
  self:_createAttackRow(row, #self.attacks)
  self:_refreshLists()
  self:_refreshAddButton()
end
function Screen:_removeAttack(row)
  local index
  for i, candidate in ipairs(self.attacks) do
    if candidate == row then index = i; break end
  end
  if not index then return end
  for _, candidate in ipairs(self.attacks) do self:_syncAttackValues(candidate) end
  self:_blurOwnedInput()
  table.remove(self.attacks, index)
  self:_clearAttackWidgets()
  for i, candidate in ipairs(self.attacks) do
    self:_createAttackRow(candidate, i, candidate.values)
  end
  self:_refreshLists()
  self:_refreshAddButton()
end
function Screen:_collect()
  local source = type(self.originalData) == "table" and deepCopy(self.originalData) or {}
  local function input(key)
    local widget = self.fields[key]
    return widget and widget.value or ""
  end
  local function integer(key, fallback)
    local value = tonumber(input(key))
    if value == nil then return fallback end
    return math.floor(value)
  end
  source.name = trim(input("name"))
  source.is_pc = self.fields.is_pc and self.fields.is_pc.checked == true or false
  source.max_hp = integer("max_hp", 10)
  source.base_speed = integer("base_speed", 30)
  source.size = trim(input("size")); if source.size == "" then source.size = "Medium" end
  source.creature_type = trim(input("creature_type"))
  if source.creature_type == "" then source.creature_type = "Humanoid" end
  source.alignment = trim(input("alignment"))
  if source.alignment == "" then source.alignment = "True Neutral" end
  local scores = type(source.ability_scores) == "table" and source.ability_scores or {}
  scores.strength = integer("str", 10)
  scores.dexterity = integer("dex", 10)
  scores.constitution = integer("con", 10)
  scores.intelligence = integer("int", 10)
  scores.wisdom = integer("wis", 10)
  scores.charisma = integer("cha", 10)
  source.ability_scores = scores
  source.base_attack_bonus = integer("bab", 0)
  source.healing_potions = math.max(0, integer("potions", 0))
  local ac = type(source.armor_class) == "table" and source.armor_class or {}
  ac.armor_bonus = integer("ac_armor", 0)
  ac.shield_bonus = integer("ac_shield", 0)
  ac.natural_armor_bonus = integer("ac_natural", 0)
  ac.deflection_bonus = integer("ac_deflection", 0)
  ac.dodge_bonus = integer("ac_dodge", 0)
  ac.size_modifier = integer("ac_size", 0)
  source.armor_class = ac
  local saves = type(source.saving_throws) == "table" and source.saving_throws or {}
  saves.fortitude_base = integer("fort", 0)
  saves.reflex_base = integer("ref", 0)
  saves.will_base = integer("will", 0)
  source.saving_throws = saves
  source.feats = splitList(input("feats"))
  source.skills = parsePairs(input("skills"), true)
  local drText = trim(input("dr_amount"))
  if drText == "" then
    source.damage_reduction = nil
  else
    source.damage_reduction = { amount = math.floor(tonumber(drText) or 0),
      type = trim(input("dr_type")) }
  end
  source.spell_resistance = math.max(0, integer("sr", 0))
  source.energy_resistances = parsePairs(input("resistances"), true)
  source.energy_immunities = splitList(input("immunities"))
  source.energy_vulnerabilities = splitList(input("vulnerabilities"))
  source.notes = trim((input("notes"):gsub("[\r\n]+", " ")))
  local attacks = {}
  for _, row in ipairs(self.attacks) do
    local values = self:_readAttackRow(row)
    local attack = type(row.base) == "table" and deepCopy(row.base) or {}
    attack.name = trim(values.name)
    attack.damage_dice = trim(values.damage_dice)
    attack.critical_threat_range = trim(values.threat)
    if attack.critical_threat_range == "" then attack.critical_threat_range = "20" end
    attack.critical_multiplier = trim(values.mult)
    if attack.critical_multiplier == "" then attack.critical_multiplier = "x2" end
    attack.damage_type = values.damage_type
    attack.attack_type = values.attack_type
    attack.reach = math.floor(tonumber(values.reach) or 5)
    attack.enhancement_bonus = math.floor(tonumber(values.enhancement) or 0)
    attack.associated_ability_for_attack = abilityShort(values.atk_ability)
    attack.associated_ability_for_damage = abilityShort(values.dmg_ability)
    attacks[#attacks + 1] = attack
  end
  for _, extra in ipairs(self.extraAttacks) do attacks[#attacks + 1] = deepCopy(extra) end
  source.attacks = attacks
  return source
end
function Screen:_persistHeroFlag(key, isPc)
  local database = self.app and self.app.database
  local entry = database and database.getEntry and database:getEntry(key)
  if not entry or type(entry.data) ~= "table" then return end
  local flag = isPc == true
  if entry.data.is_pc == flag then return end
  entry.data.is_pc = flag
  if love and love.filesystem and love.filesystem.write then
    pcall(love.filesystem.write, "custom_monsters/" .. tostring(key) .. ".json",
      json.encode(entry.data, true))
  end
end
function Screen:_save()
  local record = self:_collect()
  if record.name == "" then
    self:_setError("Name is required.")
    return
  end
  local database = self.app and self.app.database
  if not database then
    self:_setError("No monster database is available.")
    return
  end
  if self.editingKey then
    local ok, err = database:updateCustom(self.editingKey, record)
    if not ok then
      self:_setError(err or "Could not update this monster.")
      return
    end
    self:_persistHeroFlag(self.editingKey, record.is_pc)
  else
    local key, err = database:addCustom(record)
    if not key then
      self:_setError(err or "Could not create this monster.")
      return
    end
    self:_persistHeroFlag(key, record.is_pc)
  end
  self:_navigate()
end
function Screen:_setError(message)
  self.errorMessage = tostring(message or "Could not save this monster.")
end
function Screen:_destinationName()
  if self.returnTo == "setup" then return "Encounter Builder" end
  if self.returnTo == "menu" then return "Main Menu" end
  return "Bestiary"
end
function Screen:_navigate()
  if not self.app then return end
  if self.returnTo == "setup" then self.app:showSetup()
  elseif self.returnTo == "menu" then self.app:showMenu()
  else self.app:showBestiary(self.returnTo or "bestiary") end
end
function Screen:leave()
  self:_blurOwnedInput()
  self:_resetState()
end
function Screen:update(dt)
end
function Screen:draw()
  local colors = theme.colors
  local title = self.editingKey and "Edit Monster" or "Create Monster"
  local subtitle = self.editingKey and "Refine an existing custom statblock."
    or "Build a new statblock for the bestiary."
  theme.drawText(title, 32, 8, "h1", colors.gold)
  theme.drawText(subtitle, 34, 52, "small", colors.textMuted)
  theme.drawText("Returns to " .. self:_destinationName(),
    900, 60, "small", colors.textMuted, "right", 524)
  if self.errorMessage and self.errorMessage ~= "" then
    theme.drawText(self.errorMessage, 540, 20, "small", colors.red, "right", 610)
  end
  theme.drawPanel(16, 84, 560, 800, { title = "Identity & Defenses", titleFont = "h3" })
  theme.drawPanel(592, 84, 832, 800, { title = "Attacks & Notes", titleFont = "h3" })
  for _, label in ipairs(self.labels) do
    theme.drawText(label.text, label.x, label.y, "tiny", colors.textMuted)
  end
  for i = 1, #self.attacks do
    local y = ATTACK_TOP + (i - 1) * ATTACK_STEP
    theme.setColor(colors.panelAlt, 0.55)
    love.graphics.rectangle("fill", 600, y - 4, 816, 66, 4, 4)
  end
  for _, header in ipairs(ATTACK_HEADERS) do
    theme.drawText(header[1], header[2], 142, "tiny", colors.textMuted)
  end
  for i = 1, #self.attacks do
    local y = ATTACK_TOP + (i - 1) * ATTACK_STEP
    for _, label in ipairs(ATTACK_SUBLABELS) do
      theme.drawText(label[1], label[2], y + 40, "tiny", colors.textMuted)
    end
  end
  theme.drawText(string.format("Attacks %d / 6", #self.attacks),
    764, 582, "small", colors.textMuted)
  theme.drawText("Damage dice: 1d6 or 2d4+1. Threat: 20 or 18-20. Multiplier: x2. " ..
    "Up to six attack rows.", 608, 616, "small", colors.textMuted, nil, 790)
  for _, widget in ipairs(self.inputs) do widget:draw() end
  for _, widget in ipairs(self.leftCheckboxes) do widget:draw() end
  for _, widget in ipairs(self.buttons) do widget:draw() end
  for _, widget in ipairs(self.dropdowns) do
    if not widget:isOpen() then widget:draw() end
  end
  for _, widget in ipairs(self.dropdowns) do
    if widget:isOpen() then widget:draw() end
  end
end
function Screen:mousepressed(x, y, button)
  for _, dropdown in ipairs(self.dropdowns) do
    if dropdown:isOpen() and dropdown:mousepressed(x, y, button) then return true end
  end
  for _, dropdown in ipairs(self.dropdowns) do
    if not dropdown:isOpen() and dropdown:mousepressed(x, y, button) then return true end
  end
  for _, widget in ipairs(self.inputs) do
    if widget:mousepressed(x, y, button) then return true end
  end
  for _, widget in ipairs(self.leftCheckboxes) do
    if widget:mousepressed(x, y, button) then return true end
  end
  for _, widget in ipairs(self.buttons) do
    if widget:mousepressed(x, y, button) then return true end
  end
  return false
end
function Screen:mousereleased(x, y, button)
  for _, widget in ipairs(self.buttons) do
    if widget.mousereleased then widget:mousereleased(x, y, button) end
  end
end
function Screen:keypressed(key)
  if key == "escape" then
    self:_navigate()
    return true
  end
  local focused = ui._focusedInput
  if focused then
    for _, widget in ipairs(self.inputs) do
      if widget == focused then return widget:keypressed(key) end
    end
  end
  return false
end
function Screen:textinput(text)
  local focused = ui._focusedInput
  if focused then
    for _, widget in ipairs(self.inputs) do
      if widget == focused then return widget:textinput(text) end
    end
  end
  return false
end
function Screen:wheelmoved(dx, dy)
  return false
end
return Screen
