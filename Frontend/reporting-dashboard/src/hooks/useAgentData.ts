import { useState, useEffect, useCallback } from 'react'
import { API_ENDPOINTS, buildApiUrl } from '../config/api'

export interface AgentBalanceSheet {
  household_id: string
  balance_sheet: {
    primaryHomeValue: number
    secondaryREValue: number
    retirementAccounts: number
    taxableInvestments: number
    liquidSavings: number
    vehiclesValue: number
    durablesOther: number
    mortgageBalance: number
    autoLoans: number
    creditCardRevolving: number
    studentLoans: number
    otherDebt: number
    assetsTotal: number
    liabilitiesTotal: number
    netWorth: number
    sim_clock_datetime: string
    net_worth_bucket: string
  } | null
  household_members: Array<{
    agent_id: string
    name: string | null
    created_at: string
  }>
}

export interface AgentActivity {
  actions: Array<{
    action_id: number
    action_name: string
    timestamp: string
    status: string
    action_params: any
    execution_time_ms: number
  }>
  transactions: Array<{
    transaction_id: number
    transaction_type: string
    from_entity: string
    to_entity: string
    amount: number
    created_at: string
  }>
}

/**
 * Hook for fetching agent balance sheet data
 */
export function useAgentBalanceSheet(agentId: string | null, simulationId: string | null) {
  const [data, setData] = useState<AgentBalanceSheet | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchBalanceSheet = useCallback(async () => {
    if (!agentId || !simulationId) {
      setData(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const url = API_ENDPOINTS.AGENT_BALANCE_SHEET(agentId, simulationId)
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`Failed to fetch balance sheet: ${response.statusText}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      console.error('Error fetching balance sheet:', err)
    } finally {
      setLoading(false)
    }
  }, [agentId, simulationId])

  useEffect(() => {
    fetchBalanceSheet()
  }, [fetchBalanceSheet])

  return { data, loading, error, refetch: fetchBalanceSheet }
}

/**
 * Hook for fetching agent activity data
 */
export function useAgentActivity(agentId: string | null, simulationId: string | null, limit: number = 100) {
  const [data, setData] = useState<AgentActivity | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchActivity = useCallback(async () => {
    if (!agentId || !simulationId) {
      setData(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const url = API_ENDPOINTS.AGENT_ACTIVITY(agentId, simulationId)
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`Failed to fetch activity: ${response.statusText}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      console.error('Error fetching activity:', err)
    } finally {
      setLoading(false)
    }
  }, [agentId, simulationId, limit])

  useEffect(() => {
    fetchActivity()
  }, [fetchActivity])

  return { data, loading, error, refetch: fetchActivity }
}

/**
 * Hook for fetching household members
 */
export function useHouseholdMembers(agentId: string | null, simulationId: string | null) {
  const [data, setData] = useState<{ household_id: string; members: any[] } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMembers = useCallback(async () => {
    if (!agentId || !simulationId) {
      setData(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const url = API_ENDPOINTS.AGENT_HOUSEHOLD_MEMBERS(agentId, simulationId)
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`Failed to fetch household members: ${response.statusText}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      console.error('Error fetching household members:', err)
    } finally {
      setLoading(false)
    }
  }, [agentId, simulationId])

  useEffect(() => {
    fetchMembers()
  }, [fetchMembers])

  return { data, loading, error, refetch: fetchMembers }
}

export interface AgentPoiKnowledgeRow {
  osm_id: number
  name?: string
  display_name?: string
  category_name: string
  subcategory_name: string
  category_display_name?: string
  distance_km_from_home: number
  times_seen: number
  number_of_times_visited: number
  first_time_seen: string
  last_time_seen: string
  last_time_visited: string
  knowledge_strength: number
  familiarity_score?: number
  recency_days?: number
  visit_frequency?: number
  source?: string
}

export function useAgentPoiKnowledge(agentId: string | null, simulationId: string | null, limit: number = 200) {
  const [data, setData] = useState<AgentPoiKnowledgeRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchKnowledge = useCallback(async () => {
    if (!agentId || !simulationId) {
      setData([])
      return
    }

    setLoading(true)
    setError(null)

    try {
      const url = API_ENDPOINTS.AGENT_POI_KNOWLEDGE(agentId, simulationId, limit)
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Failed to fetch agent POI knowledge: ${response.statusText}`)
      }
      const result = await response.json()
      if (result && Array.isArray(result.pois)) {
        setData(result.pois.map((item: any) => ({
          ...item,
          distance_km_from_home: Number(item.distance_km_from_home ?? 0),
          knowledge_strength: Number(item.knowledge_strength ?? 0),
          times_seen: Number(item.times_seen ?? 0),
          number_of_times_visited: Number(item.number_of_times_visited ?? 0),
          familiarity_score: item.familiarity_score != null ? Number(item.familiarity_score) : undefined,
          recency_days: item.recency_days != null ? Number(item.recency_days) : undefined,
          visit_frequency: item.visit_frequency != null ? Number(item.visit_frequency) : undefined,
        })))
      } else {
        setData([])
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      console.error('Error fetching agent POI knowledge:', err)
    } finally {
      setLoading(false)
    }
  }, [agentId, simulationId, limit])

  useEffect(() => {
    fetchKnowledge()
  }, [fetchKnowledge])

  return { data, loading, error, refetch: fetchKnowledge }
}
