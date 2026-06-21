import { useEffect, useRef } from 'react'
import { useStore } from '../store'
import { api, getSocket } from '../lib/api'

const POLL_MS = 10_000

export function useSatellites() {
  const { group, setSatellites, setConnected } = useStore()
  const timerRef = useRef(null)

  async function fetch() {
    try {
      const data = await api.satellites.live(group)
      const valid = (data.positions ?? []).filter(p => !p.error)
      setSatellites(valid)
    } catch (e) {
      console.warn('[useSatellites] fetch failed:', e.message)
    }
  }

  useEffect(() => {
    fetch()
    timerRef.current = setInterval(fetch, POLL_MS)

    // socket for push updates (flask-socketio)
    const socket = getSocket()
    socket.on('connect', () => setConnected(true))
    socket.on('disconnect', () => setConnected(false))
    socket.on('positions', (data) => {
      const valid = (data.positions ?? []).filter(p => !p.error)
      setSatellites(valid)
    })

    return () => {
      clearInterval(timerRef.current)
      socket.off('positions')
    }
  }, [group])
}
