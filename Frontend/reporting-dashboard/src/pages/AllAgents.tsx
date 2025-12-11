import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { User, MapPin, DollarSign, Users, Home, ArrowUpDown, Search as SearchIcon, Filter } from 'lucide-react'
import { TopBar } from '../components/TopBar'
import { LeftNav } from '../components/LeftNav'
import { useSimulationId } from '../hooks/useSimulationId'
import { API_ENDPOINTS, buildApiUrl } from '../config/api'
import { formatCurrency, getInitials, getPartyColors } from '../utils/agentUtils'
import LoadingSpinner from '../components/shared/LoadingSpinner'

interface AgentListItem {
  agent_id: string
  name: string | null
  age: number | null
  gender: string | null
  city: string | null
  state: string | null
  party: string | null
  net_worth: string | number | null
  household_size: number | null
  home_value: number | null
}

type SortKey = 'name' | 'age' | 'net_worth' | 'household_size' | 'city'
type SortDir = 'asc' | 'desc'

export const AllAgents: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const simulationIdParam = searchParams.get('simulation_id')
  
  const { simulations, simulationId: simId, setSimulationId: setSimId, loading: simLoading } = useSimulationId()
  const [agents, setAgents] = useState<AgentListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [isFetchingMore, setIsFetchingMore] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState<number | null>(null)
  const PAGE_SIZE = 250
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  // Initialize simulation ID from URL
  useEffect(() => {
    if (simulationIdParam && simulationIdParam !== simId) {
      setSimId(simulationIdParam)
    }
  }, [simulationIdParam, simId, setSimId])

  // Reset list when simulation changes
  useEffect(() => {
    setAgents([])
    setOffset(0)
    setHasMore(true)
    setTotal(null)
  }, [simId])

  // Fetch total count once per simulation
  useEffect(() => {
    const fetchTotal = async () => {
      if (!simId) return
      try {
        const res = await fetch(API_ENDPOINTS.AGENTS_COUNT(simId))
        if (!res.ok) throw new Error('Failed to fetch total agents')
        const data = await res.json()
        setTotal(Number(data?.total ?? 0))
      } catch (e) {
        setTotal(null)
      }
    }
    fetchTotal()
  }, [simId])

  // Fetch a page of agents
  const fetchPage = async (pageOffset: number, initial = false) => {
    if (!simId || (!initial && (!hasMore || isFetchingMore))) return

    if (initial) setLoading(true)
    if (!initial) setIsFetchingMore(true)
    setError(null)
    try {
      const url = API_ENDPOINTS.AGENTS_LIST(simId, PAGE_SIZE, pageOffset)
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Failed to fetch agents (status ${res.status})`)
      const data: AgentListItem[] = await res.json()

      setAgents(prev => [...prev, ...(data || [])])
      setOffset(pageOffset + (data?.length || 0))
      if (!data || data.length < PAGE_SIZE) setHasMore(false)
    } catch (e: any) {
      setError(e?.message || 'Failed to load agents')
    } finally {
      if (initial) setLoading(false)
      setIsFetchingMore(false)
    }
  }

  // Initial load
  useEffect(() => {
    if (simId) fetchPage(0, true)
  }, [simId])

  // Infinite scroll via IntersectionObserver
  useEffect(() => {
    if (!sentinelRef.current) return
    const node = sentinelRef.current
    const observer = new IntersectionObserver((entries) => {
      const first = entries[0]
      if (first.isIntersecting) {
        fetchPage(offset)
      }
    }, { root: null, rootMargin: '600px', threshold: 0 })
    observer.observe(node)
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sentinelRef.current, offset, hasMore, isFetchingMore, simId])

  // Filter and sort agents
  const filteredAgents = agents
    .filter(agent => {
      if (!searchQuery.trim()) return true
      const query = searchQuery.toLowerCase()
      return (
        agent.agent_id.toLowerCase().includes(query) ||
        agent.name?.toLowerCase().includes(query) ||
        agent.city?.toLowerCase().includes(query) ||
        agent.state?.toLowerCase().includes(query)
      )
    })
    .sort((a, b) => {
      let aVal: any = a[sortKey]
      let bVal: any = b[sortKey]
      
      if (sortKey === 'name') {
        aVal = (a.name || '').toLowerCase()
        bVal = (b.name || '').toLowerCase()
      }
      
      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1
      
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
      return 0
    })

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const simOptions = (simulations.length
    ? simulations.map((s: any) => ({
        label: s.created_at ? `${s.id} — ${new Date(s.created_at).toLocaleString()}` : s.id,
        value: s.id
      }))
    : [{ label: 'Latest', value: 'latest' }]
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <TopBar
        simulationId={simId}
        setSimulationId={setSimId}
        simulationOptions={simOptions}
        simulationLoading={simLoading}
      />
      <LeftNav />

      <div className="pt-16 min-h-screen">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-6">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-white mb-2">All Agents</h1>
            <p className="text-sm text-slate-400">
              {total !== null ? total : '—'} agents in simulation {simId}
            </p>
          </div>

          {/* Search and filters */}
          <div className="mb-6 flex gap-4">
            <div className="flex-1 relative">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search by ID, name, or location..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
              />
            </div>
          </div>

          {/* Agents table */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size={32} />
            </div>
          ) : error ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center">
              <p className="text-red-400">{error}</p>
            </div>
          ) : (
            <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl overflow-hidden shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
              <div className="overflow-x-auto">
                <table className="w-full table-auto divide-y divide-slate-800 text-sm">
                  <thead className="bg-slate-900/70">
                    <tr className="text-slate-300 text-[11px] uppercase tracking-wide">
                      <th className="px-3 py-3 text-left">Agent</th>
                      <th className="px-3 py-3 text-left">Location</th>
                      <th className="px-3 py-3 text-right cursor-pointer hover:text-white transition-colors" onClick={() => toggleSort('age')}>
                        <div className="flex items-center gap-1 justify-end">
                          Age {sortKey === 'age' && <ArrowUpDown className="w-3 h-3" />}
                        </div>
                      </th>
                      <th className="px-3 py-3 text-right cursor-pointer hover:text-white transition-colors" onClick={() => toggleSort('net_worth')}>
                        <div className="flex items-center gap-1 justify-end">
                          Net Worth {sortKey === 'net_worth' && <ArrowUpDown className="w-3 h-3" />}
                        </div>
                      </th>
                      <th className="px-3 py-3 text-right cursor-pointer hover:text-white transition-colors" onClick={() => toggleSort('household_size')}>
                        <div className="flex items-center gap-1 justify-end">
                          Household {sortKey === 'household_size' && <ArrowUpDown className="w-3 h-3" />}
                        </div>
                      </th>
                      <th className="px-3 py-3 text-left">Party</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-200">
                    {filteredAgents.map((agent) => {
                      const partyColors = agent.party ? getPartyColors(agent.party) : null
                      return (
                        <tr
                          key={agent.agent_id}
                          onClick={() => navigate(`/agent/${agent.agent_id}?simulation_id=${simId}`)}
                          className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                        >
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-slate-300">
                                {getInitials(agent.name)}
                              </div>
                              <div>
                                <div className="font-medium text-white">
                                  {agent.name || 'Unnamed Agent'}
                                </div>
                                <div className="text-xs text-slate-500 font-mono">
                                  {agent.agent_id}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-1 text-sm">
                              <MapPin className="w-3 h-3 text-slate-500" />
                              {agent.city && agent.state ? `${agent.city}, ${agent.state}` : agent.city || agent.state || '—'}
                            </div>
                          </td>
                          <td className="px-3 py-3 text-right">
                            {agent.age || '—'}
                            {agent.gender && `, ${agent.gender.charAt(0)}`}
                          </td>
                          <td className="px-3 py-3 text-right">
                            {agent.net_worth !== null && agent.net_worth !== undefined 
                              ? (typeof agent.net_worth === 'number' 
                                  ? formatCurrency(agent.net_worth) 
                                  : String(agent.net_worth))
                              : '—'}
                          </td>
                          <td className="px-3 py-3 text-right">
                            <div className="flex items-center gap-1 justify-end">
                              <Users className="w-3 h-3 text-slate-500" />
                              {agent.household_size || '—'}
                            </div>
                          </td>
                          <td className="px-3 py-3">
                            {agent.party && partyColors ? (
                              <span className={`px-2 py-0.5 rounded text-xs ${partyColors.bg} ${partyColors.text}`}>
                                {agent.party.length > 15 ? agent.party.substring(0, 15) + '...' : agent.party}
                              </span>
                            ) : (
                              '—'
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              {/* Infinite scroll sentinel */}
              <div ref={sentinelRef} />

              {filteredAgents.length === 0 && (
                <div className="py-12 text-center text-slate-400">
                  <User className="w-12 h-12 mx-auto mb-3 text-slate-600" />
                  <p>No agents found matching your search</p>
                </div>
              )}

              {isFetchingMore && (
                <div className="flex items-center justify-center py-4 text-slate-400 text-sm">
                  Loading more…
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

