-- Shared UI widgets for the dark fantasy tabletop screens.
-- Setup: call theme.init() once in love.load.
-- Each frame: ui.beginFrame(); draw widgets in order; ui.drawDeferred() last.
-- Forward mousepressed/mousereleased/keypressed/textinput to widgets; widgets
-- read theme.mouseX/theme.mouseY during :draw() for hover. Handled mouse
-- presses return true.
local theme = require("src.ui.theme")

local ui = {}
ui._pendingTooltips = {}
ui._focusedInput = nil

function ui.beginFrame()
  -- Clears tooltips queued by widget :draw() calls during the previous frame.
  ui._pendingTooltips = {}
end

function ui.queueTooltip(text, x, y)
  if text == nil or text == "" then return end
  if not ui._pendingTooltips then ui._pendingTooltips = {} end
  ui._pendingTooltips[#ui._pendingTooltips + 1] = {
    text = tostring(text),
    x = x or theme.mouseX or 0,
    y = y or theme.mouseY or 0,
  }
end

function ui.drawDeferred()
  local pending = ui._pendingTooltips
  if not pending then return end
  for i = 1, #pending do
    local item = pending[i]
    theme.drawTooltip(item.text, item.x, item.y)
  end
  ui._pendingTooltips = {}
end

local function pointInRect(px, py, x, y, w, h)
  return px >= x and py >= y and px < x + w and py < y + h
end

local function queueWidgetTooltip(widget, mouseX, mouseY)
  if widget.tooltip and widget.tooltip ~= "" then
    ui.queueTooltip(widget.tooltip, mouseX, mouseY)
  end
end

local function pushScissor(x, y, w, h)
  local sx, sy, sw, sh = love.graphics.getScissor()
  love.graphics.setScissor(x, y, w, h)
  return sx, sy, sw, sh
end

local function popScissor(sx, sy, sw, sh)
  if sx then
    love.graphics.setScissor(sx, sy, sw, sh)
  else
    love.graphics.setScissor()
  end
end

local BUTTON_STYLES = {
  default = {
    fill = theme.colors.panelLight,
    hoverFill = { 0.205, 0.225, 0.275 },
    pressedFill = theme.colors.panel,
    border = theme.colors.border,
    hoverBorder = theme.colors.borderBright,
    text = theme.colors.text,
    icon = theme.colors.gold,
  },
  primary = {
    fill = { 0.700, 0.560, 0.260 },
    hoverFill = { 0.840, 0.690, 0.360 },
    pressedFill = { 0.580, 0.450, 0.200 },
    border = { 0.900, 0.760, 0.440 },
    hoverBorder = { 0.980, 0.860, 0.550 },
    text = { 0.080, 0.070, 0.040 },
    icon = { 0.220, 0.170, 0.070 },
  },
  danger = {
    fill = { 0.340, 0.130, 0.140 },
    hoverFill = { 0.460, 0.170, 0.170 },
    pressedFill = { 0.270, 0.095, 0.105 },
    border = { 0.550, 0.220, 0.220 },
    hoverBorder = theme.colors.red,
    text = { 0.960, 0.880, 0.840 },
    icon = theme.colors.gold,
  },
  ghost = {
    fill = { 0, 0, 0, 0 },
    hoverFill = { 0.170, 0.180, 0.220, 0.55 },
    pressedFill = { 0.120, 0.130, 0.160, 0.65 },
    border = { 0, 0, 0, 0 },
    hoverBorder = theme.colors.border,
    text = theme.colors.textMuted,
    hoverText = theme.colors.text,
    icon = theme.colors.gold,
    ghost = true,
  },
}

local Button = {}
Button.__index = Button
ui.Button = Button

function Button.new(opts)
  opts = opts or {}
  local self = setmetatable({}, Button)
  self.x = opts.x or 0
  self.y = opts.y or 0
  self.w = opts.w or 120
  self.h = opts.h or 36
  self.label = opts.label or ""
  self.onClick = opts.onClick
  self.enabled = opts.enabled ~= false
  self.tooltip = opts.tooltip
  self.hotkey = opts.hotkey
  self.style = opts.style or "default"
  self.font = opts.font
  self.icon = opts.icon
  self.compact = opts.compact == true
  self.hover = false
  self._pressed = false
  return self
end

function Button:contains(x, y)
  return pointInRect(x, y, self.x, self.y, self.w, self.h)
end

