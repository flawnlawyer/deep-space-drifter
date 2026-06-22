import { useEffect, useRef, useMemo } from 'react'
import {
  Viewer, Entity, PointGraphics, PathGraphics,
  CameraFlyTo, Globe as CesiumGlobe,
} from 'resium'
import {
  Cartesian3, Color, IonImageryProvider, IonResource,
  NearFarScalar, SampledPositionProperty, JulianDate,
  ClockRange, ClockStep, createWorldTerrainAsync,
  ArcGisMapServerImageryProvider, UrlTemplateImageryProvider,
} from 'cesium'
import { useStore } from '../store'
import { satColor } from '../lib/satUtils'

// Build a stable SampledPositionProperty for trail rendering
function buildPositionProperty(history) {
  const prop = new SampledPositionProperty()
  for (const h of history) {
    try {
      const t = JulianDate.fromIso8601(h.epoch)
      const pos = Cartesian3.fromDegrees(h.lon, h.lat, h.alt_km * 1000)
      prop.addSample(t, pos)
    } catch (_) {}
  }
  return prop
}

export default function Globe() {
  const { satellites, selectedSat, setSelectedSat, trailsEnabled } = useStore()
  const viewerRef = useRef(null)

  // Fly to selected satellite
  useEffect(() => {
    if (!viewerRef.current?.cesiumElement || !selectedSat) return
    const sat = satellites.find(s => s.name === selectedSat)
    if (!sat) return
    const viewer = viewerRef.current.cesiumElement
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(sat.lon, sat.lat, sat.alt_km * 1000 + 2_500_000),
      duration: 1.8,
    })
  }, [selectedSat])

  // ESRI World Imagery — no token, real satellite imagery
  const imageryProvider = useMemo(() => new ArcGisMapServerImageryProvider({
    url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
  }), [])

  return (
    <Viewer
      ref={viewerRef}
      full
      baseLayerPicker={false}
      geocoder={false}
      homeButton={false}
      sceneModePicker={false}
      navigationHelpButton={false}
      animation={false}
      timeline={false}
      fullscreenButton={false}
      infoBox={false}
      selectionIndicator={false}
      imageryProvider={imageryProvider}
      style={{ position: 'absolute', inset: 0 }}
      onClick={(movement, target) => {
        if (target?.id?.name) setSelectedSat(target.id.name)
        else setSelectedSat(null)
      }}
    >
      {/* Tweak globe appearance */}
      <CesiumGlobe
        enableLighting
        atmosphereLightIntensity={10}
        showGroundAtmosphere
      />

      {/* Satellite entities */}
      {satellites.map(sat => {
        const selected = sat.name === selectedSat
        const color = satColor(sat.name, selected)
        const pos = Cartesian3.fromDegrees(sat.lon, sat.lat, sat.alt_km * 1000)

        return (
          <Entity
            key={sat.name}
            name={sat.name}
            position={pos}
            onClick={() => setSelectedSat(sat.name)}
          >
            <PointGraphics
              pixelSize={selected ? 14 : 6}
              color={color}
              outlineColor={Color.fromCssColorString('#040a14')}
              outlineWidth={selected ? 2 : 1}
              scaleByDistance={new NearFarScalar(1e5, 2.5, 2e8, 0.4)}
              disableDepthTestDistance={Number.POSITIVE_INFINITY}
            />
          </Entity>
        )
      })}
    </Viewer>
  )
}
