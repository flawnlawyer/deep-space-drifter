import { io } from 'socket.io-client'

const BASE = '/api'

// ── REST helpers ─────────────────────────────────────────────────────────────

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  const json = await res.json()
  if (!json.ok) throw new Error(json.error ?? 'API error')
  return json.data
}

export const api = {
  satellites: {
    live: (group = 'stations_tle') => get(`/satellites/live?group=${group}`),
    history: (name, limit = 100) => get(`/satellites/history/${encodeURIComponent(name)}?limit=${limit}`),
    passes: (name, lat, lon, hours = 24) =>
      get(`/satellites/passes/${encodeURIComponent(name)}?lat=${lat}&lon=${lon}&hours=${hours}`),
    tracked: () => get('/satellites/tracked'),
  },
  weather: {
    current: () => get('/weather/current'),
    history: (metric, limit = 100) => get(`/weather/history/${metric}?limit=${limit}`),
  },
  analyze: {
    decay: () => get('/analyze/decay'),
    anomalies: (name, threshold = 2.0) =>
      get(`/analyze/anomalies/${encodeURIComponent(name)}?threshold=${threshold}`),
    correlate: (name) => get(`/analyze/correlate/${encodeURIComponent(name)}`),
  },
  status: () => get('/status'),
}

// ── Socket.IO ─────────────────────────────────────────────────────────────────

let _socket = null

export function getSocket() {
  if (!_socket) {
    _socket = io({ path: '/socket.io', transports: ['websocket', 'polling'] })
  }
  return _socket
}
