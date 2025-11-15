const canvas = document.getElementById('grid')
const ctx = canvas.getContext('2d')
const sizeInput = document.getElementById('size')
const algoSel = document.getElementById('algorithm')
const heurSel = document.getElementById('heuristic')
const weightInput = document.getElementById('weight')
const diagInput = document.getElementById('diag')
const startBtn = document.getElementById('startBtn')
const stepBtn = document.getElementById('stepBtn')
const autoBtn = document.getElementById('autoBtn')
const pauseBtn = document.getElementById('pauseBtn')
const resetBtn = document.getElementById('resetBtn')
const speedInput = document.getElementById('speed')
const clearObsBtn = document.getElementById('clearObsBtn')
const saveBtn = document.getElementById('saveBtn')
const openDiv = document.getElementById('open')
const closedDiv = document.getElementById('closed')
const historyDiv = document.getElementById('history')
const clearHistoryBtn = document.getElementById('clearHistoryBtn')
const expandedSpan = document.getElementById('expanded')
const elapsedSpan = document.getElementById('elapsed')

let gridSize = parseInt(sizeInput.value, 10)
let cell = Math.floor(canvas.width / gridSize)
let obstacles = new Set()
let start = [0, 0]
let goal = [gridSize - 1, gridSize - 1]
let ws
let timer = null
let lastSnapshot = null
let started = false
let isDragging = false
let dragMode = 'place' // or 'erase'
let history = []

function key(x, y) { return `${x},${y}` }
function clamp(v, min, max) { return Math.max(min, Math.min(max, v)) }
function getGridCoord(e) {
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const rx = (e.clientX - rect.left) * scaleX
  const ry = (e.clientY - rect.top) * scaleY
  const gx = clamp(Math.floor(rx / cell), 0, gridSize - 1)
  const gy = clamp(Math.floor(ry / cell), 0, gridSize - 1)
  return [gx, gy]
}
function drawGrid() {
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  cell = Math.floor(canvas.width / gridSize)
  for (let i = 0; i < gridSize; i++) {
    for (let j = 0; j < gridSize; j++) {
      const x = i * cell, y = j * cell
      ctx.strokeStyle = '#eee'
      ctx.strokeRect(x, y, cell, cell)
      if (obstacles.has(key(i, j))) {
        ctx.fillStyle = '#999'
        ctx.fillRect(x, y, cell, cell)
      }
    }
  }
  ctx.fillStyle = '#1e3a8a'
  ctx.fillRect(start[0] * cell, start[1] * cell, cell, cell)
  ctx.fillStyle = '#dc2626'
  ctx.fillRect(goal[0] * cell, goal[1] * cell, cell, cell)
  if (lastSnapshot && lastSnapshot.closed) {
    ctx.save()
    ctx.globalAlpha = 0.35
    for (const [cx, cy] of lastSnapshot.closed) {
      ctx.fillStyle = '#a78bfa'
      ctx.fillRect(cx * cell, cy * cell, cell, cell)
    }
    ctx.restore()
  }
  if (lastSnapshot && lastSnapshot.open) {
    ctx.save()
    ctx.globalAlpha = 0.5
    for (const [[ox, oy]] of lastSnapshot.open) {
      ctx.fillStyle = '#f59e0b'
      ctx.fillRect(ox * cell, oy * cell, cell, cell)
    }
    ctx.restore()
  }
  if (lastSnapshot && lastSnapshot.current) {
    const [cx, cy] = lastSnapshot.current
    ctx.fillStyle = '#06b6d4'
    ctx.fillRect(cx * cell, cy * cell, cell, cell)
  }
  if (lastSnapshot && lastSnapshot.path) {
    ctx.save()
    ctx.strokeStyle = '#22c55e'
    ctx.lineWidth = Math.max(2, Math.floor(cell * 0.2))
    ctx.beginPath()
    const centers = lastSnapshot.path.map(([px, py]) => [px * cell + cell / 2, py * cell + cell / 2])
    if (centers.length) {
      ctx.moveTo(centers[0][0], centers[0][1])
      for (let k = 1; k < centers.length; k++) ctx.lineTo(centers[k][0], centers[k][1])
      ctx.stroke()
    }
    ctx.restore()
  }
}

canvas.addEventListener('click', (e) => {
  const [x, y] = getGridCoord(e)
  if (e.shiftKey) { start = [x, y]; drawGrid(); return }
  if (e.altKey) { goal = [x, y]; drawGrid(); return }
})

canvas.addEventListener('mousedown', (e) => {
  const [x, y] = getGridCoord(e)
  if (e.shiftKey || e.altKey) return
  const k = key(x, y)
  dragMode = obstacles.has(k) ? 'erase' : 'place'
  isDragging = true
  if (dragMode === 'place') obstacles.add(k); else obstacles.delete(k)
  drawGrid()
})

canvas.addEventListener('mousemove', (e) => {
  if (!isDragging) return
  const [x, y] = getGridCoord(e)
  const k = key(x, y)
  if (dragMode === 'place') {
    if (!obstacles.has(k)) obstacles.add(k)
  } else {
    if (obstacles.has(k)) obstacles.delete(k)
  }
  drawGrid()
})

canvas.addEventListener('mouseup', () => { isDragging = false })
canvas.addEventListener('mouseleave', () => { isDragging = false })

