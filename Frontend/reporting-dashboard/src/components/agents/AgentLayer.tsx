import React, { useEffect, useState, useCallback, useRef } from 'react'
import type { Map as MapLibreMap } from 'maplibre-gl'
import { API_ENDPOINTS, buildApiUrl } from '../../config/api'
import { LAYOUT } from '../../layout'
import { agentColors } from '../../styles/colors'

interface AgentLocation {
  agent_id: string
  latitude: number
  longitude: number
  simulation_timestamp: string
}

interface AgentLayerProps {
  map: MapLibreMap | null
  simulationId: string | null
  selectedDatetime: Date | null
  zoom: number
  onAgentClick: (agentId: string) => void
  enabled?: boolean
  onVisibleAgentsCountChange?: (count: number) => void
}

export const AgentLayer: React.FC<AgentLayerProps> = ({
  map,
  simulationId,
  selectedDatetime,
  zoom,
  onAgentClick,
  enabled = true,
  onVisibleAgentsCountChange,
}) => {
  const [agentLocations, setAgentLocations] = useState<AgentLocation[]>([])
  const [loading, setLoading] = useState(false)
  const fetchControllerRef = useRef<AbortController | null>(null)

  const sourceId = 'agent-locations'
  const layerId = 'agent-markers'
  const layerIdHover = 'agent-markers-hover'
  const layerIdHit = 'agent-markers-hit'

  // Fetch agent locations when datetime changes
  const fetchAgentLocations = useCallback(async () => {
    if (!simulationId || !selectedDatetime) {
      setAgentLocations([])
      return
    }

    // Cancel previous fetch
    if (fetchControllerRef.current) {
      fetchControllerRef.current.abort()
    }

    fetchControllerRef.current = new AbortController()
    setLoading(true)

    try {
      const datetimeStr = selectedDatetime.toISOString()
      const url = buildApiUrl(API_ENDPOINTS.AGENT_LOCATIONS(simulationId), {
        datetime: datetimeStr,
      })

      const response = await fetch(url, {
        signal: fetchControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch agent locations: ${response.statusText}`)
      }

      const data = await response.json()
      setAgentLocations(data.locations || [])
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Error fetching agent locations:', error)
      }
    } finally {
      setLoading(false)
    }
  }, [simulationId, selectedDatetime])

  // Fetch on datetime change
  useEffect(() => {
    fetchAgentLocations()
  }, [fetchAgentLocations])

  // Create agent icon as SVG
  const createAgentIcon = () => {
    const svg = `
      <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <!-- Glow -->
        <circle cx="16" cy="16" r="14" fill="${agentColors.marker.glow}" opacity="0.3"/>
        <!-- Diamond -->
        <path d="M 16 8 L 24 16 L 16 24 L 8 16 Z" 
              fill="${agentColors.marker.fill}" 
              stroke="${agentColors.marker.ring}" 
              stroke-width="2.5"/>
        <!-- Center dot -->
        <circle cx="16" cy="16" r="3" fill="${agentColors.marker.core}"/>
      </svg>
    `
    return `data:image/svg+xml;base64,${btoa(svg)}`
  }

  // Ensure layers/sources exist (once)
  useEffect(() => {
    if (!map) return
    if (!map.getSource(sourceId)) {
      map.addSource(sourceId, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } as any })
    }

    // Add agent icon image to map
    const iconDataUrl = createAgentIcon()
    const img = new Image(32, 32)
    img.onload = () => {
      if (!map.hasImage('agent-icon')) {
        map.addImage('agent-icon', img as any)
      }
    }
    img.src = iconDataUrl

    // Create hover version with highlighted ring
    // OPTION 1: Simple Dot with Ring (hover)
    const hoverSvg = `
      <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <!-- Glow on hover -->
        <circle cx="16" cy="16" r="12" fill="${agentColors.marker.hover}" opacity="0.4"/>
        <!-- Outer ring (thicker on hover) -->
        <circle cx="16" cy="16" r="8" fill="none" stroke="${agentColors.marker.ring}" stroke-width="3.5"/>
        <!-- Inner dot -->
        <circle cx="16" cy="16" r="4" fill="${agentColors.marker.core}"/>
      </svg>
    `
    
    // OPTION 2: Triangle/Arrow (hover)
    // const hoverSvg = `
    //   <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    //     <!-- Glow circle -->
    //     <circle cx="16" cy="16" r="15" fill="${agentColors.marker.hover}" opacity="0.5"/>
    //     <!-- Triangle pointing up (thicker stroke) -->
    //     <path d="M 16 8 L 22 20 L 10 20 Z" 
    //           fill="${agentColors.marker.core}" 
    //           stroke="${agentColors.marker.ring}" 
    //           stroke-width="3"/>
    //   </svg>
    // `
    
    // OPTION 3: Diamond Shape (hover)
    // const hoverSvg = `
    //   <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    //     <!-- Glow -->
    //     <circle cx="16" cy="16" r="15" fill="${agentColors.marker.hover}" opacity="0.5"/>
    //     <!-- Diamond (thicker stroke) -->
    //     <path d="M 16 8 L 24 16 L 16 24 L 8 16 Z" 
    //           fill="${agentColors.marker.fill}" 
    //           stroke="${agentColors.marker.ring}" 
    //           stroke-width="3.5"/>
    //     <!-- Center dot -->
    //     <circle cx="16" cy="16" r="3" fill="${agentColors.marker.core}"/>
    //   </svg>
    // `
    const hoverImg = new Image(32, 32)
    hoverImg.onload = () => {
      if (!map.hasImage('agent-icon-hover')) {
        map.addImage('agent-icon-hover', hoverImg as any)
      }
    }
    hoverImg.src = `data:image/svg+xml;base64,${btoa(hoverSvg)}`

    // Main agent layer with icon
    if (!map.getLayer(layerId)) {
      map.addLayer({
        id: layerId,
        type: 'symbol',
        source: sourceId,
        layout: {
          'icon-image': 'agent-icon',
          'icon-size': [
            'interpolate',
            ['linear'],
            ['zoom'],
            LAYOUT.AGENT.MIN_ZOOM,
            0.8,
            LAYOUT.AGENT.MIN_ZOOM + 2,
            1.0,
            LAYOUT.AGENT.MIN_ZOOM + 4,
            1.2,
          ],
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
          'icon-anchor': 'center',
        },
      })
    }

    // Hover layer
    if (!map.getLayer(layerIdHover)) {
      map.addLayer({
        id: layerIdHover,
        type: 'symbol',
        source: sourceId,
        layout: {
          'icon-image': 'agent-icon-hover',
          'icon-size': [
            'interpolate',
            ['linear'],
            ['zoom'],
            LAYOUT.AGENT.MIN_ZOOM,
            0.9,
            LAYOUT.AGENT.MIN_ZOOM + 2,
            1.1,
            LAYOUT.AGENT.MIN_ZOOM + 4,
            1.3,
          ],
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
          'icon-anchor': 'center',
        },
        paint: {
          'icon-opacity': 0,
        },
        filter: ['==', 'agent_id', ''],
      })
    }

    // Invisible hit area to improve hover/click responsiveness
    if (!map.getLayer(layerIdHit)) {
      map.addLayer({
        id: layerIdHit,
        type: 'circle',
        source: sourceId,
        paint: {
          'circle-radius': [
            'interpolate', ['linear'], ['zoom'],
            LAYOUT.AGENT.MIN_ZOOM, 16,
            LAYOUT.AGENT.MIN_ZOOM + 2, 18,
            LAYOUT.AGENT.MIN_ZOOM + 4, 22
          ],
          // Very low opacity but non-zero so events fire
          'circle-opacity': 0.01,
          'circle-color': '#000000'
        }
      })
    }

    const ensureLayerOrder = () => {
      try {
        if (map.getLayer(layerIdHit)) map.moveLayer(layerIdHit)
        if (map.getLayer(layerIdHover)) map.moveLayer(layerIdHover)
        if (map.getLayer(layerId)) map.moveLayer(layerId)
      } catch {}
    }

    ensureLayerOrder()

    // Reassert ordering whenever data/style events occur
    const onData = () => {
      ensureLayerOrder()
    }
    map.on('data', onData)

    return () => {
      try {
        map.off('data', onData)
      } catch {}
    }
  }, [map])

  // Update data without removing layers (prevents flicker)
  useEffect(() => {
    if (!map) return
    const geojson: GeoJSON.FeatureCollection<GeoJSON.Point> = {
      type: 'FeatureCollection',
      features: agentLocations.map((loc) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [loc.longitude, loc.latitude] },
        properties: { agent_id: loc.agent_id, timestamp: loc.simulation_timestamp },
      })),
    }
    const src = map.getSource(sourceId) as any
    if (src && typeof src.setData === 'function') {
      src.setData(geojson)
    }
  }, [map, agentLocations])

  // Visibility control based on zoom and enabled state
  useEffect(() => {
    if (!map) return
    const visible = enabled && zoom >= LAYOUT.AGENT.MIN_ZOOM
    const vis = visible ? 'visible' : 'none'
    try { if (map.getLayer(layerId)) map.setLayoutProperty(layerId, 'visibility', vis) } catch {}
    try { if (map.getLayer(layerIdHover)) map.setLayoutProperty(layerIdHover, 'visibility', vis) } catch {}
    try { if (map.getLayer(layerIdHit)) map.setLayoutProperty(layerIdHit, 'visibility', vis) } catch {}
    // Keep top order when made visible
    if (visible) {
      try {
        if (map.getLayer(layerIdHit)) map.moveLayer(layerIdHit)
        if (map.getLayer(layerIdHover)) map.moveLayer(layerIdHover)
        if (map.getLayer(layerId)) map.moveLayer(layerId)
      } catch {}
    }
  }, [map, zoom, enabled])

  // Calculate and report visible agents count in viewport
  useEffect(() => {
    if (!map || !onVisibleAgentsCountChange || !enabled || zoom < LAYOUT.AGENT.MIN_ZOOM) {
      if (onVisibleAgentsCountChange) {
        onVisibleAgentsCountChange(0)
      }
      return
    }

    const calculateVisibleCount = () => {
      try {
        const bounds = map.getBounds()
        const visibleAgents = agentLocations.filter(loc => {
          const lng = loc.longitude
          const lat = loc.latitude
          return (
            lng >= bounds.getWest() &&
            lng <= bounds.getEast() &&
            lat >= bounds.getSouth() &&
            lat <= bounds.getNorth()
          )
        })
        onVisibleAgentsCountChange(visibleAgents.length)
      } catch (error) {
        // If bounds calculation fails, report 0
        onVisibleAgentsCountChange(0)
      }
    }

    // Calculate on initial load
    calculateVisibleCount()

    // Recalculate when map moves
    const onMoveEnd = () => {
      calculateVisibleCount()
    }

    map.on('moveend', onMoveEnd)
    map.on('resize', onMoveEnd)

    return () => {
      map.off('moveend', onMoveEnd)
      map.off('resize', onMoveEnd)
    }
  }, [map, agentLocations, zoom, enabled, onVisibleAgentsCountChange])

  // Handle click events
  useEffect(() => {
    if (!map) return

    const handleClick = (e: any) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [layerIdHit, layerId],
      })

      if (features.length > 0) {
        const agentId = features[0].properties?.agent_id
        if (agentId) {
          onAgentClick(agentId)
        }
      }
    }

    const handleMouseMove = (e: any) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [layerIdHit, layerId],
      })

      if (features.length > 0) {
        map.getCanvas().style.cursor = 'pointer'
        const agentId = features[0].properties?.agent_id
        if (agentId) {
          map.setFilter(layerIdHover, ['==', 'agent_id', agentId])
          map.setPaintProperty(layerIdHover, 'icon-opacity', 1)
        }
      } else {
        map.getCanvas().style.cursor = ''
        map.setFilter(layerIdHover, ['==', 'agent_id', ''])
        map.setPaintProperty(layerIdHover, 'icon-opacity', 0)
      }
    }

    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = ''
      map.setFilter(layerIdHover, ['==', 'agent_id', ''])
      map.setPaintProperty(layerIdHover, 'icon-opacity', 0)
    }

    map.on('click', layerIdHit, handleClick)
    map.on('mousemove', layerIdHit, handleMouseMove)
    map.on('mouseleave', layerIdHit, handleMouseLeave)

    return () => {
      map.off('click', layerIdHit, handleClick)
      map.off('mousemove', layerIdHit, handleMouseMove)
      map.off('mouseleave', layerIdHit, handleMouseLeave)
    }
  }, [map, layerId, layerIdHover, onAgentClick])

  return null // This is a map layer component, no DOM rendering
}
