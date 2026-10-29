local json = {}

local escapes = {
  ['"'] = '\\"',
  ['\\'] = '\\\\',
  ['\b'] = '\\b',
  ['\f'] = '\\f',
  ['\n'] = '\\n',
  ['\r'] = '\\r',
  ['\t'] = '\\t',
}

local function escapeChar(c)
  return escapes[c] or string.format("\\u%04x", string.byte(c))
end

local function escapeString(s)
  return '"' .. s:gsub('[%z\1-\31\\"]', escapeChar) .. '"'
end

local function isArray(t)
  local count = 0
  local max = 0
  for k in pairs(t) do
    if type(k) ~= "number" or k < 1 or k % 1 ~= 0 then
      return false
    end
    count = count + 1
    if k > max then max = k end
  end
  return max == count
end

local function encodeNumber(n)
  if n ~= n then return "null" end
  if n == math.huge then return "1e999" end
  if n == -math.huge then return "-1e999" end
  if n % 1 == 0 and math.abs(n) < 1e15 then
    return string.format("%d", n)
  end
  return string.format("%.14g", n)
end

local function encodeValue(v, out, indent, level)
  local tv = type(v)
  if v == nil then
    out[#out + 1] = "null"
  elseif tv == "boolean" then
    out[#out + 1] = v and "true" or "false"
  elseif tv == "number" then
    out[#out + 1] = encodeNumber(v)
  elseif tv == "string" then
    out[#out + 1] = escapeString(v)
  elseif tv == "table" then
    local array = isArray(v)
    local newline, pad, padEnd = "", "", ""
    if indent then
      newline = "\n"
      pad = string.rep("  ", level + 1)
      padEnd = string.rep("  ", level)
    end
    if array then
      if #v == 0 then
        out[#out + 1] = "[]"
        return
      end
      out[#out + 1] = "["
      for i = 1, #v do
        out[#out + 1] = newline .. pad
        encodeValue(v[i], out, indent, level + 1)
        if i < #v then out[#out + 1] = "," end
      end
      out[#out + 1] = newline .. padEnd .. "]"
    else
      local keys = {}
      for k in pairs(v) do
        if type(k) == "string" and v[k] ~= nil then keys[#keys + 1] = k end
      end
      table.sort(keys)
      if #keys == 0 then
        out[#out + 1] = "{}"
        return
      end
      out[#out + 1] = "{"
      for i, k in ipairs(keys) do
        out[#out + 1] = newline .. pad .. escapeString(k) .. (indent and ": " or ":")
        encodeValue(v[k], out, indent, level + 1)
        if i < #keys then out[#out + 1] = "," end
      end
      out[#out + 1] = newline .. padEnd .. "}"
    end
  else
    error("Cannot encode value of type " .. tv)
  end
end

function json.encode(value, pretty)
  local out = {}
  encodeValue(value, out, pretty == true, 0)
  return table.concat(out)
end

local function utf8Char(cp)
  if cp < 0x80 then
    return string.char(cp)
  elseif cp < 0x800 then
    return string.char(0xC0 + math.floor(cp / 0x40), 0x80 + cp % 0x40)
  elseif cp < 0x10000 then
    return string.char(
      0xE0 + math.floor(cp / 0x1000),
      0x80 + math.floor(cp / 0x40) % 0x40,
      0x80 + cp % 0x40
    )
  end
  return string.char(
    0xF0 + math.floor(cp / 0x40000),
    0x80 + math.floor(cp / 0x1000) % 0x40,
    0x80 + math.floor(cp / 0x40) % 0x40,
    0x80 + cp % 0x40
  )
end

function json.decode(text)
  if type(text) ~= "string" then
    error("json.decode expects a string")
  end
  local pos = 1
  local len = #text

  local function skipWhitespace()
    while pos <= len do
      local c = text:sub(pos, pos)
      if c == " " or c == "\t" or c == "\n" or c == "\r" then
        pos = pos + 1
      else
        break
      end
    end
  end

  local parseValue

  local function parseString()
    if text:sub(pos, pos) ~= '"' then error("Expected string at " .. pos) end
    pos = pos + 1
    local chunks = {}
    while pos <= len do
      local c = text:sub(pos, pos)
      if c == '"' then
        pos = pos + 1
        return table.concat(chunks)
      elseif c == "\\" then
        pos = pos + 1
        local esc = text:sub(pos, pos)
        if esc == '"' or esc == "\\" or esc == "/" then
          chunks[#chunks + 1] = esc
          pos = pos + 1
        elseif esc == "b" then
          chunks[#chunks + 1] = "\b"; pos = pos + 1
        elseif esc == "f" then
          chunks[#chunks + 1] = "\f"; pos = pos + 1
        elseif esc == "n" then
          chunks[#chunks + 1] = "\n"; pos = pos + 1
        elseif esc == "r" then
          chunks[#chunks + 1] = "\r"; pos = pos + 1
        elseif esc == "t" then
          chunks[#chunks + 1] = "\t"; pos = pos + 1
        elseif esc == "u" then
          local hex = text:sub(pos + 1, pos + 4)
          if not hex:match("^%x%x%x%x$") then error("Bad unicode escape at " .. pos) end
          chunks[#chunks + 1] = utf8Char(tonumber(hex, 16))
          pos = pos + 5
        else
          error("Bad escape at " .. pos)
        end
      else
        local start = pos
        while pos <= len do
          local ch = text:sub(pos, pos)
          if ch == '"' or ch == "\\" or string.byte(ch) < 32 then break end
          pos = pos + 1
        end
        chunks[#chunks + 1] = text:sub(start, pos - 1)
      end
    end
    error("Unterminated string")
  end

  local function parseNumber()
    local start = pos
    if text:sub(pos, pos) == "-" then pos = pos + 1 end
    while pos <= len and text:sub(pos, pos):match("%d") do pos = pos + 1 end
    if text:sub(pos, pos) == "." then
      pos = pos + 1
      while pos <= len and text:sub(pos, pos):match("%d") do pos = pos + 1 end
    end
    local c = text:sub(pos, pos)
    if c == "e" or c == "E" then
      pos = pos + 1
      c = text:sub(pos, pos)
      if c == "+" or c == "-" then pos = pos + 1 end
      while pos <= len and text:sub(pos, pos):match("%d") do pos = pos + 1 end
    end
    local num = tonumber(text:sub(start, pos - 1))
    if not num then error("Invalid number at " .. start) end
    return num
  end

  local function parseObject()
    pos = pos + 1
    local obj = {}
    skipWhitespace()
    if text:sub(pos, pos) == "}" then
      pos = pos + 1
      return obj
    end
    while true do
      skipWhitespace()
      local key = parseString()
      skipWhitespace()
      if text:sub(pos, pos) ~= ":" then error("Expected ':' at " .. pos) end
      pos = pos + 1
      obj[key] = parseValue()
      skipWhitespace()
      local c = text:sub(pos, pos)
      if c == "}" then
        pos = pos + 1
        return obj
      elseif c == "," then
        pos = pos + 1
      else
        error("Expected ',' or '}' at " .. pos)
      end
    end
  end

  local function parseArray()
    pos = pos + 1
    local arr = {}
    skipWhitespace()
    if text:sub(pos, pos) == "]" then
      pos = pos + 1
      return arr
    end
    while true do
      arr[#arr + 1] = parseValue()
      skipWhitespace()
      local c = text:sub(pos, pos)
      if c == "]" then
        pos = pos + 1
        return arr
      elseif c == "," then
        pos = pos + 1
      else
        error("Expected ',' or ']' at " .. pos)
      end
    end
  end

  parseValue = function()
    skipWhitespace()
    local c = text:sub(pos, pos)
    if c == '"' then return parseString()
    elseif c == "{" then return parseObject()
    elseif c == "[" then return parseArray()
    elseif c == "-" or c:match("%d") then return parseNumber()
    elseif text:sub(pos, pos + 3) == "true" then pos = pos + 4; return true
    elseif text:sub(pos, pos + 4) == "false" then pos = pos + 5; return false
    elseif text:sub(pos, pos + 3) == "null" then pos = pos + 4; return nil
    end
    error("Unexpected character '" .. c .. "' at " .. pos)
  end

  local value = parseValue()
  skipWhitespace()
  if pos <= len then error("Trailing content at " .. pos) end
  return value
end

return json
