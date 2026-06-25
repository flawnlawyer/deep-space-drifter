import { useStore } from '../store'
import { kpColor } from '../lib/satUtils'

const GROUPS = [
  { id: 'stations_tle', label: 'STATIONS' },
  { id: 'starlink',     label: 'STARLINK' },
  { id: 'visual',       label: 'VISUAL'   },
  { id: 'debris',       label: 'DEBRIS'   },
  { id: 'active',       label: 'ACTIVE'   },
]

export default function Header() {
  const { satellites, weather, connected, group, setGroup, trailsEnabled, setTrailsEnabled } = useStore()
  const kp = weather?.kp_current ?? null

  return (
    <header className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-5 py-3
                       bg-gradient-to-b from-[#040a14f5] to-transparent border-b border-[#1a2a45]
                       backdrop-blur-sm">

      {/* Brand */}
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-[15px] font-bold tracking-widest text-white">
          DEEP <span className="text-accent">SPACE</span> DRIFTER
        </span>
        <span className="text-[9px] tracking-[0.18em] text-dim uppercase">
          Observe · Analyze · Discover
        </span>
      </div>

      {/* Group tabs */}
      <div className="flex gap-1 glass rounded-md px-1 py-1">
        {GROUPS.map(g => (
          <button
            key={g.id}
            onClick={() => setGroup(g.id)}
            className={`px-3 py-1 rounded text-[11px] font-mono tracking-wider transition-all
              ${group === g.id
                ? 'bg-[#0d4a8f] text-accent'
                : 'text-dim hover:text-[#c8d8f0] hover:bg-[#0d1728]'
              }`}
          >
            {g.label}
          </button>
        ))}
      </div>

      {/* Live stats */}
      <div className="flex items-center gap-5">
        <Stat label="Satellites" value={satellites.length || '—'} />
        <Stat
          label="Kp Index"
          value={kp !== null ? kp.toFixed(1) : '—'}
          style={{ color: kp !== null ? kpColor(kp) : undefined }}
        />
        <Stat
          label="Solar Wind"
          value={weather?.solar_wind_speed_kms ? `${weather.solar_wind_speed_kms} km/s` : '—'}
        />

        {/* Trails toggle */}
        <button
          onClick={() => setTrailsEnabled(!trailsEnabled)}
          className={`text-[10px] font-mono tracking-wider px-2 py-1 rounded border transition-all
            ${trailsEnabled
              ? 'border-accent text-accent bg-[#1e90ff18]'
              : 'border-[#1a2a45] text-dim'
            }`}
        >
          TRAILS
        </button>

        {/* Connection dot */}
        <div className="flex items-center gap-2 text-[11px] font-mono">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-[#20c080] animate-pulse' : 'bg-[#e03050]'}`} />
          <span className={connected ? 'text-ok' : 'text-danger'}>
            {connected ? 'LIVE' : 'POLLING'}
          </span>
        </div>
      </div>
    </header>
  )
}

function Stat({ label, value, style }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-[9px] tracking-[0.12em] text-dim uppercase">{label}</span>
      <span className="font-mono text-[14px] text-accent" style={style}>{value}</span>
    </div>
  )
}
