import React, { useEffect, useMemo, useState } from 'react'
import { X, ExternalLink, Copy, ChevronDown, ChevronUp, Globe, Phone, Mail } from 'lucide-react'
import { computeEntityView, EntityInput, EntityView } from '../lib/entity/view'

export interface EntityDetailDrawerProps {
  entity: EntityInput | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Tab = 'summary' | 'details' | 'links'

// Get category color matching InfoSidebar
const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    // POI categories
    'amenity': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    'shop': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    'tourism': 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    'leisure': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    'healthcare': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    'office': 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',
    'craft': 'bg-lime-100 text-lime-800 dark:bg-lime-900/30 dark:text-lime-300',
    'religion': 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
    'historic': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
    'building': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    'place': 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300',
    'natural': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
    // Road categories
    'highway': 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
    // Boundary/border types - unique colors for each
    'town': 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
    'city': 'bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900/30 dark:text-fuchsia-300',
    'county': 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
    'state': 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300',
    'country': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    'administrative': 'bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-300',
    'municipality': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
    'province': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    'district': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    'region': 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',
    'other': 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
  }
  return colors[category] || colors['other']
}

// Derive a POI category from raw entity properties/tags when missing in computeEntityView
const derivePoiCategory = (entity: EntityInput | null): string | null => {
  if (!entity) return null
  const tags: Record<string, any> = (entity.properties as any) || (entity as any).tags || {}
  const direct = tags.category as string | undefined
  if (direct && typeof direct === 'string') return direct
  const preferred = ['amenity','shop','tourism','leisure','healthcare','office','craft','religion','historic','natural','building','place']
  for (const key of preferred) {
    const val = tags[key]
    if (typeof val === 'string' && val) {
      return key
    }
  }
  return null
}

const PropertyGrid: React.FC<{ tags: Record<string, string> }> = ({ tags }) => (
  <div className="grid grid-cols-1 gap-2">
    {Object.entries(tags).map(([key, value]) => (
      <div key={key} className="flex items-start justify-between gap-3 py-2 border-b border-gray-100 dark:border-gray-800">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide flex-shrink-0">{key}</span>
        <span className="text-sm text-gray-900 dark:text-white text-right break-all">{String(value)}</span>
      </div>
    ))}
  </div>
)

const SectionAccordion: React.FC<{ 
  section: { title: string; key: string; tags: Record<string, string> }
  defaultExpanded?: boolean
}> = ({ section, defaultExpanded = true }) => {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{section.title}</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {Object.keys(section.tags).length} {Object.keys(section.tags).length === 1 ? 'field' : 'fields'}
          </span>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>
      {expanded && (
        <div className="p-4 bg-white dark:bg-gray-900">
          <PropertyGrid tags={section.tags} />
        </div>
      )}
    </div>
  )
}

