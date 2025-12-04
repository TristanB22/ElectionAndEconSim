import { useEffect } from 'react'
import type { Map as MapLibreMap } from 'maplibre-gl'
import type { Route } from '../../types/routing'

interface RouteLayerProps {
  map: MapLibreMap | null
  route: Route | null
  onRouteClick?: () => void
  emphasized?: boolean
}

export function RouteLayer({ map, route, onRouteClick, emphasized = false }: RouteLayerProps) {

  useEffect(() => {
    if (!map || !route) {
      // Clean up existing route layers if no route
      if (map) {
        const layersToRemove = [
          'route-layer-halo',
          'route-layer',
          'route-layer-dash',
          'route-start-marker',
          'route-end-marker'
        ]
        const sourcesToRemove = ['route-source', 'route-start-marker', 'route-end-marker']
        
        layersToRemove.forEach(layerId => {
          if (map.getLayer(layerId)) map.removeLayer(layerId)
        })
        sourcesToRemove.forEach(sourceId => {
          if (map.getSource(sourceId)) map.removeSource(sourceId)
        })
      }
      return
    }

    const sourceId = 'route-source'
    const haloLayerId = 'route-layer-halo'
    const mainLayerId = 'route-layer'
    const dashLayerId = 'route-layer-dash'
    const startMarkerId = 'route-start-marker'
    const endMarkerId = 'route-end-marker'

    // Add route source
    if (!map.getSource(sourceId)) {
      map.addSource(sourceId, {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'LineString',
            coordinates: route.coordinates
          }
        }
      })
    } else {
      const source = map.getSource(sourceId) as any
      if (source && source.type === 'geojson') {
        source.setData({
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'LineString',
            coordinates: route.coordinates
          }
        })
      }
    }

    // Layer 1: Halo (thick white outline for separation from map)
    if (!map.getLayer(haloLayerId)) {
      map.addLayer({
        id: haloLayerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#ffffff',
          'line-width': 12,
          'line-opacity': 0.3,
          'line-blur': 2
        }
      })
    }

    // Layer 2: Primary route (saturated brand color)
    if (!map.getLayer(mainLayerId)) {
      map.addLayer({
        id: mainLayerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': emphasized ? '#93c5fd' : '#3b82f6',
          'line-width': emphasized ? 9 : 6,
          'line-opacity': emphasized ? 1.0 : 0.95
        }
      })
    }
    else {
      map.setPaintProperty(mainLayerId, 'line-color', emphasized ? '#93c5fd' : '#3b82f6')
      map.setPaintProperty(mainLayerId, 'line-width', emphasized ? 9 : 6)
      map.setPaintProperty(mainLayerId, 'line-opacity', emphasized ? 1.0 : 0.95)
    }

    // Layer 3: Directional dashes (optional, at higher zoom)
    if (!map.getLayer(dashLayerId)) {
      map.addLayer({
        id: dashLayerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#60a5fa',
          'line-width': 3,
          'line-opacity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            10, 0,
            14, 0.6
          ],
          'line-dasharray': [0.5, 2],
          'line-offset': 0
        }
      })
    }

    // Start marker
    const startCoord = route.coordinates[0]
    if (!map.getSource(startMarkerId)) {
      map.addSource(startMarkerId, {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Point',
            coordinates: startCoord
          }
        }
      })

      map.addLayer({
        id: startMarkerId,
        type: 'circle',
        source: startMarkerId,
        paint: {
          'circle-radius': 12,
          'circle-color': '#10b981',
          'circle-stroke-width': 3,
          'circle-stroke-color': '#ffffff'
        }
      })
    } else {
      const source = map.getSource(startMarkerId) as any
      if (source && source.type === 'geojson') {
        source.setData({
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Point',
            coordinates: startCoord
          }
        })
      }
    }

    // End marker
    const endCoord = route.coordinates[route.coordinates.length - 1]
    if (!map.getSource(endMarkerId)) {
      map.addSource(endMarkerId, {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Point',
            coordinates: endCoord
          }
        }
      })

      map.addLayer({
        id: endMarkerId,
        type: 'circle',
        source: endMarkerId,
        paint: {
          'circle-radius': 12,
          'circle-color': '#ef4444',
          'circle-stroke-width': 3,
          'circle-stroke-color': '#ffffff'
        }
      })
    } else {
      const source = map.getSource(endMarkerId) as any
      if (source && source.type === 'geojson') {
        source.setData({
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Point',
            coordinates: endCoord
          }
        })
      }
    }

    // Zoom to route bounds with smooth animation
    const lons = route.coordinates.map(c => c[0])
    const lats = route.coordinates.map(c => c[1])
    const bounds: [[number, number], [number, number]] = [
      [Math.min(...lons), Math.min(...lats)],
      [Math.max(...lons), Math.max(...lats)]
    ]
    map.fitBounds(bounds, { padding: 100, duration: 800 })

    // Do not add click handlers; route should not open details on click
    // Keep route non-interactive here. Toast triggers details instead.

  }, [map, route, onRouteClick])

  return null
}
