local dice = {}

local customRoller = nil

local function baseRandom(n)
  if love and love.math and love.math.random then
    return love.math.random(n)
  end
  return math.random(n)
end

function dice.setRoller(fn)
  customRoller = fn
end

function dice.clearRoller()
  customRoller = nil
end

function dice.seed(n)
  if love and love.math and love.math.setRandomSeed then
    love.math.setRandomSeed(n)
  else
    math.randomseed(n)
  end
end

function dice.roll(sides)
  if customRoller then return customRoller(sides) end
  return baseRandom(sides)
end

function dice.d20()
  return dice.roll(20)
end

function dice.rollRange(a, b)
  local n = b - a + 1
  return a + dice.roll(n) - 1
end

-- Parses standard dice notation such as "2d6+3", "1d8", "1d12 - 1".
function dice.parse(notation)
  local text = tostring(notation or ""):gsub("%s+", ""):lower()
  if text == "" then return nil end
  if not text:find("d") then
    local num = tonumber(text)
    if num then
      return { count = 0, sides = 0, bonus = num, valid = true }
    end
    return nil
  end
  local count, sides, bonus = text:match("^(%d*)d(%d+)([%+%-]%d+)$")
  if not count then
    count, sides = text:match("^(%d*)d(%d+)$")
    bonus = "0"
  end
  if not count then return nil end
  count = tonumber(count) or 1
  sides = tonumber(sides)
  bonus = tonumber(bonus) or 0
  if count < 0 or sides <= 0 then return nil end
  return { count = count, sides = sides, bonus = bonus, valid = true, text = text }
end

function dice.rollNotation(notation)
  local parsed = dice.parse(notation)
  if not parsed then
    return { total = 1, rolls = {}, bonus = 0, valid = false }
  end
  local rolls = {}
  local total = parsed.bonus
  for i = 1, parsed.count do
    local r = dice.roll(parsed.sides)
    rolls[i] = r
    total = total + r
  end
  return {
    total = total,
    rolls = rolls,
    bonus = parsed.bonus,
    count = parsed.count,
    sides = parsed.sides,
    valid = parsed.valid,
  }
end

function dice.formatRolls(result)
  if not result or not result.rolls or #result.rolls == 0 then
    return tostring(result and result.bonus or 0)
  end
  local parts = {}
  for _, r in ipairs(result.rolls) do parts[#parts + 1] = tostring(r) end
  local text = table.concat(parts, " + ")
  if result.bonus and result.bonus ~= 0 then
    text = text .. (result.bonus > 0 and " + " or " - ") .. math.abs(result.bonus)
  end
  return text
end

return dice
