import { useState, useRef, useEffect } from 'react'
import { Navigation, Loader2, MapPin, Target, Car, User, X, Bike, Bus, Truck, Zap } from 'lucide-react'
import axios from 'axios'
import { API_ENDPOINTS } from '../../config/api'
import { log } from '../../config/log'
import type { Route, RouteRequest, RoutingMode } from '../../types/routing'
import type { ToastType } from '../../components/ToastNotification'

interface RoutePlannerPanelProps {
  expanded: boolean
  onToggle: () => void
  onRouteCalculated: (route: Route) => void
  onRequestMapClick: (type: 'start' | 'end') => void
  waitingForMapClick: 'start' | 'end' | null // NEW: Track which location is waiting
  startLat: string
  startLon: string
  endLat: string
  endLon: string
  onStartLatChange: (value: string) => void
  onStartLonChange: (value: string) => void
  onEndLatChange: (value: string) => void
  onEndLonChange: (value: string) => void
  isInline?: boolean // New prop for inline rendering
  addToast?: (message: string, type?: ToastType, options?: { persistent?: boolean; duration?: number }) => string
}

type LocationState = 'empty' | 'waiting' | 'set'

// Visual Location Input Component
interface LocationInputProps {
  label: string
  icon: 'start' | 'end'
  state: LocationState
  lat: string
  lon: string
  onClick: () => void
  onClear: () => void
}

function LocationInput({ label, icon, state, lat, lon, onClick, onClear }: LocationInputProps) {
  const Icon = icon === 'start' ? MapPin : Target
  
  // Visual state classes - glassmorphic aesthetic
  const containerClasses = {
    empty: 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10 backdrop-blur-sm',
    waiting: 'border-blue-500/50 bg-blue-950/20 shadow-[0_0_20px_rgba(59,130,246,0.15)] animate-pulse backdrop-blur-sm',
    set: 'border-green-500/30 bg-green-950/20 shadow-[0_0_12px_rgba(34,197,94,0.1)] backdrop-blur-sm'
  }
  
  const iconClasses = {
    empty: 'text-gray-400',
    waiting: 'text-blue-400 animate-bounce',
    set: 'text-green-400'
  }

  const hasValue = state === 'set'
  
  return (
    <div className="relative">
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } }}
        className={`
          w-full relative group
          rounded-xl border-2 transition-all duration-300
          ${containerClasses[state]}
          ${!hasValue && 'cursor-pointer'}
          outline-none focus:ring-2 focus:ring-blue-500/50
        `}
      >
        <div className="flex items-center gap-3 p-3.5">
          {/* Icon with state indicator */}
          <div className="relative flex-shrink-0">
            <div className={`
              w-10 h-10 rounded-full flex items-center justify-center
              transition-all duration-300
              ${state === 'empty' ? 'bg-gray-700/50' : ''}
              ${state === 'waiting' ? 'bg-blue-500/20' : ''}
              ${state === 'set' ? 'bg-green-500/20' : ''}
            `}>
              <Icon className={`w-5 h-5 transition-all duration-300 ${iconClasses[state]}`} />
            </div>
            
            {/* Waiting state pulse ring */}
            {state === 'waiting' && (
              <div className="absolute inset-0 rounded-full border-2 border-blue-400/50 animate-ping" />
            )}
            
            {/* Set state check indicator */}
            {state === 'set' && (
              <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-900" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 text-left min-w-0">
            <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-0.5">
              {label}
            </div>
            {hasValue ? (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-300 font-mono truncate">
                  {parseFloat(lat).toFixed(5)}, {parseFloat(lon).toFixed(5)}
                </span>
              </div>
            ) : (
              <div className="text-xs text-gray-500">
                {state === 'waiting' ? (
                  <span className="text-blue-400 font-medium">Tap map to set location...</span>
                ) : (
                  <span>Tap to select from map</span>
                )}
              </div>
            )}
          </div>

          {/* Clear button when set */}
          {hasValue && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onClear()
              }}
              className="flex-shrink-0 w-7 h-7 rounded-full bg-gray-700/50 hover:bg-red-500/20 border border-gray-600/50 hover:border-red-500/50 flex items-center justify-center transition-all duration-200 group/clear"
            >
              <X className="w-3.5 h-3.5 text-gray-400 group-hover/clear:text-red-400 transition-colors" />
            </button>
          )}
        </div>

        {/* Hover glow effect when empty */}
        {!hasValue && (
          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/0 via-blue-500/5 to-blue-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        )}
      </div>
    </div>
  )
}

