/**
 * Centralized API configuration
 * All API-related constants are imported from here
 */

// Get API base URL from environment variable with fallback
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// API timeout configuration
export const API_TIMEOUT = parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10)

// Feature flags
export const ENABLE_DEBUG = import.meta.env.VITE_ENABLE_DEBUG === 'true'
export const ENABLE_MAP_CACHE = import.meta.env.VITE_ENABLE_MAP_CACHE !== 'false'
export const ENABLE_MAP_LABELS = import.meta.env.VITE_ENABLE_MAP_LABELS !== 'false'

// API endpoints (for consistency)
export const API_ENDPOINTS = {
  // Map endpoints
  MAP_CONFIG: `${API_BASE_URL}/api/map/config`,
  MAP_TILES: (z: number, x: number, y: number) => `${API_BASE_URL}/api/map/tiles/${z}/${x}/${y}.png`,
  MAP_FEATURES: `${API_BASE_URL}/api/map/features/all`,
  
  // POI endpoints
  POIS_SPATIAL: `${API_BASE_URL}/api/pois/spatial`,
  POIS_HEATMAP: `${API_BASE_URL}/api/pois/spatial/heatmap`,
  POIS_LIGHTWEIGHT: `${API_BASE_URL}/api/pois/lightweight`,
  POIS_DETAIL: (id: string | number) => `${API_BASE_URL}/api/pois/spatial/${id}`,
  POIS_BY_ID: (id: string | number) => `${API_BASE_URL}/api/pois/${id}`,
  
  // Roads endpoints
  ROADS_SPATIAL: `${API_BASE_URL}/api/roads/spatial`,
  
  // Address search
  ADDRESS_SEARCH: `${API_BASE_URL}/api/addresses/search`,
  
  // Financial data
  FINANCIAL_STATEMENTS: `${API_BASE_URL}/financial_statements`,
  FIRMS: `${API_BASE_URL}/firms`,
  FIRM_DEFAULTS: (id: string) => `${API_BASE_URL}/firms/${id}/defaults`,
  SIMULATIONS: `${API_BASE_URL}/simulations`,
  SIMULATION_DETAIL: (id: string) => `${API_BASE_URL}/simulations/${id}`,
  TRANSACTIONS: `${API_BASE_URL}/transactions`,
  
  // GDP endpoints
  GDP_CURRENT: `${API_BASE_URL}/gdp/current`,
  GDP_SECTORS: `${API_BASE_URL}/gdp/sectors`,
  GDP_PERIODS: `${API_BASE_URL}/gdp/periods`,
  
  // Export
  EXPORT_EXCEL: `${API_BASE_URL}/export_excel`,
  
  // Health
  HEALTH: `${API_BASE_URL}/health`,
  
  // Routing endpoints
  ROUTING_ROUTE: `${API_BASE_URL}/api/routing/route`,
  ROUTING_MODES: `${API_BASE_URL}/api/routing/modes`,
  
  // Agent endpoints
  AGENT_SIMULATION_BOUNDS: (simulationId: string) => `${API_BASE_URL}/api/agents/simulation/${simulationId}/bounds`,
  AGENT_LOCATIONS: (simulationId: string) => `${API_BASE_URL}/api/agents/simulation/${simulationId}/locations`,
  AGENTS_LIST: (simulationId: string, limit: number, offset: number) =>
    `${API_BASE_URL}/api/agents/list?simulation_id=${simulationId}&limit=${limit}&offset=${offset}`,
  AGENTS_COUNT: (simulationId: string) => `${API_BASE_URL}/api/agents/count?simulation_id=${simulationId}`,
  AGENT_DETAILS: (agentId: string) => `${API_BASE_URL}/api/agents/${agentId}/details`,
  AGENT_BALANCE_SHEET: (agentId: string, simulationId: string) => `${API_BASE_URL}/api/agents/${agentId}/balance-sheet?simulation_id=${simulationId}`,
  AGENT_HOUSEHOLD_MEMBERS: (agentId: string, simulationId: string) => `${API_BASE_URL}/api/agents/${agentId}/household-members?simulation_id=${simulationId}`,
  AGENT_ACTIVITY: (agentId: string, simulationId: string) => `${API_BASE_URL}/api/agents/${agentId}/activity?simulation_id=${simulationId}`,
  AGENT_POI_KNOWLEDGE: (agentId: string, simulationId: string, limit?: number) => {
    const base = `${API_BASE_URL}/api/agents/${agentId}/poi-knowledge?simulation_id=${simulationId}`
    return typeof limit === 'number' ? `${base}&limit=${limit}` : base
  },
  
  // POI details endpoint
  POI_DETAILS: `${API_BASE_URL}/api/pois/details`,
}

// Helper function to build URL with query params
export function buildApiUrl(endpoint: string, params?: Record<string, any>): string {
  if (!params) return endpoint
  
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      qs.append(key, String(value))
    }
  })
  
  const queryString = qs.toString()
  return queryString ? `${endpoint}?${queryString}` : endpoint
}

// Debug logging (only in development)
if (ENABLE_DEBUG && import.meta.env.DEV) {
  console.log('[API Config]', {
    baseUrl: API_BASE_URL,
    timeout: API_TIMEOUT,
    features: {
      debug: ENABLE_DEBUG,
      mapCache: ENABLE_MAP_CACHE,
      mapLabels: ENABLE_MAP_LABELS,
    }
  })
}