function Button:draw()
  local colors = theme.colors
  local font = theme.getFont(self.font or "bodyBold")
  local mouseX, mouseY = theme.mouseX or 0, theme.mouseY or 0
  local inside = self:contains(mouseX, mouseY)
  self.hover = inside and self.enabled
  if self._pressed and not love.mouse.isDown(1) then
    self._pressed = false
  end
  if inside then queueWidgetTooltip(self, mouseX, mouseY) end

  local style = BUTTON_STYLES[self.style] or BUTTON_STYLES.default
  local disabled = not self.enabled
  local pressed = self._pressed and self.enabled and inside
  local radius = math.max(0, math.min(5, self.w / 2, self.h / 2))

  local fill
  local border
  local textColor
  if disabled then
    fill = style.ghost and nil or colors.panel
    border = style.ghost and nil or colors.border
    textColor = colors.textMuted
  else
    fill = pressed and style.pressedFill or (self.hover and style.hoverFill or style.fill)
    border = self.hover and style.hoverBorder or style.border
    textColor = self.hover and (style.hoverText or style.text) or style.text
  end

  if fill and not disabled and not style.ghost and not pressed then
    theme.setColor(colors.black, 0.26)
    love.graphics.rectangle("fill", self.x + 1, self.y + 2, self.w, self.h,
      radius, radius)
  end

  if fill then
    theme.setColor(fill, disabled and 0.60 or 1)
    love.graphics.rectangle("fill", self.x, self.y, self.w, self.h,
      radius, radius)
  end

  if border then
    theme.setColor(border, disabled and 0.45 or 1)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", self.x + 0.5, self.y + 0.5,
      self.w - 1, self.h - 1, math.max(0, radius - 0.5),
      math.max(0, radius - 0.5))
  end

  local padding = self.compact and 3 or 12
  local hotkeyText = self.hotkey and tostring(self.hotkey) or ""
  local hotkeyFont = theme.fonts.smallBold or font
  local hotkeyWidth = 0
  if #hotkeyText > 0 and self.w > 96 then
    hotkeyWidth = hotkeyFont:getWidth(hotkeyText) + 16
  end

  local iconText = self.icon and tostring(self.icon) or ""
  local iconWidth = 0
  if #iconText > 0 then
    iconWidth = font:getWidth(iconText) + 7
  end

  local left = self.x + padding
  local right = self.x + self.w - padding - hotkeyWidth
  local contentWidth = math.max(0, right - left)
  local labelMaxWidth = math.max(0, contentWidth - iconWidth)
  local label = theme.truncateText(tostring(self.label or ""), font, labelMaxWidth)
  local groupWidth = iconWidth + font:getWidth(label)
  local groupX = left + (contentWidth - groupWidth) / 2
  local labelX = groupX + iconWidth
  local textY = self.y + (self.h - font:getHeight()) / 2

  love.graphics.setFont(font)
  theme.setColor(textColor, disabled and 0.55 or 1)
  love.graphics.print(label, math.floor(labelX), math.floor(textY))

  if #iconText > 0 then
    theme.setColor(disabled and colors.textMuted or (style.icon or textColor),
      disabled and 0.50 or 1)
    love.graphics.setFont(font)
    love.graphics.print(iconText, math.floor(groupX), math.floor(textY))
  end

  if hotkeyWidth > 0 then
    love.graphics.setFont(hotkeyFont)
    theme.setColor(textColor, disabled and 0.40 or 0.65)
    local hotkeyX = self.x + self.w - padding - hotkeyFont:getWidth(hotkeyText)
    local hotkeyY = self.y + (self.h - hotkeyFont:getHeight()) / 2
    love.graphics.print(hotkeyText, math.floor(hotkeyX), math.floor(hotkeyY))
  end
end

function Button:mousepressed(x, y, button)
  if button ~= 1 or not self.enabled then return false end
  if not self:contains(x, y) then return false end
  self._pressed = true
  if self.onClick then self.onClick(self) end
  return true
end

function Button:mousereleased(x, y, button)
  if button == 1 then self._pressed = false end
end

function Button:setEnabled(value)
  self.enabled = value ~= false
  if not self.enabled then
    self.hover = false
    self._pressed = false
  end
  return self
end

function Button:setLabel(text)
  self.label = text or ""
  return self
end

local TextInput = {}
TextInput.__index = TextInput
ui.TextInput = TextInput

local function isValidNumeric(text)
  return text:match("^%-?%d*%.?%d*$") ~= nil
end

