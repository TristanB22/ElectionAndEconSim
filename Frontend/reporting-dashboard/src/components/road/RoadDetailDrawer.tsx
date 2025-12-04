import React, { useEffect, useState } from 'react'
import { X, ExternalLink, Copy, BadgeInfo, Code } from 'lucide-react'
import { computeRoadView, RoadView, RoadSummaryField, RoadSection } from '../../lib/road/view'

export interface RoadDetailDrawerProps {
  road: {
    id: string | number
    geometry?: { type: string; coordinates: any }
    properties?: Record<string, any>
  } | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Tab = 'summary' | 'details' | 'links'

const PropertyGrid: React.FC<{ tags: Record<string, string> }> = ({ tags }) => (
  <div className="grid grid-cols-1 gap-2">
    {Object.entries(tags).map(([key, value]) => (
      <div key={key} className="flex items-center justify-between gap-3 p-2 bg-gray-50 dark:bg-gray-800/50 rounded">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide truncate">{key}</span>
        <span className="text-sm text-gray-900 dark:text-white truncate">{typeof value === 'string' ? value : JSON.stringify(value)}</span>
      </div>
    ))}
  </div>
)

const SummaryField: React.FC<{ field: RoadSummaryField }> = ({ field }) => (
  <div className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
    <div className="text-gray-400 dark:text-gray-500 mt-0.5">
      <BadgeInfo className="w-4 h-4" />
    </div>
    <div className="flex-1 min-w-0">
      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">{field.label}</div>
      <div className="text-sm text-gray-900 dark:text-white">{field.value}</div>
    </div>
  </div>
)

export const RoadDetailDrawer: React.FC<RoadDetailDrawerProps> = ({ road, open, onOpenChange }) => {
  const [activeTab, setActiveTab] = useState<Tab>('summary')
  const [view, setView] = useState<RoadView | null>(null)
  const [showRawJson, setShowRawJson] = useState(false)

  useEffect(() => {
    if (road) {
      const v = computeRoadView(road.properties || {}, road.id, road.geometry)
      setView(v)
      setActiveTab('summary')
    } else {
      setView(null)
    }
  }, [road])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && open) onOpenChange(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onOpenChange])

  if (!open || !road || !view) return null

  const isBoundary = view.sections.some(s => s.key === 'boundary')
  const name = (road.properties?.name as string) || (isBoundary ? `Boundary #${road.id}` : `Road #${road.id}`)
  const highway = road.properties?.highway || road.properties?.tags?.highway
  const ref = road.properties?.ref || road.properties?.tags?.ref

  const openInOSM = () => {
    try {
      if (!road.geometry) return
      const coords = road.geometry.type === 'MultiLineString' ? road.geometry.coordinates?.[0]?.[0] : road.geometry.coordinates?.[0]
      if (coords && coords.length >= 2) {
        const [lon, lat] = coords
        window.open(`https://www.openstreetmap.org/#map=17/${lat}/${lon}`,'_blank')
      }
    } catch {}
  }

  const copyGeoJSON = () => {
    const geoJSON = JSON.stringify({ type: 'Feature', properties: road.properties || {}, geometry: road.geometry }, null, 2)
    navigator.clipboard.writeText(geoJSON)
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={() => onOpenChange(false)} />
      <div className="fixed inset-y-0 right-0 w-[480px] max-w-full bg-white dark:bg-gray-950 shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                {isBoundary ? 'BOUNDARY' : 'ROAD'}
              </span>
              {!isBoundary && highway && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">{String(highway)}</span>
              )}
              {!isBoundary && ref && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">{String(ref)}</span>
              )}
            </div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white truncate mt-1">{name}</div>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800 flex items-center gap-2 text-sm">
          <button className={`px-3 py-1.5 rounded-lg ${activeTab==='summary'?'bg-gray-900 text-white dark:bg-white dark:text-gray-900':'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300'}`} onClick={() => setActiveTab('summary')}>Summary</button>
          <button className={`px-3 py-1.5 rounded-lg ${activeTab==='details'?'bg-gray-900 text-white dark:bg-white dark:text-gray-900':'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300'}`} onClick={() => setActiveTab('details')}>Details</button>
          <button className={`px-3 py-1.5 rounded-lg ${activeTab==='links'?'bg-gray-900 text-white dark:bg-white dark:text-gray-900':'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300'}`} onClick={() => setActiveTab('links')}>Links</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeTab === 'summary' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <button onClick={openInOSM} className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
                  <ExternalLink className="w-4 h-4" /> Open in OSM
                </button>
                <button onClick={copyGeoJSON} className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors">
                  <Copy className="w-4 h-4" /> Copy GeoJSON
                </button>
              </div>
              <div className="space-y-3">
                {view.summary.map(f => <SummaryField key={f.key} field={f} />)}
              </div>
            </div>
          )}

          {activeTab === 'details' && (
            <div className="space-y-4">
              {view.sections.map((section: RoadSection) => (
                <div key={section.key} className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                  <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800/50 text-sm font-semibold text-gray-900 dark:text-white">{section.title}</div>
                  <div className="p-4 bg-white dark:bg-gray-900">
                    <PropertyGrid tags={section.tags} />
                  </div>
                </div>
              ))}
              <button
                onClick={() => setShowRawJson(!showRawJson)}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <Code className="w-4 h-4" /> {showRawJson ? 'Hide' : 'View'} Raw OSM Tags
              </button>
              {showRawJson && (
                <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                  <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800/50 text-sm font-semibold text-gray-900 dark:text-white">Raw OSM Tags (JSON)</div>
                  <div className="p-4 bg-white dark:bg-gray-900 overflow-x-auto">
                    <pre className="text-xs font-mono text-gray-900 dark:text-gray-100 whitespace-pre-wrap break-words">
                      {JSON.stringify(view.rawJsonTags, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'links' && (
            <div className="space-y-3">
              <button onClick={openInOSM} className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
                <ExternalLink className="w-4 h-4" /> Open in OSM
              </button>
              <button onClick={copyGeoJSON} className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors">
                <Copy className="w-4 h-4" /> Copy as GeoJSON
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}