sizeInput.addEventListener('change', () => {
  gridSize = parseInt(sizeInput.value, 10)
  goal = [gridSize - 1, gridSize - 1]
  drawGrid()
})

function connect(onOpen) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws`)
  ws.onopen = () => { if (typeof onOpen === 'function') onOpen() }
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.type === 'ok') {
      if (!started) {
        started = true
        setButtonsForStarted(true)
      }
      if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'step' }))
      return
    }
    if (msg.type === 'snapshot' || msg.type === 'finished') {
      lastSnapshot = msg
      expandedSpan.textContent = msg.stats?.expanded ?? 0
      if (msg.type === 'finished') {
        elapsedSpan.textContent = msg.stats?.elapsed_ms ?? 0
        if (timer) { clearInterval(timer); timer = null }
        setButtonsForStarted(false)
        const record = {
          time: new Date().toLocaleString(),
          size: gridSize,
          obstacles: obstacles.size,
          algo: algoSel.value,
          heuristic: heurSel.value,
          diagonal: diagInput.checked,
          expanded: msg.stats?.expanded ?? 0,
          elapsed_ms: msg.stats?.elapsed_ms ?? 0,
          steps: (msg.path || []).length,
          cost: msg.stats?.cost ?? 0
        }
        history.unshift(record)
        renderHistory()
      }
      renderTables(msg)
      drawGrid()
    }
  }
  ws.onclose = () => {}
}

function payload() {
  return {
    size: gridSize,
    obstacles: [...obstacles].map(s => s.split(',').map(Number)),
    start,
    goal,
    diagonal: diagInput.checked,
    algorithm: algoSel.value,
    heuristic: heurSel.value,
    weight: parseFloat(weightInput.value)
  }
}

function renderTables(msg) {
  openDiv.innerHTML = ''
  closedDiv.innerHTML = ''
  if (msg.open) {
    for (const [[x, y], g, h, f] of msg.open.slice(0, 50)) {
      const row = document.createElement('div')
      row.className = 'row'
      row.textContent = `(${x},${y}) g=${g.toFixed(2)} h=${h.toFixed(2)} f=${f.toFixed(2)}`
      openDiv.appendChild(row)
    }
  }
  if (msg.closed) {
    for (const [x, y] of msg.closed.slice(0, 50)) {
      const row = document.createElement('div')
      row.className = 'row'
      row.textContent = `(${x},${y})`
      closedDiv.appendChild(row)
    }
  }
}

startBtn.addEventListener('click', () => {
  if (!ws || ws.readyState !== 1) {
    connect(() => {
      ws.send(JSON.stringify({ type: 'start', payload: payload() }))
    })
  } else {
    ws.send(JSON.stringify({ type: 'start', payload: payload() }))
  }
})
stepBtn.addEventListener('click', () => {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'step' }))
})
autoBtn.addEventListener('click', () => {
  if (timer) return
  const interval = parseInt(speedInput.value || '50', 10)
  timer = setInterval(() => {
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'step' }))
  }, Math.max(10, interval))
})
pauseBtn.addEventListener('click', () => {
  if (timer) { clearInterval(timer); timer = null }
})
resetBtn.addEventListener('click', () => {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'reset' }))
  // 保留障碍物
  start = [0, 0]
  goal = [gridSize - 1, gridSize - 1]
  lastSnapshot = null
  expandedSpan.textContent = '0'
  elapsedSpan.textContent = '0'
  started = false
  setButtonsForStarted(false)
  drawGrid()
})

clearObsBtn.addEventListener('click', () => {
  obstacles = new Set()
  drawGrid()
})

saveBtn.addEventListener('click', () => {
  const url = canvas.toDataURL('image/png')
  const a = document.createElement('a')
  a.href = url
  a.download = `grid-${Date.now()}.png`
  document.body.appendChild(a)
  a.click()
  a.remove()
})

function renderHistory() {
  if (!historyDiv) return
  historyDiv.innerHTML = ''
  for (const r of history.slice(0, 50)) {
    const row = document.createElement('div')
    row.className = 'history-row'
    const left = `${r.time} | 算法:${r.algo} 启发:${r.heuristic} 尺寸:${r.size} 斜走:${r.diagonal ? '✓' : '×'}`
    const right = `障碍:${r.obstacles} 步数:${r.steps} 成本:${r.cost.toFixed(2)} 耗时:${r.elapsed_ms}ms 展开:${r.expanded}`
    row.innerHTML = `<span>${left}</span><span>${right}</span>`
    historyDiv.appendChild(row)
  }
}

if (clearHistoryBtn) {
  clearHistoryBtn.addEventListener('click', () => { history = []; renderHistory() })
}

drawGrid()

function setButtonsForStarted(isStarted) {
  stepBtn.disabled = !isStarted
  autoBtn.disabled = !isStarted
  pauseBtn.disabled = !isStarted
}

setButtonsForStarted(false)

function resizeCanvas() {
  const wrap = document.querySelector('.canvas-wrap')
  const w = wrap.clientWidth - 20
  canvas.width = Math.max(300, Math.min(1200, w))
  cell = Math.max(4, Math.floor(canvas.width / gridSize))
  canvas.height = cell * gridSize
  cell = Math.floor(canvas.width / gridSize)
  drawGrid()
}

window.addEventListener('resize', resizeCanvas)
resizeCanvas()
