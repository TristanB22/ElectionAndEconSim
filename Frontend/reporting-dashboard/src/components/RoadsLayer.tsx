import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { log } from '../config/log'
import { Map as MapLibreMap, Popup } from 'maplibre-gl'
import { usePopupManager } from '../hooks/usePopupManager'
import { createBaseModal, BaseModalProps } from './BaseMapModal'
import { SelectedItem } from './InfoSidebar'
import { API_ENDPOINTS } from '../config/api'
const WINDOW_SESSION_ID = (() => {
  try {
    const key = 'reportingWindowSessionId'
    let id = sessionStorage.getItem(key)
    if (!id) {
      id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
      sessionStorage.setItem(key, id)
    }
    return id
  } catch {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
  }
})()

type RoadsLayerProps = {
  map: MapLibreMap | null
  onItemSelect?: (item: SelectedItem) => void
  showBoundaries?: boolean
  disableInteraction?: boolean
  onLoadingChange?: (loading: boolean) => void
  enabled?: boolean
}

type RoadFeature = {
  type: 'Feature'
  properties: {
    osm_id: number
    name?: string
    highway?: string
    ref?: string
    oneway?: string
    maxspeed?: string
    bridge?: string
    tunnel?: string
    surface?: string
    lanes?: string
    layer?: string
    access?: string
    tags?: Record<string, any>
    source?: string
  }
  geometry: {
    type: 'LineString' | 'MultiLineString'
    coordinates: any
  }
}

const SOURCE_ID = 'ws-roads-src'
const LAYER_ID = 'ws-roads-line'
const LAYER_CASING_ID = 'ws-roads-casing'

const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes
const roadDataCache = new Map<string, { data: any; timestamp: number }>()

