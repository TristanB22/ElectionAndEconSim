import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import axios from 'axios'
import { log } from '../config/log'
import { Map as MapLibreMap } from 'maplibre-gl'
import { TopBar } from '../components/TopBar'
import { useSimulationId } from '../hooks/useSimulationId'
import { LeftNav } from '../components/LeftNav'
import MapBase from '../components/MapBase'
import FrontendHeatmapLayer from '../components/FrontendHeatmapLayer'
import RoadsLayer from '../components/RoadsLayer'
import { POIDetailsDrawer } from '../components/drawers/POIDetailsDrawer'
import { RouteLayer } from '../components/routing/RouteLayer'
import { RoutePlannerPanel } from '../components/routing/RoutePlannerPanel'
import { RouteOverviewDrawer } from '../components/drawers/RouteOverviewDrawer'
import { RouteSelectionMarkers } from '../components/routing/RouteSelectionMarkers'
import { ToastNotification, useToasts } from '../components/ToastNotification'
import { AgentLayer } from '../components/agents/AgentLayer'
import { SimulationTimeline } from '../components/simulation/SimulationTimeline'
import { Settings as SettingsIcon, Navigation, Search, Target } from 'lucide-react'
import { LAYOUT } from '../layout'
import { API_ENDPOINTS, buildApiUrl } from '../config/api'
import { MAP_ANIMATIONS } from '../config/mapAnimations'
import type { Route } from '../types/routing'

export interface SelectedItem {
  type: 'poi' | 'road' | 'agent'
  data: any
  coordinates: [number, number]
  timestamp: number
}

