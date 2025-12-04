import { useState } from 'react'
import { motion } from 'framer-motion'
import { Navigation, Clock, MapPin, Target, Gauge, DollarSign, TrendingUp, Copy, ArrowDownUp, Crosshair, ChevronDown, Car, Bike, User } from 'lucide-react'
import type { Map as MapLibreMap } from 'maplibre-gl'
import type { Route } from '../../types/routing'
import { BaseDrawer } from './BaseDrawer'
import { ActionChip } from './ActionChip'
import { MetricCard } from './MetricCard'
import { staggerContainerVariants, staggerChildVariants, accordionVariants } from '../../hooks/useDrawerMotion'

/**
 * RouteOverviewDrawer - Main routing interface
 * 
 * Design Philosophy:
 * - Show critical info (duration, distance) prominently in metric cards
 * - Start/End sections use consistent layout with action chips
 * - Turn-by-turn accordion collapses by default to reduce cognitive load
 * - All interactions are icon-first: users understand actions without reading
 * 
 * Layout Hierarchy:
 * 1. Header: Route mode + navigation icon
 * 2. Metrics: Duration + Distance in glass cards (2-column grid)
 * 3. Route features: Highway/Toll badges if applicable
 * 4. Endpoints: Start → Swap → End (vertical flow with clear visual separation)
 * 5. Directions: Collapsible accordion timeline
 */

interface RouteOverviewDrawerProps {
  route: Route | null
  open: boolean
  onOpenChange: (open: boolean) => void
  map: MapLibreMap | null
  onSwapRoute: () => void
  onClearRoute?: () => void
  onHighlightStep?: (index: number | null) => void
}