const RawJsonAccordion: React.FC<{ data: any }> = ({ data }) => {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-green-500/30 dark:border-green-400/30 rounded-xl overflow-hidden bg-green-950/20 dark:bg-green-950/40">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 bg-green-900/20 dark:bg-green-900/40 hover:bg-green-900/30 dark:hover:bg-green-900/50 transition-colors"
      >
        <h3 className="text-sm font-semibold text-green-700 dark:text-green-300 font-mono">Raw OSM Tags</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-green-600 dark:text-green-400 font-mono">JSON</span>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-green-600 dark:text-green-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-green-600 dark:text-green-400" />
          )}
        </div>
      </button>
      {expanded && (
        <div className="p-4 bg-black/40 dark:bg-black/60 overflow-x-auto">
          <pre className="text-xs font-mono text-green-400 dark:text-green-300 whitespace-pre-wrap break-words">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export const EntityDetailDrawer: React.FC<EntityDetailDrawerProps> = ({ entity, open, onOpenChange }) => {
  const [activeTab, setActiveTab] = useState<Tab>('summary')
  const [view, setView] = useState<EntityView | null>(null)

  useEffect(() => {
    if (entity) {
      setView(computeEntityView(entity))
      setActiveTab('summary')
    } else {
      setView(null)
    }
  }, [entity])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && open) onOpenChange(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onOpenChange])

  if (!open || !entity || !view) return null

  // Ensure POIs show their category badge even if computeEntityView omitted it
  const badgesToDisplay = (() => {
    const base = Array.isArray(view.badges) ? [...view.badges] : []
    if (view.type === 'poi') {
      const cat = derivePoiCategory(entity)
      if (cat && !base.includes(cat)) base.unshift(cat)
    }
    return base
  })()

  const openInOSM = () => {
    try {
      if (!entity.geometry) return
      const coords = (entity.geometry as any).coordinates
      const first = entity.geometry.type === 'Point' ? coords : (entity.geometry.type === 'MultiLineString' || entity.geometry.type === 'MultiPolygon') ? coords?.[0]?.[0] : coords?.[0]
      if (Array.isArray(first) && first.length >= 2) {
        const [lon, lat] = first
        window.open(`https://www.openstreetmap.org/#map=17/${lat}/${lon}`,'_blank')
      }
    } catch {}
  }

  const copyGeoJSON = () => {
    const geoJSON = JSON.stringify({ type: 'Feature', properties: entity.properties || entity.tags || {}, geometry: entity.geometry }, null, 2)
    navigator.clipboard.writeText(geoJSON)
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={() => onOpenChange(false)} />
      <div className="fixed inset-y-0 right-0 w-[520px] max-w-full bg-white dark:bg-gray-950 shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              {badgesToDisplay.map((badge, i) => (
                <span key={i} className={`text-xs px-2 py-0.5 rounded-full ${getCategoryColor(badge)}`}>
                  {badge}
                </span>
              ))}
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                view.type === 'poi' 
                  ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' 
                  : view.type === 'boundary'
                  ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
                  : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
              }`}>
                {view.type.toUpperCase()}
              </span>
            </div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white truncate mt-1">{view.name}</div>
          </div>
          <button onClick={() => onOpenChange(false)} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">
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
              {/* Category badges section */}
              {badgesToDisplay.length > 0 && (
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Category</div>
                  <div className="flex flex-wrap gap-2">
                    {badgesToDisplay.map((badge, i) => (
                      <span key={i} className={`text-xs px-2.5 py-1 rounded-full font-medium ${getCategoryColor(badge)}`}>
                        {badge}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Summary fields */}
              <div className="space-y-3">
                {view.summary.map(f => (
                  <div key={f.key} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">{f.label}</div>
                      <div className="text-sm text-gray-900 dark:text-white">{f.value}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'details' && (
            <div className="space-y-4">
              {view.sections
                .filter(section => Object.keys(section.tags).length > 0)
                .map(section => (
                  <SectionAccordion key={section.key} section={section} />
                ))}

              {/* Raw JSON as an expandable section with hacker aesthetic */}
              <RawJsonAccordion data={view.rawJsonTags || entity.properties || entity.tags || {}} />
            </div>
          )}

          {activeTab === 'links' && (
            <div className="space-y-4">
              {/* Entity-specific links */}
              {view.links.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Contact & External Links</h3>
                  {view.links.map((link, i) => {
                    const icon = link.type === 'website' ? <Globe className="w-4 h-4" /> : link.type === 'phone' ? <Phone className="w-4 h-4" /> : <Mail className="w-4 h-4" />
                    return (
                      <a
                        key={i}
                        href={link.href}
                        target={link.type === 'website' ? '_blank' : undefined}
                        rel={link.type === 'website' ? 'noopener noreferrer' : undefined}
                        className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      >
                        {icon}
                        <span className="flex-1 truncate">{link.href.replace('tel:', '').replace('mailto:', '').replace('https://', '').replace('http://', '')}</span>
                        {link.type === 'website' && <ExternalLink className="w-3 h-3 flex-shrink-0" />}
                      </a>
                    )
                  })}
                </div>
              )}
              
              {/* Generic actions */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Actions</h3>
                <button onClick={openInOSM} className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors w-full">
                  <ExternalLink className="w-4 h-4" /> Open in OpenStreetMap
                </button>
                <button onClick={copyGeoJSON} className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors w-full">
                  <Copy className="w-4 h-4" /> Copy as GeoJSON
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
