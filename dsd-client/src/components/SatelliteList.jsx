import { useStore } from '../store'
import { satColorHex, classifySat, SAT_TYPES } from '../lib/satUtils'

const TYPE_ICONS = {
  [SAT_TYPES.STATION]:  '🛰',
  [SAT_TYPES.STARLINK]: '◆',
  [SAT_TYPES.DEBRIS]:   '✕',
  [SAT_TYPES.OTHER]:    '·',
}

export default function SatelliteList() {
  const { satellites, selectedSat, setSelectedSat } = useStore()
  const selected = satellites.find(s => s.name === selectedSat)

  return (
    <>
      {/* Detail card for selected satellite */}
      {selected && (
        <div className="glass rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-mono text-accent truncate max-w-[200px]">
              {selected.name}
            </span>
            <button
              onClick={() => setSelectedSat(null)}
              className="text-dim hover:text-[#c8d8f0] text-[12px] leading-none"
            >✕</button>
          </div>
          <div className="space-y-1.5">
            <DetailRow label="Latitude"  value={`${selected.lat?.toFixed(4)}°`} />
            <DetailRow label="Longitude" value={`${selected.lon?.toFixed(4)}°`} />
            <DetailRow label="Altitude"  value={`${selected.alt_km?.toFixed(1)} km`} />
            <DetailRow label="Speed"     value={`${selected.speed_kms?.toFixed(3)} km/s`} />
            <DetailRow label="Epoch"     value={selected.epoch?.slice(0, 19).replace('T', ' ')} />
          </div>
        </div>
      )}

      {/* Satellite list card */}
      <div className="glass rounded-lg p-3">
        <div className="text-[9px] tracking-[0.15em] text-dim uppercase mb-2">
          Tracked Objects · {satellites.length}
        </div>
        <div className="space-y-0.5 max-h-[400px] overflow-y-auto">
          {satellites.length === 0 ? (
            <div className="text-dim text-[11px] py-4 text-center">Loading...</div>
          ) : (
            satellites.map(sat => {
              const type = classifySat(sat.name)
              const color = satColorHex(sat.name)
              const isSelected = sat.name === selectedSat
              return (
                <button
                  key={sat.name}
                  onClick={() => setSelectedSat(sat.name)}
                  className={`w-full flex items-center justify-between px-2 py-1.5 rounded
                    text-left transition-all group
                    ${isSelected ? 'bg-[#0d4a8f]' : 'hover:bg-[#0d1728]'}`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[10px] shrink-0" style={{ color }}>
                      {TYPE_ICONS[type]}
                    </span>
                    <span className="text-[11px] truncate" style={{ color: isSelected ? '#fff' : undefined }}>
                      {sat.name}
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-dim shrink-0 ml-2">
                    {sat.alt_km?.toFixed(0)} km
                  </span>
                </button>
              )
            })
          )}
        </div>
      </div>
    </>
  )
}

function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-[#1a2a45] last:border-0">
      <span className="text-[10px] text-dim">{label}</span>
      <span className="font-mono text-[11px]">{value}</span>
    </div>
  )
}