function TextInput.new(opts)
  opts = opts or {}
  local self = setmetatable({}, TextInput)
  self.x = opts.x or 0
  self.y = opts.y or 0
  self.w = opts.w or 220
  self.h = opts.h or 34
  self.value = opts.value ~= nil and tostring(opts.value) or ""
  self.placeholder = opts.placeholder or ""
  self.numeric = opts.numeric == true
  self.maxLength = tonumber(opts.maxLength)
  if self.maxLength then
    self.maxLength = math.max(0, math.floor(self.maxLength))
  end
  self.onChange = opts.onChange
  self.onSubmit = opts.onSubmit
  self.font = opts.font
  self.tooltip = opts.tooltip
  self.hover = false
  self._focused = false
  self._caretTimer = 0
  return self
end

function TextInput:focus()
  local previous = ui._focusedInput
  if previous and previous ~= self and previous.blur then
    previous:blur()
  end
  if not self._focused then
    self._caretTimer = 0
  end
  self._focused = true
  ui._focusedInput = self
  return self
end

function TextInput:blur()
  self._focused = false
  if ui._focusedInput == self then
    ui._focusedInput = nil
  end
  return self
end

function TextInput:focused()
  return self._focused
end

function TextInput:contains(x, y)
  return pointInRect(x, y, self.x, self.y, self.w, self.h)
end

function TextInput:mousepressed(x, y, button)
  if button ~= 1 then return false end
  if pointInRect(x, y, self.x, self.y, self.w, self.h) then
    self:focus()
    return true
  end
  if self._focused then self:blur() end
  return false
end

