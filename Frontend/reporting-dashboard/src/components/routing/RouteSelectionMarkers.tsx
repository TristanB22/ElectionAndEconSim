import { useEffect, useRef } from 'react'
import type { Map as MapLibreMap } from 'maplibre-gl'

/**
 * RouteSelectionMarkers - Draggable markers for route start/end points
 * 
 * Design:
 * - Green circle for start location
 * - Red circle for end location
 * - Both markers are draggable when route is not yet calculated
 * - Drag updates coordinates in real-time
 * - Hover shows subtle pulse effect
 */

interface RouteSelectionMarkersProps {
  map: MapLibreMap | null
  startLat: string
  startLon: string
  endLat: string
  endLon: string
  routePresent: boolean
  onStartLocationChange?: (lat: number, lon: number) => void
  onEndLocationChange?: (lat: number, lon: number) => void
}

export function RouteSelectionMarkers({ 
  map, 
  startLat, 
  startLon, 
  endLat, 
  endLon, 
  routePresent,
  onStartLocationChange,
  onEndLocationChange
}: RouteSelectionMarkersProps) {
  const isDraggingRef = useRef<'start' | 'end' | null>(null)
  const lastCoordsRef = useRef<{ startLat: string, startLon: string, endLat: string, endLon: string } | null>(null)
  
  useEffect(() => {
    if (!map) return
    
    // Wait for map to be fully loaded before proceeding
    if (!map.isStyleLoaded()) {
      const onStyleLoad = () => {
        // Re-trigger effect by forcing a tiny update
        map.off('styledata', onStyleLoad)
      }
      map.on('styledata', onStyleLoad)
      return
    }

    const startSourceId = 'route-pick-start-src'
    const endSourceId = 'route-pick-end-src'
    const startLayerId = 'route-pick-start'
    const endLayerId = 'route-pick-end'

    const removeAll = () => {
      try {
        // Always check map exists before any map method calls
        if (!map || !map.isStyleLoaded()) return
        if (typeof (map as any).getLayer !== 'function') return
        if (map.getLayer(startLayerId)) map.removeLayer(startLayerId)
        if (map.getLayer(endLayerId)) map.removeLayer(endLayerId)
        if (map.getSource(startSourceId)) map.removeSource(startSourceId)
        if (map.getSource(endSourceId)) map.removeSource(endSourceId)
      } catch {}
    }

    // If a full route is being displayed, hide pick markers to avoid duplicates
    if (routePresent) {
      removeAll()
      return
    }

    const startLatNum = parseFloat(startLat)
    const startLonNum = parseFloat(startLon)
    const endLatNum = parseFloat(endLat)
    const endLonNum = parseFloat(endLon)

    // Check if coordinates have actually changed to avoid unnecessary updates
    const coordsChanged = !lastCoordsRef.current || 
      lastCoordsRef.current.startLat !== startLat ||
      lastCoordsRef.current.startLon !== startLon ||
      lastCoordsRef.current.endLat !== endLat ||
      lastCoordsRef.current.endLon !== endLon

    // Update ref with current coordinates
    if (coordsChanged) {
      lastCoordsRef.current = { startLat, startLon, endLat, endLon }
    }

    // START marker
    if (!isNaN(startLatNum) && !isNaN(startLonNum) && startLat && startLon) {
      if (!map || !map.isStyleLoaded()) return // Safety check
      const startData = {
        type: 'Feature',
        properties: {},
        geometry: { type: 'Point', coordinates: [startLonNum, startLatNum] }
      }

      try {
        if (!map.getSource(startSourceId)) {
          map.addSource(startSourceId, { type: 'geojson', data: startData as any })
        } else if (coordsChanged) {
          // Only update data if coordinates actually changed
          const src: any = map.getSource(startSourceId)
          src.setData(startData)
        }
      } catch (e) {
        return // Map not ready
      }

      if (!map.getLayer(startLayerId)) {
        map.addLayer({
          id: startLayerId,
          type: 'circle',
          source: startSourceId,
          paint: {
            'circle-radius': 10,
            'circle-color': '#10b981',
            'circle-stroke-width': 3,
            'circle-stroke-color': '#ffffff'
          }
        })
      }
    } else {
      if (map && typeof (map as any).getLayer === 'function' && map.getLayer(startLayerId)) map.removeLayer(startLayerId)
      if (map && typeof (map as any).getSource === 'function' && map.getSource(startSourceId)) map.removeSource(startSourceId)
    }

    // END marker
    if (!isNaN(endLatNum) && !isNaN(endLonNum) && endLat && endLon) {
      if (!map || !map.isStyleLoaded()) return // Safety check
      const endData = {
        type: 'Feature',
        properties: {},
        geometry: { type: 'Point', coordinates: [endLonNum, endLatNum] }
      }

      try {
        if (!map.getSource(endSourceId)) {
          map.addSource(endSourceId, { type: 'geojson', data: endData as any })
        } else if (coordsChanged) {
          // Only update data if coordinates actually changed
          const src: any = map.getSource(endSourceId)
          src.setData(endData)
        }
      } catch (e) {
        return // Map not ready
      }

      if (!map.getLayer(endLayerId)) {
        map.addLayer({
          id: endLayerId,
          type: 'circle',
          source: endSourceId,
          paint: {
            'circle-radius': 10,
            'circle-color': '#ef4444',
            'circle-stroke-width': 3,
            'circle-stroke-color': '#ffffff'
          }
        })
      }
    } else {
      if (map && typeof (map as any).getLayer === 'function' && map.getLayer(endLayerId)) map.removeLayer(endLayerId)
      if (map && typeof (map as any).getSource === 'function' && map.getSource(endSourceId)) map.removeSource(endSourceId)
    }

    // Dragging functionality - enable when route not calculated yet
    if (!routePresent) {
      // Mouse down on markers - start dragging
      const onMouseDown = (e: any) => {
        if (e.features && e.features.length > 0) {
          const layerId = e.features[0].layer.id
          if (layerId === startLayerId) {
            isDraggingRef.current = 'start'
            map?.getCanvas()?.style && (map.getCanvas().style.cursor = 'grabbing')
            e.preventDefault()
          } else if (layerId === endLayerId) {
            isDraggingRef.current = 'end'
            map?.getCanvas()?.style && (map.getCanvas().style.cursor = 'grabbing')
            e.preventDefault()
          }
        }
      }

      // Mouse move - update marker position while dragging
      const onMouseMove = (e: any) => {
        if (isDraggingRef.current) {
          const { lng, lat } = e.lngLat
          
          if (isDraggingRef.current === 'start') {
            onStartLocationChange?.(lat, lng)
          } else if (isDraggingRef.current === 'end') {
            onEndLocationChange?.(lat, lng)
          }
        }
      }

      // Mouse up - stop dragging
      const onMouseUp = () => {
        if (isDraggingRef.current) {
          isDraggingRef.current = null
          map?.getCanvas()?.style && (map.getCanvas().style.cursor = '')
        }
      }

      // Hover cursor change
      const onMouseEnter = () => {
        map?.getCanvas()?.style && (map.getCanvas().style.cursor = 'grab')
      }

      const onMouseLeave = () => {
        if (!isDraggingRef.current) {
          map?.getCanvas()?.style && (map.getCanvas().style.cursor = '')
        }
      }

      // Attach listeners to both marker layers
      if (map && typeof (map as any).getLayer === 'function' && map.getLayer(startLayerId)) {
        map.on('mousedown', startLayerId, onMouseDown)
        map.on('mouseenter', startLayerId, onMouseEnter)
        map.on('mouseleave', startLayerId, onMouseLeave)
      }
      if (map && typeof (map as any).getLayer === 'function' && map.getLayer(endLayerId)) {
        map.on('mousedown', endLayerId, onMouseDown)
        map.on('mouseenter', endLayerId, onMouseEnter)
        map.on('mouseleave', endLayerId, onMouseLeave)
      }

      // Global listeners for drag and release
      map.on('mousemove', onMouseMove)
      map.on('mouseup', onMouseUp)

      // Cleanup drag listeners
      return () => {
        try {
          if (!map) return
          if (typeof (map as any).getLayer === 'function' && map.getLayer(startLayerId)) {
            map.off('mousedown', startLayerId, onMouseDown)
            map.off('mouseenter', startLayerId, onMouseEnter)
            map.off('mouseleave', startLayerId, onMouseLeave)
          }
          if (typeof (map as any).getLayer === 'function' && map.getLayer(endLayerId)) {
            map.off('mousedown', endLayerId, onMouseDown)
            map.off('mouseenter', endLayerId, onMouseEnter)
            map.off('mouseleave', endLayerId, onMouseLeave)
          }
          map.off('mousemove', onMouseMove)
          map.off('mouseup', onMouseUp)
          removeAll()
        } catch {}
      }
    } else {
      // Cleanup on unmount
      return () => removeAll()
    }
  }, [map, startLat, startLon, endLat, endLon, routePresent, onStartLocationChange, onEndLocationChange])

  return null
}


