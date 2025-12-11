import React, { useState, useMemo } from 'react'
import { ChevronLeft, ChevronRight, ChevronDown } from 'lucide-react'
import { MAP_CONTROL_STYLES, createMapControlStyle } from '../../styles/mapControls'

interface CalendarPickerProps {
  selectedDate: Date
  minDate: Date
  maxDate: Date
  onDateSelect: (date: Date) => void
}

export function CalendarPicker({ selectedDate, minDate, maxDate, onDateSelect }: CalendarPickerProps) {
  const [viewYear, setViewYear] = useState(selectedDate.getFullYear())
  const [viewMonth, setViewMonth] = useState(selectedDate.getMonth())
  const [showYearPicker, setShowYearPicker] = useState(false)
  
  // Calculate valid year range
  const validYears = useMemo(() => {
    const years: number[] = []
    for (let year = minDate.getFullYear(); year <= maxDate.getFullYear(); year++) {
      years.push(year)
    }
    return years
  }, [minDate, maxDate])
  
  // Check if a month is selectable for the current view year
  const isMonthSelectable = (month: number): boolean => {
    const firstDayOfMonth = new Date(viewYear, month, 1)
    const lastDayOfMonth = new Date(viewYear, month + 1, 0)
    return firstDayOfMonth <= maxDate && lastDayOfMonth >= minDate
  }
  
  // Check if a day is selectable
  const isDaySelectable = (day: number): boolean => {
    const date = new Date(viewYear, viewMonth, day)
    return date >= minDate && date <= maxDate
  }
  
  // Get days in month
  const daysInMonth = useMemo(() => {
    return new Date(viewYear, viewMonth + 1, 0).getDate()
  }, [viewYear, viewMonth])
  
  // Get first day of month (0 = Sunday, 6 = Saturday)
  const firstDayOfMonth = useMemo(() => {
    return new Date(viewYear, viewMonth, 1).getDay()
  }, [viewYear, viewMonth])
  
  // Generate calendar grid
  const calendarDays = useMemo(() => {
    const days: (number | null)[] = []
    
    // Add empty cells for days before the first day of month
    for (let i = 0; i < firstDayOfMonth; i++) {
      days.push(null)
    }
    
    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(day)
    }
    
    return days
  }, [firstDayOfMonth, daysInMonth])
  
  const handleDayClick = (day: number) => {
    if (!isDaySelectable(day)) return
    
    const newDate = new Date(viewYear, viewMonth, day, selectedDate.getHours(), selectedDate.getMinutes())
    onDateSelect(newDate)
  }
  
  const handlePrevMonth = () => {
    if (viewMonth === 0) {
      setViewYear(viewYear - 1)
      setViewMonth(11)
    } else {
      setViewMonth(viewMonth - 1)
    }
  }
  
  const handleNextMonth = () => {
    if (viewMonth === 11) {
      setViewYear(viewYear + 1)
      setViewMonth(0)
    } else {
      setViewMonth(viewMonth + 1)
    }
  }
  
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  
  const canGoPrev = viewYear > minDate.getFullYear() || (viewYear === minDate.getFullYear() && viewMonth > minDate.getMonth())
  const canGoNext = viewYear < maxDate.getFullYear() || (viewYear === maxDate.getFullYear() && viewMonth < maxDate.getMonth())
  
  return (
    <div className="p-4">
      {/* Month/Year Header */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={handlePrevMonth}
          disabled={!canGoPrev}
          className={`p-2 rounded-lg transition-colors ${
            canGoPrev 
              ? 'hover:bg-white/10 text-white/80' 
              : 'opacity-30 cursor-not-allowed text-white/30'
          }`}
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowYearPicker(!showYearPicker)}
            className="px-3 py-1.5 rounded-lg hover:bg-white/10 text-white font-medium transition-colors flex items-center gap-1"
          >
            {monthNames[viewMonth]} {viewYear}
            <ChevronDown className={`w-4 h-4 transition-transform ${showYearPicker ? 'rotate-180' : ''}`} />
          </button>
        </div>
        
        <button
          onClick={handleNextMonth}
          disabled={!canGoNext}
          className={`p-2 rounded-lg transition-colors ${
            canGoNext 
              ? 'hover:bg-white/10 text-white/80' 
              : 'opacity-30 cursor-not-allowed text-white/30'
          }`}
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      
      {/* Year/Month Picker Dropdown */}
      {showYearPicker && (
        <div className="mb-4 p-3 rounded-lg bg-white/5 border border-white/10 max-h-48 overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.2) transparent' }}>
          <div className="grid grid-cols-3 gap-2">
            {validYears.map(year => (
              <button
                key={year}
                onClick={() => {
                  setViewYear(year)
                  setShowYearPicker(false)
                }}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  year === viewYear
                    ? 'bg-blue-500 text-white'
                    : 'text-white/70 hover:bg-white/10'
                }`}
              >
                {year}
              </button>
            ))}
          </div>
          
          <div className="mt-3 pt-3 border-t border-white/10">
            <div className="grid grid-cols-3 gap-2">
              {monthNames.map((month, idx) => {
                const selectable = isMonthSelectable(idx)
                return (
                  <button
                    key={month}
                    onClick={() => {
                      if (selectable) {
                        setViewMonth(idx)
                        setShowYearPicker(false)
                      }
                    }}
                    disabled={!selectable}
                    className={`px-2 py-1.5 rounded text-xs font-medium transition-colors ${
                      idx === viewMonth && viewYear === viewYear
                        ? 'bg-blue-500 text-white'
                        : selectable
                        ? 'text-white/70 hover:bg-white/10'
                        : 'text-white/20 cursor-not-allowed'
                    }`}
                  >
                    {month.slice(0, 3)}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}
      
      {/* Day Names */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {dayNames.map(day => (
          <div key={day} className="text-center text-xs font-medium text-white/50 py-1">
            {day}
          </div>
        ))}
      </div>
      
      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-1">
        {calendarDays.map((day, idx) => {
          if (day === null) {
            return <div key={`empty-${idx}`} className="aspect-square" />
          }
          
          const selectable = isDaySelectable(day)
          const isSelected = 
            day === selectedDate.getDate() && 
            viewMonth === selectedDate.getMonth() && 
            viewYear === selectedDate.getFullYear()
          
          return (
            <button
              key={day}
              onClick={() => handleDayClick(day)}
              disabled={!selectable}
              className={`aspect-square rounded-lg text-sm font-medium transition-all ${
                isSelected
                  ? 'bg-blue-500 text-white ring-2 ring-blue-400'
                  : selectable
                  ? 'text-white/80 hover:bg-white/10 hover:scale-105'
                  : 'text-white/20 cursor-not-allowed'
              }`}
            >
              {day}
            </button>
          )
        })}
      </div>
    </div>
  )
}

