import React, { useState, useEffect } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { 
  User, 
  Home, 
  DollarSign, 
  Activity, 
  Users, 
  ArrowLeft,
  MapPin,
  Calendar,
  Briefcase,
  CreditCard,
  GraduationCap,
  Heart,
  Building2,
  RefreshCw,
  ArrowUpDown,
  Search as SearchIcon,
} from 'lucide-react'
import { PLACE_LIST_CONFIG, distanceClass, SortKey, formatEncounters } from '../config/placeListConfig'
import { TopBar } from '../components/TopBar'
import { LeftNav } from '../components/LeftNav'
import { API_ENDPOINTS, buildApiUrl } from '../config/api'
import { useSimulationId } from '../hooks/useSimulationId'
import { useAgentBalanceSheet, useAgentActivity, useAgentPoiKnowledge, AgentPoiKnowledgeRow } from '../hooks/useAgentData'
import { BaseCard } from '../components/shared'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import { 
  MetricCard,
  AgentHeader,
  AgentSummaryCard,
  AgentTabs,
  CollapsibleSection,
  DataGrid,
  type AgentTabId,
} from '../components/agent'
import { poiCategoryColors } from '../styles/colors'
import { SPACING } from '../spacing'
import { TYPOGRAPHY } from '../typography'
import { ANIMATIONS } from '../animations'
import { 
  formatCurrency, 
  formatDate, 
  formatDateTime,
  getStatusColors,
  getRelativeTime,
  getNetWorthTier,
} from '../utils/agentUtils'
import { normalizeAgent, DEFAULT_SCHEMA_TO_UI } from '../utils/normalizeAgent'
import { DefinitionListCard } from '../components/agent/DefinitionListCard'
import { SensitiveDataCard } from '../components/agent/SensitiveDataCard'
import { JsonViewer } from '../components/shared/JsonViewer'
import { PersonalSummaryCard } from '../components/agent/PersonalSummaryCard'

interface AgentDetails {
  agent_id: string
  agent_data: any
  personal_summary: string | null
  l2_data: {
    l2_agent_core?: any
    l2_location?: any
    l2_geo?: any
    l2_political_part_1?: any
    l2_political_part_2?: any
    l2_political_part_3?: any
    l2_other_part_1?: any
    l2_other_part_2?: any
    l2_other_part_3?: any
    l2_other_part_4?: any
  }
  l2_data_flat: any
  location_history: any[]
}