export default function MapPage() {
  const [map, setMap] = useState<MapLibreMap | null>(null)
  const [mapZoom, setMapZoom] = useState<number>(0)
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null)
  const [showEntityDrawer, setShowEntityDrawer] = useState(false)
  const [settingsExpanded, setSettingsExpanded] = useState(false)
  const [pointsEnabled, setPointsEnabled] = useState(true)
  const [heatmapEnabled, setHeatmapEnabled] = useState(true)
  const [boundariesEnabled, setBoundariesEnabled] = useState(true)
  const [agentsEnabled, setAgentsEnabled] = useState(true)
  const [roadsEnabled, setRoadsEnabled] = useState(true)
  const [roadsLoading, setRoadsLoading] = useState(false)
  const [visibleAgentsCount, setVisibleAgentsCount] = useState(0)
  
  // Agent visualization state
  const [selectedDatetime, setSelectedDatetime] = useState<Date | null>(null)
  const [simulationBounds, setSimulationBounds] = useState<{
    start_datetime: string | null
    end_datetime: string | null
    current_datetime: string | null
    agent_count: number
  } | null>(null)
  
  // Routing state
  const [showRoutePlanner, setShowRoutePlanner] = useState(false)
  const [currentRoute, setCurrentRoute] = useState<Route | null>(null)
  const [showRouteDetails, setShowRouteDetails] = useState(false)
  const [waitingForMapClick, setWaitingForMapClick] = useState<'start' | 'end' | null>(null)
  const [routeStartLat, setRouteStartLat] = useState('')
  const [routeStartLon, setRouteStartLon] = useState('')
  const [routeEndLat, setRouteEndLat] = useState('')
  const [routeEndLon, setRouteEndLon] = useState('')
  
  // Search state
  const [showSearch, setShowSearch] = useState(false)
  const [searchAgentId, setSearchAgentId] = useState('')
  const [searchingAgent, setSearchingAgent] = useState(false)
  // Grace-period gate to suppress entity drawers immediately after map-pick
  const [suppressEntityOpenUntil, setSuppressEntityOpenUntil] = useState<number>(0)
  // Refs for stable, one-time global click handler
  const waitingForMapClickRef = useRef<'start' | 'end' | null>(null)
  const suppressUntilRef = useRef<number>(0)
  const routeStartLatRef = useRef(routeStartLat)
  const routeStartLonRef = useRef(routeStartLon)
  const routeEndLatRef = useRef(routeEndLat)
  const routeEndLonRef = useRef(routeEndLon)
  const agentLocationPrefetchRef = useRef<Map<string, { fetchedAt: number; locations: Array<{ latitude: number; longitude: number; [key: string]: any }>; meta: { simulationId: string; datetime: string } }>>(new Map())
  const dataIntegrityRef = useRef({
    missingPoiFrames: 0,
    missingRoadFrames: 0,
    lastPoiRefresh: 0,
    lastRoadRefresh: 0,
    poiRetryCount: 0,
    roadRetryCount: 0,
    poiCooldownUntil: 0,
    roadCooldownUntil: 0,
  })
  
  // Toast notifications
  const { toasts, addToast, dismissToast, clearAll: clearAllToasts } = useToasts()
  
  // Debug logging for selected items
  useEffect(() => {
    if (selectedItem) {
      log.debug('Selected item:', selectedItem)
    }
  }, [selectedItem])
  const { simulations, simulationId, setSimulationId, loading: simLoading, refresh: refreshSimulations } = useSimulationId()
  
  // Memoize simulations length and first ID to avoid unnecessary re-renders
  const simulationsLengthRef = useRef(0)
  const firstSimulationIdRef = useRef<string | null>(null)
  
  useEffect(() => {
    simulationsLengthRef.current = simulations.length
    firstSimulationIdRef.current = simulations.length > 0 ? simulations[0].id : null
  }, [simulations.length, simulations[0]?.id])
  
  // Track last simulationId we fetched bounds for (avoid duplicate fetches e.g., StrictMode)
  const lastBoundsSimIdRef = useRef<string | null>(null)

  // Fetch simulation bounds when simulation changes
  useEffect(() => {
    if (!simulationId) {
      setSimulationBounds(null)
      setSelectedDatetime(null)
      return
    }
    if (lastBoundsSimIdRef.current === simulationId) {
      return
    }
    
    const fetchBounds = async () => {
      try {
        const url = API_ENDPOINTS.AGENT_SIMULATION_BOUNDS(simulationId)
        const controller = new AbortController()
        const response = await fetch(url, { signal: controller.signal })
        
        if (!response.ok) {
          console.error('Failed to fetch simulation bounds:', response.statusText)
          setSimulationBounds(null)
          
          // If simulation doesn't exist (404), clear it and select the first valid one
          if (response.status === 404) {
            console.warn(`Simulation ${simulationId} not found, clearing from cache`)
            localStorage.removeItem('wsim_simulation_id')
            // Switch to the first available simulation (use refs to avoid dependency on simulations array)
            if (simulationsLengthRef.current > 0 && firstSimulationIdRef.current && firstSimulationIdRef.current !== simulationId) {
              setSimulationId(firstSimulationIdRef.current)
            }
          }
          return
        }
        
        const data = await response.json()
        setSimulationBounds(data)
        lastBoundsSimIdRef.current = simulationId
        
        // Initialize selected datetime to simulation start to ensure deterministic initial frame
        // Only set if it's different to avoid unnecessary re-renders
        const newDatetime = data.start_datetime 
          ? new Date(data.start_datetime)
          : (data.current_datetime ? new Date(data.current_datetime) : null)
        
        if (newDatetime) {
          // Only update if the datetime is actually different
          setSelectedDatetime((prev) => {
            if (!prev || prev.getTime() !== newDatetime.getTime()) {
              return newDatetime
            }
            return prev
          })
        }
      } catch (error) {
        console.error('Error fetching simulation bounds:', error)
        setSimulationBounds(null)
      }
    }
    
    fetchBounds()
  }, [simulationId])

  // Auto-center on selected item without zooming (no instruction needed)

  // Memoized callback to prevent re-renders - auto-open drawer on selection
  // BUT NOT during click mode for routing
  const handleItemSelect = useCallback((item: SelectedItem) => {
    // Block while picking route locations
    if (waitingForMapClick) {
    log.debug('[DRAWER BLOCKED] waitingForMapClick is active - ignoring item selection')
      return
    }
    // Block within short grace period after a pick to avoid late-bubbling clicks
    if (Date.now() < suppressEntityOpenUntil) {
    log.debug('[DRAWER BLOCKED] Within grace period - ignoring item selection')
      return
    }
    log.debug('[DRAWER] Opening drawer for selected item:', item)
    setSelectedItem(item)
    setShowEntityDrawer(true) // Auto-open drawer
  }, [waitingForMapClick, suppressEntityOpenUntil])
  
  // Handle agent click
  const handleAgentClick = useCallback((agentId: string) => {
    if (waitingForMapClick) {
      log.debug('[AGENT DRAWER BLOCKED] waitingForMapClick is active')
      return
    }
    if (Date.now() < suppressEntityOpenUntil) {
      log.debug('[AGENT DRAWER BLOCKED] Within grace period')
      return
    }
    log.debug('[AGENT DRAWER] Opening drawer for agent:', agentId)
    // Create agent entity for unified drawer
    const agentEntity = {
      type: 'agent' as const,
      id: agentId,
      geometry: undefined,
      properties: {},
    }
    setSelectedItem({ 
      type: 'agent', 
      data: agentEntity, 
      coordinates: [0, 0], // Will be ignored for agents
      timestamp: Date.now() 
    })
    setShowEntityDrawer(true)
  }, [waitingForMapClick, suppressEntityOpenUntil])

  const handleAgentSearch = useCallback(async () => {
    const trimmedId = searchAgentId.trim()
    if (!trimmedId) {
      addToast('Please enter an agent ID to begin search', 'warning', { 
        duration: 2600,
        metadata: {
          isAgentToast: true,
          icon: 'search'
        }
      })
      return
    }
    if (!simulationId) {
      addToast('Please select a simulation first', 'warning', { 
        duration: 2800,
        metadata: {
          isAgentToast: true,
          icon: 'search'
        }
      })
      return
    }
    if (!map) {
      addToast('Map is initializing... please wait', 'info', { 
        duration: 2600,
        metadata: {
          isAgentToast: true,
          icon: 'search'
        }
      })
      return
    }

    setSearchingAgent(true)
    try {
      const url = buildApiUrl(API_ENDPOINTS.AGENT_DETAILS(trimmedId), {
        simulation_id: simulationId || undefined,
      })
      const response = await fetch(url)

      if (!response.ok) {
        if (response.status === 404) {
          addToast('Agent not found in this simulation', 'error', { 
            duration: 3000,
            metadata: {
              isAgentToast: true,
              agentId: trimmedId,
              icon: 'search'
            }
          })
          return
        }
        throw new Error(`Failed to fetch agent: ${response.statusText}`)
      }

      const details = await response.json()
      const history = Array.isArray(details?.location_history) ? details.location_history : []

      const parseCoord = (value: any): number | null => {
        if (value === null || value === undefined) return null
        const numeric = typeof value === 'string' ? parseFloat(value) : Number(value)
        return Number.isFinite(numeric) ? numeric : null
      }

      let latitude: number | null = null
      let longitude: number | null = null

      if (history.length > 0) {
        latitude = parseCoord(history[0]?.latitude)
        longitude = parseCoord(history[0]?.longitude)
      }

      if (latitude === null || longitude === null) {
        const l2Geo = details?.l2_data?.l2_geo || {}
        latitude = parseCoord(l2Geo.latitude ?? l2Geo.Latitude)
        longitude = parseCoord(l2Geo.longitude ?? l2Geo.Longitude)
      }

      if (latitude === null || longitude === null) {
        addToast('No location data available for this agent', 'warning', { 
          duration: 3200,
          metadata: {
            isAgentToast: true,
            agentId: trimmedId,
            icon: 'search'
          }
        })
        return
      }

      const targetZoom = Math.max(Math.min(map.getZoom(), 18), 13)
      // Jump immediately to the target view to avoid loading tiles
      // along an animated flight path. Only requests tiles for the final
      // viewport, not every intermediate frame.
      map.jumpTo({
        center: [longitude, latitude],
        zoom: targetZoom,
      })

      setShowSearch(false)
      setSearchAgentId('')

      addToast(
        'Agent located successfully — navigating to position',
        'success',
        { 
          duration: 3000,
          metadata: {
            isAgentToast: true,
            agentId: trimmedId,
            coordinates: { lat: latitude, lon: longitude },
            icon: 'navigation'
          }
        }
      )

      handleAgentClick(trimmedId)
    } catch (error) {
      console.error('Error locating agent', error)
      addToast('Search failed — please try again', 'error', { 
        duration: 3200,
        metadata: {
          isAgentToast: true,
          agentId: trimmedId,
          icon: 'search'
        }
      })
    } finally {
      setSearchingAgent(false)
    }
  }, [searchAgentId, simulationId, map, addToast, handleAgentClick])

  // Memoized map components to prevent re-renders when search bar state changes
  const activeAgentId = useMemo(() => {
    if (selectedItem?.type === 'agent') {
      const rawId = (selectedItem.data?.id ?? selectedItem.data?.agent_id ?? null)
      return rawId ? String(rawId) : null
    }
    return null
  }, [selectedItem])

  const memoizedMapComponents = useMemo(() => {
    if (!map) return null
    
    return (
      <>
        <FrontendHeatmapLayer 
          map={map} 
          region="maine"
          onItemSelect={handleItemSelect}
          pointsEnabled={pointsEnabled}
          heatmapEnabled={heatmapEnabled}
          disableInteraction={!!waitingForMapClick}
          roadsLoading={roadsLoading}
          visibleAgentsCount={visibleAgentsCount}
        />
        <RoadsLayer 
          map={map} 
          onItemSelect={handleItemSelect}
          showBoundaries={boundariesEnabled}
          disableInteraction={!!waitingForMapClick}
          enabled={roadsEnabled}
          onLoadingChange={setRoadsLoading}
        />
        <AgentLayer
          map={map}
          simulationId={simulationId}
          selectedDatetime={selectedDatetime}
          zoom={mapZoom}
          onAgentClick={handleAgentClick}
          enabled={agentsEnabled}
          selectedAgentId={activeAgentId}
          onVisibleAgentsCountChange={setVisibleAgentsCount}
        />
      </>
    )
  }, [map, handleItemSelect, handleAgentClick, pointsEnabled, heatmapEnabled, boundariesEnabled, roadsEnabled, waitingForMapClick, simulationId, selectedDatetime, agentsEnabled, mapZoom, roadsLoading, activeAgentId, visibleAgentsCount]) // Only re-render when dependencies change

  const settingsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!settingsExpanded) return

    const handleClickOutside = (event: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setSettingsExpanded(false)
      }
    }
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSettingsExpanded(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [settingsExpanded])

  // Handle route calculation
  const handleRouteCalculated = useCallback((route: Route) => {
    setCurrentRoute(route)
    // DO NOT auto-open details drawer - user must click "View Details" button
    console.log('Route calculated:', route)
  }, [])
  
  // Handle clear route
  const handleClearRoute = useCallback(() => {
    setCurrentRoute(null)
    setShowRouteDetails(false)
    setRouteStartLat('')
    setRouteStartLon('')
    setRouteEndLat('')
    setRouteEndLon('')
    clearAllToasts()
  }, [clearAllToasts])
  
  // Handle swap route (swap start and end, then recalculate)
  const handleSwapRoute = useCallback(async () => {
    // Swap the coordinates
    const tempLat = routeStartLat
    const tempLon = routeStartLon
    setRouteStartLat(routeEndLat)
    setRouteStartLon(routeEndLon)
    setRouteEndLat(tempLat)
    setRouteEndLon(tempLon)
    
    // Show toast indicating swap
    addToast('Start and end swapped — recalculating route...', 'info', { duration: 2000 })
    
    // Auto-recalculate the route with swapped coordinates
    if (routeEndLat && routeEndLon && tempLat && tempLon) {
      try {
        const request = {
          start_lat: parseFloat(routeEndLat),
          start_lon: parseFloat(routeEndLon),
          end_lat: parseFloat(tempLat),
          end_lon: parseFloat(tempLon),
          mode: currentRoute?.mode || 'auto',
          include_directions: true,
          units: 'miles'
        }
        const response = await axios.post(API_ENDPOINTS.ROUTING_ROUTE, request)
        setCurrentRoute(response.data)
        setShowRouteDetails(true)
      } catch (err: any) {
        addToast('Failed to recalculate route', 'error', { duration: 2000 })
      }
    }
  }, [routeStartLat, routeStartLon, routeEndLat, routeEndLon, currentRoute, addToast])
  
  // Handle request for map click to fill coordinates
  const handleRequestMapClick = useCallback((type: 'start' | 'end') => {
    setWaitingForMapClick(type)
    // Cursor will be set by CSS .pick-mode class via useEffect above
    // Status shown in metallic pill in top-left (no toast needed)
  }, [])

  // Center agents on demand (uses same logic as prior auto-centering)
  const handleCenterAgents = useCallback(async () => {
    if (!map) return

    const centerDefault = () => {
      try {
        map.jumpTo({
          center: [-69.0, 44.5],
          zoom: 6,
        })
      } catch {}
    }

    try {
      if (!simulationId || !selectedDatetime || !simulationBounds || (simulationBounds.agent_count ?? 0) === 0) {
        centerDefault()
        return
      }
      const url = buildApiUrl(API_ENDPOINTS.AGENT_LOCATIONS(simulationId), { datetime: selectedDatetime.toISOString() })
      const res = await fetch(url)
      if (!res.ok) { centerDefault(); return }
      const data = await res.json()
      const locs: Array<{ latitude: number; longitude: number }> = data.locations || []
      if (!locs.length) { centerDefault(); return }

      let minLat = Infinity, minLon = Infinity, maxLat = -Infinity, maxLon = -Infinity
      let sumLat = 0, sumLon = 0
      for (const p of locs) {
        const lat = Number(p.latitude), lon = Number(p.longitude)
        if (!isFinite(lat) || !isFinite(lon)) continue
        minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat)
        minLon = Math.min(minLon, lon); maxLon = Math.max(maxLon, lon)
        sumLat += lat; sumLon += lon
      }
      if (!isFinite(minLat) || !isFinite(minLon) || !isFinite(maxLat) || !isFinite(maxLon)) { centerDefault(); return }

      const meanLat = sumLat / locs.length
      const meanLon = sumLon / locs.length

      // 5% margin
      const w = map.getCanvas().clientWidth || 1200
      const h = map.getCanvas().clientHeight || 800
      const padX = Math.round(w * 0.05)
      const padY = Math.round(h * 0.05)
      const bounds: [[number, number], [number, number]] = [[minLon, minLat], [maxLon, maxLat]]
      const cam = map.cameraForBounds(bounds as any, { padding: { top: padY, bottom: padY, left: padX, right: padX } })
      if (cam && typeof cam.zoom === 'number') {
        // Jump directly to the camera for the agent cluster; this avoids
        // loading tiles along an animated path across the map.
        map.jumpTo({
          ...cam,
          zoom: Math.min(cam.zoom, 18),
        })
      } else {
        map.jumpTo({
          center: [meanLon, meanLat],
          zoom: 10,
        })
      }
    } catch {
      centerDefault()
    }
  }, [map, simulationId, selectedDatetime, simulationBounds])

  // Use ref to track the last datetime we prefetched to avoid redundant calls
  const lastPrefetchedDatetimeRef = useRef<string | null>(null)
  
  useEffect(() => {
    if (!simulationId) return
    const effectiveDatetime =
      selectedDatetime ??
      (simulationBounds?.current_datetime ? new Date(simulationBounds.current_datetime) : null)
    if (!effectiveDatetime) return

    const isoDatetime = effectiveDatetime.toISOString()
    
    // Skip if we already prefetched this exact datetime
    if (lastPrefetchedDatetimeRef.current === isoDatetime) return
    
    const cacheKey = `${simulationId}:${isoDatetime}`
    if (agentLocationPrefetchRef.current.has(cacheKey)) {
      lastPrefetchedDatetimeRef.current = isoDatetime
      return
    }

    const controller = new AbortController()
    const prefetchAgentLocations = async () => {
      try {
        const url = buildApiUrl(API_ENDPOINTS.AGENT_LOCATIONS(simulationId), {
          datetime: isoDatetime,
        })
        const response = await fetch(url, { signal: controller.signal })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const payload = await response.json()
        if (!controller.signal.aborted) {
          agentLocationPrefetchRef.current.set(cacheKey, {
            fetchedAt: Date.now(),
            locations: Array.isArray(payload?.locations) ? payload.locations : [],
            meta: { simulationId, datetime: isoDatetime },
          })
          lastPrefetchedDatetimeRef.current = isoDatetime
          log.debug('[AGENT PREFETCH] cached agent locations', cacheKey)
        }
      } catch (error: any) {
        if (error?.name === 'AbortError') return
        log.warn('[AGENT PREFETCH] failed to load agent locations', error)
      }
    }

    prefetchAgentLocations()
    return () => controller.abort()
  }, [simulationId, selectedDatetime, simulationBounds?.current_datetime])

  useEffect(() => {
    if (!map) return
    const integrityState = dataIntegrityRef.current
    const interval = window.setInterval(() => {
      if (!map || !map.isStyleLoaded()) return
      if (map.isMoving()) {
        integrityState.missingPoiFrames = 0
        integrityState.missingRoadFrames = 0
        return
      }

      const now = Date.now()
      const zoom = map.getZoom()

      // POI integrity check
      const shouldCheckPois = pointsEnabled && zoom >= 10
      if (shouldCheckPois && now >= integrityState.poiCooldownUntil) {
        let poiLayerExists = false
        let poiFeatureCount = 0
        try {
          poiLayerExists = Boolean(map.getLayer('frontend-poi-markers'))
          if (poiLayerExists) {
            poiFeatureCount = ((map as any).queryRenderedFeatures({ layers: ['frontend-poi-markers'] }) || []).length
          }
        } catch {
          poiLayerExists = false
          poiFeatureCount = 0
        }
        const poiSource = map.getSource('frontend-poi-source')
        const needRefresh = !poiLayerExists || !poiSource || poiFeatureCount === 0

        if (needRefresh) {
          integrityState.missingPoiFrames += 1
          if (integrityState.missingPoiFrames >= 2 && now - integrityState.lastPoiRefresh > 1500) {
            ;(map as any).fire('force-refresh-pois', { detail: { reason: 'integrity-check', immediate: true } })
            integrityState.lastPoiRefresh = now
            integrityState.poiRetryCount += 1
            if (integrityState.poiRetryCount >= 3) {
              integrityState.poiCooldownUntil = now + 15000
              integrityState.poiRetryCount = 0
            }
            integrityState.missingPoiFrames = 0
          }
        } else {
          integrityState.missingPoiFrames = 0
          integrityState.poiRetryCount = 0
          integrityState.poiCooldownUntil = 0
        }
      } else if (!shouldCheckPois) {
        integrityState.missingPoiFrames = 0
      }

      // Roads integrity check
      const shouldCheckRoads = (roadsEnabled || boundariesEnabled) && zoom >= 6
      if (shouldCheckRoads && now >= integrityState.roadCooldownUntil) {
        let roadLayerExists = false
        let roadFeatureCount = 0
        try {
          roadLayerExists = Boolean(map.getLayer('ws-roads-line'))
          if (roadLayerExists) {
            roadFeatureCount = ((map as any).queryRenderedFeatures({ layers: ['ws-roads-line'] }) || []).length
          }
        } catch {
          roadLayerExists = false
          roadFeatureCount = 0
        }
        const roadSource = map.getSource('ws-roads-src')
        const needRefresh = !roadLayerExists || !roadSource || roadFeatureCount === 0

        if (needRefresh) {
          integrityState.missingRoadFrames += 1
          if (integrityState.missingRoadFrames >= 2 && now - integrityState.lastRoadRefresh > 1500) {
            ;(map as any).fire('force-refresh-roads', { detail: { reason: 'integrity-check' } })
            integrityState.lastRoadRefresh = now
            integrityState.roadRetryCount += 1
            if (integrityState.roadRetryCount >= 3) {
              integrityState.roadCooldownUntil = now + 15000
              integrityState.roadRetryCount = 0
            }
            integrityState.missingRoadFrames = 0
          }
        } else {
          integrityState.missingRoadFrames = 0
          integrityState.roadRetryCount = 0
          integrityState.roadCooldownUntil = 0
        }
      } else if (!shouldCheckRoads) {
        integrityState.missingRoadFrames = 0
      }
    }, 1000)

    return () => {
      window.clearInterval(interval)
      integrityState.missingPoiFrames = 0
      integrityState.missingRoadFrames = 0
    }
  }, [map, pointsEnabled, roadsEnabled, boundariesEnabled])

  const LayerToggle = ({
    label,
    description,
    enabled,
    onToggle
  }: {
    label: string
    description: string
    enabled: boolean
    onToggle: () => void
  }) => (
    <button
      onClick={onToggle}
      className="flex items-center justify-between w-full px-3 py-2 rounded-xl border backdrop-blur-sm transition-all duration-200"
      type="button"
      style={{
        background: 'rgba(255, 255, 255, 0.05)',
        borderColor: 'rgba(255, 255, 255, 0.1)',
      }}
    >
      <div className="text-left">
        <div className="text-sm font-semibold text-gray-200">{label}</div>
        <div className="text-[11px] text-gray-400">{description}</div>
        </div>
      <span
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          enabled ? 'bg-blue-500' : 'bg-gray-600'
        }`}
        aria-hidden="true"
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform ${
            enabled ? 'translate-x-5' : 'translate-x-1'
          }`}
        />
      </span>
    </button>
  )

  const settingsPanel = useMemo(() => (
    <div ref={settingsRef} className="absolute top-4 left-4 z-20 flex items-start gap-3">
      {/* Settings Button - Glassmorphic */}
      <div className="relative">
        <button
          type="button"
          aria-label="Toggle map settings"
          aria-expanded={settingsExpanded}
          onClick={() => {
            setSettingsExpanded(prev => !prev)
            if (!settingsExpanded) {
              setShowRoutePlanner(false)
              setShowSearch(false)
            }
          }}
          className="w-12 h-12 rounded-2xl border shadow-lg flex items-center justify-center hover:shadow-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
          style={{
            background: 'rgba(20, 22, 28, 0.55)',
            borderColor: 'rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(12px) saturate(140%)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
          }}
        >
          <SettingsIcon
            className={`w-5 h-5 transition-transform duration-300 ${
              settingsExpanded ? 'text-blue-400 rotate-90' : 'text-gray-300'
            }`}
          />
        </button>
      </div>

      {/* Route Planner Button - Glassmorphic */}
      <div className="relative">
        <button
          type="button"
          aria-label="Toggle route planner"
          title="Route Planner (or press Escape)"
          aria-expanded={showRoutePlanner}
          onClick={() => {
            setShowRoutePlanner(prev => !prev)
            if (!showRoutePlanner) {
              setSettingsExpanded(false)
              setShowSearch(false)
            }
          }}
          className="w-12 h-12 rounded-2xl border shadow-lg flex items-center justify-center hover:shadow-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
          style={{
            background: 'rgba(20, 22, 28, 0.55)',
            borderColor: 'rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(12px) saturate(140%)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
          }}
        >
          <Navigation
            className={`w-5 h-5 transition-transform duration-300 ${
              showRoutePlanner ? 'text-blue-400 rotate-45' : 'text-gray-300'
            }`}
          />
        </button>
      </div>

      {/* Search Button - Glassmorphic */}
      <div className="relative">
        <button
          type="button"
          aria-label="Toggle location search"
          title="Search Location"
          aria-expanded={showSearch}
          onClick={() => {
            setShowSearch(prev => !prev)
            if (!showSearch) {
              setSettingsExpanded(false)
              setShowRoutePlanner(false)
            }
          }}
          className="w-12 h-12 rounded-2xl border shadow-lg flex items-center justify-center hover:shadow-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
          style={{
            background: 'rgba(20, 22, 28, 0.55)',
            borderColor: 'rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(12px) saturate(140%)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
          }}
        >
          <Search
            className={`w-5 h-5 transition-transform duration-300 ${
              showSearch ? 'text-blue-400 scale-110' : 'text-gray-300'
            }`}
          />
        </button>
      </div>

      {/* Center Agents Button - Glassmorphic */}
      <div className="relative">
        <button
          type="button"
          aria-label="Center agents"
          title="Center Agents"
          onClick={handleCenterAgents}
          className="w-12 h-12 rounded-2xl border shadow-lg flex items-center justify-center hover:shadow-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
          style={{
            background: 'rgba(20, 22, 28, 0.55)',
            borderColor: 'rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(12px) saturate(140%)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
          }}
        >
          <Target
            className={`w-5 h-5 text-gray-300`}
          />
        </button>
      </div>

      {/* Settings Popout - Glassmorphic */}
      <div
        className={`absolute left-0 top-0 mt-16 w-72 origin-top-left rounded-2xl border transition-all duration-200 ${
          settingsExpanded ? 'opacity-100 scale-100 pointer-events-auto' : 'opacity-0 scale-90 pointer-events-none'
        }`}
        style={{
          background: 'rgba(20, 22, 28, 0.55)',
          borderColor: 'rgba(255, 255, 255, 0.12)',
          backdropFilter: 'blur(12px) saturate(140%)',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
        }}
      >
          <div className="relative px-4 py-4 space-y-3">
            <div>
              <p className="text-xs font-semibold text-gray-200 tracking-wide uppercase">Map Layers</p>
              <p className="text-[11px] text-gray-400">Toggle the overlays shown on the map.</p>
            </div>
            <div className="space-y-2.5">
              <LayerToggle
                label="Roads & Boundaries"
                description="Road network and administrative boundaries"
                enabled={roadsEnabled}
                onToggle={() => setRoadsEnabled(prev => !prev)}
              />
              <LayerToggle
                label="Points"
                description="Individual points of interest at close zoom"
                enabled={pointsEnabled}
                onToggle={() => setPointsEnabled(prev => !prev)}
              />
          <LayerToggle
            label="Agents"
            description="Simulation agents (zoom ≥ 8)"
            enabled={agentsEnabled}
            onToggle={() => setAgentsEnabled(prev => !prev)}
          />
            </div>
          </div>
          </div>
          
      {/* Route Planner Popout - Glassmorphic */}
      <div
        className={`absolute left-0 top-0 mt-16 w-80 origin-top-left rounded-2xl border transition-all duration-200 ${
          showRoutePlanner ? 'opacity-100 scale-100 pointer-events-auto' : 'opacity-0 scale-90 pointer-events-none'
        }`}
        style={{
          background: 'rgba(20, 22, 28, 0.55)',
          borderColor: 'rgba(255, 255, 255, 0.12)',
          backdropFilter: 'blur(12px) saturate(140%)',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
        }}
      >
        <div className="relative px-4 py-4 space-y-4">
          <div>
            <p className="text-xs font-semibold text-gray-200 tracking-wide uppercase">Route Planner</p>
            <p className="text-[11px] text-gray-400">Plan routes between locations</p>
          </div>
          
          <RoutePlannerPanel
            expanded={true}
            onToggle={() => setShowRoutePlanner(false)} // Collapse after calculation
            onRouteCalculated={handleRouteCalculated}
            onRequestMapClick={handleRequestMapClick}
            waitingForMapClick={waitingForMapClick}
            startLat={routeStartLat}
            startLon={routeStartLon}
            endLat={routeEndLat}
            endLon={routeEndLon}
            onStartLatChange={setRouteStartLat}
            onStartLonChange={setRouteStartLon}
            onEndLatChange={setRouteEndLat}
            onEndLonChange={setRouteEndLon}
            isInline={true}
            addToast={addToast}
          />
        </div>
      </div>

      {/* Search Popout - Glassmorphic */}
      <div
        className={`absolute left-0 top-0 mt-16 w-80 origin-top-left rounded-2xl border transition-all duration-200 ${
          showSearch ? 'opacity-100 scale-100 pointer-events-auto' : 'opacity-0 scale-90 pointer-events-none'
        }`}
        style={{
          background: 'rgba(20, 22, 28, 0.55)',
          borderColor: 'rgba(255, 255, 255, 0.12)',
          backdropFilter: 'blur(12px) saturate(140%)',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
        }}
      >
        <div className="relative px-4 py-4 space-y-4">
          <div>
            <p className="text-xs font-semibold text-gray-200 tracking-wide uppercase">Agent Search</p>
            <p className="text-[11px] text-gray-400">Jump to an agent&apos;s latest activity</p>
          </div>
          
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Agent ID</label>
              <input
                type="text"
                value={searchAgentId}
                onChange={(e) => setSearchAgentId(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAgentSearch()
                  }
                }}
                placeholder="e.g., L2-000123456"
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400/50 transition-all"
              />
            </div>

            <button
              onClick={() => handleAgentSearch()}
              disabled={searchingAgent}
              className={`w-full px-4 py-2.5 text-white text-sm font-semibold rounded-lg shadow-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50 ${
                searchingAgent
                  ? 'bg-blue-500/60 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-500 hover:scale-[1.02] active:scale-[0.98]'
              }`}
            >
              {searchingAgent ? 'Locating…' : 'Find Agent'}
            </button>
          </div>
        </div>
      </div>
    </div>
  ), [settingsExpanded, showRoutePlanner, showSearch, heatmapEnabled, pointsEnabled, boundariesEnabled, waitingForMapClick, handleRouteCalculated, handleRequestMapClick, routeStartLat, routeStartLon, routeEndLat, routeEndLon, searchAgentId, searchingAgent, map, addToast, handleAgentSearch])

  // Track zoom for dependent layers (no auto-centering)
  useEffect(() => {
    if (!map) return

    const onZoom = () => setMapZoom(map.getZoom())
    
    // Wait for map to be fully loaded before setting initial zoom
    const initializeZoom = () => {
      const container = map.getContainer()
      if (container && container.offsetWidth > 0 && container.offsetHeight > 0) {
        setMapZoom(map.getZoom())
      }
    }
    
    if (map.isStyleLoaded() && map.loaded()) {
      initializeZoom()
    } else {
      map.once('load', initializeZoom)
    }
    
    map.on('zoom', onZoom)
    map.on('resize', onZoom) // Update zoom on resize

    return () => {
      try { 
        map.off('zoom', onZoom)
        map.off('resize', onZoom)
        map.off('load', initializeZoom)
      } catch {}
    }
  }, [map])

  // Close settings panel when user starts moving or zooming the map
  useEffect(() => {
    if (!map) return

    const closeSettings = () => {
      if (settingsExpanded) {
        setSettingsExpanded(false)
      }
    }

    map.on('movestart', closeSettings)
    map.on('zoomstart', closeSettings)

    return () => {
      try { 
        map.off('movestart', closeSettings)
        map.off('zoomstart', closeSettings)
      } catch {}
    }
  }, [map, settingsExpanded])

  // Toggle pick-mode class on map container to force pin cursor
  useEffect(() => {
    if (!map) return
    const container = map.getContainer()
    
    if (waitingForMapClick) {
      container.classList.add('pick-mode')
    } else {
      container.classList.remove('pick-mode')
    }
    
    return () => container.classList.remove('pick-mode')
  }, [map, waitingForMapClick])

  // Handle escape key to cancel click mode, close drawers, or close route planner
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        // Priority 1: Cancel click mode
        if (waitingForMapClick) {
          setWaitingForMapClick(null)
          // Cursor will be reset by CSS .pick-mode class removal
          return
        }
        // Priority 2: Close route details drawer
        if (showRouteDetails) {
          setShowRouteDetails(false)
          return
        }
        // Priority 3: Close route planner
        if (showRoutePlanner) {
          setShowRoutePlanner(false)
          return
        }
        // Priority 4: Close entity drawer
        if (showEntityDrawer) {
          setShowEntityDrawer(false)
          setSelectedItem(null)
          return
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showEntityDrawer, showRoutePlanner, showRouteDetails, waitingForMapClick, map])

  // Keep refs in sync with state
  useEffect(() => { waitingForMapClickRef.current = waitingForMapClick }, [waitingForMapClick])
  useEffect(() => { suppressUntilRef.current = suppressEntityOpenUntil }, [suppressEntityOpenUntil])
  useEffect(() => { routeStartLatRef.current = routeStartLat }, [routeStartLat])
  useEffect(() => { routeStartLonRef.current = routeStartLon }, [routeStartLon])
  useEffect(() => { routeEndLatRef.current = routeEndLat }, [routeEndLat])
  useEffect(() => { routeEndLonRef.current = routeEndLon }, [routeEndLon])

  // One-time global click handler: handles both picking and entity selection
  useEffect(() => {
    if (!map) return

    const handleGlobalClick = (e: any) => {
      const { lng, lat } = e.lngLat || {}
      const now = Date.now()

      // Priority: route picking mode
      if (waitingForMapClickRef.current) {
        if (waitingForMapClickRef.current === 'start') {
          setRouteStartLat(lat.toFixed(6))
          setRouteStartLon(lng.toFixed(6))
    log.debug(`[ROUTE PICKER] Start location set: ${lat.toFixed(6)}, ${lng.toFixed(6)}`)
          addToast(`Start location set: ${lat.toFixed(6)}, ${lng.toFixed(6)}`, 'success')
        } else {
          setRouteEndLat(lat.toFixed(6))
          setRouteEndLon(lng.toFixed(6))
    log.debug(`[ROUTE PICKER] End location set: ${lat.toFixed(6)}, ${lng.toFixed(6)}`)
          addToast(`End location set: ${lat.toFixed(6)}, ${lng.toFixed(6)}`, 'success')
        }
        setSuppressEntityOpenUntil(now + 1000)
        setWaitingForMapClick(null)
        return
      }

      // Grace window: ignore late bubbling
      if (now < (suppressUntilRef.current || 0)) {
        return
      }

      // Not picking: act like previous layer handlers but centrally
      // Priority order: Agent > POI > Road (agents are handled by AgentLayer component)
      try {
        // First try agents (symbol layer)
        const agentLayerId = 'agent-markers'
        const agentFeatures = map.getLayer(agentLayerId) ? map.queryRenderedFeatures(e.point, { layers: [agentLayerId] }) : []
        if (agentFeatures && agentFeatures.length > 0) {
          const feature = agentFeatures[0]
          const agentId = feature.properties?.agent_id
          if (agentId) {
            handleAgentClick(agentId)
            return
          }
        }
        
        // Then try POIs (check both marker layer and old circle layer for backwards compatibility)
        const poiMarkerLayerId = 'frontend-poi-markers'
        const poiCircleLayerId = 'frontend-points'
        const poiMarkerFeatures = map.getLayer(poiMarkerLayerId) ? map.queryRenderedFeatures(e.point, { layers: [poiMarkerLayerId] }) : []
        const poiCircleFeatures = map.getLayer(poiCircleLayerId) ? map.queryRenderedFeatures(e.point, { layers: [poiCircleLayerId] }) : []
        const poiFeatures = poiMarkerFeatures.length > 0 ? poiMarkerFeatures : poiCircleFeatures
        if (poiFeatures && poiFeatures.length > 0) {
          const feature = poiFeatures[0]
          
          // Don't auto-zoom on POI click - only select and open drawer
          // Center manually using the "Center" button in the drawer
          
          setSelectedItem({ type: 'poi', data: feature, coordinates: [e.lngLat.lng, e.lngLat.lat], timestamp: now })
          setShowEntityDrawer(true)
          return
        }
        
        // Finally roads (hit-test layer) - lowest priority
        const roadHitId = 'ws-roads-hit'
        const roadFeatures = map.getLayer(roadHitId) ? map.queryRenderedFeatures(e.point, { layers: [roadHitId] }) : []
        if (roadFeatures && roadFeatures.length > 0) {
          const selectedFeature = roadFeatures[0]
          setSelectedItem({ type: 'road', data: selectedFeature, coordinates: [e.lngLat.lng, e.lngLat.lat], timestamp: now })
          setShowEntityDrawer(true)
          return
        }
        
        // Else: click on empty map closes drawer
        if (showEntityDrawer) {
          setShowEntityDrawer(false)
          setSelectedItem(null)
        }
      } catch (err) {
        log.warn('[GLOBAL CLICK HANDLER] selection error', err)
      }
    }

    map.on('click', handleGlobalClick)
    return () => { try { map.off('click', handleGlobalClick) } catch {} }
  }, [map, addToast, showEntityDrawer, handleAgentClick])
  
  // Keep POI highlighted while drawer is open
  useEffect(() => {
    if (!map) return
    
    const poiMarkerLayerIdHover = 'frontend-poi-markers-hover'
    
    const applyHighlight = () => {
      if (!map.isStyleLoaded()) return
      
      try {
        if (showEntityDrawer && selectedItem?.type === 'poi') {
          // Extract OSM ID from multiple possible locations
          const d: any = selectedItem.data || {}
          const props: any = d.properties || {}
          const tags: any = d.tags || props || {}
          const rawId: any = d.osm_id || d.id || props.osm_id || props.id || tags.osm_id || tags.id || tags['@id']
          const osmId = typeof rawId === 'string' && rawId.includes('/') ? rawId.split('/').pop() : rawId
          
          if (osmId && map.getLayer(poiMarkerLayerIdHover)) {
            // Ensure layer is visible and highlighted (override parent component visibility)
            map.setLayoutProperty(poiMarkerLayerIdHover, 'visibility', 'visible')
            map.setFilter(poiMarkerLayerIdHover, ['==', 'osm_id', osmId])
            map.setPaintProperty(poiMarkerLayerIdHover, 'icon-opacity', 1)
          }
        } else {
          // Clear highlight when drawer closes or item changes
          if (map.getLayer(poiMarkerLayerIdHover)) {
            map.setFilter(poiMarkerLayerIdHover, ['==', 'osm_id', ''])
            map.setPaintProperty(poiMarkerLayerIdHover, 'icon-opacity', 0)
          }
        }
      } catch (e) {
        // Layer might not exist yet
      }
    }
    
    // Apply immediately
    applyHighlight()
    
    // Re-apply after style/data events to maintain visibility
    const onStyleData = () => {
      if (showEntityDrawer && selectedItem?.type === 'poi') {
        setTimeout(applyHighlight, 50)
      }
    }
    
    const onData = () => {
      if (showEntityDrawer && selectedItem?.type === 'poi') {
        setTimeout(applyHighlight, 50)
      }
    }
    
    map.on('styledata', onStyleData)
    map.on('data', onData)
    
    // Also set up an interval to ensure visibility is maintained
    const intervalId = setInterval(() => {
      if (showEntityDrawer && selectedItem?.type === 'poi') {
        applyHighlight()
      }
    }, 500)
    
    return () => {
      map.off('styledata', onStyleData)
      map.off('data', onData)
      clearInterval(intervalId)
    }
  }, [map, showEntityDrawer, selectedItem])
  
  // Keep road highlighted while drawer is open
  useEffect(() => {
    if (!map) return
    
    const roadHoverLayerId = 'ws-roads-hover'
    
    const applyHighlight = () => {
      if (!map.isStyleLoaded()) return
      
      try {
        if (showEntityDrawer && selectedItem?.type === 'road') {
          // Extract OSM ID from multiple possible locations
          const d: any = selectedItem.data || {}
          const props: any = d.properties || {}
          const rawId: any = d.osm_id || d.id || props?.osm_id || props?.id
          const osmId = typeof rawId === 'string' && rawId.includes('/') ? rawId.split('/').pop() : rawId
          
          if (osmId && map.getLayer(roadHoverLayerId)) {
            // Ensure layer is visible and highlighted (override parent component visibility)
            map.setLayoutProperty(roadHoverLayerId, 'visibility', 'visible')
            map.setFilter(roadHoverLayerId, ['==', ['get', 'osm_id'], osmId])
            map.setPaintProperty(roadHoverLayerId, 'line-opacity', 0.8)
          }
        } else {
          // Clear highlight when drawer closes or item changes
          if (map.getLayer(roadHoverLayerId)) {
            map.setFilter(roadHoverLayerId, ['==', ['get', 'osm_id'], ''])
            map.setPaintProperty(roadHoverLayerId, 'line-opacity', 0)
          }
        }
      } catch (e) {
        // Layer might not exist yet
      }
    }
    
    // Apply immediately
    applyHighlight()
    
    // Re-apply after style/data events to maintain visibility
    const onStyleData = () => {
      if (showEntityDrawer && selectedItem?.type === 'road') {
        setTimeout(applyHighlight, 50)
      }
    }
    
    const onData = () => {
      if (showEntityDrawer && selectedItem?.type === 'road') {
        setTimeout(applyHighlight, 50)
      }
    }
    
    map.on('styledata', onStyleData)
    map.on('data', onData)
    
    // Also set up an interval to ensure visibility is maintained
    const intervalId = setInterval(() => {
      if (showEntityDrawer && selectedItem?.type === 'road') {
        applyHighlight()
      }
    }, 500)
    
    return () => {
      map.off('styledata', onStyleData)
      map.off('data', onData)
      clearInterval(intervalId)
    }
  }, [map, showEntityDrawer, selectedItem])

  // Keep agent highlighted while drawer is open
  useEffect(() => {
    if (!map) return

    const agentHoverLayerId = 'agent-markers-hover'

    const applyHighlight = () => {
      if (!map.isStyleLoaded()) return
      
      try {
        if (showEntityDrawer && selectedItem?.type === 'agent') {
          const agentId = selectedItem.data?.agent_id || selectedItem.data?.id
          if (agentId && map.getLayer(agentHoverLayerId)) {
            // Ensure layer is visible and highlighted (override parent component visibility)
            map.setLayoutProperty(agentHoverLayerId, 'visibility', 'visible')
            map.setFilter(agentHoverLayerId, ['==', 'agent_id', agentId])
            map.setPaintProperty(agentHoverLayerId, 'icon-opacity', 1)
          }
        } else {
          // Clear highlight when drawer closes or item changes
          if (map.getLayer(agentHoverLayerId)) {
            map.setFilter(agentHoverLayerId, ['==', 'agent_id', ''])
            map.setPaintProperty(agentHoverLayerId, 'icon-opacity', 0)
          }
        }
      } catch (e) {
        // Layer might not exist yet
      }
    }

    // Apply immediately
    applyHighlight()
    
    // Re-apply after style/data events to maintain visibility
    const onStyleData = () => {
      if (showEntityDrawer && selectedItem?.type === 'agent') {
        setTimeout(applyHighlight, 50)
      }
    }
    
    const onData = () => {
      if (showEntityDrawer && selectedItem?.type === 'agent') {
        setTimeout(applyHighlight, 50)
      }
    }
    
    map.on('styledata', onStyleData)
    map.on('data', onData)
    
    // Also set up an interval to ensure visibility is maintained
    const intervalId = setInterval(() => {
      if (showEntityDrawer && selectedItem?.type === 'agent') {
        applyHighlight()
      }
    }, 500)

    return () => {
      map.off('styledata', onStyleData)
      map.off('data', onData)
      clearInterval(intervalId)
    }
  }, [map, showEntityDrawer, selectedItem])

  // Cursor management and reticle effect
  const [reticlePos, setReticlePos] = useState<{ x: number; y: number } | null>(null)

  // Clear reticle when exiting pick mode
  useEffect(() => {
    if (!waitingForMapClick) {
      setReticlePos(null)
    }
  }, [waitingForMapClick])

  useEffect(() => {
    if (!map) return

    const canvas = map.getCanvas()
    if (!canvas) return

    const handleMouseMove = (e: any) => {
      // If in route picking mode, show crosshair and reticle
      if (waitingForMapClickRef.current) {
        canvas.style.cursor = 'crosshair'
        // Update reticle position
        const rect = canvas.getBoundingClientRect()
        setReticlePos({
          x: e.point.x + rect.left,
          y: e.point.y + rect.top
        })
        return
      } else {
        setReticlePos(null)
      }

      // Check if hovering over POI or road
      try {
        const poiMarkerFeatures = map.getLayer('frontend-poi-markers') ? map.queryRenderedFeatures(e.point, { layers: ['frontend-poi-markers'] }) : []
        const poiCircleFeatures = map.getLayer('frontend-points') ? map.queryRenderedFeatures(e.point, { layers: ['frontend-points'] }) : []
        const roadFeatures = map.getLayer('ws-roads-hit') ? map.queryRenderedFeatures(e.point, { layers: ['ws-roads-hit'] }) : []
        
        if ((poiMarkerFeatures && poiMarkerFeatures.length > 0) || (poiCircleFeatures && poiCircleFeatures.length > 0) || (roadFeatures && roadFeatures.length > 0)) {
          canvas.style.cursor = 'pointer'
        } else {
          canvas.style.cursor = ''
        }
      } catch {}
    }

    const handleMouseLeave = () => {
      // Clear reticle when cursor leaves the map
      setReticlePos(null)
      canvas.style.cursor = ''
    }

    map.on('mousemove', handleMouseMove)
    canvas.addEventListener('mouseleave', handleMouseLeave)
    
    return () => {
      try { 
        map.off('mousemove', handleMouseMove)
        canvas.removeEventListener('mouseleave', handleMouseLeave)
        setReticlePos(null)
      } catch {} 
    }
  }, [map])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // D - Open route details
      if (e.key === 'd' && currentRoute && !showRouteDetails && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const target = e.target as HTMLElement
        // Don't trigger if typing in an input
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
        e.preventDefault()
        setShowRouteDetails(true)
      }
      
      // Backspace - Clear route (with confirmation if route exists)
      if (e.key === 'Backspace' && currentRoute && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const target = e.target as HTMLElement
        // Don't trigger if typing in an input
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
        e.preventDefault()
        if (confirm('Clear current route?')) {
          handleClearRoute()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentRoute, showRouteDetails])

  return (
    <div className="fixed inset-0 overflow-hidden">
      <style>{`
        /* Prevent scrolling on the map page */
        html, body {
          overflow: hidden !important;
          height: 100% !important;
        }
        
        .poi-popup-container .maplibregl-popup-content {
          padding: 0 !important;
          border-radius: 0.75rem !important;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
          border: 1px solid rgba(229, 231, 235, 0.8) !important;
          backdrop-filter: blur(8px) !important;
          background: rgba(255, 255, 255, 0.95) !important;
        }
        .dark .poi-popup-container .maplibregl-popup-content {
          background: rgba(17, 24, 39, 0.95) !important;
          border: 1px solid rgba(55, 65, 81, 0.8) !important;
        }
        .poi-popup-container .maplibregl-popup-tip {
          /* Base arrow styles - will be overridden by dynamic CSS */
          border: none !important;
          width: 0 !important;
          height: 0 !important;
          position: absolute !important;
          z-index: 1 !important;
          margin: 0 !important;
          padding: 0 !important;
          background: none !important;
        }
        .dark .poi-popup-container .maplibregl-popup-tip {
          border: none !important;
          width: 0 !important;
          height: 0 !important;
          position: absolute !important;
          z-index: 1 !important;
          margin: 0 !important;
          padding: 0 !important;
          background: none !important;
        }
        .poi-popup-container .maplibregl-popup-close-button {
          color: rgba(107, 114, 128, 0.8) !important;
          font-size: 18px !important;
          padding: 8px !important;
          right: 8px !important;
          top: 8px !important;
        }
        .poi-popup-container .maplibregl-popup-close-button:hover {
          color: rgba(55, 65, 81, 1) !important;
        }
        .dark .poi-popup-container .maplibregl-popup-close-button:hover {
          color: rgba(209, 213, 219, 1) !important;
        }
        
        /* Modern search bar expansion with responsive width */
        .address-search-expanded {
          width: calc(100vw - 16rem - 3rem); /* Full width minus heatmap indicator and margins */
          max-width: 32rem; /* Reasonable maximum width */
          min-width: 20rem; /* Minimum usable width */
        }
        
        @media (max-width: 640px) {
          .address-search-expanded {
            width: calc(100vw - 10rem - 2rem); /* Smaller gap on mobile */
            min-width: 16rem; /* Smaller minimum on mobile */
          }
        }
        
        @media (min-width: 768px) {
          .address-search-expanded {
            width: calc(100vw - 18rem - 3rem); /* Medium screens */
          }
        }
        
        @media (min-width: 1024px) {
          .address-search-expanded {
            width: calc(100vw - 20rem - 3rem); /* Large screens */
          }
        }
        
        @media (min-width: 1280px) {
          .address-search-expanded {
            width: calc(100vw - 22rem - 3rem); /* Extra large screens */
          }
        }
      `}</style>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <TopBar
        simulationId={simulationId}
        setSimulationId={setSimulationId}
        simulationOptions={simulations.map(sim => ({
          value: sim.id,
          label: `${sim.id} — ${sim.created_at}`
        }))}
        simulationLoading={simLoading}
        onRefreshSimulations={refreshSimulations}
      />
  <LeftNav simulationId={simulationId} />

      {/* Full-width map layout with configurable spacing */}
      <div 
        className="max-w-[100vw] mx-auto overflow-hidden pt-16"
        style={{ 
          paddingLeft: LAYOUT.MAP_PAGE.LEFT_NAV_OFFSET,
          paddingRight: LAYOUT.MAP_PAGE.PADDING_X,
          paddingBottom: LAYOUT.MAP_PAGE.PADDING_Y
        }}
      >
        <div className="h-[calc(100vh-4rem)]">
          {/* Map Area - Full Width */}
          <div className="w-full h-full bg-white dark:bg-gray-900 rounded-xl shadow-lg border border-gray-200 dark:border-gray-800 p-1 relative backdrop-blur-sm bg-white/95 dark:bg-gray-900/95">
            {/* Settings and Route Planner Controls */}
            {settingsPanel}

                {/* Map */}
                <MapBase onMap={setMap} className="w-full h-full rounded-xl overflow-hidden shadow-inner" />
                {memoizedMapComponents}
            {/* Temporary start/end selection markers shown before route is calculated */}
            <RouteSelectionMarkers 
              map={map} 
              startLat={routeStartLat}
              startLon={routeStartLon}
              endLat={routeEndLat}
              endLon={routeEndLon}
              routePresent={!!currentRoute}
              onStartLocationChange={(lat, lon) => {
                setRouteStartLat(lat.toFixed(6))
                setRouteStartLon(lon.toFixed(6))
              }}
              onEndLocationChange={(lat, lon) => {
                setRouteEndLat(lat.toFixed(6))
                setRouteEndLon(lon.toFixed(6))
              }}
            />
            
            {/* Route Layer */}
            <RouteLayer 
              map={map} 
              route={currentRoute}
              emphasized={showRouteDetails}
            />

            {/* Simulation Timeline (positioned within map container for exact alignment) */}
            {simulationBounds && simulationBounds.agent_count > 0 && (
              <SimulationTimeline
                simulationId={simulationId}
                startDatetime={simulationBounds.start_datetime ? new Date(simulationBounds.start_datetime) : null}
                endDatetime={simulationBounds.end_datetime ? new Date(simulationBounds.end_datetime) : null}
                currentDatetime={selectedDatetime}
                onDatetimeChange={setSelectedDatetime}
                categoryPanelVisible={pointsEnabled || heatmapEnabled}
                timeStepMinutes={simulations.find(s => s.id === simulationId)?.time_step_minutes || 15}
                zoom={mapZoom}
              />
            )}

            {/* Route Control Toast - Top Right */}
            {currentRoute && (
              <div className="absolute top-4 right-4 z-20 animate-in fade-in slide-in-from-right-4 duration-300">
                <div className="w-64 bg-gray-900/95 backdrop-blur-xl rounded-2xl border-2 border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.1)] overflow-hidden">
                  {/* Context line */}
                  <div className="px-4 py-2 border-b border-white/10">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
                      <span className="text-xs font-medium text-gray-300">Route ready</span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {currentRoute.distance_miles ? `${currentRoute.distance_miles.toFixed(1)} mi` : ''}
                      {currentRoute.duration_minutes ? ` • ${Math.round(currentRoute.duration_minutes)} min` : ''}
                    </div>
              </div>
              
                  {/* Action buttons */}
                  <div className="p-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShowRouteDetails(true)}
                      className="
                        flex-1 px-3 py-2 rounded-xl
                        bg-blue-600 hover:bg-blue-500
                        text-white text-sm font-semibold
                        shadow-lg shadow-blue-500/30
                        transition-all duration-200
                        hover:scale-[1.02] active:scale-[0.98]
                      "
                    >
                      View Details
                    </button>
                    <button
                      type="button"
                      onClick={handleClearRoute}
                      className="
                        px-3 py-2 rounded-xl
                        bg-transparent hover:bg-red-500/20
                        text-gray-400 hover:text-red-400
                        text-sm font-medium
                        border border-gray-700/50 hover:border-red-500/50
                        transition-all duration-200
                      "
                    >
                      Clear
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Toast Notifications */}
      <ToastNotification toasts={toasts} onDismiss={dismissToast} />
      
      {/* Unified Entity Detail Drawer (POI/Road/Agent) */}
      <POIDetailsDrawer
        entity={!selectedItem ? null : (selectedItem.type === 'agent' ? selectedItem.data : selectedItem.type === 'poi' ? (() => {
          // Robust OSM id resolution with multi-source fallback
          const d: any = selectedItem.data || {}
          const props: any = d.properties || {}
          const tags: any = d.tags || props || {}
          const rawId: any = d.osm_id || d.id || props.osm_id || props.id || tags.osm_id || tags.id || tags['@id']
          // Normalize @id like "node/123" -> 123
          const normalizedId = typeof rawId === 'string' && rawId.includes('/') ? rawId.split('/').pop() : rawId
          return {
            type: 'poi',
            id: normalizedId,
            geometry: { type: 'Point', coordinates: selectedItem.coordinates },
            properties: d,
            tags: props || d
          }
        })() : {
          type: 'road',
          id: selectedItem.data.properties?.osm_id || selectedItem.data.osm_id,
          geometry: selectedItem.data.geometry,
          properties: selectedItem.data.properties
        })}
        open={showEntityDrawer}
        onOpenChange={(open) => {
          setShowEntityDrawer(open)
          if (!open) setSelectedItem(null) // Clear selection when drawer closes
        }}
        map={map}
        simulationId={simulationId}
        selectedDatetime={selectedDatetime}
      />
      
      {/* Route Overview Drawer */}
      <RouteOverviewDrawer
        route={currentRoute}
        open={showRouteDetails}
        onOpenChange={setShowRouteDetails}
        map={map}
        onSwapRoute={handleSwapRoute}
        onClearRoute={handleClearRoute}
        onHighlightStep={(idx) => {
          // Placeholder: hook for segment emphasis
          // In future, we can split route line and adjust paint for hovered segment
        }}
      />
      
      

      {/* Reticle - Pulsing ring during pick mode */}
      {reticlePos && (
        <div
          className="fixed pointer-events-none z-[60]"
          style={{
            left: `${reticlePos.x}px`,
            top: `${reticlePos.y}px`,
            transform: 'translate(-50%, -50%)'
          }}
        >
          <div className="w-8 h-8 rounded-full border-2 border-blue-400 animate-ping opacity-50"></div>
          <div className="absolute inset-0 w-8 h-8 rounded-full border-2 border-blue-300"></div>
        </div>
      )}
      </div>
    </div>
  )
}
