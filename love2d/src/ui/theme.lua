-- Dark fantasy tabletop theme and shared drawing helpers.
-- Call theme.init() once in love.load. All coordinates are virtual 1440x900
-- pixels; main.lua should set theme.mouseX / theme.mouseY before drawing.
local theme = {}

theme.width = 1440
theme.height = 900
theme.mouseX = 0
theme.mouseY = 0

theme.colors = {
  bg =          { 0.055, 0.060, 0.075 },
  panel =       { 0.095, 0.105, 0.130 },
  panelAlt =    { 0.125, 0.138, 0.168 },
  panelLight =  { 0.170, 0.185, 0.220 },
  border =      { 0.270, 0.295, 0.360 },
  borderBright = { 0.420, 0.460, 0.550 },
  text =        { 0.890, 0.850, 0.750 },
  textMuted =   { 0.550, 0.580, 0.630 },
  gold =        { 0.830, 0.680, 0.340 },
  goldDark =    { 0.530, 0.410, 0.190 },
  red =         { 0.780, 0.290, 0.270 },
  green =       { 0.410, 0.670, 0.420 },
  blue =        { 0.380, 0.550, 0.790 },
  orange =      { 0.860, 0.550, 0.270 },
  purple =      { 0.640, 0.460, 0.780 },
  hp =          { 0.720, 0.200, 0.200 },
  hpBack =      { 0.200, 0.105, 0.115 },
  white =       { 1.000, 1.000, 1.000 },
  black =       { 0.000, 0.000, 0.000 },
  overlay =     { 0.000, 0.000, 0.000, 0.660 },
}

local FONT_SANS = "assets/fonts/DejaVuSans.ttf"
local FONT_SANS_BOLD = "assets/fonts/DejaVuSans-Bold.ttf"
local FONT_MONO = "assets/fonts/DejaVuSansMono.ttf"
local FONT_SERIF_BOLD = "assets/fonts/DejaVuSerif-Bold.ttf"

theme.fonts = {}
local fontCache = {}

local function loadFont(path, size)
  return love.graphics.newFont(path, size)
end

function theme.init()
  if theme.fonts.body then return end
  local body = loadFont(FONT_SANS, 16)
  theme.fonts = {
    title = loadFont(FONT_SERIF_BOLD, 42),
    h1 = loadFont(FONT_SERIF_BOLD, 30),
    h2 = loadFont(FONT_SANS_BOLD, 22),
    h3 = loadFont(FONT_SANS_BOLD, 18),
    body = body,
    bodyBold = loadFont(FONT_SANS_BOLD, 16),
    small = loadFont(FONT_SANS, 14),
    smallBold = loadFont(FONT_SANS_BOLD, 14),
    tiny = loadFont(FONT_SANS, 11),
    mono = loadFont(FONT_MONO, 14),
    monoSmall = loadFont(FONT_MONO, 12),
    -- No italic face ships with the project; reuse the body face.
    italic = body,
  }
end

local function lookupColor(value)
  if type(value) == "string" then
    return theme.colors[value]
  end
  return value
end

function theme.resolveColor(value, fallback)
  local resolved = lookupColor(value)
  if not resolved then resolved = lookupColor(fallback) end
  if type(resolved) == "table" then return resolved end
  return theme.colors.white
end

-- Name string -> theme.fonts[name]. Number -> cached body-face font at that
-- size. A Font object is passed through unchanged.
function theme.getFont(nameOrSize)
  if type(nameOrSize) == "userdata" or type(nameOrSize) == "table" then
    return nameOrSize
  end
  if not theme.fonts.body then theme.init() end
  if type(nameOrSize) == "string" then
    return theme.fonts[nameOrSize] or theme.fonts.body
  elseif type(nameOrSize) == "number" then
    local size = math.max(1, math.floor(nameOrSize))
    if not fontCache[size] then
      fontCache[size] = love.graphics.newFont(FONT_SANS, size)
    end
    return fontCache[size]
  end
  return theme.fonts.body
end

function theme.setColor(colorTable, alpha)
  local c = theme.resolveColor(colorTable, theme.colors.white)
  alpha = tonumber(alpha) or 1
  if alpha < 0 then alpha = 0 elseif alpha > 1 then alpha = 1 end
  local a = (tonumber(c[4]) or 1) * alpha
  love.graphics.setColor(c[1] or 1, c[2] or 1, c[3] or 1, a)
end

