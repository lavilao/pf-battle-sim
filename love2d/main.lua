local theme = require("src.ui.theme")
local App = require("src.app")

local app
local canvas
local scale = 1
local offsetX = 0
local offsetY = 0

local autopilot = nil
local shotCount = 0

local function updateViewport()
  local width, height = love.graphics.getDimensions()
  scale = math.min(width / theme.width, height / theme.height)
  if scale <= 0 then scale = 1 end
  offsetX = math.floor((width - theme.width * scale) / 2)
  offsetY = math.floor((height - theme.height * scale) / 2)
end

local function toVirtual(x, y)
  local vx = (x - offsetX) / scale
  local vy = (y - offsetY) / scale
  if vx < 0 or vy < 0 or vx >= theme.width or vy >= theme.height then
    return nil, nil
  end
  return vx, vy
end

local function updateMouse()
  local mx, my = love.mouse.getPosition()
  local vx, vy = toVirtual(mx, my)
  theme.mouseX = vx or -100
  theme.mouseY = vy or -100
end

local function captureCanvas(name)
  shotCount = shotCount + 1
  local filename = string.format("%s_%02d_%s.png",
    autopilot.prefix or "pf", shotCount, name)
  local ok, err = pcall(function()
    local imageData = canvas:newImageData()
    imageData:encode("png", filename)
  end)
  if ok then
    print(string.format("[screenshot] %s/%s", love.filesystem.getSaveDirectory(), filename))
  else
    print("[screenshot] failed: " .. tostring(err))
  end
end

local function startAutopilot()
  local smoke = os.getenv("PF_SMOKE") == "1"
  local enabled = os.getenv("PF_AUTOPILOT") == "1" or smoke
  if not enabled then return end

  local steps = {}
  if smoke then
    steps = {
      { t = 0.4, action = function()
        print("[smoke] app loaded; screen=" .. tostring(app.screenName))
      end },
      { t = 0.7, action = function() love.event.quit() end },
    }
  else
    steps = {
      { t = 0.9, shot = "menu" },
      { t = 1.4, action = function() app:showSetup() end },
      { t = 2.2, shot = "setup" },
      { t = 2.8, action = function() app:startQuickBattle({ autoBattle = true }) end },
      { t = 4.6, shot = "battle" },
      { t = 5.2, action = function() app:showBestiary("menu") end },
      { t = 6.0, shot = "bestiary" },
      { t = 6.6, action = function() app:showCreator({ returnTo = "menu" }) end },
      { t = 7.4, shot = "creator" },
      { t = 8.0, action = function() app:showHelp() end },
      { t = 8.8, shot = "help" },
      { t = 9.4, action = function() love.event.quit() end },
    }
  end

  autopilot = {
    time = 0,
    index = 1,
    steps = steps,
    prefix = os.getenv("PF_SHOT_PREFIX") or "pf",
  }
end

local function updateAutopilot(dt)
  if not autopilot then return end
  autopilot.time = autopilot.time + dt
  while autopilot.index <= #autopilot.steps do
    local step = autopilot.steps[autopilot.index]
    if autopilot.time < step.t then break end
    autopilot.index = autopilot.index + 1
    if step.action then
      local ok, err = pcall(step.action)
      if not ok then print("[autopilot] error: " .. tostring(err)) end
    end
    if step.shot then
      autopilot.pendingShot = step.shot
    end
  end
end

function love.load()
  love.graphics.setDefaultFilter("linear", "linear", 1)
  love.graphics.setBackgroundColor(theme.colors.bg)
  love.keyboard.setKeyRepeat(false)

  theme.init()
  canvas = love.graphics.newCanvas(theme.width, theme.height)
  canvas:setFilter("linear", "linear")
  updateViewport()

  local ok, err = pcall(function() app = App.new() end)
  if not ok then
    print("[fatal] failed to start app: " .. tostring(err))
    error(err)
  end
  print("[pf-battle-sim] save directory: " .. love.filesystem.getSaveDirectory())
  startAutopilot()
end

function love.update(dt)
  updateMouse()
  if app then app:update(dt) end
  updateAutopilot(dt)
end

function love.draw()
  updateMouse()
  love.graphics.setCanvas(canvas)
  love.graphics.clear(theme.colors.bg)
  if app then app:draw() end
  love.graphics.setCanvas()

  love.graphics.clear(0, 0, 0)
  love.graphics.setColor(1, 1, 1, 1)
  love.graphics.draw(canvas, offsetX, offsetY, 0, scale, scale)

  if autopilot and autopilot.pendingShot then
    local name = autopilot.pendingShot
    autopilot.pendingShot = nil
    captureCanvas(name)
  end
end

function love.resize()
  updateViewport()
end

function love.mousepressed(x, y, button, istouch, presses)
  if not app then return end
  local vx, vy = toVirtual(x, y)
  if not vx then return end
  updateMouse()
  app:mousepressed(vx, vy, button, istouch, presses)
end

function love.mousereleased(x, y, button, istouch, presses)
  if not app then return end
  local vx, vy = toVirtual(x, y)
  if not vx then vx, vy = theme.mouseX, theme.mouseY end
  app:mousereleased(vx, vy, button, istouch, presses)
end

function love.wheelmoved(dx, dy)
  updateMouse()
  if app then app:wheelmoved(dx, dy) end
end

function love.keypressed(key, scancode, isrepeat)
  if key == "f11" then
    local fullscreen = love.window.getFullscreen()
    love.window.setFullscreen(not fullscreen, "desktop")
    updateViewport()
    return
  elseif key == "f12" then
    shotCount = shotCount + 1
    local filename = string.format("theater_%02d.png", shotCount)
    local imageData = canvas:newImageData()
    imageData:encode("png", filename)
    print("[screenshot] " .. love.filesystem.getSaveDirectory() .. "/" .. filename)
    return
  end
  if app then app:keypressed(key, scancode, isrepeat) end
end

function love.textinput(text)
  if app then app:textinput(text) end
end
