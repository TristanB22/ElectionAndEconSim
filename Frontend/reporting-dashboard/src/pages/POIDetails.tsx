import React, { useState, useEffect } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { MapPin, ArrowLeft, Map as MapIcon, Users, Phone, Globe, Mail } from 'lucide-react'
import { TopBar } from '../components/TopBar'
import { LeftNav } from '../components/LeftNav'
import { useSimulationId } from '../hooks/useSimulationId'
import { API_ENDPOINTS } from '../config/api'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import { MetricCard, AgentHeader, AgentTabs, type AgentTabId } from '../components/agent'
import { DefinitionListCard } from '../components/agent/DefinitionListCard'
import { JsonViewer } from '../components/shared/JsonViewer'
import { normalizePoi, DEFAULT_POI_SCHEMA } from '../utils/normalizePoi'

interface POIResponse {
  type: string
  properties: Record<string, any>
  geometry: { type: string; coordinates: [number, number] }
}

export const POIDetails: React.FC = () => {
  const { osmId } = useParams<{ osmId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const simulationIdParam = searchParams.get('simulation_id')

  const { simulations, simulationId: simId, setSimulationId: setSimId, loading: simLoading } = useSimulationId()
  const [poi, setPoi] = useState<POIResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<AgentTabId>('overview')

  useEffect(() => {
    if (simulationIdParam && simulationIdParam !== simId) setSimId(simulationIdParam)
  }, [simulationIdParam, simId, setSimId])

  useEffect(() => {
    const fetchPOI = async () => {
      if (!osmId) return
      setLoading(true)
      setError(null)
      try {
        const response = await fetch(API_ENDPOINTS.POIS_DETAIL(String(osmId)))
        if (!response.ok) throw new Error('Failed to fetch POI details')
        const data = await response.json()
        setPoi(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load POI details')
      } finally {
        setLoading(false)
      }
    }
    fetchPOI()
  }, [osmId])

  const simOptions = (simulations.length
    ? simulations.map((s: any) => ({ label: s.created_at ? `${s.id} — ${new Date(s.created_at).toLocaleString()}` : s.id, value: s.id }))
    : [{ label: 'Latest', value: 'latest' }]
  )

  const model = poi ? normalizePoi(poi, DEFAULT_POI_SCHEMA) : null
  const displayName = model?.identity.displayName || model?.identity.name || model?.identity.category || 'Unknown Place'

  const tabs = [
    { id: 'overview' as AgentTabId, label: 'Overview', icon: <MapPin className="w-4 h-4" /> },
    { id: 'activity' as AgentTabId, label: 'Activity', icon: <Users className="w-4 h-4" /> },
  ]

  if (!osmId) {
    return (
      <div className="min-h-screen" style={{ background: '#0F1520' }}>
        <TopBar />
        <LeftNav />
        <div className="ml-14 pt-16 p-8 text-slate-400">POI ID not provided</div>
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Fixed gradient background */}
      <div className="fixed inset-0 bg-gradient-to-br from-[#0B111A] via-[#0F1520] to-[#0B111A] -z-10 h-[200vh]"></div>

      <TopBar simulationId={simId} setSimulationId={setSimId} simulationOptions={simOptions} simulationLoading={simLoading} />
      <LeftNav />

      <div className="ml-14 relative z-0">
        {loading ? (
          <div className="pt-16 min-h-screen">
            <div className="max-w-6xl mx-auto px-4 lg:px-6 py-8 space-y-8">
              <div className="bg-slate-900/50 border border-slate-800/50 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-slate-800/50 to-slate-700/50 animate-pulse" />
                  <div className="flex-1 space-y-3">
                    <div className="h-7 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded-lg w-56 animate-shimmer bg-[length:200%_100%]" />
                    <div className="h-4 bg-gradient-to-r from-slate-800/50 via-slate-700/50 to-slate-800/50 rounded w-72 animate-shimmer bg-[length:200%_100%]" />
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <div className="relative">
                  <div className="w-16 h-16 border-4 border-slate-800/30 rounded-full"></div>
                  <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin absolute top-0 left-0"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-3 h-3 bg-sky-500 rounded-full animate-pulse"></div>
                  </div>
                </div>
                <div className="text-center space-y-1">
                  <p className="text-sm font-medium text-slate-400">Loading POI details...</p>
                  <p className="text-xs text-slate-500">Fetching place information</p>
                </div>
              </div>
            </div>
          </div>
        ) : error || !poi || !model ? (
          <div className="pt-16 min-h-screen">
            <div className="max-w-6xl mx-auto px-4 lg:px-6 py-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center">
                <MapPin className="w-12 h-12 mx-auto mb-3 text-red-500" />
                <p className="text-red-400">{error || 'POI not found'}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="pt-16 min-h-[200vh]">
            <AgentHeader
              agentId={String(model.identity.osmId)}
              name={displayName}
              city={model.location.city}
              state={model.location.state}
              age={null}
              gender={null}
              party={model.identity.category || null}
              simulationId={simId}
              onViewOnMap={() => navigate(simId ? `/map?simulation_id=${simId}` : '/map')}
              onCopyLink={() => navigator.clipboard.writeText(window.location.href)}
            />

            <div className="max-w-6xl mx-auto px-4 lg:px-6 py-4 space-y-4">
              <button onClick={() => navigate(simId ? `/map?simulation_id=${simId}` : '/map')} className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors">
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Map</span>
              </button>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <MetricCard icon={<MapPin className="w-5 h-5" />} iconClassName="bg-sky-500/15 text-sky-100" label="Location" value={model.location.lat && model.location.lon ? `${model.location.lat}, ${model.location.lon}` : '—'} accentColor="cyan" sublabel="Latitude, Longitude" />
                <MetricCard icon={<MapPin className="w-5 h-5" />} iconClassName="bg-emerald-500/15 text-emerald-100" label="Category" value={model.identity.category || '—'} accentColor="green" sublabel={model.identity.subcategory || undefined} />
                <MetricCard icon={<Users className="w-5 h-5" />} iconClassName="bg-violet-500/15 text-violet-100" label="Visitors" value="—" accentColor="violet" sublabel="Coming soon" />
              </div>
            </div>

            <AgentTabs tabs={[{ id: 'overview' as AgentTabId, label: 'Overview', icon: <MapPin className="w-4 h-4" /> }, { id: 'activity' as AgentTabId, label: 'Activity', icon: <Users className="w-4 h-4" /> }]} activeTab={activeTab} onTabChange={setActiveTab} />

            <div className="max-w-6xl mx-auto px-4 lg:px-6 py-6 pb-24 min-h-[calc(100vh-400px)]">
              {activeTab === 'overview' && (<OverviewTab poi={model} />)}
              {activeTab === 'activity' && (<ActivityTab osmId={String(model.identity.osmId)} simulationId={simId} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const OverviewTab: React.FC<{ poi: ReturnType<typeof normalizePoi> }> = ({ poi }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 space-y-4">
        <DefinitionListCard title="Identity" items={[{ label: 'Name', value: poi.identity.name }, { label: 'OSM ID', value: poi.identity.osmId }, { label: 'Category', value: poi.identity.category }, { label: 'Subcategory', value: poi.identity.subcategory }]} />
        <DefinitionListCard title="Location" items={[{ label: 'Address', value: poi.location.address }, { label: 'City', value: poi.location.city }, { label: 'State', value: poi.location.state }, { label: 'Postcode', value: poi.location.postcode }, { label: 'Country', value: poi.location.country }, { label: 'Coordinates', value: poi.location.lat && poi.location.lon ? `${poi.location.lat}, ${poi.location.lon}` : null }]} />
        {(poi.contact.phone || poi.contact.website || poi.contact.email) && (
          <DefinitionListCard title="Contact" items={[{ label: 'Phone', value: poi.contact.phone }, { label: 'Website', value: poi.contact.website }, { label: 'Email', value: poi.contact.email }]} />
        )}
        {Object.keys(poi.amenities).length > 0 && (
          <DefinitionListCard title="Amenities & Features" items={Object.entries(poi.amenities).map(([k, v]) => ({ label: k.replace(/_/g, ' ').replace(/:/g, ' - '), value: String(v) }))} />
        )}
        {poi.allData && (<JsonViewer data={poi.allData} title="All POI Data (GeoJSON)" />)}
      </div>
      <div className="space-y-4">
        <div style={{ background: '#0B111A', border: '1px solid #1C2836', borderRadius: 16, padding: 16 }}>
          <h3 style={{ color: '#E6EDF6', fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Quick Actions</h3>
          <div className="space-y-2">
            {poi.contact.phone && (<a href={`tel:${poi.contact.phone}`} className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg" style={{ background: '#0D1420', border: '1px solid #1C2836', color: '#E6EDF6' }}><Phone className="w-4 h-4" /><span>Call</span></a>)}
            {poi.contact.website && (<a href={poi.contact.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg" style={{ background: '#0D1420', border: '1px solid #1C2836', color: '#E6EDF6' }}><Globe className="w-4 h-4" /><span>Visit Website</span></a>)}
            {poi.contact.email && (<a href={`mailto:${poi.contact.email}`} className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg" style={{ background: '#0D1420', border: '1px solid #1C2836', color: '#E6EDF6' }}><Mail className="w-4 h-4" /><span>Email</span></a>)}
            {poi.location.lat && poi.location.lon && (<a href={`https://www.openstreetmap.org/#map=17/${poi.location.lat}/${poi.location.lon}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg" style={{ background: '#0D1420', border: '1px solid #1C2836', color: '#E6EDF6' }}><MapIcon className="w-4 h-4" /><span>Open in OSM</span></a>)}
          </div>
        </div>
      </div>
    </div>
  )
}

const ActivityTab: React.FC<{ osmId: string; simulationId: string | null }> = ({ osmId, simulationId }) => {
  return (
    <div className="space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 rounded-full bg-violet-500/15 flex items-center justify-center mx-auto">
            <Users className="w-8 h-8 text-violet-300" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">No Activity Data Available</h3>
            <p className="text-sm text-slate-400 leading-relaxed">Visitor data and activity metrics for this POI are not yet available.{simulationId ? ' Run a simulation to see agent interactions with this location.' : ' Select a simulation to view POI activity history.'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default POIDetails
