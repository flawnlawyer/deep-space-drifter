import { useStore } from '../store'
import { kpColor, stormLabel } from '../lib/satUtils'

export default function WeatherPanel() {
  const weather = useStore(s => s.weather)

  if (!weather) {
    return (
      <div className="glass rounded-lg p-4 text-dim text-[11px] text-center">
        Fetching NOAA space weather...
      </div>
    )
  }

  const kp = weather.kp_current ?? 0
  const color = kpColor(kp)
  const storm = stormLabel(kp)
  const kpPct = Math.min((kp / 9) * 100, 100)

  return (
    <div className="glass rounded-lg p-4 space-y-4">
      <div className="text-[9px] tracking-[0.15em] text-dim uppercase">
        Space Weather · NOAA SWPC
      </div>

      {/* Kp gauge */}
      <div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="font-mono text-5xl font-bold" style={{ color }}>
            {kp.toFixed(2)}
          </span>
          <span className="text-dim text-[12px]">Kp index</span>
        </div>
        <div className="w-full h-1.5 bg-[#0d1728] rounded-full overflow-hidden mb-1">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${kpPct}%`, background: color }}
          />
        </div>
        <div className="text-[11px]" style={{ color }}>
          {storm}
        </div>
        {weather.kp_time && (
          <div className="text-[9px] text-dim mt-0.5">
            {weather.kp_status} · {weather.kp_time?.slice(0, 16).replace('T', ' ')} UTC
          </div>
        )}
      </div>

      {/* Solar wind */}
      <div className="space-y-2">
        <div className="text-[9px] tracking-[0.12em] text-dim uppercase">Solar Wind</div>
        <WeatherRow label="Speed"   value={weather.solar_wind_speed_kms}    unit="km/s"  />
        <WeatherRow label="Density" value={weather.solar_wind_density_pcm3}  unit="p/cm³" />
        {weather.solar_wind_time && (
          <div className="text-[9px] text-dim">
            Measured {weather.solar_wind_time?.slice(0, 16).replace('T', ' ')} UTC
          </div>
        )}
      </div>

      {/* Forecast */}
      {weather.kp_max_predicted && (
        <div className="border border-[#1a2a45] rounded-md p-2 space-y-1">
          <div className="text-[9px] tracking-[0.12em] text-dim uppercase">24-72h Forecast</div>
          <div className="flex justify-between items-center">
            <span className="text-[11px] text-dim">Peak Kp</span>
            <span className="font-mono text-[13px]" style={{ color: kpColor(weather.kp_max_predicted) }}>
              {weather.kp_max_predicted}
            </span>
          </div>
          <div className="text-[9px] text-dim">
            {weather.kp_max_time?.slice(0, 16).replace('T', ' ')} UTC
          </div>
        </div>
      )}
    </div>
  )
}

function WeatherRow({ label, value, unit }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-[#1a2a45] last:border-0">
      <span className="text-[10px] text-dim">{label}</span>
      <span className="font-mono text-[12px]">
        {value !== null && value !== undefined ? value : '—'} <span className="text-dim text-[9px]">{unit}</span>
      </span>
    </div>
  )
}
