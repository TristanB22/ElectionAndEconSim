import React, { useState, useEffect, useMemo, useRef } from 'react'
import { Calendar, Clock, Play, Pause, StepBack, StepForward, X } from 'lucide-react'
import { LAYOUT } from '../../layout'
import { MAP_CONTROL_STYLES, createMapControlStyle } from '../../styles/mapControls'
import { CalendarPicker } from './CalendarPicker'

interface SimulationTimelineProps {
  simulationId: string | null
  startDatetime: Date | null
  endDatetime: Date | null
  currentDatetime: Date | null
  onDatetimeChange: (datetime: Date) => void
  categoryPanelVisible?: boolean // Whether the category panel is showing on the left
  timeStepMinutes?: number // Granularity from simulation config (default: 1 minute)
  zoom?: number // Current map zoom level for display
}

export const SimulationTimeline: React.FC<SimulationTimelineProps> = ({
  simulationId,
  startDatetime,
  endDatetime,
  currentDatetime,
  onDatetimeChange,
  categoryPanelVisible = false,
  timeStepMinutes = 1, // Default to 1 minute if not provided
  zoom,
}) => {
  // Local state for date and time
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [selectedTime, setSelectedTime] = useState<string>('12:00')
  const [playing, setPlaying] = useState(false)
  const [showCalendar, setShowCalendar] = useState(false)
  const playIntervalRef = useRef<NodeJS.Timeout | null>(null)
  
  // Calculate total steps based on granularity
  const totalSteps = useMemo(() => {
    return Math.floor((24 * 60) / timeStepMinutes)
  }, [timeStepMinutes])
  
  // Format granularity for display
  const granularityLabel = useMemo(() => {
    if (timeStepMinutes >= 60) {
      const hours = Math.floor(timeStepMinutes / 60)
      return `${hours}h`
    }
    return `${timeStepMinutes}m`
  }, [timeStepMinutes])

  // Initialize from currentDatetime or startDatetime
  useEffect(() => {
    const initial = currentDatetime || startDatetime
    if (initial) {
      setSelectedDate(formatDateForInput(initial))
      setSelectedTime(formatTimeForInput(initial))
    }
  }, [currentDatetime, startDatetime])

  // Compute min/max dates for date picker
  const minDate = useMemo(() => {
    return startDatetime ? formatDateForInput(startDatetime) : ''
  }, [startDatetime])

  const maxDate = useMemo(() => {
    return endDatetime ? formatDateForInput(endDatetime) : ''
  }, [endDatetime])

  // Handle date change
  const handleDateChange = (newDate: string) => {
    setSelectedDate(newDate)
    emitDatetime(newDate, selectedTime)
  }

  // Handle time slider change (with hard clamp to avoid flicker)
  const handleTimeChange = (newTime: string) => {
    if (!selectedDate) return
    const candidate = new Date(`${selectedDate}T${newTime}:00`)

    // Clamp to bounds before emitting to parent and before updating UI state
    if (startDatetime && candidate < startDatetime) {
      const clamped = startDatetime
      setSelectedDate(formatDateForInput(clamped))
      setSelectedTime(formatTimeForInput(clamped))
      onDatetimeChange(clamped)
      return
    }
    if (endDatetime && candidate > endDatetime) {
      const clamped = endDatetime
      setSelectedDate(formatDateForInput(clamped))
      setSelectedTime(formatTimeForInput(clamped))
      onDatetimeChange(clamped)
      return
    }

    setSelectedTime(newTime)
    onDatetimeChange(candidate)
  }

  // Emit combined datetime to parent
  const emitDatetime = (date: string, time: string) => {
    if (!date || !time) return
    
    const combined = new Date(`${date}T${time}:00`)
    
    // Clamp to simulation bounds
    if (startDatetime && combined < startDatetime) {
      onDatetimeChange(startDatetime)
      return
    }
    if (endDatetime && combined > endDatetime) {
      onDatetimeChange(endDatetime)
      return
    }
    
    onDatetimeChange(combined)
  }

  // Play/pause functionality - respects granularity
  useEffect(() => {
    if (playing) {
      const intervalMs = Math.min(1000, timeStepMinutes * 60 * 1000) // Update every second or granularity (whichever is shorter)
      playIntervalRef.current = setInterval(() => {
        const current = new Date(`${selectedDate}T${selectedTime}:00`)
        const nextStep = new Date(current.getTime() + timeStepMinutes * 60000) // Add time step
        
        if (endDatetime && nextStep > endDatetime) {
          setPlaying(false)
          return
        }
        
        setSelectedDate(formatDateForInput(nextStep))
        setSelectedTime(formatTimeForInput(nextStep))
        onDatetimeChange(nextStep)
      }, intervalMs)
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current)
        playIntervalRef.current = null
      }
    }
    
    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current)
      }
    }
  }, [playing, selectedDate, selectedTime, endDatetime, onDatetimeChange, timeStepMinutes])

  // Step forward (by granularity)
  const handleStepForward = () => {
    const current = new Date(`${selectedDate}T${selectedTime}:00`)
    const next = new Date(current.getTime() + timeStepMinutes * 60000) // Add time step
    
    if (endDatetime && next > endDatetime) {
      setSelectedDate(formatDateForInput(endDatetime))
      setSelectedTime(formatTimeForInput(endDatetime))
      onDatetimeChange(endDatetime)
    } else {
      setSelectedDate(formatDateForInput(next))
      setSelectedTime(formatTimeForInput(next))
      onDatetimeChange(next)
    }
  }

  // Step back (by granularity)
  const handleStepBack = () => {
    const current = new Date(`${selectedDate}T${selectedTime}:00`)
    const prev = new Date(current.getTime() - timeStepMinutes * 60000) // Subtract time step
    
    if (startDatetime && prev < startDatetime) {
      setSelectedDate(formatDateForInput(startDatetime))
      setSelectedTime(formatTimeForInput(startDatetime))
      onDatetimeChange(startDatetime)
    } else {
      setSelectedDate(formatDateForInput(prev))
      setSelectedTime(formatTimeForInput(prev))
      onDatetimeChange(prev)
    }
  }

  // Toggle play/pause
  const handlePlayPause = () => {
    setPlaying(!playing)
  }

  // Don't render if no simulation or no bounds
  if (!simulationId || !startDatetime || !endDatetime) {
    return null
  }

  // Calculate positioning based on category panel visibility and screen size
  const getTimelineStyles = (): React.CSSProperties => {
    const baseStyles: React.CSSProperties = {
      maxWidth: LAYOUT.TIMELINE.MAX_WIDTH,
    }
    
    // On small screens: full width from edges
    // On large screens: always centered
    return {
      ...baseStyles,
    }
  }

  // Get container classes based on category panel visibility
  const getContainerClasses = () => {
    const baseClasses = 'absolute bottom-6 z-30 transition-all duration-300'
    
    // On small screens: full width with padding
    // On large screens: always centered
    return `${baseClasses} left-1/2 -translate-x-1/2 w-[calc(100%-3rem)] lg:w-auto`
  }

  return (
    <div
      className={getContainerClasses()}
      style={getTimelineStyles()}
    >
      <div
        className={`${MAP_CONTROL_STYLES.borderRadius} ${MAP_CONTROL_STYLES.border} ${MAP_CONTROL_STYLES.backdropBlur} ${MAP_CONTROL_STYLES.shadow} ${MAP_CONTROL_STYLES.transition}`}
        style={createMapControlStyle('primary')}
      >
        {/* Two-layer layout: Top = slider, Bottom = controls */}
        <div className="px-4 py-3 space-y-3">
          {/* Top Layer: Time slider with labels */}
          <div className="flex items-center gap-2">
            <span className={`${MAP_CONTROL_STYLES.text.timeDisplay} flex-shrink-0 text-xs`}>00:00</span>
            <input
              type="range"
              min="0"
              max="1439"
              step={timeStepMinutes}
              value={timeToMinutes(selectedTime)}
              onChange={(e) => {
                const rawMinutes = parseInt(e.target.value)
                const snappedMinutes = Math.round(rawMinutes / timeStepMinutes) * timeStepMinutes
                const clampedMinutes = Math.min(1439, Math.max(0, snappedMinutes))
                handleTimeChange(minutesToTime(clampedMinutes))
              }}
              className="flex-1 h-1.5 rounded-lg appearance-none cursor-pointer bg-white/20 hover:bg-white/25 transition-colors"
              style={{ accentColor: '#60a5fa' }}
              title={`Adjust time (${granularityLabel} increments)`}
            />
            <span className={`${MAP_CONTROL_STYLES.text.timeDisplay} flex-shrink-0 text-xs`}>23:59</span>
          </div>

          {/* Bottom Layer: Centered controls in one line */}
          <div className="flex items-center justify-center gap-2">
            {/* Clock icon */}
            <Clock className="w-4 h-4 text-white/80 flex-shrink-0" />
            
            {/* Zoom badge - show on small screens only */}
            {zoom !== undefined && (
              <span className={`${MAP_CONTROL_STYLES.text.badge} ${MAP_CONTROL_STYLES.text.badgeBg} ${MAP_CONTROL_STYLES.text.badgeText} lg:hidden`} title="Map zoom level">
                z{Math.round(zoom)}
              </span>
            )}
            
            {/* Date badge */}
            <span className={`${MAP_CONTROL_STYLES.text.badge} ${MAP_CONTROL_STYLES.text.badgeBg} ${MAP_CONTROL_STYLES.text.badgeText}`}>
              {selectedDate || '—'}
            </span>
            
            {/* Granularity badge - show on large screens */}
            <span className={`${MAP_CONTROL_STYLES.text.badge} bg-blue-500/20 text-blue-300 border-blue-400/30 hidden lg:inline-block`} title={`Time step: ${timeStepMinutes} minutes`}>
              {granularityLabel}
            </span>

            {/* Divider */}
            <div className="w-px h-5 bg-white/10" />

            {/* Play/Pause button */}
            <button 
              onClick={handlePlayPause}
              aria-label={playing ? 'Pause' : 'Play'} 
              className={`w-8 h-8 rounded-lg ${MAP_CONTROL_STYLES.button.base} ${MAP_CONTROL_STYLES.button.hover} bg-white/5 border border-white/10 flex items-center justify-center`}
            >
              {playing ? <Pause className="w-4 h-4 text-white/80" /> : <Play className="w-4 h-4 text-white/80" />}
            </button>
            
            {/* Step buttons - show on medium+ screens */}
            <button 
              onClick={handleStepBack}
              aria-label={`Step back ${granularityLabel}`}
              className={`w-8 h-8 rounded-lg ${MAP_CONTROL_STYLES.button.base} ${MAP_CONTROL_STYLES.button.hover} bg-white/5 border border-white/10 items-center justify-center hidden md:flex`}
            >
              <StepBack className="w-4 h-4 text-white/80" />
            </button>
            <button 
              onClick={handleStepForward}
              aria-label={`Step forward ${granularityLabel}`}
              className={`w-8 h-8 rounded-lg ${MAP_CONTROL_STYLES.button.base} ${MAP_CONTROL_STYLES.button.hover} bg-white/5 border border-white/10 items-center justify-center hidden md:flex`}
            >
              <StepForward className="w-4 h-4 text-white/80" />
            </button>

            {/* Divider */}
            <div className="w-px h-5 bg-white/10 hidden md:block" />
            
            {/* Calendar button */}
            <button 
              onClick={() => setShowCalendar(!showCalendar)}
              aria-label="Pick date" 
              className={`w-8 h-8 rounded-lg ${MAP_CONTROL_STYLES.button.base} ${MAP_CONTROL_STYLES.button.hover} bg-white/5 border border-white/10 flex items-center justify-center`}
            >
              <Calendar className="w-4 h-4 text-white/80" />
            </button>
            
            {/* Time display */}
            <div className={`${MAP_CONTROL_STYLES.text.timeDisplayLarge} min-w-[56px] text-center font-mono`}>
              {selectedTime}
            </div>
          </div>
        </div>
      </div>
      
      {/* Calendar Picker Modal */}
      {showCalendar && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/30 z-30"
            onClick={() => setShowCalendar(false)}
          />
          
          {/* Calendar */}
          <div 
            className={`fixed bottom-20 left-1/2 -translate-x-1/2 z-40 ${MAP_CONTROL_STYLES.borderRadius} ${MAP_CONTROL_STYLES.border} ${MAP_CONTROL_STYLES.backdropBlur} w-auto max-w-3xl md:w-[52rem]`}
            style={{
              ...createMapControlStyle('primary'),
              boxShadow: '0 20px 60px rgba(0,0,0,0.4)'
            }}
          >
            <div className="flex items-center justify-between px-4 pt-4">
              <h3 className="text-sm font-semibold text-white">Select Date & Time</h3>
              <button 
                onClick={() => setShowCalendar(false)}
                className="w-6 h-6 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4 text-white/80" />
              </button>
            </div>
            
            {/* Two-column responsive layout: calendar | time + actions */}
            <div className="md:grid md:grid-cols-2 md:gap-2">
              {/* Calendar Component */}
              <div>
                <CalendarPicker
                  selectedDate={currentDatetime || startDatetime || new Date()}
                  minDate={startDatetime || new Date()}
                  maxDate={endDatetime || new Date()}
                  onDateSelect={(date) => {
                    setSelectedDate(formatDateForInput(date))
                    setSelectedTime(formatTimeForInput(date))
                    onDatetimeChange(date)
                    setShowCalendar(false)
                  }}
                />
              </div>

              {/* Right column: Time input and quick actions */}
              <div className="px-4 pb-4 md:pb-4 md:border-l md:border-white/10 flex flex-col">
                <div className="pb-3 md:pt-4">
                  <label className="text-xs text-white/60 mb-2 block mt-3 md:mt-0">Time</label>
                  <input
                    type="time"
                    value={selectedTime}
                    onChange={(e) => handleTimeChange(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border text-white text-sm bg-white/5 hover:bg-white/10 transition-colors"
                    style={{
                      borderColor: 'rgba(255, 255, 255, 0.1)',
                      colorScheme: 'dark'
                    }}
                  />
                </div>

                {/* Quick Actions */}
                <div className="flex gap-2 mt-auto">
                  <button
                    onClick={() => {
                      if (startDatetime) {
                        setSelectedDate(formatDateForInput(startDatetime))
                        setSelectedTime(formatTimeForInput(startDatetime))
                        onDatetimeChange(startDatetime)
                        setShowCalendar(false)
                      }
                    }}
                    className="flex-1 px-3 py-2 rounded-lg text-xs font-medium text-white/80 bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
                  >
                    Go to Start
                  </button>
                  <button
                    onClick={() => {
                      if (endDatetime) {
                        setSelectedDate(formatDateForInput(endDatetime))
                        setSelectedTime(formatTimeForInput(endDatetime))
                        onDatetimeChange(endDatetime)
                        setShowCalendar(false)
                      }
                    }}
                    className="flex-1 px-3 py-2 rounded-lg text-xs font-medium text-white/80 bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
                  >
                    Go to End
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// Helper functions
function formatDateForInput(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatTimeForInput(date: Date): string {
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}

function timeToMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number)
  return hours * 60 + minutes
}

function minutesToTime(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`
}