export const AgentProfile: React.FC = () => {
  const { agentId } = useParams<{ agentId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const simulationId = searchParams.get('simulation_id')

  // real simulation picker wiring
  const { simulations, simulationId: simId, setSimulationId: setSimId, loading: simLoading } = useSimulationId()
  const simOptions = (simulations.length
    ? simulations.map((s: any) => ({
        label: s.created_at ? `${s.id} — ${new Date(s.created_at).toLocaleString()}` : s.id,
        value: s.id
      }))
    : [{ label: 'Latest', value: 'latest' }]
  )

  // One-time: if URL has simulation_id on mount, adopt it into state
  const didInitUrl = React.useRef(false)
  useEffect(() => {
    if (didInitUrl.current) return
    didInitUrl.current = true
    if (simulationId && simulationId !== simId) {
      setSimId(simulationId)
    }
  }, [])

  useEffect(() => {
    if (!simulations.length || !agentId) return
    if (simId && simulations.some((s: any) => s.id === simId)) {
      return
    }
    const fallback = simulations[0]?.id
    if (fallback && fallback !== simId) {
      setSimulationAndNavigate(fallback)
    }
  }, [simulations, simId, agentId])

  // Provide a setter that also updates URL immediately to avoid sync loops
  const setSimulationAndNavigate = (id: string | null) => {
    setSimId(id)
    if (!agentId) return
    if (id) {
      navigate(`/agent/${agentId}?simulation_id=${id}`, { replace: true })
    } else {
      navigate(`/agent/${agentId}`, { replace: true })
    }
  }

  const [activeTab, setActiveTab] = useState<AgentTabId>('overview')
  const [agentDetails, setAgentDetails] = useState<AgentDetails | null>(null)
  const [loading, setLoading] = useState(true)

  // Fetch agent details - use simId from state (which is synced with URL)
  useEffect(() => {
    if (!agentId) return

    const fetchAgentDetails = async () => {
      setLoading(true)
      try {
        // Use simId from state (which reflects the current selection)
        const url = buildApiUrl(API_ENDPOINTS.AGENT_DETAILS(agentId), {
          simulation_id: simId || undefined,
        })

        const response = await fetch(url)
        if (!response.ok) {
          throw new Error(`Failed to fetch agent details: ${response.statusText}`)
        }

        const data = await response.json()
        setAgentDetails(data)
      } catch (error) {
        console.error('Error fetching agent details:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAgentDetails()
  }, [agentId, simId])

  // Fetch balance sheet and activity using custom hooks - use simId from state
  const balanceSheet = useAgentBalanceSheet(agentId || null, simId)
  const activity = useAgentActivity(agentId || null, simId)
  const poiKnowledge = useAgentPoiKnowledge(agentId || null, simId)

  if (!agentId) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <TopBar />
        <LeftNav />
        <div className="ml-14 pt-16">
          <div className="p-8">
            <p className="text-gray-500 dark:text-gray-400">Agent ID not provided</p>
          </div>
        </div>
      </div>
    )
  }

  const tabs = [
    { id: 'overview' as AgentTabId, label: 'Overview', icon: <User className="w-4 h-4" /> },
    { id: 'cognition' as AgentTabId, label: 'Cognition', icon: <Activity className="w-4 h-4" /> },
    { id: 'balance-sheet' as AgentTabId, label: 'Balance Sheet', icon: <DollarSign className="w-4 h-4" /> },
    { id: 'activity' as AgentTabId, label: 'Activity', icon: <Activity className="w-4 h-4" /> },
    { id: 'places' as AgentTabId, label: 'Places', icon: <MapPin className="w-4 h-4" /> },
    { id: 'relationships' as AgentTabId, label: 'Relationships', icon: <Users className="w-4 h-4" /> },
  ]


  const l2Data = agentDetails?.l2_data_flat || {}
  const l2Nested = agentDetails?.l2_data || {}
  const l2CoreNested = (l2Nested as any)?.l2_agent_core || {}
  const computedName = (
    agentDetails?.agent_data?.name ||
    [l2CoreNested?.Voters_FirstName, l2CoreNested?.Voters_MiddleName, l2CoreNested?.Voters_LastName]
      .filter((p: string | undefined) => !!p && String(p).trim().length > 0)
      .join(' ') ||
    (l2Data?.Voters_FirstName && l2Data?.Voters_LastName
      ? `${l2Data.Voters_FirstName} ${l2Data.Voters_LastName}`
      : null)
  )

  // metric colors - accent colors only on small surfaces (icon circles)
  const metricColors = {
    money: 'bg-sky-500/15 text-sky-100',
    home: 'bg-emerald-500/15 text-emerald-100',
    people: 'bg-violet-500/15 text-violet-100',
  }

  return (
    <div className="relative">
      {/* Fixed background layer - never changes */}
      <div className="fixed inset-0 bg-gradient-to-br from-[#0B111A] via-[#0F1520] to-[#0B111A] -z-10 h-[200vh]"></div>
      
      <TopBar 
        simulationId={simId}
        setSimulationId={setSimulationAndNavigate}
        simulationOptions={simOptions}
        simulationLoading={simLoading}
      />
      <LeftNav simulationId={simId} />
      
      <div className="ml-14 relative z-0">
        {loading ? (
          <div className="pt-16 min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
            <div className="max-w-6xl mx-auto px-4 lg:px-6 py-8 space-y-8">
              {/* Header skeleton with shimmer effect */}
              <div className="bg-slate-900/50 border border-slate-800/50 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-slate-800/50 to-slate-700/50 animate-pulse" />
                  <div className="flex-1 space-y-3">
                    <div className="h-7 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded-lg w-56 animate-shimmer bg-[length:200%_100%]" />
                    <div className="h-4 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded w-72 animate-shimmer bg-[length:200%_100%]" />
                  </div>
                </div>
              </div>

              {/* Metrics skeleton with staggered animation */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[...Array(3)].map((_, idx) => (
                  <div 
                    key={idx} 
                    className="bg-slate-900/50 border border-slate-800/50 rounded-2xl p-5 backdrop-blur-sm"
                    style={{ animationDelay: `${idx * 100}ms` }}
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-800/50 to-slate-700/50 animate-pulse" />
                      <div className="h-4 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded w-28 animate-shimmer bg-[length:200%_100%]" />
                    </div>
                    <div className="h-9 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded-lg w-36 mb-2 animate-shimmer bg-[length:200%_100%]" />
                    <div className="h-3 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded w-24 animate-shimmer bg-[length:200%_100%]" />
                  </div>
                ))}
              </div>

              {/* Content cards skeleton */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[...Array(4)].map((_, idx) => (
                  <div 
                    key={idx} 
                    className="bg-slate-900/50 border border-slate-800/50 rounded-2xl p-5 backdrop-blur-sm"
                    style={{ animationDelay: `${(idx + 3) * 100}ms` }}
                  >
                    <div className="h-5 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded w-36 mb-4 animate-shimmer bg-[length:200%_100%]" />
                    <div className="space-y-3">
                      {[...Array(4)].map((_, i) => (
                        <div key={i} className="flex justify-between items-center">
                          <div className="h-4 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded w-28 animate-shimmer bg-[length:200%_100%]" />
                          <div className="h-4 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded w-36 animate-shimmer bg-[length:200%_100%]" />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Centered animated loading indicator */}
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <div className="relative">
                  <div className="w-16 h-16 border-4 border-slate-800/30 rounded-full"></div>
                  <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin absolute top-0 left-0"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-3 h-3 bg-sky-500 rounded-full animate-pulse"></div>
                  </div>
                </div>
                <div className="text-center space-y-1">
                  <p className="text-sm font-medium text-slate-400">Loading agent profile...</p>
                  <p className="text-xs text-slate-500">Fetching detailed information</p>
                </div>
              </div>
            </div>
          </div>
        ) : agentDetails ? (
          <div className="pt-16 min-h-[200vh]">
            {/* compact header bar with breadcrumb and actions */}
            <AgentHeader
              agentId={agentId}
              name={computedName}
              city={l2Data.Residence_Addresses_City || null}
              state={l2Data.Residence_Addresses_State || null}
              age={l2Data.Voters_Age || null}
              gender={l2Data.Voters_Gender || null}
              party={l2Data.Parties_Description || null}
              simulationId={simId}
              onViewOnMap={() => {
                const target = simId ? `/map?simulation_id=${simId}` : '/map'
                navigate(target)
              }}
              onCopyLink={() => {
                const url = window.location.href
                navigator.clipboard.writeText(url)
              }}
            />

            {/* main content area - tighter padding */}
            <div className="max-w-6xl mx-auto px-4 lg:px-6 py-4 space-y-4">
              {/* back button */}
              <button
                onClick={() => {
                  const target = simId ? `/agents?simulation_id=${simId}` : '/agents'
                  navigate(target)
                }}
                className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>All Agents</span>
              </button>

              {/* removed top-of-page tiles (kept only in Overview) */}
            </div>

            {/* tabs - sticky glass bubble design */}
            <AgentTabs
              tabs={tabs}
              activeTab={activeTab}
              onTabChange={setActiveTab}
            />

            {/* tab content - always maintains consistent height */}
            <div className="max-w-6xl mx-auto px-4 lg:px-6 py-6 pb-24 min-h-[calc(100vh-400px)]">
              {activeTab === 'overview' && (
                <OverviewTab agentDetails={agentDetails} balanceSheet={balanceSheet.data} />
              )}
              {activeTab === 'cognition' && (
                <CognitionTab 
                  agentId={agentId}
                  simulationId={simId}
                />
              )}
              {activeTab === 'balance-sheet' && (
                <BalanceSheetTab 
                  balanceSheet={balanceSheet.data} 
                  loading={balanceSheet.loading}
                  error={balanceSheet.error}
                />
              )}
              {activeTab === 'activity' && (
                <ActivityTab 
                  activity={activity.data} 
                  loading={activity.loading}
                  error={activity.error}
                />
              )}
              {activeTab === 'places' && (
                <PlacesTab
                  knowledge={poiKnowledge.data}
                  loading={poiKnowledge.loading}
                  error={poiKnowledge.error}
                  onRefresh={poiKnowledge.refetch}
                  simulationId={simId}
                />
              )}
              {activeTab === 'relationships' && (
                <RelationshipsTab 
                  householdMembers={balanceSheet.data?.household_members || []}
                  loading={balanceSheet.loading}
                  agentId={agentId}
                  simulationId={simId}
                  navigate={navigate}
                />
              )}
            </div>
          </div>
        ) : (
          <div className="max-w-6xl mx-auto px-4 lg:px-6 py-12 pt-16 text-center">
            <p className="text-slate-400">No agent data found for ID: {agentId}</p>
          </div>
        )}
      </div>
    </div>
  )
}

// Overview Tab Component
const OverviewTab: React.FC<{ agentDetails: AgentDetails | null; balanceSheet?: any }> = ({ agentDetails, balanceSheet }) => {
  if (!agentDetails) {
    return <p className={TYPOGRAPHY.COLORS.MUTED}>No agent details available</p>
  }

  const model = normalizeAgent(agentDetails, DEFAULT_SCHEMA_TO_UI)
  
  // Prefer balance sheet values if available, fallback to normalized model
  const netWorth = balanceSheet?.balance_sheet?.netWorth ?? model.snapshot.netWorthUsd
  const homeValue = balanceSheet?.balance_sheet?.primaryHomeValue ?? model.snapshot.homeValueUsd

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Left: Snapshot + Facts */}
      <div className="lg:col-span-2 space-y-4">
        {/* Snapshot tiles */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            icon={<DollarSign className="w-5 h-5" />}
            iconClassName="bg-sky-500/15 text-sky-100"
            label="Net worth"
            value={netWorth != null ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(netWorth) : ''}
            accentColor="cyan"
          />
          <MetricCard
            icon={<Home className="w-5 h-5" />}
            iconClassName="bg-emerald-500/15 text-emerald-100"
            label="Home value"
            value={homeValue != null ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(homeValue) : ''}
            accentColor="green"
          />
          <MetricCard
            icon={<Users className="w-5 h-5" />}
            iconClassName="bg-violet-500/15 text-violet-100"
            label="Household"
            value={model.snapshot.householdSize != null ? String(model.snapshot.householdSize) : ''}
            sublabel={
              model.snapshot.adults != null || model.snapshot.children != null
                ? `${Math.max(0, model.snapshot.adults ?? 0)} adults • ${Math.max(0, model.snapshot.children ?? 0)} children`
                : undefined
            }
            accentColor="violet"
          />
        </div>

        {/* Residence */}
        <DefinitionListCard
          title="Residence"
          items={[
            { label: 'Address', value: model.residence.address },
            { label: 'ZIP', value: model.residence.zip5 },
            { label: 'Dwelling type', value: model.residence.dwellingType },
            { label: 'Square footage', value: model.residence.homeSqft != null ? model.residence.homeSqft.toLocaleString('en-US') + ' sq ft' : null },
            { label: 'Coordinates', value: model.residence.lat != null && model.residence.lon != null ? `${model.residence.lat}, ${model.residence.lon}` : null },
          ]}
        />

        {/* Civic / Voter */}
        <DefinitionListCard
          title="Civic / Voter"
          items={[
            { label: 'Party', value: model.civicVoter.party },
            { label: 'Precinct', value: model.civicVoter.precinct },
            { label: 'Registration date', value: model.civicVoter.registrationDate ? formatDate(model.civicVoter.registrationDate) : null },
            { label: 'Voter ID', value: model.civicVoter.voterId },
          ]}
        />

        {/* Consumer & Income */}
        <DefinitionListCard
          title="Consumer & Income"
          items={[
            { label: 'Estimated income', value: model.consumerIncome.estimatedIncomeUsd != null ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(model.consumerIncome.estimatedIncomeUsd)) : null },
            { label: 'Income range', value: model.consumerIncome.incomeRange },
            { label: 'Credit band', value: model.consumerIncome.creditBand },
            { label: 'Marital status', value: model.consumerIncome.maritalStatus },
            { label: 'Education', value: model.consumerIncome.education },
            { label: 'Occupation', value: model.consumerIncome.occupation },
            { label: 'Presence of children', value: model.consumerIncome.presenceOfChildren },
          ]}
        />

        {/* Sensitive identifiers */}
        <SensitiveDataCard items={model.identifiers} />

        {/* JSON viewer */}
        {agentDetails.l2_data && Object.keys(agentDetails.l2_data).length > 0 && (
          <JsonViewer data={agentDetails.l2_data} />
        )}
      </div>

      {/* Right rail: Personal Summary */}
      <div className="space-y-4">
        <PersonalSummaryCard summary={agentDetails.personal_summary} netWorth={model.snapshot.netWorthUsd} />
      </div>
    </div>
  )
}

// Balance Sheet Tab Component
const BalanceSheetTab: React.FC<{ 
  balanceSheet: any
  loading: boolean
  error: string | null
}> = ({ balanceSheet, loading, error }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size={32} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center">
        <div className="max-w-md mx-auto space-y-3">
          <div className="w-12 h-12 rounded-full bg-red-500/15 flex items-center justify-center mx-auto">
            <DollarSign className="w-6 h-6 text-red-300" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white mb-1">Error Loading Balance Sheet</h3>
            <p className="text-sm text-red-400">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!balanceSheet?.balance_sheet) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 rounded-full bg-emerald-500/15 flex items-center justify-center mx-auto">
            <DollarSign className="w-8 h-8 text-emerald-300" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">
              No Financial Data Available
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Balance sheet information has not been generated for this agent.
              {' '}Run a simulation to initialize household financial data.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const bs = balanceSheet.balance_sheet

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  return (
    <div className="space-y-4">
      {/* summary cards - enhanced with gradients */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gradient-to-br from-emerald-500/20 to-slate-900/90 border border-slate-800 rounded-2xl p-4 md:p-5 text-center transition-all duration-300 hover:border-slate-700 hover:-translate-y-0.5 hover:shadow-[0_0_15px_rgba(16,185,129,0.1)]">
          <div className="w-10 h-10 rounded-full bg-emerald-500/15 flex items-center justify-center mx-auto mb-3">
            <DollarSign className="w-5 h-5 text-emerald-100" />
          </div>
          <p className="text-xs uppercase tracking-wide text-slate-400 mb-1">
            Total Assets
          </p>
          <p className="text-2xl md:text-3xl font-semibold text-white">
            {formatCurrency(bs.assetsTotal)}
          </p>
        </div>

        <div className="bg-gradient-to-br from-red-500/20 to-slate-900/90 border border-slate-800 rounded-2xl p-4 md:p-5 text-center transition-all duration-300 hover:border-slate-700 hover:-translate-y-0.5 hover:shadow-[0_0_15px_rgba(239,68,68,0.1)]">
          <div className="w-10 h-10 rounded-full bg-red-500/15 flex items-center justify-center mx-auto mb-3">
            <DollarSign className="w-5 h-5 text-red-100" />
          </div>
          <p className="text-xs uppercase tracking-wide text-slate-400 mb-1">
            Total Liabilities
          </p>
          <p className="text-2xl md:text-3xl font-semibold text-white">
            {formatCurrency(bs.liabilitiesTotal)}
          </p>
        </div>

        <div className="bg-gradient-to-br from-cyan-500/20 to-slate-900/90 border border-slate-800 rounded-2xl p-4 md:p-5 text-center transition-all duration-300 hover:border-slate-700 hover:-translate-y-0.5 hover:shadow-[0_0_15px_rgba(6,182,212,0.1)]">
          <div className="w-10 h-10 rounded-full bg-sky-500/15 flex items-center justify-center mx-auto mb-3">
            <DollarSign className="w-5 h-5 text-sky-100" />
          </div>
          <p className="text-xs uppercase tracking-wide text-slate-400 mb-1">
            Net Worth
          </p>
          <p className="text-2xl md:text-3xl font-semibold text-white">
            {formatCurrency(bs.netWorth)}
          </p>
        </div>
      </div>

      {/* Assets */}
      <BaseCard title="Assets" icon={Home}>
        <div className="space-y-2">
          <BalanceRow label="Primary Home" value={formatCurrency(bs.primaryHomeValue)} />
          <BalanceRow label="Secondary Real Estate" value={formatCurrency(bs.secondaryREValue)} />
          <BalanceRow label="Retirement Accounts" value={formatCurrency(bs.retirementAccounts)} />
          <BalanceRow label="Taxable Investments" value={formatCurrency(bs.taxableInvestments)} />
          <BalanceRow label="Liquid Savings" value={formatCurrency(bs.liquidSavings)} />
          <BalanceRow label="Vehicles" value={formatCurrency(bs.vehiclesValue)} />
          <BalanceRow label="Other Durables" value={formatCurrency(bs.durablesOther)} />
          <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-700">
            <BalanceRow 
              label="Total Assets" 
              value={formatCurrency(bs.assetsTotal)} 
              bold 
            />
          </div>
        </div>
      </BaseCard>

      {/* Liabilities */}
      <BaseCard title="Liabilities" icon={DollarSign}>
        <div className="space-y-2">
          <BalanceRow label="Mortgage Balance" value={formatCurrency(bs.mortgageBalance)} />
          <BalanceRow label="Auto Loans" value={formatCurrency(bs.autoLoans)} />
          <BalanceRow label="Credit Card Revolving" value={formatCurrency(bs.creditCardRevolving)} />
          <BalanceRow label="Student Loans" value={formatCurrency(bs.studentLoans)} />
          <BalanceRow label="Other Debt" value={formatCurrency(bs.otherDebt)} />
          <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-700">
            <BalanceRow 
              label="Total Liabilities" 
              value={formatCurrency(bs.liabilitiesTotal)} 
              bold 
            />
          </div>
        </div>
      </BaseCard>

      {/* Metadata */}
      <BaseCard title="Balance Sheet Info" icon={Calendar}>
        <div className="space-y-2">
          <InfoRow 
            label="Household ID" 
            value={balanceSheet.household_id} 
          />
          <InfoRow 
            label="Net Worth Bucket" 
            value={bs.net_worth_bucket || 'N/A'} 
          />
          <InfoRow 
            label="Snapshot Date" 
            value={new Date(bs.sim_clock_datetime).toLocaleDateString()} 
          />
        </div>
      </BaseCard>
    </div>
  )
}

// Activity Tab Component
const ActivityTab: React.FC<{ 
  activity: any
  loading: boolean
  error: string | null
}> = ({ activity, loading, error }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size={32} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center">
        <div className="max-w-md mx-auto space-y-3">
          <div className="w-12 h-12 rounded-full bg-red-500/15 flex items-center justify-center mx-auto">
            <Activity className="w-6 h-6 text-red-300" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white mb-1">Error Loading Activity</h3>
            <p className="text-sm text-red-400">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!activity) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 rounded-full bg-sky-500/15 flex items-center justify-center mx-auto">
            <Activity className="w-8 h-8 text-sky-300" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">
              No Activity Data Available
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              This agent has no recorded actions or transactions in the current period.
              {' '}Run a simulation or expand the date range to see agent activity.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* actions section - neutral card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 md:p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Actions ({activity.actions?.length || 0})</h3>
        {activity.actions && activity.actions.length > 0 ? (
          <div className="space-y-3">
            {activity.actions.slice(0, 20).map((action: any, idx: number) => {
              const statusColors = getStatusColors(action.status)
              return (
                <div
                  key={idx}
                  className="p-3 bg-slate-800 border border-slate-700 rounded-lg"
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-sm font-medium text-white">
                      {action.action_name}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded ${statusColors.bg} ${statusColors.text}`}>
                      {action.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    {formatDateTime(action.timestamp)}
                    {action.execution_time_ms && (
                      <span className="ml-2">• {action.execution_time_ms}ms</span>
                    )}
                  </p>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">No actions recorded</p>
        )}
      </div>

      {/* transactions section - neutral card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 md:p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Transactions ({activity.transactions?.length || 0})</h3>
        {activity.transactions && activity.transactions.length > 0 ? (
          <div className="space-y-3">
            {activity.transactions.slice(0, 20).map((txn: any, idx: number) => (
              <div
                key={idx}
                className="p-3 bg-slate-800 border border-slate-700 rounded-lg"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="text-sm font-medium text-white">
                      {txn.transaction_type}
                    </span>
                    <p className="text-xs text-slate-400 mt-1">
                      {txn.from_entity} → {txn.to_entity}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-emerald-400">
                    {formatCurrency(Number(txn.amount))}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {formatDateTime(txn.created_at)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">No transactions recorded</p>
        )}
      </div>
    </div>
  )
}

// Places tab component
const PlacesTab: React.FC<{
  knowledge: AgentPoiKnowledgeRow[]
  loading: boolean
  error: string | null
  onRefresh: () => void
  simulationId: string | null
}> = ({ knowledge, loading, error, onRefresh, simulationId }) => {
  const navigate = useNavigate()
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size={32} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center">
        <div className="max-w-md mx-auto space-y-3">
          <div className="w-12 h-12 rounded-full bg-red-500/15 flex items-center justify-center mx-auto">
            <MapPin className="w-6 h-6 text-red-300" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white mb-1">Error Loading Places</h3>
            <p className="text-sm text-red-400">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!knowledge || knowledge.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto">
            <MapPin className="w-8 h-8 text-slate-300" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">
              No Known Places Yet
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              This agent has not established knowledge of any places in simulation
              {simulationId ? ` ${simulationId}` : ''}. Run the simulation or drive the agent to
              new locations to populate their spatial awareness.
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Filtering, sorting, units, and search controls
  const [categoryFilter, setCategoryFilter] = React.useState<string>('All')
  const [sortBy, setSortBy] = React.useState<SortKey>(PLACE_LIST_CONFIG.defaultSortKey)
  const [sortDir, setSortDir] = React.useState<'desc' | 'asc'>(PLACE_LIST_CONFIG.defaultSortDir)
  const [useMiles, setUseMiles] = React.useState<boolean>(false)
  const [search, setSearch] = React.useState<string>('')

  const categories = React.useMemo(() => {
    const set = new Set<string>()
    knowledge.forEach(k => set.add((k.category_display_name || k.category_name || 'Other')))
    return ['All', ...Array.from(set).sort()]
  }, [knowledge])

  const filtered = React.useMemo(() => {
    let arr = categoryFilter === 'All' ? knowledge : knowledge.filter(k => (k.category_display_name || k.category_name) === categoryFilter)
    if (search.trim()) {
      const q = search.toLowerCase()
      arr = arr.filter(k => (
        (k.display_name || k.name || k.subcategory_name || '').toLowerCase().includes(q) ||
        (k.category_display_name || k.category_name || '').toLowerCase().includes(q)
      ))
    }
    return arr
  }, [knowledge, categoryFilter, search])

  const sortedKnowledge = React.useMemo(() => {
    const arr = [...filtered]
    arr.sort((a: any, b: any) => {
      const av = a[sortBy]
      const bv = b[sortBy]
      const an = typeof av === 'string' ? av.toLowerCase() : Number(av ?? 0)
      const bn = typeof bv === 'string' ? bv.toLowerCase() : Number(bv ?? 0)
      if (an < bn) return sortDir === 'asc' ? -1 : 1
      if (an > bn) return sortDir === 'asc' ? 1 : -1
      // tie-breakers
      const distDiff = (a.distance_km_from_home || 0) - (b.distance_km_from_home || 0)
      if (Math.abs(distDiff) > 1e-6) return distDiff
      return (b.knowledge_strength || 0) - (a.knowledge_strength || 0)
    })
    return arr
  }, [filtered, sortBy, sortDir])
  const visitedCount = sortedKnowledge.filter(item => item.number_of_times_visited > 0).length
  const highConfidenceCount = sortedKnowledge.filter(item => item.knowledge_strength >= 0.75).length
  const essentialCount = sortedKnowledge.filter(item => item.times_seen > 0 && (item.category_name || '').match(/gas|fuel|grocery|pharmacy|bank/i)).length

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <BaseCard title="Known Places" icon={MapPin}>
          <div className="text-3xl font-semibold text-white">{knowledge.length}</div>
          <p className="text-xs text-slate-400 mt-1">Total POIs in memory</p>
        </BaseCard>
        <BaseCard title="Visited" icon={Activity}>
          <div className="text-3xl font-semibold text-white">{visitedCount}</div>
          <p className="text-xs text-slate-400 mt-1">Visited at least once</p>
        </BaseCard>
        <BaseCard title="High Confidence" icon={RefreshCw}>
          <div className="text-3xl font-semibold text-white">{highConfidenceCount}</div>
          <p className="text-xs text-slate-400 mt-1">Knowledge strength ≥ 0.75</p>
        </BaseCard>
      </div>

      <div className={PLACE_LIST_CONFIG.styles.container}>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 px-4 md:px-5 py-4 border-b border-neutral-700">
          <div>
            <h3 className="text-sm font-semibold text-white">Place Memory</h3>
            <p className="text-xs text-slate-400">Includes essentials ({essentialCount}) and discovery over time</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Quick category chips - color-coded to match map POI colors */}
            <div className="flex flex-wrap gap-1">
              {['All', ...PLACE_LIST_CONFIG.quickCategories, ...categories.filter(c => c !== 'All' && !PLACE_LIST_CONFIG.quickCategories.includes(c))]
                .slice(0, 12)
                .map((c) => {
                  const label = c
                  const key = label.toLowerCase().replace(/\s+/g, '_')
                  // find a representative category_name for this subcategory label
                  const sample = knowledge.find(k => (k.subcategory_name || '').toLowerCase() === key)
                  const catKey = sample?.category_name || 'other'
                  const colorHex = poiCategoryColors[catKey]?.color || poiCategoryColors.other.color
                  const active = categoryFilter === label
                  const bg = active ? `${colorHex}33` : 'rgba(30, 41, 59, 0.8)' // translucent
                  const border = active ? colorHex : 'rgba(51, 65, 85, 0.9)'
                  const text = active ? '#e2e8f0' : '#cbd5e1'
                  return (
                    <button
                      key={label}
                      onClick={() => setCategoryFilter(label)}
                      className="px-2 py-1 rounded-full text-xs transition-colors"
                      style={{ background: bg, borderColor: border, color: text, borderWidth: 1 }}
                      title={poiCategoryColors[catKey]?.label || 'Other'}
                    >
                      {label}
                    </button>
                  )
                })}
            </div>
            {/* Search */}
            <div className="relative">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search places…"
                className="pl-7 pr-2 py-1 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-200"
              />
              <SearchIcon className="w-3.5 h-3.5 text-slate-400 absolute left-2 top-1.5" />
            </div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortKey)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-1"
            >
              <option value="knowledge_strength">Knowledge</option>
              <option value="display_name">Name</option>
              <option value="category_display_name">Category</option>
              <option value="familiarity_score">Familiarity</option>
              <option value="visit_frequency">Visits/mo</option>
              <option value="recency_days">Recency (days)</option>
              <option value="number_of_times_visited">Visited</option>
              <option value="times_seen">Seen</option>
              <option value="distance_km_from_home">Distance</option>
            </select>
            <button
              onClick={() => setSortDir(d => d === 'asc' ? 'desc' : 'asc')}
              className="px-2 py-1 text-xs rounded-lg border border-slate-700 text-slate-200 hover:border-slate-500 inline-flex items-center gap-1"
              title="Toggle sort direction"
            >
              <ArrowUpDown className="w-3.5 h-3.5" /> {sortDir === 'asc' ? 'Asc' : 'Desc'}
            </button>
            <button
              onClick={() => setUseMiles(v => !v)}
              className="px-2 py-1 text-xs rounded-lg border border-slate-700 text-slate-200 hover:border-slate-500"
              title="Toggle units"
            >{useMiles ? 'mi' : 'km'}</button>
            <button
              onClick={onRefresh}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-700 text-slate-200 hover:border-slate-500 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full table-auto divide-y divide-slate-800 text-sm">
            <thead className="bg-slate-900/70">
              <tr className="text-slate-300 text-[11px] uppercase tracking-wide">
                <th className="px-3 py-3 text-left">Name</th>
                <th className="px-3 py-3 text-center">Knowledge</th>
                <th className="px-3 py-3 text-right hidden md:table-cell whitespace-nowrap">Familiarity</th>
                <th className="px-3 py-3 text-right whitespace-nowrap">Distance ({useMiles ? 'mi' : 'km'})</th>
                <th className="px-3 py-3 text-right hidden lg:table-cell whitespace-nowrap">Visits/mo</th>
                <th className="px-3 py-3 text-right whitespace-nowrap">Seen</th>
                <th className="px-3 py-3 text-right whitespace-nowrap">Visited</th>
                <th className="px-3 py-3 text-left whitespace-nowrap">Last Seen</th>
              </tr>
            </thead>
            <tbody className={`divide-y divide-slate-800 text-slate-200 ${PLACE_LIST_CONFIG.styles.rowStripe}`}> 
              {sortedKnowledge.map((item) => {
                const strengthPercent = Math.round(item.knowledge_strength * 100)
                const dist = item.distance_km_from_home ? (useMiles ? (item.distance_km_from_home * 0.621371) : item.distance_km_from_home) : null
                const lastSeenDays = item.recency_days != null ? Number(item.recency_days) : undefined
                const newBadge = lastSeenDays != null && lastSeenDays <= 7
                return (
                  <tr 
                    key={item.osm_id} 
                    className={`${PLACE_LIST_CONFIG.styles.rowHover} cursor-pointer`}
                    onClick={() => navigate(`/poi/${item.osm_id}?simulation_id=${simulationId}`)}
                  >
                    <td className="px-3 py-3 text-sm font-medium text-white align-middle">
                      <button 
                        onClick={() => navigate(`/poi/${item.osm_id}?simulation_id=${simulationId}`)}
                        className="text-left hover:underline"
                      >
                        {item.display_name || item.name || item.subcategory_name || item.category_name || 'Unknown'}
                      </button>
                      <div className="text-xs text-neutral-400">{item.subcategory_name || item.category_name}</div>
                    </td>
                    <td className="px-3 py-3 align-middle">
                      <div className="flex items-center gap-2 justify-center">
                        <div className={`relative h-1.5 ${PLACE_LIST_CONFIG.styles.barBg} rounded-full overflow-hidden w-20`} title="Derived from recency × frequency × distance">
                          <div className={`absolute inset-y-0 ${PLACE_LIST_CONFIG.styles.barGradient} rounded-full`} style={{ width: `${Math.min(100, Math.max(0, strengthPercent))}%` }} />
                        </div>
                        <span className="text-xs text-slate-300 w-8 text-right">{strengthPercent}%</span>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right text-sm text-slate-200 hidden md:table-cell align-middle whitespace-nowrap">{item.familiarity_score ?? '—'}</td>
                    <td className={`px-3 py-3 text-right text-sm align-middle whitespace-nowrap ${distanceClass(dist ?? undefined)}`}>{dist != null ? dist.toFixed(2) : '—'}</td>
                    <td className="px-3 py-3 text-right text-sm text-slate-200 hidden lg:table-cell align-middle whitespace-nowrap">{item.visit_frequency != null ? item.visit_frequency.toFixed(2) : '—'}</td>
                    <td className="px-3 py-3 text-right text-sm text-slate-200 align-middle whitespace-nowrap">{item.times_seen}</td>
                    <td className="px-3 py-3 text-right text-sm text-slate-200 align-middle whitespace-nowrap">{item.number_of_times_visited}</td>
                    <td className="px-3 py-3 text-xs text-slate-400 align-middle whitespace-nowrap">
                      {lastSeenDays != null ? `${lastSeenDays} days ago` : (formatDateTime(item.last_time_seen))}
                      {newBadge && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-sky-800/60 text-sky-200 border border-sky-700">New</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// Cognition Tab Component
const CognitionTab: React.FC<{
  agentId: string
  simulationId: string | null
}> = ({ agentId, simulationId }) => {
  // TODO: Implement actual cognition data fetching
  // For now, show a professional empty state

  return (
    <div className="space-y-4">
      {/* Empty state - consistent with other pages */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 rounded-full bg-violet-500/15 flex items-center justify-center mx-auto">
            <Activity className="w-8 h-8 text-violet-300" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">
              No Decision Data Available
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              This agent has no recorded decisions or reasoning chains in the current period.
              {simulationId 
                ? ' Run a simulation step to see agent cognition data here.'
                : ' Select a simulation to view agent decision history.'}
            </p>
          </div>
          {!simulationId && (
            <div className="pt-2">
              <p className="text-xs text-slate-500">
                Agent cognition tracking requires an active simulation context.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Preview of what will be here */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <h3 className="text-sm font-semibold text-white mb-3">Decision Timeline</h3>
          <p className="text-xs text-slate-500">
            A chronological list of agent decisions, observations, and state changes will appear here.
          </p>
        </div>
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <h3 className="text-sm font-semibold text-white mb-3">Explanation Viewer</h3>
          <p className="text-xs text-slate-500">
            When you select a decision, this panel will show the agent's reasoning chain, 
            context variables, and resulting state updates.
          </p>
        </div>
      </div>
    </div>
  )
}

// Relationships Tab Component
const RelationshipsTab: React.FC<{ 
  householdMembers: any[]
  loading: boolean
  agentId: string
  simulationId: string | null
  navigate: any
}> = ({ householdMembers, loading, agentId, simulationId, navigate }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* household members section - neutral card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 md:p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Household Members ({householdMembers.length})</h3>
        {householdMembers.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {householdMembers.map((member, idx) => {
              const isCurrentAgent = member.agent_id === agentId
              const isPlaceholder = member.is_placeholder || (member.agent_id && member.agent_id.startsWith('ANON-'))
              const canClick = !isCurrentAgent && !isPlaceholder
              
              return (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border transition-all ${
                    isCurrentAgent 
                      ? 'border-sky-500/50 bg-sky-500/10' 
                      : isPlaceholder
                      ? 'border-slate-700/50 bg-slate-800/50 opacity-60 cursor-not-allowed'
                      : 'border-slate-700 bg-slate-800 hover:border-slate-600 cursor-pointer'
                  }`}
                  onClick={() => {
                    if (canClick) {
                      const url = simulationId 
                        ? `/agent/${member.agent_id}?simulation_id=${simulationId}`
                        : `/agent/${member.agent_id}`
                      navigate(url)
                    }
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-xs font-semibold text-slate-300">
                      {member.name ? member.name.substring(0, 2).toUpperCase() : '?'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">
                        {member.name || 'Unnamed Agent'}
                      </p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-xs text-slate-400 font-mono">
                          {member.agent_id}
                        </p>
                        {member.age && (
                          <span className="text-xs text-slate-500">
                            Age: {member.age}
                          </span>
                        )}
                        {member.gender && (
                          <span className="text-xs text-slate-500">
                            {member.gender}
                          </span>
                        )}
                      </div>
                    </div>
                    {/* keep highlight styling only; no 'You' tag */}
                    {isPlaceholder && (
                      <span className="text-xs px-2 py-1 rounded bg-slate-700/50 text-slate-400 border border-slate-600/50">
                        Placeholder
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">No household members found</p>
        )}
      </div>
    </div>
  )
}

// Helper Components
const InfoRow: React.FC<{ label: string; value: string | number }> = ({ label, value }) => (
  <div className="flex items-start justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</span>
    <span className="text-sm text-gray-900 dark:text-white text-right max-w-xs">{value}</span>
  </div>
)

const BalanceRow: React.FC<{ 
  label: string
  value: string
  bold?: boolean 
}> = ({ label, value, bold }) => (
  <div className="flex items-center justify-between py-2">
    <span className={`text-sm ${bold ? 'font-bold' : 'font-medium'} text-gray-700 dark:text-gray-300`}>
      {label}
    </span>
    <span className={`text-sm ${bold ? 'font-bold' : ''} text-gray-900 dark:text-white`}>
      {value}
    </span>
  </div>
)

export default AgentProfile
