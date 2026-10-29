local theme = require("src.ui.theme")
local ui = require("src.ui.widgets")
local MonsterDatabase = require("src.core.monster_database")

local MenuScreen = require("src.screens.menu")
local SetupScreen = require("src.screens.setup")
local BattleScreen = require("src.screens.battle")
local BestiaryScreen = require("src.screens.bestiary")
local CreatorScreen = require("src.screens.creator")
local HelpScreen = require("src.screens.help")

local App = {}
App.__index = App

function App.new()
  local self = setmetatable({}, App)
  self.database = MonsterDatabase.new()
  self.settings = {
    autoNpc = true,
    showThreats = true,
    speed = 1,
    pillars = false,
  }
  self.screen = nil
  self.screenName = nil
  self.fade = 1
  self.bestiaryReturn = "menu"

  self.screens = {
    menu = MenuScreen.new(self),
    setup = SetupScreen.new(self),
    battle = BattleScreen.new(self),
    bestiary = BestiaryScreen.new(self),
    creator = CreatorScreen.new(self),
    help = HelpScreen.new(self),
  }

  self:showMenu()
  return self
end

function App:setScreen(name, params)
  local screen = self.screens[name]
  if not screen then return end
  if self.screen and self.screen.leave then
    self.screen:leave()
  end
  self.screen = screen
  self.screenName = name
  self.fade = 1
  if screen.enter then
    screen:enter(params)
  end
end

function App:showMenu()
  self:setScreen("menu")
end

function App:showSetup(params)
  self:setScreen("setup", params)
end

function App:showBattle(config)
  self:setScreen("battle", config)
end

function App:showBestiary(returnTo)
  self.bestiaryReturn = returnTo or "menu"
  self:setScreen("bestiary")
end

function App:showCreator(opts)
  self:setScreen("creator", opts)
end

function App:showHelp()
  self:setScreen("help")
end

function App:makeDefaultRoster()
  local roster = {}
  local function add(key, side)
    if self.database:get(key) then
      roster[#roster + 1] = { key = key, side = side }
    end
  end
  add("sir_roderick", "pc")
  add("shadowstep", "pc")
  add("orc_warrior", "npc")
  add("goblin_archer", "npc")
  if #roster > 0 then return roster end
  for _, entry in ipairs(self.database:getDefinitions()) do
    roster[#roster + 1] = {
      key = entry.key,
      side = entry.data.is_pc and "pc" or "npc",
    }
  end
  return roster
end

function App:startQuickBattle(opts)
  opts = opts or {}
  local config = {
    entries = self:makeDefaultRoster(),
    gridW = 20,
    gridH = 14,
    pillars = self.settings.pillars,
    pcsAware = true,
    npcsAware = true,
    autoBattle = opts.autoBattle == true,
  }
  self:showBattle(config)
end

function App:update(dt)
  if self.fade > 0 then
    self.fade = math.max(0, self.fade - dt * 3.5)
  end
  if self.screen and self.screen.update then
    self.screen:update(dt)
  end
end

function App:draw()
  love.graphics.clear(theme.colors.bg)

  if self.screen and self.screen.draw then
    ui.beginFrame()
    self.screen:draw()
    ui.drawDeferred()
  end

  if self.fade > 0 then
    love.graphics.setColor(0, 0, 0, self.fade)
    love.graphics.rectangle("fill", 0, 0, theme.width, theme.height)
  end
end

function App:mousepressed(x, y, button)
  if not self.screen then return false end
  local focused = ui._focusedInput
  local handled = false
  if self.screen.mousepressed then
    handled = self.screen:mousepressed(x, y, button) or false
  end
  if focused and focused.focused and ui._focusedInput == focused and
     not focused:contains(x, y) then
    focused:blur()
  end
  return handled
end

function App:mousereleased(x, y, button)
  if self.screen and self.screen.mousereleased then
    return self.screen:mousereleased(x, y, button)
  end
  return false
end

function App:keypressed(key, scancode, isrepeat)
  if self.screen and self.screen.keypressed then
    return self.screen:keypressed(key, scancode, isrepeat)
  end
  return false
end

function App:textinput(text)
  if self.screen and self.screen.textinput then
    return self.screen:textinput(text)
  end
  return false
end

function App:wheelmoved(dx, dy)
  if self.screen and self.screen.wheelmoved then
    return self.screen:wheelmoved(dx, dy)
  end
  return false
end

function App:hasFocusedInput()
  return ui._focusedInput ~= nil and ui._focusedInput.focused
end

return App
