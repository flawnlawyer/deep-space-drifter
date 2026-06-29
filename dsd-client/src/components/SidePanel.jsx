import { useStore } from '../store'
import SatelliteList from './SatelliteList'
import WeatherPanel from './WeatherPanel'
import AnalyticsPanel from './AnalyticsPanel'

const TABS = [
  { id: 'satellites', label: 'OBJECTS'   },
  { id: 'weather',    label: 'WEATHER'   },
  { id: 'analytics',  label: 'INTEL'     },
]

export default function SidePanel() {
  const { sidePanel, setSidePanel } = useStore()

  return (
    <aside className="absolute top-[64px] right-4 z-10 w-[288px] flex flex-col gap-2
                      max-h-[calc(100vh-80px)]">

      {/* Tab bar */}
      <div className="glass rounded-lg flex p-1 gap-1">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setSidePanel(t.id)}
            className={`flex-1 py-1.5 rounded text-[10px] font-mono tracking-wider transition-all
              ${sidePanel === t.id
                ? 'bg-[#0d4a8f] text-accent'
                : 'text-dim hover:text-[#c8d8f0]'
              }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Panel content */}
      <div className="overflow-y-auto flex flex-col gap-2 pr-0.5">
        {sidePanel === 'satellites' && <SatelliteList />}
        {sidePanel === 'weather'    && <WeatherPanel />}
        {sidePanel === 'analytics'  && <AnalyticsPanel />}
      </div>
    </aside>
  )
}
