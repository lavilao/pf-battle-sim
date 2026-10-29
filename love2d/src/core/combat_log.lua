local CombatLog = {}
CombatLog.__index = CombatLog

function CombatLog.new()
  local self = setmetatable({}, CombatLog)
  self.entries = {}
  return self
end

function CombatLog:add(text, kind)
  local entry = {
    text = tostring(text),
    kind = kind or "info",
    time = os.clock(),
  }
  self.entries[#self.entries + 1] = entry
  return entry
end

function CombatLog:header(text)
  return self:add(text, "header")
end

function CombatLog:clear()
  self.entries = {}
end

function CombatLog:get_text()
  local lines = {}
  for _, e in ipairs(self.entries) do
    lines[#lines + 1] = e.text
  end
  return table.concat(lines, "\n")
end

function CombatLog:size()
  return #self.entries
end

return CombatLog
