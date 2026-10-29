local SavingThrows = {}
SavingThrows.__index = SavingThrows

function SavingThrows.new(opts)
  opts = opts or {}
  local self = setmetatable({}, SavingThrows)
  self.fortitude_base = tonumber(opts.fortitude_base) or 0
  self.reflex_base = tonumber(opts.reflex_base) or 0
  self.will_base = tonumber(opts.will_base) or 0
  return self
end

-- Returns the total bonus for a save; the caller supplies ability modifiers
-- and condition penalties so this module stays free of combatant rules.
function SavingThrows:base(save_type)
  if save_type == "fortitude" then return self.fortitude_base end
  if save_type == "reflex" then return self.reflex_base end
  if save_type == "will" then return self.will_base end
  return 0
end

function SavingThrows:to_dict()
  return {
    fortitude_base = self.fortitude_base,
    reflex_base = self.reflex_base,
    will_base = self.will_base,
  }
end

function SavingThrows.from_dict(data)
  return SavingThrows.new(data)
end

return SavingThrows
