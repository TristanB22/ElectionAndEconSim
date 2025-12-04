import React, { useMemo, useState, useEffect } from 'react'
import { BarChart3, Calendar, Clock, RefreshCw, TrendingUp } from 'lucide-react'
import { TopBar } from '../components/TopBar'
import { useSimulationId } from '../hooks/useSimulationId'
import { LeftNav } from '../components/LeftNav'
import { API_ENDPOINTS, buildApiUrl } from '../config/api'

const granularities = ['Monthly', 'Quarterly', 'Yearly'] as const

export default function GDP() {
  const { simulations, simulationId, setSimulationId, loading: simLoading } = useSimulationId()
  const simOptions = useMemo(() => (simulations.length
    ? simulations.map(s => ({ 
        label: s.start_datetime ? `${s.id} — ${new Date(s.start_datetime).toLocaleDateString()} (Simulation Date)` : s.id, 
        value: s.id 
      }))
    : [{ label: 'Latest', value: 'latest' }]
  ), [simulations])
  const [gStart, setGStart] = useState<string>('')
  const [gEnd, setGEnd] = useState<string>('')
  const [gGran, setGGran] = useState<typeof granularities[number]>('Quarterly')
  const [gLoading, setGLoading] = useState(false)
  const [gError, setGError] = useState('')
  
  // GDP data state
  const [gdpData, setGdpData] = useState<any>(null)
  const [sectorData, setSectorData] = useState<any>(null)
  const [periodData, setPeriodData] = useState<any>(null)
  
  // Fetch real GDP data
  const fetchGDPData = async () => {
    if (!simulationId) return
    
    setGLoading(true)
    setGError('')
    
    try {
      // Fetch current GDP
      const gdpResponse = await fetch(buildApiUrl(API_ENDPOINTS.GDP_CURRENT, { simulation_id: simulationId }))
      if (!gdpResponse.ok) throw new Error('Failed to fetch GDP data')
      const gdpResult = await gdpResponse.json()
      setGdpData(gdpResult)
      
      // Fetch sector breakdown if we have date range
      if (gStart && gEnd) {
        const sectorResponse = await fetch(buildApiUrl(API_ENDPOINTS.GDP_SECTORS, { 
          simulation_id: simulationId, 
          start_date: gStart, 
          end_date: gEnd 
        }))
        if (sectorResponse.ok) {
          const sectorResult = await sectorResponse.json()
          setSectorData(sectorResult)
        }
        
        // Fetch period data
        const periodResponse = await fetch(buildApiUrl(API_ENDPOINTS.GDP_PERIODS, { 
          simulation_id: simulationId, 
          start_date: gStart, 
          end_date: gEnd, 
          period_type: gGran.toLowerCase() 
        }))
        if (periodResponse.ok) {
          const periodResult = await periodResponse.json()
          setPeriodData(periodResult)
        }
      }
      
    } catch (error) {
      setGError('Failed to fetch GDP data')
      console.error('GDP fetch error:', error)
    } finally {
      setGLoading(false)
    }
  }
  
  // Auto-fetch when simulation changes
  useEffect(() => {
    if (simulationId) {
      fetchGDPData()
    }
  }, [simulationId])
  
  // Set default time range to simulation date when simulation changes
  useEffect(() => {
    if (simulations.length > 0 && simulationId) {
      const sim = simulations.find(s => s.id === simulationId) || simulations[0]
      if (sim?.start_datetime) {
        const simDate = new Date(sim.start_datetime)
        const startTime = new Date(simDate)
        startTime.setHours(0, 0, 0, 0) // Start of day
        const endTime = new Date(simDate)
        endTime.setHours(23, 59, 59, 999) // End of day
        
        setGStart(startTime.toISOString())
        setGEnd(endTime.toISOString())
      }
    }
  }, [simulations, simulationId])
  
  const handleRefresh = fetchGDPData

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <TopBar
        simulationId={simulationId}
        setSimulationId={setSimulationId}
        simulationOptions={simOptions}
        simulationLoading={simLoading}
      />
      <LeftNav />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pt-24">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <aside className="lg:col-span-1 space-y-4">
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 sticky top-20">
              <div className="flex items-center mb-3">
                <label className="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300">
                  <Calendar className="w-4 h-4 mr-2" />
                  Date Range
                </label>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Start Date & Time</label>
                  <div className="flex gap-2">
                    <input 
                      type="date" 
                      value={gStart.split('T')[0] || ''} 
                      onChange={e => {
                        const time = gStart.includes('T') ? gStart.split('T')[1] : '00:00'
                        setGStart(`${e.target.value}T${time}`)
                      }} 
                      className="flex-1 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" 
                    />
                    <input 
                      type="time" 
                      value={gStart.includes('T') ? gStart.split('T')[1] : '00:00'} 
                      onChange={e => {
                        const date = gStart.split('T')[0] || new Date().toISOString().split('T')[0]
                        setGStart(`${date}T${e.target.value}`)
                      }} 
                      className="w-24 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" 
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">End Date & Time</label>
                  <div className="flex gap-2">
                    <input 
                      type="date" 
                      value={gEnd.split('T')[0] || ''} 
                      onChange={e => {
                        const time = gEnd.includes('T') ? gEnd.split('T')[1] : '23:59'
                        setGEnd(`${e.target.value}T${time}`)
                      }} 
                      className="flex-1 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" 
                    />
                    <input 
                      type="time" 
                      value={gEnd.includes('T') ? gEnd.split('T')[1] : '23:59'} 
                      onChange={e => {
                        const date = gEnd.split('T')[0] || new Date().toISOString().split('T')[0]
                        setGEnd(`${date}T${e.target.value}`)
                      }} 
                      className="w-24 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" 
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 sticky top-72">
              <label className="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                <Clock className="w-4 h-4 mr-2" />
                Granularity
              </label>
              <select value={gGran} onChange={e => setGGran(e.target.value as any)} className="w-full border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                {granularities.map(g => (<option key={g} value={g}>{g}</option>))}
              </select>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 sticky top-[28rem]">
              <button onClick={handleRefresh} className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white border border-indigo-500">
                {gLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                {gLoading ? 'Loading...' : 'Refresh Data'}
              </button>
              {gError && <div className="mt-3 text-sm text-red-600">{gError}</div>}
            </div>
          </aside>
          <main className="lg:col-span-3 space-y-6">
            {/* Simulation Time Display */}
            {simulationId && simulations.length > 0 && (
              <div className="bg-white dark:bg-gray-900 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-600" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Simulation Time</span>
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {(() => {
                      const sim = simulations.find(s => s.id === simulationId)
                      if (sim?.start_datetime) {
                        const startDate = new Date(sim.start_datetime)
                        const currentDate = sim.current_datetime ? new Date(sim.current_datetime) : startDate
                        return `${startDate.toLocaleDateString()} → ${currentDate.toLocaleDateString()}`
                      }
                      return 'Unknown'
                    })()}
                  </div>
                </div>
              </div>
            )}
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-gray-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Total GDP</span>
                  <TrendingUp className="w-4 h-4 text-green-600" />
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {gdpData ? `$${gdpData.gdp.toLocaleString()}` : 'Loading...'}
                </div>
                {gdpData && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {gdpData.period?.start ? 
                      `${new Date(gdpData.period.start).toLocaleDateString()} - ${new Date(gdpData.period.end).toLocaleDateString()}` : 
                      `${gdpData.period?.type || 'Current'} period`
                    }
                  </div>
                )}
              </div>
              <div className="bg-white dark:bg-gray-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Consumption Share</span>
                  <BarChart3 className="w-4 h-4 text-purple-600" />
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {gdpData ? `${gdpData.component_shares?.consumption_share?.toFixed(1) || 0}%` : 'Loading...'}
                </div>
                {gdpData && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    ${gdpData.components?.consumption?.toLocaleString() || 0}
                  </div>
                )}
              </div>
              <div className="bg-white dark:bg-gray-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Investment Share</span>
                  <BarChart3 className="w-4 h-4 text-blue-600" />
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {gdpData ? `${gdpData.component_shares?.investment_share?.toFixed(1) || 0}%` : 'Loading...'}
                </div>
                {gdpData && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    ${gdpData.components?.investment?.toLocaleString() || 0}
                  </div>
                )}
              </div>
              <div className="bg-white dark:bg-gray-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Net Exports</span>
                  <BarChart3 className="w-4 h-4 text-amber-600" />
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {gdpData ? `$${gdpData.components?.net_exports?.toLocaleString() || 0}` : 'Loading...'}
                </div>
                {gdpData && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {gdpData.component_shares?.net_exports_share?.toFixed(1) || 0}% of GDP
                  </div>
                )}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
                <div className="font-semibold text-gray-900 dark:text-white">GDP by Sector</div>
              </div>
              <div className="p-6">
                {sectorData ? (
                  <div className="space-y-4">
                    {sectorData.sectors?.map((sector: any, index: number) => (
                      <div key={index} className="border-b border-gray-200 dark:border-gray-700 pb-3">
                        <div className="flex justify-between items-center mb-2">
                          <div className="font-medium text-gray-900 dark:text-white">
                            {sector.sector}
                            {sector.subsector && (
                              <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                                ({sector.subsector})
                              </span>
                            )}
                          </div>
                          <div className="text-lg font-bold text-gray-900 dark:text-white">
                            ${sector.total_amount.toLocaleString()}
                          </div>
                        </div>
                        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                          <span>{sector.transaction_count} transactions</span>
                          <span>
                            {sector.by_buyer_type?.household && `Household: $${sector.by_buyer_type.household.toLocaleString()}`}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-600 dark:text-gray-300">
                    {gStart && gEnd ? 'Loading sector data...' : 'Set date range to view sector breakdown'}
                  </div>
                )}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
                <div className="font-semibold text-gray-900 dark:text-white">GDP Growth Over Time</div>
              </div>
              <div className="p-6">
                {periodData ? (
                  <div className="space-y-4">
                    {periodData.periods?.map((period: any, index: number) => (
                      <div key={index} className="border-b border-gray-200 dark:border-gray-700 pb-3">
                        <div className="flex justify-between items-center mb-2">
                          <div className="font-medium text-gray-900 dark:text-white">
                            {new Date(period.start).toLocaleDateString()} - {new Date(period.end).toLocaleDateString()}
                          </div>
                          <div className="text-lg font-bold text-gray-900 dark:text-white">
                            ${period.gdp.toLocaleString()}
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4 text-sm text-gray-600 dark:text-gray-400">
                          <div>
                            <span className="font-medium">Consumption:</span> ${period.components.consumption.toLocaleString()}
                          </div>
                          <div>
                            <span className="font-medium">Investment:</span> ${period.components.investment.toLocaleString()}
                          </div>
                          <div>
                            <span className="font-medium">Net Exports:</span> ${period.components.net_exports.toLocaleString()}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-600 dark:text-gray-300">
                    {gStart && gEnd ? 'Loading period data...' : 'Set date range to view GDP growth over time'}
                  </div>
                )}
              </div>
            </div>
            
          </main>
        </div>
      </div>
    </div>
  )
}


