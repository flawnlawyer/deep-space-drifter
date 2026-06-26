import Globe from './components/Globe'
import Header from './components/Header'
import SidePanel from './components/SidePanel'
import BottomBar from './components/BottomBar'
import { useSatellites } from './hooks/useSatellites'
import { useWeather } from './hooks/useWeather'

export default function App() {
  // Boot data fetching
  useSatellites()
  useWeather()

  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: '#040a14' }}>
      <Globe />
      <Header />
      <SidePanel />
      <BottomBar />
    </div>
  )
}