export function RoutePlannerPanel({ 
  expanded, 
  onToggle, 
  onRouteCalculated,
  onRequestMapClick,
  waitingForMapClick,
  startLat,
  startLon,
  endLat,
  endLon,
  onStartLatChange,
  onStartLonChange,
  onEndLatChange,
  onEndLonChange,
  isInline = false,
  addToast
}: RoutePlannerPanelProps) {
  // Persist mode selection to localStorage
  const [mode, setMode] = useState<RoutingMode>(() => {
    const saved = localStorage.getItem('wsim_routing_mode')
    return (saved as RoutingMode) || 'auto'
  })
  const [isCalculating, setIsCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  // Persist mode changes to localStorage
  useEffect(() => {
    localStorage.setItem('wsim_routing_mode', mode)
  }, [mode])

  // Derive location states from props - synchronized with parent
  const startState: LocationState = 
    waitingForMapClick === 'start' ? 'waiting' :
    (startLat && startLon) ? 'set' : 'empty'
  
  const endState: LocationState = 
    waitingForMapClick === 'end' ? 'waiting' :
    (endLat && endLon) ? 'set' : 'empty'

  // Close panel when clicking outside
  useEffect(() => {
    if (!expanded) return

    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        onToggle()
      }
    }
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onToggle()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [expanded, onToggle])

  const handleCalculate = async () => {
    // Validate inputs
    const startLatNum = parseFloat(startLat)
    const startLonNum = parseFloat(startLon)
    const endLatNum = parseFloat(endLat)
    const endLonNum = parseFloat(endLon)

    if (isNaN(startLatNum) || isNaN(startLonNum) || isNaN(endLatNum) || isNaN(endLonNum)) {
      const msg = 'Please enter valid numbers for all coordinates'
      setError(null)
      addToast?.(msg, 'warning')
      return
    }

    if (startLatNum < -90 || startLatNum > 90 || endLatNum < -90 || endLatNum > 90) {
      const msg = 'Latitude must be between -90 and 90'
      setError(null)
      addToast?.(msg, 'warning')
      return
    }

    if (startLonNum < -180 || startLonNum > 180 || endLonNum < -180 || endLonNum > 180) {
      const msg = 'Longitude must be between -180 and 180'
      setError(null)
      addToast?.(msg, 'warning')
      return
    }

    setIsCalculating(true)
    setError(null)

    try {
      const request: RouteRequest = {
        start_lat: startLatNum,
        start_lon: startLonNum,
        end_lat: endLatNum,
        end_lon: endLonNum,
        mode,
        include_directions: true, // Always include directions for the drawer
        units: 'miles'
      }

      const response = await axios.post<Route>(
        API_ENDPOINTS.ROUTING_ROUTE,
        request
      )

      onRouteCalculated(response.data)
      onToggle() // Close panel after successful calculation
    } catch (err: any) {
      let errorMsg = 'Unable to calculate route'
      
      // Handle specific error cases with user-friendly messages
      if (err.response?.status === 404) {
        errorMsg = 'No route found between these locations'
      } else if (err.response?.status === 400) {
        errorMsg = err.response?.data?.detail || 'Invalid coordinates or travel mode'
      } else if (err.response?.status === 503) {
        errorMsg = 'Routing service unavailable - try again later'
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorMsg = 'Request timed out - check your connection'
      } else if (err.response?.data?.detail) {
        errorMsg = err.response.data.detail
      } else if (err.message) {
        errorMsg = err.message
      }
      
      setError(null)
      addToast?.(errorMsg, 'error', { duration: 3500 })
      log.debug('[ROUTE CALC] Error:', err)
    } finally {
      setIsCalculating(false)
    }
  }

  const handleClear = () => {
    onStartLatChange('')
    onStartLonChange('')
    onEndLatChange('')
    onEndLonChange('')
    setError(null)
  }

  const handleLocationClick = (type: 'start' | 'end') => {
    // Simply notify parent - parent will manage waitingForMapClick state
    onRequestMapClick(type)
  }

  const clearLocation = (type: 'start' | 'end') => {
    if (type === 'start') {
      onStartLatChange('')
      onStartLonChange('')
    } else {
      onEndLatChange('')
      onEndLonChange('')
    }
  }

  // If inline mode, just render the form content without wrapper
  if (isInline) {
    return (
      <div className="space-y-4">
        {/* Location Inputs */}
        <div className="space-y-3">
          <LocationInput
            label="Start Location"
            icon="start"
            state={startState}
            lat={startLat}
            lon={startLon}
            onClick={() => handleLocationClick('start')}
            onClear={() => clearLocation('start')}
          />
          
          <LocationInput
            label="End Location"
            icon="end"
            state={endState}
            lat={endLat}
            lon={endLon}
            onClick={() => handleLocationClick('end')}
            onClear={() => clearLocation('end')}
          />
        </div>

        {/* Travel Mode - Comprehensive Grid */}
        <div className="space-y-2.5">
          <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
            Travel Mode
          </div>
          <div className="grid grid-cols-4 gap-2">
            {/* Auto */}
            <button
              type="button"
              onClick={() => setMode('auto')}
              title="Driving"
              className={`
                flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl
                border transition-all duration-200 backdrop-blur-sm
                ${mode === 'auto' 
                  ? 'border-blue-500/50 bg-blue-950/30 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                  : 'border-white/10 bg-white/5 text-gray-400 hover:border-white/20 hover:bg-white/10'
                }
              `}
            >
              <Car className="w-4 h-4" />
              <span className="text-[10px] font-medium">Drive</span>
            </button>

            {/* Bicycle */}
            <button
              type="button"
              onClick={() => setMode('bicycle')}
              title="Bicycle"
              className={`
                flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl
                border transition-all duration-200 backdrop-blur-sm
                ${mode === 'bicycle' 
                  ? 'border-blue-500/50 bg-blue-950/30 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                  : 'border-white/10 bg-white/5 text-gray-400 hover:border-white/20 hover:bg-white/10'
                }
              `}
            >
              <Bike className="w-4 h-4" />
              <span className="text-[10px] font-medium">Bike</span>
            </button>

            {/* Pedestrian */}
            <button
              type="button"
              onClick={() => setMode('pedestrian')}
              title="Walking"
              className={`
                flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl
                border transition-all duration-200 backdrop-blur-sm
                ${mode === 'pedestrian' 
                  ? 'border-blue-500/50 bg-blue-950/30 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                  : 'border-white/10 bg-white/5 text-gray-400 hover:border-white/20 hover:bg-white/10'
                }
              `}
            >
              <User className="w-4 h-4" />
              <span className="text-[10px] font-medium">Walk</span>
            </button>

            {/* Motor Scooter */}
            <button
              type="button"
              onClick={() => setMode('motor_scooter')}
              title="Motor Scooter"
              className={`
                flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl
                border-2 transition-all duration-200
                ${mode === 'motor_scooter' 
                  ? 'border-blue-500/70 bg-blue-950/40 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                  : 'border-gray-700/50 bg-gray-800/30 text-gray-400 hover:border-gray-600 hover:bg-gray-800/50'
                }
              `}
            >
              <Zap className="w-4 h-4" />
              <span className="text-[10px] font-medium">Scooter</span>
            </button>

            {/* Bus */}
            <button
              type="button"
              onClick={() => setMode('bus')}
              title="Bus"
              className={`
                flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl
                border-2 transition-all duration-200
                ${mode === 'bus' 
                  ? 'border-blue-500/70 bg-blue-950/40 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                  : 'border-gray-700/50 bg-gray-800/30 text-gray-400 hover:border-gray-600 hover:bg-gray-800/50'
                }
              `}
            >
              <Bus className="w-4 h-4" />
              <span className="text-[10px] font-medium">Bus</span>
            </button>

            {/* Transit */}
            <button
              type="button"
              onClick={() => setMode('transit')}
              title="Public Transit"
              className={`
                flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl
                border transition-all duration-200 backdrop-blur-sm
                ${mode === 'transit' 
                  ? 'border-blue-500/50 bg-blue-950/30 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                  : 'border-white/10 bg-white/5 text-gray-400 hover:border-white/20 hover:bg-white/10'
                }
              `}
            >
              <Navigation className="w-4 h-4" />
              <span className="text-[10px] font-medium">Transit</span>
            </button>

            {/* Truck */}
            <button
              type="button"
              onClick={() => setMode('truck')}
              title="Truck"
              className={`
                flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl
                border transition-all duration-200 backdrop-blur-sm
                ${mode === 'truck' 
                  ? 'border-blue-500/50 bg-blue-950/30 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                  : 'border-white/10 bg-white/5 text-gray-400 hover:border-white/20 hover:bg-white/10'
                }
              `}
            >
              <Truck className="w-4 h-4" />
              <span className="text-[10px] font-medium">Truck</span>
            </button>
          </div>
        </div>

        {/* Error messages now displayed via global toasts */}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={handleCalculate}
            disabled={isCalculating || !startLat || !startLon || !endLat || !endLon}
            className={`
              flex-1 flex items-center justify-center gap-2 px-4 py-3
              rounded-xl font-semibold text-sm
              transition-all duration-200
              ${isCalculating || !startLat || !startLon || !endLat || !endLon
                ? 'bg-gray-700/50 text-gray-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-600 text-white shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:scale-[1.02] active:scale-[0.98]'
              }
            `}
          >
            {isCalculating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Calculating...
              </>
            ) : (
              <>
                <Navigation className="w-4 h-4" />
                Calculate Route
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="px-4 py-3 border text-gray-400 hover:text-gray-300 rounded-xl font-medium text-sm transition-all duration-200 backdrop-blur-sm"
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              borderColor: 'rgba(255, 255, 255, 0.1)',
            }}
          >
            Clear
          </button>
        </div>
      </div>
    )
  }

  return (
    <div ref={panelRef} className="absolute top-4 left-4 z-20">
      <div className="relative">
        {/* Toggle Button - Glassmorphic */}
        <button
          type="button"
          aria-label={expanded ? "Close route planner" : "Open route planner"}
          aria-expanded={expanded}
          onClick={onToggle}
          title={expanded ? "Close route planner" : "Open route planner (or press Escape)"}
          className="w-12 h-12 rounded-2xl border shadow-lg flex items-center justify-center hover:shadow-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
          style={{
            background: 'rgba(20, 22, 28, 0.55)',
            borderColor: 'rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(12px) saturate(140%)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
          }}
        >
          <Navigation
            className={`w-5 h-5 transition-all duration-300 ${
              expanded ? 'text-blue-400 rotate-90 scale-110' : 'text-gray-300'
            }`}
          />
        </button>

        {/* Dropdown Panel - Glassmorphic */}
        <div
          className={`absolute left-0 mt-3 w-80 origin-top-left rounded-2xl border transition-all duration-200 ${
            expanded ? 'opacity-100 scale-100 pointer-events-auto' : 'opacity-0 scale-95 pointer-events-none'
          }`}
          style={{
            background: 'rgba(20, 22, 28, 0.55)',
            borderColor: 'rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(12px) saturate(140%)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
          }}
        >
          <div className="relative p-4 space-y-4">
            {/* Header */}
            <div className="pb-2 border-b border-gray-700/50">
              <h3 className="text-sm font-semibold text-gray-100 tracking-wide flex items-center gap-2">
                <Navigation className="w-4 h-4 text-blue-400" />
                Route Planner
              </h3>
            </div>

            {/* Location Inputs */}
            <div className="space-y-3">
              <LocationInput
                label="Start Location"
                icon="start"
                state={startState}
                lat={startLat}
                lon={startLon}
                onClick={() => handleLocationClick('start')}
                onClear={() => clearLocation('start')}
              />
              
              <LocationInput
                label="End Location"
                icon="end"
                state={endState}
                lat={endLat}
                lon={endLon}
                onClick={() => handleLocationClick('end')}
                onClear={() => clearLocation('end')}
              />
            </div>

            {/* Travel Mode - Icon Toggle */}
            <div className="space-y-2">
              <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
                Travel Mode
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setMode('auto')}
                  className={`
                    flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg
                    border-2 transition-all duration-200
                    ${mode === 'auto' 
                      ? 'border-blue-500/70 bg-blue-950/40 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                      : 'border-gray-700/50 bg-gray-800/30 text-gray-400 hover:border-gray-600 hover:bg-gray-800/50'
                    }
                  `}
                >
                  <Car className="w-4 h-4" />
                  <span className="text-xs font-medium">Drive</span>
                </button>
                
                <button
                  type="button"
                  onClick={() => setMode('pedestrian')}
                  className={`
                    flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg
                    border-2 transition-all duration-200
                    ${mode === 'pedestrian' 
                      ? 'border-blue-500/70 bg-blue-950/40 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                      : 'border-gray-700/50 bg-gray-800/30 text-gray-400 hover:border-gray-600 hover:bg-gray-800/50'
                    }
                  `}
                >
                  <User className="w-4 h-4" />
                  <span className="text-xs font-medium">Walk</span>
                </button>
              </div>
            </div>

            {/* Error messages now displayed via global toasts */}

            {/* Actions - Emphasized CTA */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={handleCalculate}
                disabled={isCalculating || !startLat || !startLon || !endLat || !endLon}
                className={`
                  flex-1 flex items-center justify-center gap-2 px-4 py-3
                  rounded-xl font-semibold text-sm
                  transition-all duration-200
                  ${isCalculating || !startLat || !startLon || !endLat || !endLon
                    ? 'bg-gray-700/50 text-gray-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-600 text-white shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:scale-[1.02] active:scale-[0.98]'
                  }
                `}
              >
                {isCalculating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Calculating...
                  </>
                ) : (
                  <>
                    <Navigation className="w-4 h-4" />
                    Calculate Route
                  </>
                )}
              </button>
              
              <button
                onClick={handleClear}
                className="px-4 py-3 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 hover:border-gray-600/50 text-gray-400 hover:text-gray-300 rounded-xl font-medium text-sm transition-all duration-200"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
