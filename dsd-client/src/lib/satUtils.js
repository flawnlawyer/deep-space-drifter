import { Color } from 'cesium'

export const SAT_TYPES = {
  STATION:  'station',
  STARLINK: 'starlink',
  DEBRIS:   'debris',
  OTHER:    'other',
}

export function classifySat(name = '') {
  const n = name.toUpperCase()
  if (n.includes('ISS') || n.includes('CSS') || n.includes('TIANHE') ||
      n.includes('SOYUZ') || n.includes('DRAGON') || n.includes('CYGNUS') ||
      n.includes('PROGRESS') || n.includes('TIANZHOU') || n.includes('SHENZHOU') ||
      n.includes('NAUKA') || n.includes('POISK') || n.includes('ZARYA'))
    return SAT_TYPES.STATION

  if (n.includes('STARLINK')) return SAT_TYPES.STARLINK

  if (n.includes('DEB') || n.includes('DEBRIS') || n.includes('FRAG') ||
      n.includes('OBJECT') || n.includes('R/B') || n.includes('ROCKET'))
    return SAT_TYPES.DEBRIS

  return SAT_TYPES.OTHER
}

export function satColor(name, selected = false) {
  if (selected) return Color.YELLOW
  const type = classifySat(name)
  switch (type) {
    case SAT_TYPES.STATION:  return Color.fromCssColorString('#1e90ff')
    case SAT_TYPES.STARLINK: return Color.fromCssColorString('#20c080')
    case SAT_TYPES.DEBRIS:   return Color.fromCssColorString('#e03050')
    default:                 return Color.fromCssColorString('#a0c0f0')
  }
}

export function satColorHex(name, selected = false) {
  if (selected) return '#facc15'
  const type = classifySat(name)
  switch (type) {
    case SAT_TYPES.STATION:  return '#1e90ff'
    case SAT_TYPES.STARLINK: return '#20c080'
    case SAT_TYPES.DEBRIS:   return '#e03050'
    default:                 return '#a0c0f0'
  }
}

export function kpColor(kp) {
  if (kp >= 7) return '#e03050'
  if (kp >= 5) return '#f0a020'
  return '#20c080'
}

export function stormLabel(kp) {
  if (kp >= 9) return 'G5 Extreme'
  if (kp >= 8) return 'G4 Severe'
  if (kp >= 7) return 'G3 Strong'
  if (kp >= 6) return 'G2 Moderate'
  if (kp >= 5) return 'G1 Minor'
  return 'Quiet'
}