export default function RoadsLayer({ map, onItemSelect, showBoundaries = true, disableInteraction = false, onLoadingChange, enabled = true }: RoadsLayerProps) {
  const [bounds, setBounds] = useState<[number, number, number, number] | null>(null)
  const [zoom, setZoom] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentRoadData, setCurrentRoadData] = useState<any>(null) // Current visible data
  const { showPopup, closeCurrentPopup } = usePopupManager()
  const popup = useRef<Popup | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const fetchTimeoutRef = useRef<number | null>(null)
  const currentHighlightedRoad = useRef<string | null>(null)
  // Keep a stable reference to the latest road data to avoid
  // re-creating callbacks when data updates (prevents re-fetch loops)
  const currentRoadDataRef = useRef<any>(null)

  // Report loading state changes to parent
  useEffect(() => {
    onLoadingChange?.(loading)
  }, [loading, onLoadingChange])

  // Track map state and close popups on movement
  useEffect(() => {
    if (!map) return
    
    // Close popup immediately when map starts moving
    const onMoveStart = () => {
      if (popup.current) {
        popup.current.remove()
        popup.current = null
      }
      closeCurrentPopup()
    }
    
    const onMoveEnd = () => {
      try {
        const z = Math.floor(map.getZoom())
        const b = map.getBounds()
        setZoom(z)
        setBounds([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()])
        
        // Close any open road popup when map moves/zooms
        if (popup.current) {
          popup.current.remove()
          popup.current = null
        }
        closeCurrentPopup()
      } catch (e) {}
    }
    
    // Wait for map to be fully loaded before setting initial state
    const onMapLoad = () => {
      // Ensure map has valid dimensions before calculating bounds
      const container = map.getContainer()
      if (container && container.offsetWidth > 0 && container.offsetHeight > 0) {
        onMoveEnd()
      }
    }
    
    if (map.isStyleLoaded() && map.loaded()) {
      onMapLoad()
    } else {
      map.once('load', onMapLoad)
    }
    
    map.on('movestart', onMoveStart)
    map.on('moveend', onMoveEnd)
    map.on('resize', onMoveEnd) // Handle screen size changes
    
    return () => { 
      map.off('movestart', onMoveStart)
      map.off('moveend', onMoveEnd)
      map.off('resize', onMoveEnd)
      map.off('load', onMapLoad)
    }
  }, [map, closeCurrentPopup])

  // Show layer if either roads or boundaries are enabled at zoom >=6
  const shouldShow = (enabled || showBoundaries) && zoom >= 6

  const cacheKeyFor = (
    bbox: [number, number, number, number],
    z: number,
    includeBoundaries: boolean,
    includeExcluded: boolean
  ) => `${z}:${includeBoundaries ? 1 : 0}:${includeExcluded ? 1 : 0}:${bbox.map(v => v.toFixed(3)).join(',')}`

  const addOrUpdateLayers = useCallback((data: any) => {
    if (!map || !map.isStyleLoaded()) return

    if (!map.getSource(SOURCE_ID)) {
      map.addSource(SOURCE_ID, { type: 'geojson', data })
    } else {
      (map.getSource(SOURCE_ID) as any).setData(data)
    }
    
    // Update current data state (and stable ref)
    setCurrentRoadData(data)
    currentRoadDataRef.current = data
    
    // Reset hover state when data changes to prevent stale highlights
    currentHighlightedRoad.current = null

    // Determine a safe insertion point: put roads before POI points if that layer exists,
    // otherwise just add to the top to avoid failing on first load before POIs are added.
    const beforeId = map.getLayer('frontend-points') ? 'frontend-points' : undefined

    // Bottom casing for contrast
    if (!map.getLayer(LAYER_CASING_ID)) {
      map.addLayer({
        id: LAYER_CASING_ID,
        type: 'line',
        source: SOURCE_ID,
        paint: {
          'line-color': '#1f2937', // gray-800
          'line-width': [
            'interpolate', ['linear'], ['zoom'],
            10, 1.5,
            12, 2,
            14, 3,
            16, 4
          ],
          'line-opacity': 0.35
        }
      }, beforeId as any)
    }

    if (!map.getLayer(LAYER_ID)) {
      map.addLayer({
        id: LAYER_ID,
        type: 'line',
        source: SOURCE_ID,
        paint: {
          // Color boundaries by border_type, roads by highway class
          'line-color': [
            'case',
            // If no highway property, it's a boundary - color by border_type
            ['!', ['has', 'highway']],
            [
              'case',
              // Check for border_type in tags (need to parse the tags JSON string)
              ['has', 'border_type'],
              [
                'match', ['get', 'border_type'],
                'country', '#dc2626', // red-600 for countries
                'state', '#8b5cf6', // violet-500 for states
                'county', '#ec4899', // pink-500 for counties
                'city', '#d946ef', // fuchsia-500 for cities
                'town', '#a855f7', // purple-500 for towns
                'municipality', '#06b6d4', // cyan-500 for municipalities
                'province', '#6366f1', // indigo-500 for provinces
                'district', '#14b8a6', // teal-500 for districts
                'region', '#10b981', // emerald-500 for regions
                /* default */ '#9ca3af' // gray-400 for unspecified boundaries
              ],
              // No border_type, use gray
              '#9ca3af'
            ],
            // Otherwise color by highway class
            [
              'match', ['get', 'highway'],
              'motorway', '#f59e0b',
              'trunk', '#f59e0b',
              'primary', '#fbbf24',
              'secondary', '#fde047',
              'tertiary', '#9ca3af',
              'residential', '#9ca3af',
              'unclassified', '#9ca3af',
              /* default */ '#9ca3af'
            ]
          ],
          // Width by class and zoom - increased for better hit detection
          'line-width': [
            'interpolate', ['linear'], ['zoom'],
            6, [
              'case',
              ['!', ['has', 'highway']], 2.0, // Boundaries at low zoom
              ['in', ['get', 'highway'], ['literal', ['motorway','trunk']]], 2.0,
              ['in', ['get', 'highway'], ['literal', ['primary']]], 1.5,
              1.0
            ],
            10, [
              'case',
              ['!', ['has', 'highway']], 2.5, // Boundaries at medium zoom
              ['in', ['get', 'highway'], ['literal', ['motorway','trunk']]], 3.0,
              ['in', ['get', 'highway'], ['literal', ['primary']]], 2.5,
              ['in', ['get', 'highway'], ['literal', ['secondary','tertiary']]], 2.0,
              1.5
            ],
            13, [
              'case',
              ['!', ['has', 'highway']], 3.0, // Boundaries at high zoom
              ['in', ['get', 'highway'], ['literal', ['motorway','trunk']]], 5.0,
              ['in', ['get', 'highway'], ['literal', ['primary']]], 4.0,
              ['in', ['get', 'highway'], ['literal', ['secondary','tertiary']]], 3.0,
              2.5
            ]
          ],
          'line-opacity': 0.9
        }
      }, beforeId as any)
    }

    // Add invisible hit detection layer with larger hit box
    if (!map.getLayer('ws-roads-hit')) {
      map.addLayer({
        id: 'ws-roads-hit',
        type: 'line',
        source: SOURCE_ID,
        paint: {
          'line-color': 'transparent',
          'line-width': [
            'interpolate', ['linear'], ['zoom'],
            10, 8.0,  // Much larger hit box
            12, 12.0,
            14, 16.0,
            16, 20.0
          ],
          'line-opacity': 0
        }
      }, beforeId as any)
    }

    // Add hover layer for highlighting
    if (!map.getLayer('ws-roads-hover')) {
      map.addLayer({
        id: 'ws-roads-hover',
        type: 'line',
        source: SOURCE_ID,
        paint: {
          'line-color': '#3b82f6',
          'line-width': [
            'interpolate', ['linear'], ['zoom'],
            10, 2.5,
            12, 3.5,
            14, 5.5,
            16, 7.5
          ],
          'line-opacity': 0
        },
        filter: ['==', ['get', 'osm_id'], '']
      }, beforeId as any)
    }

    // Filter logic: roads have 'highway' property, boundaries don't
    // Combine enabled (roads) and showBoundaries to determine what to show
    let filter: any = null
    if (enabled && showBoundaries) {
      // Show both roads and boundaries
      filter = null
    } else if (enabled && !showBoundaries) {
      // Show only roads
      filter = ['has', 'highway']
    } else if (!enabled && showBoundaries) {
      // Show only boundaries
      filter = ['!', ['has', 'highway']]
    }
    
    if (map.getLayer(LAYER_ID)) {
      map.setFilter(LAYER_ID, filter as any)
    }
    if (map.getLayer(LAYER_CASING_ID)) {
      map.setFilter(LAYER_CASING_ID, filter as any)
    }
    if (map.getLayer('ws-roads-hit')) {
      map.setFilter('ws-roads-hit', filter as any)
    }
    if (map.getLayer('ws-roads-hover')) {
      // Reset hover layer to show nothing when data changes
      map.setFilter('ws-roads-hover', ['==', ['get', 'osm_id'], ''])
      map.setPaintProperty('ws-roads-hover', 'line-opacity', 0)
    }
  }, [map, showBoundaries, enabled])

  useEffect(() => {
    if (!map) return
    // Filter logic: roads have 'highway' property, boundaries don't
    // Combine enabled (roads) and showBoundaries to determine what to show
    let filter: any = null
    if (enabled && showBoundaries) {
      // Show both roads and boundaries
      filter = null
    } else if (enabled && !showBoundaries) {
      // Show only roads
      filter = ['has', 'highway']
    } else if (!enabled && showBoundaries) {
      // Show only boundaries
      filter = ['!', ['has', 'highway']]
    }
    
    if (map.getLayer(LAYER_ID)) map.setFilter(LAYER_ID, filter as any)
    if (map.getLayer(LAYER_CASING_ID)) map.setFilter(LAYER_CASING_ID, filter as any)
    if (map.getLayer('ws-roads-hit')) map.setFilter('ws-roads-hit', filter as any)
    if (map.getLayer('ws-roads-hover')) {
      // Reset hover layer to show nothing when filter changes
      map.setFilter('ws-roads-hover', ['==', ['get', 'osm_id'], ''])
      map.setPaintProperty('ws-roads-hover', 'line-opacity', 0)
      currentHighlightedRoad.current = null
    }
  }, [map, showBoundaries, enabled])

  const removeLayers = useCallback(() => {
    if (!map || !map.getStyle()) return
    
    try {
      if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID)
      if (map.getLayer(LAYER_CASING_ID)) map.removeLayer(LAYER_CASING_ID)
      if (map.getLayer('ws-roads-hover')) map.removeLayer('ws-roads-hover')
      if (map.getLayer('ws-roads-hit')) map.removeLayer('ws-roads-hit')
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID)
    } catch (error) {
      // Map might be removed or style not loaded yet
      log.warn('Error removing road layers:', error)
    }
  }, [map])

  // Smart caching: filter current data to new bounds while fetching
  const filterCurrentDataToBounds = useCallback((currentData: any, newBounds: [number, number, number, number]) => {
    if (!currentData || !currentData.features) return currentData
    
    const [minLon, minLat, maxLon, maxLat] = newBounds
    const filteredFeatures = currentData.features.filter((feature: any) => {
      if (!feature.geometry || !feature.geometry.coordinates) return false
      
      // For LineString, check if any coordinate is within bounds
      if (feature.geometry.type === 'LineString') {
        return feature.geometry.coordinates.some((coord: [number, number]) => {
          const [lon, lat] = coord
          return lon >= minLon && lon <= maxLon && lat >= minLat && lat <= maxLat
        })
      }
      
      // For MultiLineString, check if any line has any coordinate within bounds
      if (feature.geometry.type === 'MultiLineString') {
        return feature.geometry.coordinates.some((line: [number, number][]) => 
          line.some((coord: [number, number]) => {
            const [lon, lat] = coord
            return lon >= minLon && lon <= maxLon && lat >= minLat && lat <= maxLat
          })
        )
      }
      
      return false
    })
    
    return {
      ...currentData,
      features: filteredFeatures
    }
  }, [])

  // Fetch roads with smart caching
  const fetchRoads = useCallback((bbox: [number, number, number, number], z: number) => {
    if (abortRef.current) abortRef.current.abort()
    if (!shouldShow) {
      removeLayers()
      setCurrentRoadData(null)
      return
    }
    const includeExcluded = z >= 12
    const includeBoundaries = Boolean(showBoundaries)
    const key = cacheKeyFor(bbox, z, includeBoundaries, includeExcluded)
    const now = Date.now()
    const cached = roadDataCache.get(key)
    
    // If we have cached data, use it immediately
    if (cached && (now - cached.timestamp) < CACHE_TTL_MS) {
      addOrUpdateLayers(cached.data)
      return
    }

    // If we have current data, filter it to new bounds and show while fetching
    const existingData = currentRoadDataRef.current
    if (existingData) {
      const filteredData = filterCurrentDataToBounds(existingData, bbox)
      if (filteredData.features.length > 0) {
        addOrUpdateLayers(filteredData)
      }
    }

    abortRef.current = new AbortController()
    const [minLon, minLat, maxLon, maxLat] = bbox
    const qs = new URLSearchParams({
      min_lat: String(minLat),
      min_lon: String(minLon),
      max_lat: String(maxLat),
      max_lon: String(maxLon),
      zoom: String(z),
      include_boundaries: includeBoundaries ? 'true' : 'false',
      include_excluded: includeExcluded ? 'true' : 'false'
    })

    setLoading(true)
    setError(null)
    fetch(`${API_ENDPOINTS.ROADS_SPATIAL}?${qs.toString()}`, {
      signal: abortRef.current.signal,
      headers: { 'X-Client-Session': WINDOW_SESSION_ID }
    })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(json => {
        const data = json && json.type ? json : { type: 'FeatureCollection', features: [] }
        roadDataCache.set(key, { data, timestamp: Date.now() })
        addOrUpdateLayers(data)
      })
      .catch(err => {
        if (err?.name === 'AbortError') return
        setError(err?.message || 'Failed to load roads')
      })
      .finally(() => {
        if (!abortRef.current?.signal.aborted) setLoading(false)
      })
  }, [addOrUpdateLayers, removeLayers, shouldShow, filterCurrentDataToBounds, showBoundaries])

  // Debounce fetching
  useEffect(() => {
    if (!bounds) return
    
    // Remove layers if neither roads nor boundaries should be shown
    if (!enabled && !showBoundaries) {
      removeLayers()
      setCurrentRoadData(null)
      return
    }
    
    // If out of scope, clear any lingering layers/sources immediately
    if (!shouldShow) {
      removeLayers()
      setCurrentRoadData(null)
      return
    }
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current)
    fetchTimeoutRef.current = setTimeout(() => fetchRoads(bounds, zoom), 300)
    return () => { if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current) }
  }, [bounds, zoom, shouldShow, fetchRoads, enabled, showBoundaries, removeLayers])

  useEffect(() => {
    if (!map) return
    const handleForceRefresh = () => {
      if (!shouldShow) return
      const activeBounds =
        bounds ??
        (() => {
          try {
            const b = map.getBounds()
            return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] as [number, number, number, number]
          } catch {
            return null
          }
        })()
      if (!activeBounds) return
      fetchRoads(activeBounds, zoom)
    }

    map.on('force-refresh-roads' as any, handleForceRefresh)
    return () => {
      map.off('force-refresh-roads' as any, handleForceRefresh)
    }
  }, [map, bounds, fetchRoads, shouldShow, zoom])


  // Simple, fast highlighting function - no complex logic, just immediate response
  const highlightRoad = useCallback((e: any) => {
    if (!map || !map.getLayer('ws-roads-hit')) return
    
    // Check if POI is being hovered - if so, don't highlight roads
    const poiFeatures = map.getLayer('frontend-points') ? map.queryRenderedFeatures(e.point, { layers: ['frontend-points'] }) : []
    if (poiFeatures && poiFeatures.length > 0) {
      // POI is being hovered, remove road highlight
      if (currentHighlightedRoad.current !== null) {
        map.setPaintProperty('ws-roads-hover', 'line-opacity', 0)
        currentHighlightedRoad.current = null
      }
      return
    }
    
    // Get the first road feature under the cursor (MapLibre will handle the rest)
    const features = map.queryRenderedFeatures(e.point, { layers: ['ws-roads-hit'] })
    
    if (features.length === 0) {
      // No roads under cursor, remove highlight
      if (currentHighlightedRoad.current !== null) {
        map.setPaintProperty('ws-roads-hover', 'line-opacity', 0)
        currentHighlightedRoad.current = null
      }
      return
    }
    
    // Get the OSM ID of the first road (MapLibre's queryRenderedFeatures already orders by distance)
    const osmId = features[0].properties?.osm_id
    
    // Only update if the highlighted road has changed
    if (osmId !== currentHighlightedRoad.current) {
      if (osmId) {
        map.setFilter('ws-roads-hover', ['==', ['get', 'osm_id'], osmId])
        map.setPaintProperty('ws-roads-hover', 'line-opacity', 0.8)
      } else {
        map.setPaintProperty('ws-roads-hover', 'line-opacity', 0)
      }
      currentHighlightedRoad.current = osmId
    }
  }, [map])

  // Hover interactions for roads - with POI prioritization and sampled highlighting
  useEffect(() => {
    if (!map) return

    let lastMousePosition: { point: any } | null = null
    let highlightInterval: number | null = null
    let isMouseOverRoads = false

    const onMouseEnter = (e: any) => {
      map.getCanvas().style.cursor = 'pointer'
      isMouseOverRoads = true
      lastMousePosition = { point: e.point }
      
      // Start sampling mouse position every 100ms
      if (highlightInterval) clearInterval(highlightInterval)
      highlightInterval = setInterval(() => {
        if (lastMousePosition && isMouseOverRoads) {
          highlightRoad({ point: lastMousePosition.point })
        }
      }, 50)
      
      // Immediate highlight on enter
      highlightRoad(e)
    }

    const onMouseLeave = () => {
      map.getCanvas().style.cursor = ''
      isMouseOverRoads = false
      lastMousePosition = null
      
      // Clear the sampling interval
      if (highlightInterval) {
        clearInterval(highlightInterval)
        highlightInterval = null
      }
      
      // Remove highlight
      map.setPaintProperty('ws-roads-hover', 'line-opacity', 0)
      currentHighlightedRoad.current = null
    }

    const onMouseMove = (e: any) => {
      // Update the last known mouse position for sampling
      if (isMouseOverRoads) {
        lastMousePosition = { point: e.point }
      }
    }

    map.on('mouseenter', 'ws-roads-hit', onMouseEnter)
    map.on('mousemove', 'ws-roads-hit', onMouseMove)
    map.on('mouseleave', 'ws-roads-hit', onMouseLeave)

    return () => {
      map.off('mouseenter', 'ws-roads-hit', onMouseEnter)
      map.off('mousemove', 'ws-roads-hit', onMouseMove)
      map.off('mouseleave', 'ws-roads-hit', onMouseLeave)
      
      // Clean up interval
      if (highlightInterval) {
        clearInterval(highlightInterval)
        highlightInterval = null
      }
    }
  }, [map, highlightRoad])

  // Helper function to find the closest point on a road line to the click point
  const findClosestPointOnRoad = (clickPoint: { lng: number; lat: number }, roadFeature: any) => {
    if (!roadFeature.geometry || !roadFeature.geometry.coordinates) {
      return clickPoint
    }

    const coordinates = roadFeature.geometry.coordinates
    let closestPoint = clickPoint
    let minDistance = Infinity

    // Handle both LineString and MultiLineString
    const lines = roadFeature.geometry.type === 'MultiLineString' ? coordinates : [coordinates]
    
    for (const line of lines) {
      for (let i = 0; i < line.length - 1; i++) {
        const p1 = line[i]
        const p2 = line[i + 1]
        
        // Find closest point on line segment
        const closest = findClosestPointOnLineSegment(clickPoint, p1, p2)
        const distance = Math.sqrt(
          Math.pow(closest.lng - clickPoint.lng, 2) + Math.pow(closest.lat - clickPoint.lat, 2)
        )
        
        if (distance < minDistance) {
          minDistance = distance
          closestPoint = closest
        }
      }
    }

    return closestPoint
  }

  // Helper function to find closest point on a line segment
  const findClosestPointOnLineSegment = (point: { lng: number; lat: number }, p1: [number, number], p2: [number, number]) => {
    const A = point.lng - p1[0]
    const B = point.lat - p1[1]
    const C = p2[0] - p1[0]
    const D = p2[1] - p1[1]

    const dot = A * C + B * D
    const lenSq = C * C + D * D
    
    if (lenSq === 0) return { lng: p1[0], lat: p1[1] }
    
    const param = dot / lenSq
    
    let xx, yy
    if (param < 0) {
      xx = p1[0]
      yy = p1[1]
    } else if (param > 1) {
      xx = p2[0]
      yy = p2[1]
    } else {
      xx = p1[0] + param * C
      yy = p1[1] + param * D
    }
    
    return { lng: xx, lat: yy }
  }

  // REMOVED: All click interaction moved to Map.tsx global handler
  // This prevents MapLibre listener registry corruption

  // Handle escape key to close popup
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (popup.current) {
          popup.current.remove()
          popup.current = null
        }
        closeCurrentPopup()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [closeCurrentPopup])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (popup.current) { popup.current.remove(); popup.current = null }
      removeLayers()
      if (abortRef.current) abortRef.current.abort()
    }
  }, [removeLayers])

  // Optional: small loading/error indicator
  if (error) {
    return (
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
        Roads: {error}
      </div>
    )
  }
  if (loading && shouldShow) {
    return (
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 bg-black/50 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
        Loading roads…
      </div>
    )
  }
  return null
}
