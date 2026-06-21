import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // ── Satellites ──────────────────────────────────────────────────────────
  satellites: [],           // current live positions [{name, lat, lon, alt_km, speed_kms, epoch}]
  selectedSat: null,        // name string
  group: 'stations_tle',    // active TLE group
  lastEpoch: null,

  setSatellites: (satellites) => set({ satellites, lastEpoch: satellites[0]?.epoch ?? null }),
  setSelectedSat: (name) => set((s) => ({ selectedSat: s.selectedSat === name ? null : name })),
  setGroup: (group) => set({ group, selectedSat: null }),

  // ── Space weather ────────────────────────────────────────────────────────
  weather: null,            // current conditions from /api/weather/current

  setWeather: (weather) => set({ weather }),

  // ── Analytics ───────────────────────────────────────────────────────────
  decayRates: [],
  anomalies: {},            // { [satName]: [anomaly, ...] }

  setDecayRates: (decayRates) => set({ decayRates }),
  setAnomalies: (name, hits) => set((s) => ({
    anomalies: { ...s.anomalies, [name]: hits }
  })),

  // ── UI ───────────────────────────────────────────────────────────────────
  sidePanel: 'satellites',  // 'satellites' | 'weather' | 'analytics'
  trailsEnabled: true,
  connected: false,

  setSidePanel: (sidePanel) => set({ sidePanel }),
  setTrailsEnabled: (v) => set({ trailsEnabled: v }),
  setConnected: (connected) => set({ connected }),
}))
