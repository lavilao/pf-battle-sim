local constants = {}

constants.VERSION = "1.0.0"

constants.DamageType = {
  SLASHING = "slashing",
  PIERCING = "piercing",
  BLUDGEONING = "bludgeoning",
  FIRE = "fire",
  COLD = "cold",
  ACID = "acid",
  ELECTRICITY = "electricity",
  SONIC = "sonic",
  FORCE = "force",
}

constants.DamageTypes = {
  "slashing", "piercing", "bludgeoning", "fire", "cold",
  "acid", "electricity", "sonic", "force",
}

constants.PhysicalDamage = {
  slashing = true,
  piercing = true,
  bludgeoning = true,
}

constants.AttackType = {
  MELEE = "melee",
  RANGED = "ranged",
  NATURAL = "natural",
}

constants.AttackTypes = { "melee", "ranged", "natural" }

constants.ActionType = {
  STANDARD = "standard",
  MOVE = "move",
  FULL_ROUND = "full_round",
  SWIFT = "swift",
  FREE = "free",
}

constants.Sizes = {
  "Fine", "Diminutive", "Tiny", "Small", "Medium",
  "Large", "Huge", "Gargantuan", "Colossal",
}

-- space = squares occupied (1 square = 5 ft); reach = natural reach in feet
constants.SizeData = {
  Fine =       { attackMod =  8, cmbMod = -8, space = 1, reach = 0 },
  Diminutive = { attackMod =  4, cmbMod = -4, space = 1, reach = 0 },
  Tiny =       { attackMod =  2, cmbMod = -2, space = 1, reach = 5 },
  Small =      { attackMod =  1, cmbMod = -1, space = 1, reach = 5 },
  Medium =     { attackMod =  0, cmbMod =  0, space = 1, reach = 5 },
  Large =      { attackMod = -1, cmbMod =  1, space = 2, reach = 10 },
  Huge =       { attackMod = -2, cmbMod =  2, space = 3, reach = 15 },
  Gargantuan = { attackMod = -4, cmbMod =  4, space = 4, reach = 20 },
  Colossal =   { attackMod = -8, cmbMod =  8, space = 6, reach = 30 },
}

constants.Conditions = {
  blinded = {
    label = "Blinded",
    help = "-2 AC, loses Dex to AC, 50% miss chance on attacks.",
  },
  confused = {
    label = "Confused",
    help = "Acts erratically; treated as unable to act in this simulator.",
  },
  cowering = {
    label = "Cowering",
    help = "-2 AC, loses Dex to AC, cannot act.",
  },
  dazed = {
    label = "Dazed",
    help = "Unable to act for the duration.",
  },
  dazzled = {
    label = "Dazzled",
    help = "-1 on attack rolls.",
  },
  dead = {
    label = "Dead",
    help = "Slain. Cannot act or be targeted by healing.",
  },
  deafened = {
    label = "Deafened",
    help = "-4 on initiative and Perception checks.",
  },
  disabled = {
    label = "Disabled",
    help = "At 0 HP. May take only a single move or standard action; a standard action deals 1 damage.",
  },
  dying = {
    label = "Dying",
    help = "Below 0 HP. Unconscious and losing blood; must stabilize.",
  },
  energy_drained = {
    label = "Energy Drained",
    help = "Negative levels (not simulated in depth).",
  },
  entangled = {
    label = "Entangled",
    help = "-2 on attack rolls and -4 Dexterity.",
  },
  exhausted = {
    label = "Exhausted",
    help = "-6 Strength and Dexterity.",
  },
  fatigued = {
    label = "Fatigued",
    help = "-2 Strength and Dexterity.",
  },
  ["flat-footed"] = {
    label = "Flat-Footed",
    help = "Has not acted yet; loses Dex and dodge bonuses to AC and cannot make Attacks of Opportunity.",
  },
  frightened = {
    label = "Frightened",
    help = "-2 on attack rolls, saves, and skill checks.",
  },
  grappled = {
    label = "Grappled",
    help = "-2 on attack rolls; loses Dex to AC (not fully simulated).",
  },
  helpless = {
    label = "Helpless",
    help = "Cannot act; -4 AC and loses Dex to AC.",
  },
  nauseated = {
    label = "Nauseated",
    help = "May take only a single move action per turn.",
  },
  paralyzed = {
    label = "Paralyzed",
    help = "Cannot act; loses Dex to AC.",
  },
  petrified = {
    label = "Petrified",
    help = "Turned to stone; effectively defeated.",
  },
  pinned = {
    label = "Pinned",
    help = "Cannot act; -4 AC and loses Dex to AC.",
  },
  prone = {
    label = "Prone",
    help = "-4 on melee attacks; -4 AC against melee, +4 AC against ranged. Standing up provokes.",
  },
  shaken = {
    label = "Shaken",
    help = "-2 on attack rolls, saves, and skill checks.",
  },
  sickened = {
    label = "Sickened",
    help = "-2 on attack rolls, damage rolls, saves, and skill checks.",
  },
  stable = {
    label = "Stable",
    help = "Dying but no longer losing hit points.",
  },
  staggered = {
    label = "Staggered",
    help = "May take only a single move or standard action.",
  },
  stunned = {
    label = "Stunned",
    help = "Cannot act; -2 AC and loses Dex to AC.",
  },
  unconscious = {
    label = "Unconscious",
    help = "Cannot act; loses Dex to AC.",
  },
  disarmed = {
    label = "Disarmed",
    help = "Weapon has been knocked away. Recover it with a move action.",
  },
  ["weapon-damaged"] = {
    label = "Weapon Damaged",
    help = "A weapon has taken a sunder hit and suffers -2 on attacks and damage.",
  },
  charge = {
    label = "Charging",
    help = "-2 AC until next turn.",
  },
}

-- stable iteration order for UI lists
constants.ConditionOrder = {
  "blinded", "cowering", "dazed", "dazzled", "dead", "disabled", "dying",
  "entangled", "exhausted", "fatigued", "flat-footed", "frightened",
  "grappled", "helpless", "nauseated", "paralyzed", "petrified", "pinned",
  "prone", "shaken", "sickened", "stable", "staggered", "stunned",
  "unconscious", "disarmed", "weapon-damaged", "charge", "confused",
  "deafened", "energy_drained",
}

-- Conditions that make a creature unable to take actions.
constants.UnableConditions = {
  confused = true,
  cowering = true,
  dazed = true,
  dying = true,
  helpless = true,
  paralyzed = true,
  petrified = true,
  pinned = true,
  stunned = true,
  unconscious = true,
}

-- Conditions that cause a creature to lose its Dexterity bonus to AC.
constants.LoseDexConditions = {
  blinded = true,
  cowering = true,
  helpless = true,
  paralyzed = true,
  pinned = true,
  stunned = true,
  unconscious = true,
  grappled = true,
}

constants.StatusColors = {
  ok = { 0.42, 0.72, 0.45 },
  disabled = { 0.90, 0.72, 0.30 },
  dying = { 0.90, 0.35, 0.30 },
  stable = { 0.60, 0.62, 0.68 },
  dead = { 0.55, 0.20, 0.20 },
  unconscious = { 0.55, 0.55, 0.65 },
}

function constants.sizeData(size)
  return constants.SizeData[size] or constants.SizeData.Medium
end

return constants
