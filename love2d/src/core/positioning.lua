local positioning = {}

local DIRECTIONS = {
  { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 },
  { 1, 1 }, { 1, -1 }, { -1, 1 }, { -1, -1 },
}

function positioning.key(x, y)
  return x .. "," .. y
end

function positioning.parseKey(key)
  local x, y = tostring(key):match("^(-?%d+),(-?%d+)$")
  if not x then return nil end
  return { x = tonumber(x), y = tonumber(y) }
end

function positioning.chebyshev(ax, ay, bx, by)
  return math.max(math.abs(ax - bx), math.abs(ay - by))
end

function positioning.combatantAt(combatants, x, y, excludeId)
  for _, c in ipairs(combatants or {}) do
    if c.id ~= excludeId and c:occupiesCell(x, y) then
      return c
    end
  end
  return nil
end

function positioning.terrainBlocked(grid, x, y)
  if not grid then return false end
  return grid.blocked and grid.blocked[positioning.key(x, y)] == true
end

function positioning.inBounds(grid, x, y)
  if not grid then return true end
  return x >= 1 and y >= 1 and x <= grid.width and y <= grid.height
end

function positioning.canStand(c, x, y, combatants, grid, ignoreId)
  local space = c:getSpaceSquares()
  for dx = 0, space - 1 do
    for dy = 0, space - 1 do
      local cx, cy = x + dx, y + dy
      if not positioning.inBounds(grid, cx, cy) then return false end
      if positioning.terrainBlocked(grid, cx, cy) then return false end
      local other = positioning.combatantAt(combatants, cx, cy, ignoreId or c.id)
      if other then return false end
    end
  end
  return true
end

function positioning.findPlacement(c, combatants, grid, preferredX, preferredY)
  local maxRadius = math.max(grid and grid.width or 20, grid and grid.height or 14)
  for radius = 0, maxRadius do
    for dx = -radius, radius do
      for dy = -radius, radius do
        if math.max(math.abs(dx), math.abs(dy)) == radius then
          local x = (preferredX or 1) + dx
          local y = (preferredY or 1) + dy
          if positioning.canStand(c, x, y, combatants, grid) then
            return x, y
          end
        end
      end
    end
  end
  return nil, nil
end

-- Breadth-first movement range over anchor cells. Diagonal movement costs one
-- 5-ft square (a commonly used tabletop simplification).
function positioning.reachable(c, combatants, grid, maxCost, startPosition)
  local start = startPosition or c.position
  if not start then
    return { costs = {}, parents = {}, cells = {}, start = nil }
  end
  local startKey = positioning.key(start.x, start.y)
  local result = {
    costs = { [startKey] = 0 },
    parents = {},
    cells = { [startKey] = { x = start.x, y = start.y } },
    start = { x = start.x, y = start.y },
  }

  local queue = { { x = start.x, y = start.y, cost = 0 } }
  local head = 1
  while head <= #queue do
    local node = queue[head]
    head = head + 1
    if node.cost < maxCost then
      for _, dir in ipairs(DIRECTIONS) do
        local nx, ny = node.x + dir[1], node.y + dir[2]
        local nk = positioning.key(nx, ny)
        if result.costs[nk] == nil and
           positioning.canStand(c, nx, ny, combatants, grid) then
          result.costs[nk] = node.cost + 1
          result.parents[nk] = positioning.key(node.x, node.y)
          result.cells[nk] = { x = nx, y = ny }
          queue[#queue + 1] = { x = nx, y = ny, cost = node.cost + 1 }
        end
      end
    end
  end
  return result
end

function positioning.pathFromReachable(bfs, x, y)
  local key = positioning.key(x, y)
  if not bfs.costs[key] then return nil end
  local path = {}
  local current = key
  while bfs.parents[current] do
    local cell = bfs.cells[current]
    table.insert(path, 1, { x = cell.x, y = cell.y })
    current = bfs.parents[current]
  end
  return path
end

function positioning.findPath(c, combatants, grid, destX, destY, maxCost)
  local bfs = positioning.reachable(c, combatants, grid, maxCost or 999)
  local path = positioning.pathFromReachable(bfs, destX, destY)
  if not path then return nil, nil end
  return path, bfs.costs[positioning.key(destX, destY)]
end

function positioning.threatensCell(attacker, x, y)
  if not attacker.position then return false end
  local reachSquares = math.max(1, math.floor(attacker:getReachFeet() / 5))
  return attacker:cellDistance(x, y) <= reachSquares
end

function positioning.threatensCombatant(attacker, target)
  if not target.position then return false end
  for _, cell in ipairs(target:getFootprint()) do
    if positioning.threatensCell(attacker, cell.x, cell.y) then
      return true
    end
  end
  return false
end

function positioning.attackThreatensCombatant(attacker, target, attack)
  if not target.position or not attack then return false end
  local reachSquares = math.max(1, math.ceil(attack.reach / 5))
  for _, cell in ipairs(target:getFootprint()) do
    if attacker:cellDistance(cell.x, cell.y) <= reachSquares then
      return true
    end
  end
  return false
end

function positioning.sameLine(fromX, fromY, toX, toY)
  return fromX == toX or fromY == toY
end

-- Cells from (fromX,fromY) toward (toX,toY) inclusive of destination.
function positioning.straightCells(fromX, fromY, toX, toY)
  if not positioning.sameLine(fromX, fromY, toX, toY) then return nil end
  local cells = {}
  local dx = toX == fromX and 0 or (toX > fromX and 1 or -1)
  local dy = toY == fromY and 0 or (toY > fromY and 1 or -1)
  local x, y = fromX, fromY
  while x ~= toX or y ~= toY do
    x, y = x + dx, y + dy
    cells[#cells + 1] = { x = x, y = y }
    if #cells > 200 then break end
  end
  return cells
end

function positioning.center(c, cellSize)
  if not c.position then return nil end
  local space = c:getSpaceSquares()
  return {
    x = (c.position.x + (space - 1) / 2) * cellSize,
    y = (c.position.y + (space - 1) / 2) * cellSize,
  }
end

function positioning.distanceBetween(a, b)
  if not a.position or not b.position then return 9999 end
  local best = 9999
  for _, cellA in ipairs(a:getFootprint()) do
    for _, cellB in ipairs(b:getFootprint()) do
      local d = positioning.chebyshev(cellA.x, cellA.y, cellB.x, cellB.y)
      if d < best then best = d end
    end
  end
  return best
end

function positioning.cellsAround(c, radius)
  local cells = {}
  if not c.position then return cells end
  local seen = {}
  local reach = math.max(1, radius or 1)
  for _, cell in ipairs(c:getFootprint()) do
    for dx = -reach, reach do
      for dy = -reach, reach do
        local x, y = cell.x + dx, cell.y + dy
        local k = positioning.key(x, y)
        if not c:occupiesCell(x, y) and not seen[k] then
          if math.max(math.abs(dx), math.abs(dy)) <= reach then
            seen[k] = true
            cells[#cells + 1] = { x = x, y = y }
          end
        end
      end
    end
  end
  return cells
end

return positioning