function TextInput:keypressed(key)
  if not self._focused then return false end

  if key == "escape" then
    self:blur()
    return true
  elseif key == "backspace" then
    if #self.value > 0 then
      self.value = self.value:sub(1, #self.value - 1)
      self._caretTimer = 0
      if self.onChange then self.onChange(self.value) end
    end
    return true
  elseif key == "return" or key == "kpenter" then
    local value = self.value
    if self.onSubmit then self.onSubmit(value) end
    self:blur()
    return true
  end
  return false
end

function TextInput:textinput(text)
  if not self._focused then return false end
  if type(text) ~= "string" or text == "" then return false end

  text = text:gsub("[%c]", "")
  if text == "" then return false end

  if self.maxLength then
    local room = self.maxLength - #self.value
    if room <= 0 then return true end
    if #text > room then text = text:sub(1, room) end
  end

  local newValue = self.value .. text
  if self.numeric and not isValidNumeric(newValue) then return false end
  if newValue == self.value then return false end

  self.value = newValue
  self._caretTimer = 0
  if self.onChange then self.onChange(self.value) end
  return true
end

function TextInput:setValue(value)
  self.value = value ~= nil and tostring(value) or ""
  self._caretTimer = 0
  return self
end

function TextInput:getValue()
  return self.value
end

function TextInput:draw()
  local colors = theme.colors
  local font = theme.getFont(self.font or "body")
  local mouseX, mouseY = theme.mouseX or 0, theme.mouseY or 0
  local inside = pointInRect(mouseX, mouseY, self.x, self.y, self.w, self.h)
  self.hover = inside
  if inside then queueWidgetTooltip(self, mouseX, mouseY) end

  if self._focused then
    local dt = love.timer and love.timer.getDelta() or 0
    self._caretTimer = (self._caretTimer or 0) + dt
  end

  local radius = math.max(0, math.min(5, self.w / 2, self.h / 2))
  if self._focused then
    theme.setColor(colors.gold, 0.16)
    love.graphics.setLineWidth(3)
    love.graphics.rectangle("line", self.x - 1.5, self.y - 1.5,
      self.w + 3, self.h + 3, radius + 2, radius + 2)
  end

  theme.setColor(colors.panelAlt)
  love.graphics.rectangle("fill", self.x, self.y, self.w, self.h,
    radius, radius)

  local borderColor = colors.border
  if self._focused then
    borderColor = colors.gold
  elseif self.hover then
    borderColor = colors.borderBright
  end
  theme.setColor(borderColor)
  love.graphics.setLineWidth(1)
  love.graphics.rectangle("line", self.x + 0.5, self.y + 0.5,
    self.w - 1, self.h - 1, math.max(0, radius - 0.5),
    math.max(0, radius - 0.5))

  local padding = 10
  local available = math.max(1, self.w - padding * 2 - 2)
  local display, textColor, offset
  if self.value ~= "" then
    local textWidth = font:getWidth(self.value)
    offset = math.max(0, textWidth - available)
    display = self.value
    textColor = colors.text
  else
    display = theme.truncateText(self.placeholder or "", font, available)
    offset = 0
    textColor = colors.textMuted
  end

  local textX = self.x + padding - offset
  local textY = self.y + (self.h - font:getHeight()) / 2
  local innerW = math.max(1, self.w - 4)
  local innerH = math.max(1, self.h - 4)
  local sx, sy, sw, sh = pushScissor(math.floor(self.x + 2),
    math.floor(self.y + 2), math.floor(innerW), math.floor(innerH))

  theme.setColor(textColor)
  love.graphics.setFont(font)
  love.graphics.print(display, math.floor(textX), math.floor(textY))

  if self._focused then
    local caretVisible = math.floor((self._caretTimer or 0) / 0.5) % 2 == 0
    if caretVisible then
      local caretX
      if self.value ~= "" then
        caretX = self.x + padding + font:getWidth(self.value) - offset + 1
      else
        caretX = self.x + padding
      end
      local caretHeight = math.max(1, self.h - 12)
      local caretY = self.y + (self.h - caretHeight) / 2
      theme.setColor(colors.gold)
      love.graphics.rectangle("fill", math.floor(caretX), math.floor(caretY),
        1.5, caretHeight)
    end
  end

  popScissor(sx, sy, sw, sh)
end

local Checkbox = {}
Checkbox.__index = Checkbox
ui.Checkbox = Checkbox

function Checkbox.new(opts)
  opts = opts or {}
  local self = setmetatable({}, Checkbox)
  self.x = opts.x or 0
  self.y = opts.y or 0
  self.size = opts.size or 20
  self.checked = opts.checked == true
  self.label = opts.label or ""
  self.onChange = opts.onChange
  self.tooltip = opts.tooltip
  self.font = opts.font
  self.maxWidth = opts.maxWidth
  self.hover = false
  return self
end

function Checkbox:_font()
  return theme.getFont(self.font or "body")
end

function Checkbox:_labelText()
  local label = tostring(self.label or "")
  if self.maxWidth then
    label = theme.truncateText(label, self:_font(), self.maxWidth)
  end
  return label
end

function Checkbox:contains(x, y)
  local font = self:_font()
  local label = self:_labelText()
  local labelWidth = 0
  if label ~= "" then
    labelWidth = 8 + font:getWidth(label)
  end
  local height = math.max(self.size, font:getHeight())
  return pointInRect(x, y, self.x, self.y, self.size + labelWidth, height)
end

function Checkbox:setChecked(value)
  self.checked = value and true or false
  return self
end

function Checkbox:getChecked()
  return self.checked
end

function Checkbox:mousepressed(x, y, button)
  if button ~= 1 then return false end
  if not self:contains(x, y) then return false end
  self.checked = not self.checked
  if self.onChange then self.onChange(self.checked) end
  return true
end

function Checkbox:draw()
  local colors = theme.colors
  local font = self:_font()
  local mouseX, mouseY = theme.mouseX or 0, theme.mouseY or 0
  local inside = self:contains(mouseX, mouseY)
  self.hover = inside
  if inside then queueWidgetTooltip(self, mouseX, mouseY) end

  local label = self:_labelText()
  local lineHeight = math.max(self.size, font:getHeight())
  local boxY = self.y + (lineHeight - self.size) / 2
  local radius = math.max(0, math.min(4, self.size / 2))

  local fillColor
  local borderColor
  if self.checked then
    fillColor = self.hover and { 0.920, 0.790, 0.470 } or colors.gold
    borderColor = { 0.960, 0.870, 0.560 }
  else
    fillColor = self.hover and colors.panelLight or colors.panelAlt
    borderColor = self.hover and colors.borderBright or colors.border
  end

  theme.setColor(fillColor)
  love.graphics.rectangle("fill", self.x, boxY, self.size, self.size,
    radius, radius)
  theme.setColor(borderColor)
  love.graphics.setLineWidth(1)
  love.graphics.rectangle("line", self.x + 0.5, boxY + 0.5,
    self.size - 1, self.size - 1, math.max(0, radius - 0.5),
    math.max(0, radius - 0.5))

  if self.checked then
    theme.setColor(colors.bg)
    love.graphics.setLineWidth(2)
    love.graphics.line(
      self.x + self.size * 0.24, boxY + self.size * 0.52,
      self.x + self.size * 0.43, boxY + self.size * 0.70,
      self.x + self.size * 0.77, boxY + self.size * 0.30)
    love.graphics.setLineWidth(1)
  end

  if label ~= "" then
    theme.setColor(colors.text)
    love.graphics.setFont(font)
    love.graphics.print(label,
      math.floor(self.x + self.size + 8),
      math.floor(self.y + (lineHeight - font:getHeight()) / 2))
  end
end

local Dropdown = {}
Dropdown.__index = Dropdown
ui.Dropdown = Dropdown

function Dropdown.new(opts)
  opts = opts or {}
  local self = setmetatable({}, Dropdown)
  self.x = opts.x or 0
  self.y = opts.y or 0
  self.w = opts.w or 200
  self.h = opts.h or 34
  self.items = {}
  self.value = opts.value
  self.onChange = opts.onChange
  self.font = opts.font
  self.tooltip = opts.tooltip
  self.placeholder = opts.placeholder or "Select..."
  self.open = false
  self.hover = false
  self._hoverIndex = nil
  self._list = nil
  self:setItems(opts.items)
  return self
end

function Dropdown:setItems(items)
  local list = {}
  if type(items) == "table" then
    for i = 1, #items do list[i] = items[i] end
  end
  self.items = list
  self._hoverIndex = nil
  return self
end

function Dropdown:setValue(value)
  self.value = value
  return self
end

function Dropdown:getValue()
  return self.value
end

function Dropdown:isOpen()
  return self.open
end

function Dropdown:close()
  self.open = false
  self._hoverIndex = nil
  self._list = nil
  return self
end

function Dropdown:contains(x, y)
  if pointInRect(x, y, self.x, self.y, self.w, self.h) then return true end
  if self.open and self._list then
    local list = self._list
    return pointInRect(x, y, list.x, list.y, list.w, list.h)
  end
  return false
end

function Dropdown:mousepressed(x, y, button)
  if button ~= 1 then return false end
  local headerHit = pointInRect(x, y, self.x, self.y, self.w, self.h)

  if self.open then
    if headerHit then
      self:close()
      return true
    end

    local list = self._list
    if list and pointInRect(x, y, list.x, list.y, list.w, list.h) then
      local index = nil
      if list.count > 0 then
        local localY = y - list.itemTop
        if localY >= 0 and y <= list.itemTop + list.count * list.itemHeight then
          index = math.floor(localY / list.itemHeight) + 1
          if index < 1 or index > list.count then index = nil end
        end
      end
      if index then
        local item = self.items[index]
        self.value = item
        self:close()
        if self.onChange then self.onChange(item) end
      end
      return true
    end

    -- A click anywhere else closes the popup and is swallowed.
    self:close()
    return true
  end

  if headerHit then
    self.open = true
    self._hoverIndex = nil
    return true
  end
  return false
end

function Dropdown:_drawList(mouseX, mouseY, font)
  local colors = theme.colors
  local count = #self.items
  local listPadding = 3
  local itemHeight = math.max(24, math.min(32, math.floor(self.h)))
  local contentHeight = count > 0 and count * itemHeight or 28
  local listHeight = contentHeight + listPadding * 2
  local gap = 3
  local screenW = theme.width or 1440
  local screenH = theme.height or 900

  local listX = self.x
  local listW = self.w
  if listX + listW > screenW - 6 then
    listW = math.max(60, screenW - 6 - listX)
  end
  if listX < 6 then listX = 6 end

  local belowY = self.y + self.h + gap
  local aboveY = self.y - gap - listHeight
  local spaceBelow = screenH - 6 - belowY
  local spaceAbove = self.y - gap - 6
  local listY
  if listHeight <= spaceBelow then
    listY = belowY
  elseif listHeight <= spaceAbove then
    listY = aboveY
  elseif spaceBelow >= spaceAbove then
    listY = math.max(6, math.min(belowY, screenH - 6 - listHeight))
  else
    listY = math.max(6, aboveY)
  end

  local itemTop = listY + listPadding
  self._list = {
    x = listX,
    y = listY,
    w = listW,
    h = listHeight,
    itemHeight = itemHeight,
    itemTop = itemTop,
    count = count,
  }

  theme.setColor(colors.black, 0.40)
  love.graphics.rectangle("fill", listX + 2, listY + 3, listW, listHeight, 6, 6)
  theme.setColor(colors.panel)
  love.graphics.rectangle("fill", listX, listY, listW, listHeight, 6, 6)

  self._hoverIndex = nil
  if count == 0 then
    local noOptions = theme.truncateText("No options", font,
      math.max(1, listW - 24))
    theme.drawText(noOptions, listX + 12,
      listY + (listHeight - font:getHeight()) / 2, font, colors.textMuted)
  else
    local sx, sy, sw, sh = pushScissor(math.floor(listX + 1),
      math.floor(listY + 1), math.floor(listW - 2),
      math.floor(listHeight - 2))
    for i = 1, count do
      local itemY = itemTop + (i - 1) * itemHeight
      local hovered = mouseX >= listX + listPadding and
        mouseX < listX + listW - listPadding and
        mouseY >= itemY and mouseY < itemY + itemHeight
      if hovered then self._hoverIndex = i end
      if hovered then
        theme.setColor(colors.panelLight, 0.85)
        love.graphics.rectangle("fill", listX + listPadding, itemY + 1,
          listW - listPadding * 2, itemHeight - 2, 3, 3)
      end

      local selected = self.items[i] == self.value
      if selected then
        theme.setColor(colors.gold)
        love.graphics.rectangle("fill", listX + listPadding + 3, itemY + 6,
          2, math.max(1, itemHeight - 12), 1, 1)
      end

      local label = theme.truncateText(tostring(self.items[i]), font,
        listW - listPadding * 2 - 20)
      if selected then
        theme.setColor(colors.gold)
      elseif hovered then
        theme.setColor(colors.white)
      else
        theme.setColor(colors.text)
      end
      love.graphics.setFont(font)
      love.graphics.print(label,
        math.floor(listX + listPadding + 10),
        math.floor(itemY + (itemHeight - font:getHeight()) / 2))
    end
    popScissor(sx, sy, sw, sh)
  end

  theme.setColor(colors.border)
  love.graphics.setLineWidth(1)
  love.graphics.rectangle("line", listX + 0.5, listY + 0.5,
    listW - 1, listHeight - 1, 5.5, 5.5)
end

function Dropdown:draw()
  local colors = theme.colors
  local font = theme.getFont(self.font or "body")
  local mouseX, mouseY = theme.mouseX or 0, theme.mouseY or 0
  local headerHover = pointInRect(mouseX, mouseY, self.x, self.y, self.w, self.h)
  self.hover = headerHover
  if headerHover then queueWidgetTooltip(self, mouseX, mouseY) end

  local radius = math.max(0, math.min(5, self.w / 2, self.h / 2))
  if self.open then
    theme.setColor(colors.gold, 0.14)
    love.graphics.setLineWidth(3)
    love.graphics.rectangle("line", self.x - 1.5, self.y - 1.5,
      self.w + 3, self.h + 3, radius + 2, radius + 2)
  end

  theme.setColor(colors.panelAlt)
  love.graphics.rectangle("fill", self.x, self.y, self.w, self.h,
    radius, radius)

  local borderColor = colors.border
  if self.open then
    borderColor = colors.gold
  elseif headerHover then
    borderColor = colors.borderBright
  end
  theme.setColor(borderColor)
  love.graphics.setLineWidth(1)
  love.graphics.rectangle("line", self.x + 0.5, self.y + 0.5,
    self.w - 1, self.h - 1, math.max(0, radius - 0.5),
    math.max(0, radius - 0.5))

  local padding = 12
  local chevronSpace = 24
  local display
  local textColor
  if self.value == nil or self.value == "" then
    display = self.placeholder or "Select..."
    textColor = colors.textMuted
  else
    display = tostring(self.value)
    textColor = colors.text
  end
  local textWidth = math.max(1, self.w - padding * 2 - chevronSpace)
  display = theme.truncateText(display, font, textWidth)
  theme.drawText(display, self.x + padding,
    self.y + (self.h - font:getHeight()) / 2, font, textColor,
    "left", textWidth)

  local chevronX = self.x + self.w - padding - 4
  local chevronY = self.y + self.h / 2
  theme.setColor(self.open and colors.gold or
    ((headerHover and colors.text) or colors.textMuted))
  love.graphics.setLineWidth(2)
  if self.open then
    love.graphics.line(chevronX - 4, chevronY + 2,
      chevronX, chevronY - 2, chevronX + 4, chevronY + 2)
  else
    love.graphics.line(chevronX - 4, chevronY - 2,
      chevronX, chevronY + 2, chevronX + 4, chevronY - 2)
  end
  love.graphics.setLineWidth(1)

  if self.open then
    self:_drawList(mouseX, mouseY, font)
  end
end

return ui