local function normalizeNewlines(text)
  return (tostring(text or ""):gsub("\r\n", "\n"):gsub("\r", "\n"))
end

local function splitLines(text)
  local lines = {}
  for line in (normalizeNewlines(text) .. "\n"):gmatch("(.-)\n") do
    lines[#lines + 1] = line
  end
  return lines
end

local function breakWord(word, font, maxWidth)
  local pieces = {}
  local current = ""
  -- Character iteration that keeps UTF-8 sequences intact.
  for ch in word:gmatch("[\1-\127\194-\244][\128-\191]*") do
    if current ~= "" and font:getWidth(current .. ch) > maxWidth then
      pieces[#pieces + 1] = current
      current = ch
    else
      current = current .. ch
    end
  end
  if current ~= "" then pieces[#pieces + 1] = current end
  if #pieces == 0 then pieces[1] = "" end
  return pieces
end

-- Word wrap that preserves explicit newlines. Words longer than maxWidth are
-- split by character so callers can rely on the returned width.
function theme.wrap(text, font, maxWidth)
  font = theme.getFont(font or "body")
  maxWidth = tonumber(maxWidth) or math.huge
  if maxWidth <= 0 then maxWidth = 1 end

  local lines = {}
  local logicalLines = splitLines(text)
  for _, logical in ipairs(logicalLines) do
    local words = {}
    for word in logical:gmatch("%S+") do
      words[#words + 1] = word
    end

    if #words == 0 then
      lines[#lines + 1] = ""
    else
      local current = ""
      for _, word in ipairs(words) do
        if current == "" then
          if font:getWidth(word) <= maxWidth then
            current = word
          else
            local pieces = breakWord(word, font, maxWidth)
            for i = 1, #pieces - 1 do
              lines[#lines + 1] = pieces[i]
            end
            current = pieces[#pieces]
          end
        else
          local candidate = current .. " " .. word
          if font:getWidth(candidate) <= maxWidth then
            current = candidate
          else
            lines[#lines + 1] = current
            if font:getWidth(word) <= maxWidth then
              current = word
            else
              local pieces = breakWord(word, font, maxWidth)
              for i = 1, #pieces - 1 do
                lines[#lines + 1] = pieces[i]
              end
              current = pieces[#pieces]
            end
          end
        end
      end
      if current ~= "" then lines[#lines + 1] = current end
    end
  end
  return lines
end

function theme.measure(text, font)
  font = theme.getFont(font or "body")
  local lines = splitLines(text)
  local width = 0
  for _, line in ipairs(lines) do
    local w = font:getWidth(line)
    if w > width then width = w end
  end
  return width, #lines * font:getHeight()
end

local function utf8SafePrefix(text, count)
  if count >= #text then return text end
  local cut = count
  while cut > 0 do
    local b = text:byte(cut)
    if b >= 128 and b <= 191 then
      cut = cut - 1
    elseif b >= 194 and b <= 244 then
      local need = 2
      if b >= 240 then
        need = 4
      elseif b >= 224 then
        need = 3
      end
      if cut + need - 1 > count then
        cut = cut - 1
      else
        break
      end
    else
      break
    end
  end
  return text:sub(1, math.max(0, cut))
end

function theme.truncateText(text, font, maxWidth)
  font = theme.getFont(font or "body")
  text = tostring(text or ""):gsub("[\r\n]+", " ")
  maxWidth = tonumber(maxWidth)
  if not maxWidth or maxWidth <= 0 then return "" end
  if font:getWidth(text) <= maxWidth then return text end

  local ellipsis = "..."
  local ellipsisWidth = font:getWidth(ellipsis)
  if ellipsisWidth > maxWidth then return "" end

  local low, high = 0, #text
  while low < high do
    local mid = math.floor((low + high + 1) / 2)
    if font:getWidth(text:sub(1, mid)) + ellipsisWidth <= maxWidth then
      low = mid
    else
      high = mid - 1
    end
  end
  return utf8SafePrefix(text, low) .. ellipsis
end

-- Draws wrapped text. If maxWidth is supplied, x is the left edge of that box
-- and align is relative to it. Without maxWidth, x is the left/center/right
-- anchor for the line. Returns the y coordinate below the drawn text.
function theme.drawText(text, x, y, font, color, align, maxWidth)
  font = theme.getFont(font or "body")
  text = tostring(text or "")
  x = tonumber(x) or 0
  y = tonumber(y) or 0

  local lines
  if maxWidth and maxWidth > 0 then
    lines = theme.wrap(text, font, maxWidth)
  else
    lines = splitLines(text)
  end

  local lineHeight = font:getHeight()
  local drawY = y
  theme.setColor(color or theme.colors.text)
  love.graphics.setFont(font)

  for _, line in ipairs(lines) do
    local lineWidth = font:getWidth(line)
    local drawX = x
    if align == "center" then
      if maxWidth and maxWidth > 0 then
        drawX = x + (maxWidth - lineWidth) / 2
      else
        drawX = x - lineWidth / 2
      end
    elseif align == "right" then
      if maxWidth and maxWidth > 0 then
        drawX = x + maxWidth - lineWidth
      else
        drawX = x - lineWidth
      end
    end
    love.graphics.print(line, math.floor(drawX + 0.5), math.floor(drawY + 0.5))
    drawY = drawY + lineHeight
  end
  return drawY
end

-- Draws a rounded panel with an optional title bar. Returns the y coordinate
-- where content should start: below the header plus padding (or y + padding).
function theme.drawPanel(x, y, w, h, opts)
  opts = opts or {}
  x = tonumber(x) or 0
  y = tonumber(y) or 0
  w = math.max(1, tonumber(w) or 1)
  h = math.max(1, tonumber(h) or 1)

  local padding = tonumber(opts.padding) or 16
  local radius = math.max(0, math.min(tonumber(opts.radius) or 8, w / 2, h / 2))
  local fill = theme.resolveColor(opts.fill, theme.colors.panel)
  local border = theme.resolveColor(opts.border, theme.colors.border)

  if opts.shadow ~= false then
    theme.setColor(theme.colors.black, 0.30)
    love.graphics.rectangle("fill", x + 2, y + 3, w, h, radius, radius)
  end
  theme.setColor(fill)
  love.graphics.rectangle("fill", x, y, w, h, radius, radius)

  local contentY = y + padding
  if opts.title and opts.title ~= "" then
    local titleFont = theme.getFont(opts.titleFont or "h3")
    local headerHeight = math.max(tonumber(opts.headerHeight) or 40,
      titleFont:getHeight() + 14)
    headerHeight = math.min(headerHeight, h)

    local headerColor = theme.resolveColor(opts.headerColor, theme.colors.panelAlt)
    local inset = 1
    local headerRadius = math.max(0, radius - inset)
    theme.setColor(headerColor)
    love.graphics.rectangle("fill", x + inset, y + inset,
      w - inset * 2, headerHeight, headerRadius, headerRadius)
    -- Square off the bottom of the header while keeping the top corners round.
    love.graphics.rectangle("fill", x + inset, y + headerHeight * 0.5,
      w - inset * 2, headerHeight * 0.5)

    theme.setColor(theme.colors.border, 0.9)
    love.graphics.setLineWidth(1)
    love.graphics.line(x + inset, y + headerHeight + 0.5,
      x + w - inset, y + headerHeight + 0.5)

    local markHeight = math.max(0, math.min(titleFont:getHeight(), headerHeight - 16))
    theme.setColor(theme.colors.goldDark)
    love.graphics.rectangle("fill", x + padding, y + (headerHeight - markHeight) / 2,
      3, markHeight, 1, 1)

    local titleX = x + padding + 12
    local titleWidth = math.max(1, w - (titleX - x) - padding)
    local title = theme.truncateText(tostring(opts.title), titleFont, titleWidth)
    theme.drawText(title, titleX, y + (headerHeight - titleFont:getHeight()) / 2,
      titleFont, theme.colors.gold)

    contentY = y + headerHeight + padding
  end

  theme.setColor(border)
  love.graphics.setLineWidth(1)
  love.graphics.rectangle("line", x + 0.5, y + 0.5, w - 1, h - 1,
    math.max(0, radius - 0.5), math.max(0, radius - 0.5))
  return contentY
end

function theme.drawBar(x, y, w, h, fraction, color, opts)
  opts = opts or {}
  x = tonumber(x) or 0
  y = tonumber(y) or 0
  w = math.max(1, tonumber(w) or 1)
  h = math.max(1, tonumber(h) or 1)

  local fractionValue = tonumber(fraction) or 0
  if fractionValue ~= fractionValue then fractionValue = 0 end
  fractionValue = math.max(0, math.min(1, fractionValue))

  local radius = tonumber(opts.radius) or math.min(3, h / 2)
  radius = math.max(0, math.min(radius, w / 2, h / 2))
  local back = theme.resolveColor(opts.back, theme.colors.hpBack)

  theme.setColor(back)
  love.graphics.rectangle("fill", x, y, w, h, radius, radius)

  if fractionValue > 0 then
    local fillWidth = math.max(1, w * fractionValue)
    local fillRadius = math.min(radius, fillWidth / 2)
    theme.setColor(color or theme.colors.hp)
    love.graphics.rectangle("fill", x, y, fillWidth, h, fillRadius, fillRadius)
  end

  if opts.border then
    theme.setColor(opts.border)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", x + 0.5, y + 0.5, w - 1, h - 1,
      math.max(0, radius - 0.5), math.max(0, radius - 0.5))
  end
end

function theme.drawPill(x, y, w, h, text, color, font, opts)
  opts = opts or {}
  font = theme.getFont(font or "tiny")
  text = tostring(text or "")
  x = tonumber(x) or 0
  y = tonumber(y) or 0
  h = math.max(1, tonumber(h) or (font:getHeight() + 6))
  if not w then w = font:getWidth(text) + 12 end
  w = math.max(1, tonumber(w) or 1)

  local base = theme.resolveColor(color, theme.colors.gold)
  local radius = tonumber(opts.radius) or h / 2
  radius = math.max(0, math.min(radius, w / 2, h / 2))

  local fill = theme.resolveColor(opts.fill, base)
  theme.setColor(fill, opts.fill and 1 or 0.16)
  love.graphics.rectangle("fill", x, y, w, h, radius, radius)

  local border = theme.resolveColor(opts.border, base)
  theme.setColor(border, 0.65)
  love.graphics.setLineWidth(1)
  love.graphics.rectangle("line", x + 0.5, y + 0.5, w - 1, h - 1,
    math.max(0, radius - 0.5), math.max(0, radius - 0.5))

  local pad = math.max(2, math.min(6, w / 4))
  local maxTextWidth = math.max(1, w - pad * 2)
  local label = theme.truncateText(text, font, maxTextWidth)
  local textColor = theme.resolveColor(opts.textColor, base)
  theme.drawText(label, x + pad, y + (h - font:getHeight()) / 2,
    font, textColor, "center", maxTextWidth)
end

function theme.drawTooltip(text, x, y, maxWidth)
  text = tostring(text or "")
  if text == "" then return end

  local font = theme.getFont("small")
  local screenW = theme.width or 1440
  local screenH = theme.height or 900
  local maxW = math.max(80, math.min(tonumber(maxWidth) or 320, screenW - 32))
  local padding = 10
  local lines = theme.wrap(text, font, maxW - padding * 2)

  local contentWidth = 0
  for _, line in ipairs(lines) do
    local lineWidth = font:getWidth(line)
    if lineWidth > contentWidth then contentWidth = lineWidth end
  end

  local w = math.ceil(contentWidth + padding * 2)
  local lineHeight = font:getHeight()
  local h = math.ceil(#lines * lineHeight + padding * 2)
  local mouseX = x or theme.mouseX or 0
  local mouseY = y or theme.mouseY or 0

  local tooltipX = math.min(mouseX + 16, screenW - w - 8)
  local tooltipY = math.min(mouseY + 20, screenH - h - 8)
  tooltipX = math.max(8, tooltipX)
  tooltipY = math.max(8, tooltipY)

  theme.setColor(theme.colors.black, 0.45)
  love.graphics.rectangle("fill", tooltipX + 2, tooltipY + 3, w, h, 6, 6)
  theme.setColor(theme.colors.panelAlt)
  love.graphics.rectangle("fill", tooltipX, tooltipY, w, h, 6, 6)
  theme.setColor(theme.colors.borderBright, 0.9)
  love.graphics.setLineWidth(1)
  love.graphics.rectangle("line", tooltipX + 0.5, tooltipY + 0.5,
    w - 1, h - 1, 5.5, 5.5)
  theme.setColor(theme.colors.gold, 0.8)
  love.graphics.rectangle("fill", tooltipX + 1, tooltipY + 6, 2,
    math.max(0, h - 12), 1, 1)

  theme.setColor(theme.colors.text)
  love.graphics.setFont(font)
  for i, line in ipairs(lines) do
    love.graphics.print(line, math.floor(tooltipX + padding),
      math.floor(tooltipY + padding + (i - 1) * lineHeight))
  end
end

return theme
