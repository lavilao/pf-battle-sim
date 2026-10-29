function love.conf(t)
  t.identity = "pf_battle_sim"
  t.version = "11.5"
  t.console = false

  t.window.title = "Pathfinder 1e Battle Simulator"
  t.window.width = 1440
  t.window.height = 900
  t.window.minwidth = 1024
  t.window.minheight = 640
  t.window.resizable = true
  t.window.vsync = 1
  t.window.msaa = 4

  t.modules.joystick = false
  t.modules.physics = false

  if os.getenv("PF_HEADLESS") == "1" then
    t.window = false
  end
end
