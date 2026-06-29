import { useEffect } from 'react'
import { useStore } from '../store'
import { api } from '../lib/api'

export function useWeather() {
  const setWeather = useStore(s => s.setWeather)

  async function fetch() {
    try {
      const data = await api.weather.current()
      setWeather(data)
    } catch (e) {
      console.warn('[useWeather] fetch failed:', e.message)
    }
  }

  useEffect(() => {
    fetch()
    const timer = setInterval(fetch, 60_000)
    return () => clearInterval(timer)
  }, [])
}
