import { useEffect, useState } from 'react'
import { useStore } from '../store'
import { api } from '../lib/api'

export default function AnalyticsPanel() {
  const { decayRates, setDecayRates } = useStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const data = await api.analyze.decay()
        setDecayRates(data.rates ?? [])
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return <div className="glass rounded-lg p-4 text-dim text-[11px] text-center">Analyzing...</div>
  }

  if (error) {
    return <div className="glass rounded-lg p-4 text-danger text-[11px]">Error: {error}</div>
  }

  const reliable = decayRates.filter(r => r.reliable)
  const pending  = decayRates.filter(r => !r.reliable)

  return (
    <div className="space-y-2">
      {/* Decay rates */}
      <div className="glass rounded-lg p-3">
        <div className="text-[9px] tracking-[0.15em] text-dim uppercase mb-2">
          Altitude Decay · Orbit-Averaged
        </div>

        {reliable.length === 0 ? (
          <div className="space-y-2">
            <div className="text-[11px] text-dim">
              Need &gt;6h of logged data for reliable rates.
            </div>
            <div className="text-[10px] text-dim border border-[#1a2a45] rounded p-2">
              Run:<br/>
              <span className="font-mono text-accent">python drifter.py --watch --log</span><br/>
              and come back after a few hours.
            </div>
          </div>
        ) : (
          <div className="space-y-1 max-h-[240px] overflow-y-auto">
            {reliable.map(r => (
              <DecayRow key={r.name} rate={r} />
            ))}
          </div>
        )}

        {pending.length > 0 && (
          <div className="mt-2 text-[9px] text-dim border-t border-[#1a2a45] pt-2">
            ⚠ {pending.length} satellite(s) need more history
          </div>
        )}
      </div>

      {/* Quick stats */}
      {reliable.length > 0 && (
        <div className="glass rounded-lg p-3 space-y-2">
          <div className="text-[9px] tracking-[0.15em] text-dim uppercase">Summary</div>
          <StatRow
            label="Fastest decay"
            value={reliable[0]?.name}
            sub={`${reliable[0]?.decay_km_per_day?.toFixed(3)} km/day`}
            danger
          />
          <StatRow
            label="Most stable"
            value={reliable[reliable.length - 1]?.name}
            sub={`${reliable[reliable.length - 1]?.decay_km_per_day?.toFixed(3)} km/day`}
          />
          <StatRow
            label="Total tracked"
            value={`${decayRates.length} satellites`}
          />
        </div>
      )}
    </div>
  )
}

function DecayRow({ rate }) {
  const decay = rate.decay_km_per_day
  const isDecaying = decay !== null && decay < -0.5
  return (
    <div className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-[#0d1728]">
      <span className="text-[10px] truncate max-w-[150px]">{rate.name}</span>
      <div className="text-right shrink-0 ml-2">
        <div className={`font-mono text-[11px] ${isDecaying ? 'text-warn' : 'text-ok'}`}>
          {decay !== null ? `${decay.toFixed(3)} km/d` : '—'}
        </div>
        <div className="text-[9px] text-dim">{(rate.span_minutes / 60).toFixed(1)}h</div>
      </div>
    </div>
  )
}

function StatRow({ label, value, sub, danger }) {
  return (
    <div className="flex justify-between items-start py-1 border-b border-[#1a2a45] last:border-0">
      <span className="text-[10px] text-dim">{label}</span>
      <div className="text-right">
        <div className={`text-[11px] truncate max-w-[140px] ${danger ? 'text-warn' : ''}`}>
          {value ?? '—'}
        </div>
        {sub && <div className="font-mono text-[9px] text-dim">{sub}</div>}
      </div>
    </div>
  )
}
