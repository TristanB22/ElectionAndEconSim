import { Navigation, Clock, MapPin, Target, Gauge, DollarSign, TrendingUp, Copy, ArrowDownUp, Crosshair, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import type { Route } from '../../types/routing'
import type { Map as MapLibreMap } from 'maplibre-gl'

interface RouteDetailsDrawerProps {
  route: Route | null
  open: boolean
  onOpenChange: (open: boolean) => void
  map: MapLibreMap | null
  onSwapRoute: () => void
}

export function RouteDetailsDrawer({ route, open, onOpenChange, map, onSwapRoute }: RouteDetailsDrawerProps) {
  const [directionsExpanded, setDirectionsExpanded] = useState(false)
  
  if (!route) return null

  const formatDuration = (minutes: number): string => {
    const hours = Math.floor(minutes / 60)
    const mins = Math.round(minutes % 60)
    if (hours > 0) {
      return `${hours}h ${mins}m`
    }
    return `${mins}m`
  }

  const copyCoordinates = (lat: number, lon: number) => {
    navigator.clipboard.writeText(`${lat.toFixed(6)}, ${lon.toFixed(6)}`)
  }

  const centerOnLocation = (lat: number, lon: number) => {
    if (map) {
      map.flyTo({
        center: [lon, lat],
        zoom: Math.min(15, 18),
        duration: 1000
      })
    }
  }

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 transition-opacity duration-200"
          onClick={() => onOpenChange(false)}
        />
      )}

      {/* Sheet - Slides from right with springy animation */}
      <div
        className={`
          fixed top-0 right-0 h-full w-[560px] max-w-[90vw]
          bg-gradient-to-br from-gray-900/98 to-gray-950/98
          backdrop-blur-2xl
          border-l-2 border-white/10
          shadow-[0_0_80px_rgba(0,0,0,0.5)]
          z-50
          transform transition-all duration-300 ease-out
          ${open ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        `}
      >
        <div className="h-full flex flex-col">
          {/* Sticky Header */}
          <div className="sticky top-0 z-10 px-6 py-4 border-b border-white/10 bg-gray-900/95 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-500/20 rounded-xl border border-blue-400/30">
                  <Navigation className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Route Overview</h2>
                  <p className="text-xs text-gray-400">{route.mode_label}</p>
                </div>
              </div>
              
            </div>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {/* Summary Cards - 2up */}
            <div className="grid grid-cols-2 gap-4">
              {/* Duration Card */}
              <div className="relative group overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-blue-950/40 to-blue-900/20 p-5 hover:border-blue-400/30 transition-all duration-200">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-4 h-4 text-blue-400" />
                    <span className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Duration</span>
                  </div>
                  <p className="text-3xl font-bold text-white">{formatDuration(route.duration_minutes)}</p>
                </div>
              </div>

              {/* Distance Card */}
              <div className="relative group overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-green-950/40 to-green-900/20 p-5 hover:border-green-400/30 transition-all duration-200">
                <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative">
                  <div className="flex items-center gap-2 mb-2">
                    <Gauge className="w-4 h-4 text-green-400" />
                    <span className="text-xs font-semibold text-green-300 uppercase tracking-wider">Distance</span>
                  </div>
                  <p className="text-3xl font-bold text-white">{route.distance_miles.toFixed(1)} <span className="text-lg text-gray-400">mi</span></p>
                  <p className="text-xs text-gray-400 mt-1">{route.distance_km.toFixed(1)} km</p>
                </div>
              </div>
            </div>

            {/* Route Features */}
            {(route.has_highway || route.has_toll) && (
              <div className="flex gap-2">
                {route.has_highway && (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-800/50 border border-gray-700/50">
                    <TrendingUp className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-300">Highway</span>
                  </div>
                )}
                {route.has_toll && (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-yellow-900/30 border border-yellow-600/30">
                    <DollarSign className="w-4 h-4 text-yellow-400" />
                    <span className="text-sm text-yellow-300">Tolls</span>
                  </div>
                )}
              </div>
            )}

            {/* Endpoints */}
            <div className="space-y-4">
              {/* Start Point */}
              <div className="relative overflow-hidden rounded-2xl border border-green-500/30 bg-gradient-to-br from-green-950/40 to-transparent p-5">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-green-500/20 rounded-xl border border-green-400/30">
                    <MapPin className="w-5 h-5 text-green-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-green-300 uppercase tracking-wider mb-2">Start</p>
                    <p className="text-sm text-white font-mono mb-3">
                      {route.coordinates[0][1].toFixed(6)}, {route.coordinates[0][0].toFixed(6)}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => copyCoordinates(route.coordinates[0][1], route.coordinates[0][0])}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 text-xs text-gray-300 hover:text-white transition-colors"
                      >
                        <Copy className="w-3 h-3" />
                        Copy
                      </button>
                      <button 
                        onClick={() => centerOnLocation(route.coordinates[0][1], route.coordinates[0][0])}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 text-xs text-gray-300 hover:text-white transition-colors"
                      >
                        <Crosshair className="w-3 h-3" />
                        Center
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Swap Button */}
              <div className="flex justify-center">
                <button 
                  onClick={onSwapRoute}
                  className="p-2 rounded-xl bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 text-gray-400 hover:text-white transition-all hover:scale-110"
                  title="Swap start and end locations"
                >
                  <ArrowDownUp className="w-4 h-4" />
                </button>
              </div>

              {/* End Point */}
              <div className="relative overflow-hidden rounded-2xl border border-red-500/30 bg-gradient-to-br from-red-950/40 to-transparent p-5">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-red-500/20 rounded-xl border border-red-400/30">
                    <Target className="w-5 h-5 text-red-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-red-300 uppercase tracking-wider mb-2">End</p>
                    <p className="text-sm text-white font-mono mb-3">
                      {route.coordinates[route.coordinates.length - 1][1].toFixed(6)}, {route.coordinates[route.coordinates.length - 1][0].toFixed(6)}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => copyCoordinates(
                          route.coordinates[route.coordinates.length - 1][1],
                          route.coordinates[route.coordinates.length - 1][0]
                        )}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 text-xs text-gray-300 hover:text-white transition-colors"
                      >
                        <Copy className="w-3 h-3" />
                        Copy
                      </button>
                      <button 
                        onClick={() => centerOnLocation(
                          route.coordinates[route.coordinates.length - 1][1],
                          route.coordinates[route.coordinates.length - 1][0]
                        )}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 text-xs text-gray-300 hover:text-white transition-colors"
                      >
                        <Crosshair className="w-3 h-3" />
                        Center
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Turn-by-Turn Directions - Collapsible */}
            {route.directions && route.directions.length > 0 && (
              <div className="space-y-3">
                <button
                  onClick={() => setDirectionsExpanded(!directionsExpanded)}
                  className="flex items-center justify-between w-full group"
                >
                  <h3 className="text-sm font-bold text-white">Turn-by-Turn Directions</h3>
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${directionsExpanded ? 'rotate-180' : ''}`} />
                </button>
                
                {directionsExpanded && (
                  <div className="space-y-2">
                    {route.directions.map((direction, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3 p-4 rounded-xl bg-gray-800/30 border border-gray-700/30 hover:bg-gray-800/50 hover:border-gray-600/50 transition-all duration-200 cursor-pointer group"
                      >
                        <div className="flex items-center justify-center w-7 h-7 bg-blue-500/20 border border-blue-400/30 text-blue-300 rounded-full text-xs font-bold flex-shrink-0">
                          {index + 1}
                        </div>
                        <p className="flex-1 text-sm text-gray-300 leading-relaxed pt-0.5">
                          {direction}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
