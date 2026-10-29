-- Pure-Lua tests for the Pathfinder core rules. Run from the repository root:
--   lua5.3 tests/test_core.lua        (inside love2d/)
--   lua5.3 love2d/tests/test_core.lua (from project root)

local root = (arg and arg[0] and arg[0]:match("^(.*)/tests/[^/]+$")) or "."
package.path = root .. "/?.lua;" .. root .. "/?/init.lua;" .. package.path

local Constants = require("src.core.constants")
local Dice = require("src.core.dice")
local Combatant = require("src.core.combatant")
local Attack = require("src.core.attack")
local CombatEngine = require("src.core.combat_engine")
local ActionHandler = require("src.core.action_handler")
local MonsterDatabase = require("src.core.monster_database")
local AI = require("src.core.ai")
local json = require("src.util.json")

local passed, failed = 0, 0
local failures = {}

local function check(condition, label, detail)
  if condition then
    passed = passed + 1
  else
    failed = failed + 1
    failures[#failures + 1] = label .. (detail and (" - " .. tostring(detail)) or "")
    io.write("FAIL: " .. label .. (detail and (" - " .. tostring(detail)) or "") .. "\n")
  end
end

local function eq(actual, expected, label)
  check(actual == expected, label, string.format("expected %s, got %s",
    tostring(expected), tostring(actual)))
end

local function approx(actual, expected, label)
  check(math.abs((actual or 0) - expected) < 0.0001, label,
    string.format("expected %s, got %s", tostring(expected), tostring(actual)))
end

local rollQueue = {}
local function queueRolls(...)
  rollQueue = {}
  for _, value in ipairs({ ... }) do
    rollQueue[#rollQueue + 1] = value
  end
  Dice.setRoller(function(sides)
    local value = table.remove(rollQueue, 1)
    if value == nil then return math.random(sides) end
    return math.min(value, sides)
  end)
end

local function clearRolls()
  Dice.clearRoller()
end

local function makeFighter(name, isPc, opts)
  opts = opts or {}
  local attacks = opts.attacks or {
    {
      name = "Longsword",
      damage_dice = "1d8",
      critical_threat_range = "20",
      critical_multiplier = "x2",
      damage_type = "slashing",
      attack_type = "melee",
      reach = 5,
    },
  }
  return Combatant.new({
    name = name,
    is_pc = isPc,
    max_hp = opts.max_hp or 20,
    ability_scores = {
      strength = 16, dexterity = 12, constitution = 12,
      intelligence = 10, wisdom = 10, charisma = 10,
    },
    base_attack_bonus = opts.bab or 1,
    armor_class = { armor_bonus = 4 },
    saving_throws = { fortitude_base = 2, reflex_base = 1, will_base = 0 },
    attacks = attacks,
    feats = opts.feats or { "Weapon Focus (Longsword)" },
    skills = opts.skills or {},
  })
end

-- ---------------------------------------------------------------- ability math
do
  local scores = require("src.core.ability_scores").new({
    strength = 18, dexterity = 7, constitution = 10,
    intelligence = 10, wisdom = 10, charisma = 10,
  })
  eq(scores:get_modifier("str"), 4, "ability modifier +4 for 18")
  eq(scores:get_modifier("dex"), -2, "ability modifier -2 for 7")
  eq(scores:get_modifier("dexterity"), -2, "ability modifier accepts full name")
end

-- ------------------------------------------------------------------- database
local db
do
  db = MonsterDatabase.new({ noDisk = true })
  eq(#db.errors, 0, "bundled monsters all load without errors", table.concat(db.errors, "; "))
  local defs = db:getDefinitions()
  eq(#defs, 12, "12 bundled monsters")
  local orc = db:instantiate("orc_warrior")
  check(orc ~= nil, "instantiate orc warrior")
  if orc then
    eq(orc.name, "Orc Warrior", "orc name")
    eq(orc.max_hp, 6, "orc hp")
    check(orc:getAC("standard") >= 13, "orc AC calculated", orc:getAC("standard"))
    check(#orc.attacks == 1 and orc.attacks[1].name == "Falchion", "orc falchion")
  end
  local skeleton = db:instantiate("skeleton")
  if skeleton then
    eq(skeleton.damage_reduction.amount, 5, "skeleton DR value")
    eq(skeleton.damage_reduction.type, "bludgeoning", "skeleton DR type")
    check(skeleton.energy_immunities.cold == true, "skeleton cold immunity")
  end
  local bandit = db:instantiate("bandit")
  check(bandit and bandit:hasFeat("Dodge"), "bandit has Dodge feat")
end

-- --------------------------------------------------------------- save / import
do
  local customKey, err = db:addCustom({
    name = "Test Ooze",
    is_pc = false,
    max_hp = 22,
    ability_scores = { strength = 12 },
    attacks = {},
  })
  check(customKey ~= nil, "add custom monster", err)
  local entry = db:getEntry(customKey)
  check(entry and entry.custom, "custom entry flagged")
  eq(entry.data.ability_scores.dexterity, 10, "missing abilities default to 10")
  local exported = db:exportKey(customKey)
  check(exported and exported:find("Test Ooze", 1, true), "export JSON contains name")
  local importedKey, importErr = db:importJSON(exported)
  check(importedKey ~= nil, "re-import custom monster", importErr)
  check(db:removeCustom(customKey), "remove custom monster")
  check(db:get(customKey) == nil, "custom monster removed")
  local bad, badErr = db:addCustom({ name = "", max_hp = 0 })
  check(bad == nil and badErr ~= nil, "validation rejects bad statblock")
end

-- --------------------------------------------------------------------- attacks
local engine, handler
do
  local pc = makeFighter("Alice", true)
  local npc = makeFighter("Bob", false)
  pc.position = { x = 5, y = 5 }
  npc.position = { x = 6, y = 5 }
  pc.is_flat_footed = false
  npc.is_flat_footed = false
  pc:resetForTurn()
  npc:resetForTurn()

  engine = CombatEngine.new()
  handler = ActionHandler.new(engine)
  engine:addCombatant(pc)
  engine:addCombatant(npc)
  engine.combatants = { pc, npc }
  engine.combat_active = true

  approx(pc:getAttackBonus(pc.attacks[1]), 5, "attack bonus = BAB 1 + Str 3 + WF 1")
  eq(pc:getDamageBonus(pc.attacks[1]), 3, "damage bonus = Str 3")
  eq(pc:getAC("standard"), 15, "AC = 10 + armor 4 + Dex 1")

  queueRolls(15, 8)
  local outcome = handler:takeAttackAction(pc, npc, 1)
  check(outcome.success, "standard attack succeeds")
  eq(npc.current_hp, 20 - 11, "hit deals d8(8) + 3 damage")
  check(pc.standard_used, "standard action consumed")

  require("src.core.action_handler")
  pc:resetForTurn()
  queueRolls(1)
  local miss = handler:takeAttackAction(pc, npc, 1)
  check(miss.result and not miss.result.is_hit, "natural 1 always misses")
  pc:resetForTurn()
  queueRolls(20, 20, 8)
  local crit = handler:takeAttackAction(pc, npc, 1)
  check(crit.result and crit.result.is_critical_hit, "natural 20 threatens and confirms")
  eq(crit.result.damage, (8 + 3) * 2, "critical damage doubled")
  clearRolls()
end

-- ------------------------------------------------------------------ full attack
do
  local pc = makeFighter("HighBAB", true, { bab = 6 })
  local npc = makeFighter("Dummy", false)
  pc.position = { x = 3, y = 3 }
  npc.position = { x = 4, y = 3 }
  pc.is_flat_footed = false
  npc.is_flat_footed = false
  pc:resetForTurn()

  local engine2 = CombatEngine.new()
  local handler2 = ActionHandler.new(engine2)
  engine2:addCombatant(pc)
  engine2:addCombatant(npc)
  engine2.combatants = { pc, npc }
  engine2.combat_active = true

  queueRolls(15, 5, 15, 5)
  local outcome = handler2:takeFullAttackAction(pc, npc, 1)
  check(outcome.success, "full attack succeeds")
  eq(#outcome.results, 2, "BAB 6 grants two iterative attacks")
  eq(npc.current_hp, 20 - 16, "both iterative attacks damage the target")
  check(pc.full_round_used, "full-round action consumed")
  clearRolls()
end

-- ------------------------------------------------------ attacks of opportunity
do
  local archer = makeFighter("Archer", true, {
    attacks = {
      {
        name = "Shortbow",
        damage_dice = "1d6",
        critical_threat_range = "20",
        critical_multiplier = "x2",
        damage_type = "piercing",
        attack_type = "ranged",
        reach = 5,
        associated_ability_for_attack = "dex",
        associated_ability_for_damage = "str",
      },
    },
    bab = 2,
    feats = {},
  })
  local guard = makeFighter("Guard", false)
  archer.position = { x = 5, y = 5 }
  guard.position = { x = 6, y = 5 }
  archer.is_flat_footed = false
  guard.is_flat_footed = false
  archer:resetForTurn()
  guard:resetForTurn()
  guard.aoo_made_this_round = 0

  local engine3 = CombatEngine.new()
  local handler3 = ActionHandler.new(engine3)
  engine3:addCombatant(archer)
  engine3:addCombatant(guard)
  engine3.combatants = { archer, guard }
  engine3.combat_active = true

  queueRolls(15, 4, 15, 3)
  local outcome = handler3:takeAttackAction(archer, guard, 1)
  check(outcome.aoo ~= nil, "ranged attack triggers an AoO")
  eq(#outcome.aoo.results, 1, "guard makes one AoO")
  check(archer.current_hp < archer.max_hp, "AoO damages the archer")
  eq(guard.aoo_made_this_round, 1, "AoO usage tracked")
  check(outcome.result ~= nil, "ranged attack still resolves if not interrupted")
  clearRolls()
end

-- ------------------------------------------------------------ movement and AoO
do
  local mover = makeFighter("Mover", true)
  local guard = makeFighter("Guard", false)
  mover.position = { x = 6, y = 5 }
  guard.position = { x = 5, y = 5 }
  mover.is_flat_footed = false
  guard.is_flat_footed = false
  mover:resetForTurn()
  guard:resetForTurn()
  guard.aoo_made_this_round = 0

  local engine4 = CombatEngine.new()
  local handler4 = ActionHandler.new(engine4)
  engine4:addCombatant(mover)
  engine4:addCombatant(guard)
  engine4.combatants = { mover, guard }
  engine4.combat_active = true

  queueRolls(15, 4)
  local outcome = handler4:takeMoveAction(mover, 9, 5)
  eq(#outcome.results, 1, "leaving a threatened square provokes one AoO")
  eq(mover.position.x, 9, "uninterrupted movement completes")
  clearRolls()

  -- A lethal AoO stops movement in place.
  local frail = makeFighter("Frail", true, { max_hp = 3 })
  local guard2 = makeFighter("Guard2", false)
  frail.position = { x = 6, y = 5 }
  guard2.position = { x = 5, y = 5 }
  frail.is_flat_footed = false
  guard2.is_flat_footed = false
  frail:resetForTurn()
  guard2:resetForTurn()
  guard2.aoo_made_this_round = 0
  engine4:addCombatant(frail)
  engine4:addCombatant(guard2)
  engine4.combatants = { frail, guard2 }
  engine4.provocation_counter = 0

  queueRolls(15, 8)
  local stopped = handler4:takeMoveAction(frail, 9, 5)
  check(stopped.stopped == true or frail.current_hp < 0, "lethal AoO interrupts movement")
  eq(frail.position.x, 6, "interrupted movement stops before leaving the square")
  clearRolls()
end

-- ---------------------------------------------------------- death and combat end
do
  local pc = makeFighter("Winner", true)
  local npc = makeFighter("Loser", false, { max_hp = 5 })
  pc.position = { x = 2, y = 2 }
  npc.position = { x = 3, y = 2 }
  local engine5 = CombatEngine.new()
  engine5:addCombatant(pc)
  engine5:addCombatant(npc)
  engine5.combatants = { pc, npc }
  engine5.combat_active = true

  local effective = npc:takeDamage(50, "slashing")
  eq(effective, 50, "damage applied")
  check(npc:isDead(), "negative Constitution kills")
  eq(npc.current_hp, -12, "HP clamps at -Constitution")
  check(engine5:maybeEndCombat(), "combat ends when a side is defeated")
  eq(engine5.winner, "PCs", "PC side wins")

  local dying = makeFighter("Dying", false)
  dying:takeDamage(dying.max_hp + 2, "slashing")
  check(dying:isDying(), "below zero HP is dying")
  queueRolls(20)
  local stabilized = dying:stabilize()
  check(stabilized.success, "natural 20 stabilizes")
  check(dying:isStable(), "stable condition applied")
  clearRolls()

  local corpse = makeFighter("Corpse", false)
  corpse.current_hp = 0
  check(not corpse:isDead(), "0 HP is disabled, not dead")
  check(corpse:canAct(), "disabled creatures can still take one action")
end

-- ---------------------------------------------------------------- maneuvers
do
  local tripper = makeFighter("Tripper", true)
  local victim = makeFighter("Victim", false)
  tripper.position = { x = 1, y = 1 }
  victim.position = { x = 2, y = 1 }
  tripper.is_flat_footed = false
  victim.is_flat_footed = false
  tripper:resetForTurn()

  local engine6 = CombatEngine.new()
  local handler6 = ActionHandler.new(engine6)
  engine6:addCombatant(tripper)
  engine6:addCombatant(victim)
  engine6.combatants = { tripper, victim }
  engine6.combat_active = true

  queueRolls(19, 15)
  local result = handler6:takeCombatManeuver(tripper, victim, "trip")
  check(result.success, "trip succeeds on high roll")
  check(victim:hasCondition("prone"), "tripped target is prone")

  victim:removeCondition("prone")
  tripper:resetForTurn()
  queueRolls(15)
  local disarm = handler6:takeCombatManeuver(tripper, victim, "disarm")
  check(disarm.success, "disarm succeeds")
  check(victim:hasCondition("disarmed"), "disarmed target loses weapon")
  check(#victim.attacks == 0 and #victim.dropped_attacks > 0, "weapon moved to dropped list")
  clearRolls()
end

-- ------------------------------------------------------------------- engine flow
do
  local pc = makeFighter("Hero", true)
  local npc = makeFighter("Foe", false)
  pc.position = { x = 2, y = 2 }
  npc.position = { x = 8, y = 2 }
  local engine7 = CombatEngine.new()
  engine7:setGrid(12, 8)
  engine7:addCombatant(pc, false)
  engine7:addCombatant(npc, true)
  queueRolls(15, 15, 10, 10)
  check(engine7:startCombat(), "combat starts")
  check(engine7.is_surprise_round, "one aware and one unaware triggers a surprise round")
  check(engine7:getCurrent() ~= nil, "first turn begins")
  eq(engine7.current_round, 1, "surprise round is round 1")
  clearRolls()

  -- advance through several turns, ensuring round progression terminates correctly
  local seenTurns = 0
  for _ = 1, 6 do
    if engine7.combat_active then
      engine7:advanceTurn()
      seenTurns = seenTurns + 1
    end
  end
  check(seenTurns == 6, "advanceTurn can be called repeatedly")
  check(engine7.current_round >= 2, "rounds advance after wrapping", engine7.current_round)
end

-- --------------------------------------------------------------------------- AI
do
  Dice.seed(42)
  local engine8 = CombatEngine.new()
  engine8:setGrid(16, 10)
  local handler8 = ActionHandler.new(engine8)
  local ai = AI.new(engine8, handler8)
  local hero = db:instantiate("sir_roderick")
  local rogue = db:instantiate("shadowstep")
  local orc = db:instantiate("orc_barbarian")
  local goblin = db:instantiate("goblin_archer")
  engine8:addCombatant(hero, true)
  engine8:addCombatant(rogue, true)
  engine8:addCombatant(orc, true)
  engine8:addCombatant(goblin, true)
  engine8:startCombat()
  local turns = ai:autoResolve(200)
  check(turns > 0, "AI resolves at least one turn")
  check(engine8.ended or not engine8.combat_active or turns >= 200,
    "AI battle reaches a conclusion")
  check(engine8.log:size() > 10, "AI battle writes a combat log")
  io.write(string.format("Auto battle: %d turns, winner=%s, log entries=%d\n",
    turns, tostring(engine8.winner), engine8.log:size()))
end

-- ------------------------------------------------------------------- JSON roundtrip
do
  local value = { name = "Test", list = { 1, 2, 3 }, nested = { flag = true } }
  local text = json.encode(value)
  local decoded = json.decode(text)
  eq(decoded.name, "Test", "JSON roundtrip name")
  eq(#decoded.list, 3, "JSON roundtrip list length")
  eq(decoded.nested.flag, true, "JSON roundtrip nested boolean")
end

io.write(string.format("\n%d passed, %d failed\n", passed, failed))
if failed > 0 then
  os.exit(1)
end
