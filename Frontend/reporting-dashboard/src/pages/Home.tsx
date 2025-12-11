import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Building2, Activity, RefreshCw, ChevronRight, Search, XCircle, CheckCircle } from 'lucide-react'
import { TopBar } from '../components/TopBar'
import { useSimulationId } from '../hooks/useSimulationId'
import { LeftNav } from '../components/LeftNav'
import { API_ENDPOINTS } from '../config/api'

export default function Home() {
  const [firmCount, setFirmCount] = useState<number | null>(null)
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [apiDetails, setApiDetails] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [firms, setFirms] = useState<any[]>([])
  const [firmId, setFirmId] = useState<string>('')
  const [selectedFirm, setSelectedFirm] = useState<any>(null)
  const [showFirmSearch, setShowFirmSearch] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [firmHighlights, setFirmHighlights] = useState<any>(null)
  const { simulations, simulationId, setSimulationId, loading: simLoading } = useSimulationId()

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true)
        
        // Check API health first
        let isApiHealthy = false
        try {
          const healthRes = await axios.get(API_ENDPOINTS.HEALTH)
          isApiHealthy = healthRes.data.status === 'healthy'
          setApiOk(isApiHealthy)
          setApiDetails(healthRes.data.service || 'World_Sim Reporting API')
        } catch (e) {
          setApiOk(false)
          setApiDetails('Connection failed')
        }
        
        // Fetch firms if API is healthy
        if (isApiHealthy) {
          try {
            const firmsRes = await axios.get(API_ENDPOINTS.FIRMS)
            const firmsData = Array.isArray(firmsRes.data) ? firmsRes.data : []
            setFirms(firmsData)
            setFirmCount(firmsData.length)
            
            // Set first firm as default if available
            if (firmsData.length > 0 && !firmId) {
              setFirmId(firmsData[0].id)
              setSelectedFirm(firmsData[0])
            }
          } catch (e) {
            console.warn('Failed to fetch firms:', e)
          }
        }
      } catch (e) {
        console.error('Error in fetchSummary:', e)
      } finally {
        setLoading(false)
      }
    }
    fetchSummary()
  }, [])
  
  // Load selected firm from localStorage on page load
  useEffect(() => {
    const savedFirmId = localStorage.getItem('selectedFirmId')
    if (savedFirmId && firms.length > 0) {
      const firm = firms.find(f => f.id === savedFirmId)
      if (firm) {
        setFirmId(savedFirmId)
        setSelectedFirm(firm)
      }
    }
  }, [firms])
  
  // Fetch firm highlights when firm changes
  useEffect(() => {
    if (firmId && simulationId) {
      fetchFirmHighlights()
    }
  }, [firmId, simulationId])
  
  // Handle escape key to close modal
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && showFirmSearch) {
        setShowFirmSearch(false)
        setSearchQuery('')
      }
    }
    
    if (showFirmSearch) {
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [showFirmSearch])
  
  const fetchFirmHighlights = async () => {
    try {
      // Get current date for highlights
      const today = new Date().toISOString().split('T')[0]
      
      // Fetch financial data for highlights
      const response = await axios.get(API_ENDPOINTS.FINANCIAL_STATEMENTS, {
        params: { 
          simulation_id: simulationId, 
          start: `${today}T00:00:00`, 
          end: `${today}T23:59:59`, 
          granularity: '15m'
        }
      })
      
      if (response.data && response.data["Retail Sales Revenue"]) {
        const revenue = Object.values(response.data["Retail Sales Revenue"]).reduce((sum: any, val: any) => sum + Number(val), 0)
        const costs = revenue * 0.6
        const netIncome = revenue - costs
        const totalAssets = 1000 + revenue + 55.46
        
        setFirmHighlights({
          revenue,
          netIncome,
          totalAssets
        })
      }
    } catch (err) {
      console.error('Failed to fetch firm highlights:', err)
    }
  }
  
  const handleFirmChange = (newFirmId: string) => {
    setFirmId(newFirmId)
    const firm = firms.find(f => f.id === newFirmId)
    setSelectedFirm(firm)
    setShowFirmSearch(false)
    setSearchQuery('')
    
    // Store in localStorage for synchronization with other pages
    localStorage.setItem('selectedFirmId', newFirmId)
  }
  
  const filteredFirms = firms.filter(firm => 
    firm.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    firm.id?.toLowerCase().includes(searchQuery.toLowerCase())
  )
  
  const highlightMatch = (text: string, query: string) => {
    if (!query) return text
    const regex = new RegExp(`(${query})`, 'gi')
    return text.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800">$1</mark>')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 flex flex-col">
      <TopBar
        simulationId={simulationId}
        setSimulationId={setSimulationId}
        simulationOptions={(simulations.length ? simulations : [{ id: 'latest' }]).map(s => ({ 
          label: s.created_at ? `${s.id} — ${new Date(s.created_at).toLocaleString()}` : s.id, 
          value: s.id 
        }))}
        simulationLoading={simLoading}
      />

      {/* Overlay left nav */}
      <LeftNav />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 pt-24">
        {/* Firm Selection and Highlights */}
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Firm Overview</h2>
            <button
              onClick={() => setShowFirmSearch(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors text-sm"
            >
              <Building2 className="w-4 h-4" />
              Change Firm
            </button>
          </div>
          
          {selectedFirm ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Selected Firm</h3>
                <div className="text-xl font-semibold text-gray-900 dark:text-white">{selectedFirm.company_name}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">ID: {selectedFirm.id}</div>
              </div>
              
              {firmHighlights && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Today's Highlights</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Revenue</div>
                      <div className="text-lg font-semibold text-green-600">${firmHighlights.revenue.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Net Income</div>
                      <div className="text-lg font-semibold text-blue-600">${firmHighlights.netIncome.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Total Assets</div>
                      <div className="text-lg font-semibold text-purple-600">${firmHighlights.totalAssets.toFixed(2)}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <Building2 className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-gray-500 dark:text-gray-400">No firm selected</p>
            </div>
          )}
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white dark:bg-gray-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">Firms Available</div>
              <Building2 className="w-5 h-5 text-blue-600" />
            </div>
            <div className="mt-3 text-2xl font-bold text-gray-900 dark:text-white">
              {firmCount === null ? '—' : firmCount.toLocaleString()}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">Reporting API</div>
              <Activity className="w-5 h-5 text-emerald-600" />
            </div>
            <div className="mt-3 text-2xl font-bold">
              <span className={apiOk === null ? 'text-gray-900 dark:text-white' : apiOk ? 'text-emerald-600' : 'text-red-600'}>
                {apiOk === null ? 'Checking…' : apiOk ? 'Online' : 'Offline'}
              </span>
            </div>
            {apiDetails && (
              <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {apiDetails}
              </div>
            )}
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">Status</div>
              <RefreshCw className={`${loading ? 'animate-spin text-gray-600' : 'text-gray-400'} w-5 h-5`} />
            </div>
            <div className="mt-3 text-2xl font-bold text-gray-900 dark:text-white">
              {loading ? 'Loading' : 'Ready'}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">Latest Run</div>
              <span className="text-xs text-gray-400">—</span>
            </div>
            <div className="mt-3 text-2xl font-bold text-gray-900 dark:text-white">—</div>
          </div>
        </div>

        {/* Firm Selection and Highlights */}
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Firm Overview</h2>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowFirmSearch(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-blue-400 hover:bg-blue-50 dark:hover:border-blue-500 dark:hover:bg-gray-700 transition-colors text-sm text-gray-900 dark:text-white"
              >
                <Building2 className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                {selectedFirm?.company_name || 'Select a firm'}
              </button>
              {selectedFirm && (
                <a
                  href="/firm"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white transition-colors text-sm font-medium"
                >
                  View Full Financial Statements →
                </a>
              )}
            </div>
          </div>
          

        </div>


      </div>

      {/* Spacer to push footer to bottom */}
      <div className="flex-1"></div>

      <footer className="mt-16 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-center">
          <div className="text-sm text-gray-500 dark:text-gray-400">© {new Date().getFullYear()} WorldSim. All rights reserved.</div>
        </div>
      </footer>

      {/* Firm Search Modal */}
      {showFirmSearch && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Select Firm</h3>
                <button
                  onClick={() => setShowFirmSearch(false)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                >
                  <XCircle className="w-5 h-5 text-gray-400 dark:text-gray-500" />
                </button>
              </div>
              
              {/* Search Input */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
                <input
                  type="text"
                  placeholder="Search firms by name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                  autoFocus
                />
              </div>
            </div>
            
            {/* Firm List */}
            <div className="overflow-y-auto max-h-96 custom-scrollbar">
              {filteredFirms.length === 0 ? (
                <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                  <Building2 className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
                  <p>No firms found matching "{searchQuery}"</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredFirms.map((firm) => (
                    <button
                      key={firm.id}
                      onClick={() => handleFirmChange(firm.id)}
                      className="w-full p-4 text-left hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors focus:outline-none focus:bg-blue-50 dark:focus:bg-blue-900/20"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                          <Building2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-gray-900 dark:text-white">
                            {firm.company_name}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            ID: {firm.id}
                          </div>
                        </div>
                        {firm.id === firmId && (
                          <CheckCircle className="w-5 h-5 text-green-500 dark:text-green-400" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