export function RouteOverviewDrawer({ 
  route, 
  open, 
  onOpenChange, 
  map, 
  onSwapRoute,
  onClearRoute,
  onHighlightStep
}: RouteOverviewDrawerProps) {
  const [directionsExpanded, setDirectionsExpanded] = useState(false)

  if (!route) return null

  // Format duration for human readability
  const formatDuration = (minutes: number): string => {
    const hours = Math.floor(minutes / 60)
    const mins = Math.round(minutes % 60)
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
  }

  // Copy coordinates to clipboard
  const copyCoordinates = (lat: number, lon: number) => {
    navigator.clipboard.writeText(`${lat.toFixed(6)}, ${lon.toFixed(6)}`)
  }

  // Center map on location without changing current zoom level
  const centerOnLocation = (lat: number, lon: number) => {
    if (map) {
      const currentZoom = Math.min(map.getZoom(), 18)
      map.flyTo({
        center: [lon, lat],
        zoom: currentZoom,
        duration: 500
      })
    }
  }

  // Mode-based gradient colors (subtle, no blur)
  const mode = (route.mode as string) || 'auto'
  const modeGradient = (() => {
    if (mode === 'pedestrian' || mode === 'walk' || mode === 'walking') return { from: '#10b981', to: '#9ca3af' }
    if (mode === 'bicycle' || mode === 'bike' || mode === 'cycling') return { from: '#f59e0b', to: '#06b6d4' }
    return { from: '#3b82f6', to: '#10b981' } // driving default
  })()

  const ModeIcon = (() => {
    if (mode === 'pedestrian' || mode === 'walk' || mode === 'walking') return User
    if (mode === 'bicycle' || mode === 'bike' || mode === 'cycling') return Bike
    return Car
  })()

  // Mini-map SVG preview of route (preserves aspect ratio)
  const MiniMap = () => {
    const coords = route.coordinates
    if (!coords || coords.length < 2) return null
    const lons = coords.map(c => c[0])
    const lats = coords.map(c => c[1])
    const minLon = Math.min(...lons)
    const maxLon = Math.max(...lons)
    const minLat = Math.min(...lats)
    const maxLat = Math.max(...lats)
    
    const pad = 6
    const maxWidth = 160
    const maxHeight = 88
    
    // Calculate route bounding box in lon/lat
    const dx = maxLon - minLon || 1e-6
    const dy = maxLat - minLat || 1e-6
    
    // Determine scale to fit while preserving aspect ratio
    // Scale to the larger dimension
    const scaleX = (maxWidth - pad * 2) / dx
    const scaleY = (maxHeight - pad * 2) / dy
    const scale = Math.min(scaleX, scaleY)
    
    // Actual dimensions after preserving aspect ratio
    const actualWidth = dx * scale + pad * 2
    const actualHeight = dy * scale + pad * 2
    
    // Center the route in the viewBox
    const offsetX = (maxWidth - actualWidth) / 2
    const offsetY = (maxHeight - actualHeight) / 2
    
    const transformX = (x: number) => offsetX + pad + ((x - minLon) * scale)
    const transformY = (y: number) => offsetY + pad + ((maxLat - y) * scale)
    
    const d = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${transformX(c[0]).toFixed(1)} ${transformY(c[1]).toFixed(1)}`).join(' ')
    
    return (
      <svg width={maxWidth} height={maxHeight} viewBox={`0 0 ${maxWidth} ${maxHeight}`} className="rounded-lg border" style={{ borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
        <defs>
          <linearGradient id="routeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={modeGradient.from} />
            <stop offset="100%" stopColor={modeGradient.to} />
          </linearGradient>
        </defs>
        <path d={d} fill="none" stroke="url(#routeGrad)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <animate attributeName="stroke-dashoffset" from="20" to="0" dur="0.6s" fill="freeze" />
        </path>
      </svg>
    )
  }

  // Header component for drawer
  const header = (
    <div className="px-6 pt-4 pb-2">
      {/* Summary strip: icon + distance · duration — mode */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg border" style={{ borderColor: 'rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.04)' }}>
            <ModeIcon className="w-4 h-4 text-gray-200" />
          </div>
          <div className="text-base font-semibold" style={{
            backgroundImage: `linear-gradient(90deg, ${modeGradient.from}, ${modeGradient.to})`,
            WebkitBackgroundClip: 'text',
            color: 'transparent'
          }}>
            {route.distance_miles.toFixed(1)} mi · {formatDuration(route.duration_minutes)} — {route.mode_label}
          </div>
        </div>
        <div className="cursor-pointer" onClick={() => { if (map && route.coordinates?.length) { const mid = Math.floor(route.coordinates.length/2); const currentZoom = map.getZoom(); map.flyTo({ center: [route.coordinates[mid][0], route.coordinates[mid][1]], zoom: currentZoom, duration: 500 }) } }}>
          <MiniMap />
        </div>
      </div>
      {/* Animated underline */}
      <motion.div initial={{ width: 0 }} animate={{ width: '100%' }} transition={{ duration: 0.6, ease: 'easeOut' }} className="h-[2px] mt-2" style={{ backgroundImage: `linear-gradient(90deg, ${modeGradient.from}, ${modeGradient.to})` }} />
    </div>
  )

  return (
    <BaseDrawer
      open={open}
      onClose={() => onOpenChange(false)}
      header={header}
    >
      {/* Main content with staggered reveal */}
      <motion.div
        variants={staggerContainerVariants}
        initial="hidden"
        animate="visible"
        className="px-6 py-4 space-y-5"
      >
        {/* Start/End pills */}
        <motion.div variants={staggerChildVariants} className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-2 rounded-full border" style={{ borderColor: 'rgba(16,185,129,0.4)', background: 'rgba(16,185,129,0.08)' }}>
            <MapPin className="w-4 h-4 text-green-400" />
            <span className="text-sm font-mono text-white/90">{route.coordinates[0][1].toFixed(5)}, {route.coordinates[0][0].toFixed(5)}</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-full border" style={{ borderColor: 'rgba(239,68,68,0.4)', background: 'rgba(239,68,68,0.08)' }}>
            <Target className="w-4 h-4 text-red-400" />
            <span className="text-sm font-mono text-white/90">{route.coordinates[route.coordinates.length-1][1].toFixed(5)}, {route.coordinates[route.coordinates.length-1][0].toFixed(5)}</span>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <ActionChip icon={ArrowDownUp} label="Swap" onClick={onSwapRoute} />
            <ActionChip icon={Copy} label="Copy" onClick={() => copyCoordinates(route.coordinates[0][1], route.coordinates[0][0])} />
            <ActionChip icon={Crosshair} label="Center" onClick={() => centerOnLocation(route.coordinates[0][1], route.coordinates[0][0])} />
          </div>
        </motion.div>

        {/* Route Features - subtle badges */}
        {(route.has_highway || route.has_toll) && (
          <motion.div variants={staggerChildVariants} className="flex gap-2">
            {route.has_highway && (
              <div className="px-3 py-1.5 rounded-full border text-xs text-gray-300" style={{ background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)' }}>
                Highway
              </div>
            )}
            {route.has_toll && (
              <div className="px-3 py-1.5 rounded-full border text-xs text-yellow-200" style={{ background: 'rgba(234,179,8,0.12)', borderColor: 'rgba(234,179,8,0.3)' }}>
                Tolls
              </div>
            )}
          </motion.div>
        )}

        {/* Timeline of motion: connected vertical list (collapsed to 3) */}
        {route.directions && route.directions.length > 0 && (
          <motion.div variants={staggerChildVariants}>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">Directions</h3>
              <button onClick={() => setDirectionsExpanded(!directionsExpanded)} className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1">
                {directionsExpanded ? 'Show less' : 'Show all'}
                <ChevronDown className={`w-4 h-4 transition-transform ${directionsExpanded ? 'rotate-180' : ''}`} />
              </button>
            </div>
            <div className="mt-2">
              <div className="relative">
                <div className="absolute left-3 top-0 bottom-0 w-px bg-white/10" />
                <div className="space-y-2">
                  {(directionsExpanded ? route.directions : route.directions.slice(0, 3)).map((direction, index) => (
                    <div key={index} className="relative pl-8 pr-2 py-2 rounded-lg border hover:bg-white/5 transition-colors cursor-pointer" style={{ borderColor: 'rgba(255,255,255,0.08)' }}
                      onMouseEnter={() => onHighlightStep?.(index)}
                      onMouseLeave={() => onHighlightStep?.(null)}
                    >
                      <div className="absolute left-2 top-3 w-3 h-3 rounded-full border" style={{ borderColor: 'rgba(59,130,246,0.5)', background: 'rgba(59,130,246,0.2)' }} />
                      <div className="text-sm text-gray-200">{direction}</div>
                      <div className="text-[11px] text-gray-400 mt-0.5">Step {index + 1}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Footer actions */}
        <motion.div variants={staggerChildVariants} className="flex items-center justify-end gap-2 pt-1">
          {onClearRoute && (
            <ActionChip icon={Navigation} label="Clear" onClick={onClearRoute} />
          )}
          <ActionChip icon={ArrowDownUp} label="Swap" onClick={onSwapRoute} />
        </motion.div>
      </motion.div>
    </BaseDrawer>
  )
}

