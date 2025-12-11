import { useEffect, useState, useRef } from 'react'
import axios from 'axios'
import { API_ENDPOINTS } from '../config/api'

export type Simulation = { 
  id: string
  created_at?: string
  tick_granularity?: string  // e.g., "15m", "1m", "1h"
  time_step_minutes?: number // Parsed from tick_granularity
}

const STORAGE_KEY = 'wsim_simulation_id'
const SIMULATIONS_CACHE_KEY = 'wsim_simulations_cache'
const CACHE_DURATION = 60000 // Cache simulations for 60 seconds

/**
 * Parse tick_granularity string to minutes
 * Examples: "15m" -> 15, "1h" -> 60, "30s" -> 0.5
 */
function parseTickGranularity(tickGranularity?: string): number {
  if (!tickGranularity) return 1 // Default to 1 minute
  
  const match = tickGranularity.match(/^(\d+(?:\.\d+)?)(s|m|h)$/)
  if (!match) return 1
  
  const value = parseFloat(match[1])
  const unit = match[2]
  
  switch (unit) {
    case 's': return value / 60  // seconds to minutes
    case 'm': return value        // already in minutes
    case 'h': return value * 60   // hours to minutes
    default: return 1
  }
}

/**
 * Load cached simulations from localStorage
 */
function loadCachedSimulations(): Simulation[] | null {
  try {
    const cached = localStorage.getItem(SIMULATIONS_CACHE_KEY)
    if (!cached) return null
    
    const { simulations, timestamp } = JSON.parse(cached)
    
    // Check if cache is still valid
    if (Date.now() - timestamp > CACHE_DURATION) {
      localStorage.removeItem(SIMULATIONS_CACHE_KEY)
      return null
    }
    
    return simulations
  } catch (e) {
    console.error('Failed to load cached simulations:', e)
    return null
  }
}

/**
 * Save simulations to localStorage cache
 */
function saveCachedSimulations(simulations: Simulation[]) {
  try {
    localStorage.setItem(SIMULATIONS_CACHE_KEY, JSON.stringify({
      simulations,
      timestamp: Date.now()
    }))
  } catch (e) {
    console.error('Failed to cache simulations:', e)
  }
}

export function useSimulationId() {
  // Initialize with cached simulations if available
  const [simulations, setSimulations] = useState<Simulation[]>(() => {
    return loadCachedSimulations() || []
  })
  const [simulationId, setSimulationIdState] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const intervalRef = useRef<number | null>(null)
  const isInitialFetch = useRef(true)

  const fetchSims = async (showLoading = true) => {
    // Only show loading state on initial fetch or manual refresh
    if (showLoading) {
      setLoading(true)
    }
    setError('')
    try {
      const res = await axios.get(API_ENDPOINTS.SIMULATIONS)
      const raw: any[] = Array.isArray(res.data) ? res.data : []
      // Normalize ids to strings and parse tick_granularity
      const sims: Simulation[] = raw.map((r) => ({
        id: String(r.id),
        created_at: r.created_at,
        tick_granularity: r.tick_granularity || '15m',
        time_step_minutes: parseTickGranularity(r.tick_granularity || '15m')
      }))
      // Sort by created_at in descending order (most recent first)
      const sortedSims = [...sims].sort((a, b) => {
        const aTime = new Date(a.created_at || 0).getTime()
        const bTime = new Date(b.created_at || 0).getTime()
        return bTime - aTime
      })
      
      setSimulations(sortedSims)
      saveCachedSimulations(sortedSims) // Cache the simulations
      
      if (!simulationId && sortedSims.length > 0) {
        // Default to the most recent simulation
        setSimulationIdState(String(sortedSims[0].id))
      }
    } catch (e) {
      console.error('Failed to fetch simulations:', e)
      setError('Failed to load simulations')
      // Fallback: provide a single "Latest" virtual option
      setSimulations([{ id: 'latest' }])
      if (!simulationId) setSimulationIdState('latest')
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) setSimulationIdState(saved)
  }, [])

  useEffect(() => {
    // Initial fetch with loading indicator
    fetchSims(true)
    // Start polling every 15 seconds without loading indicator
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    intervalRef.current = window.setInterval(() => fetchSims(false), 15000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const setSimulationId = (id: string | null) => {
    setSimulationIdState(id)
    if (id) localStorage.setItem(STORAGE_KEY, id)
    else localStorage.removeItem(STORAGE_KEY)
  }

  return { 
    simulations, 
    simulationId, 
    setSimulationId, 
    loading, 
    error, 
    refresh: () => fetchSims(true) // Manual refresh shows loading
  }
}


