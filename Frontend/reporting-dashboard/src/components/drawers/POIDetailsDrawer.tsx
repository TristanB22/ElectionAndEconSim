import { useState, useEffect, type CSSProperties } from 'react'
import { motion } from 'framer-motion'
import { MapPin, Copy, Crosshair, ExternalLink, ChevronDown, Navigation, User, GitBranch } from 'lucide-react'
import type { Map as MapLibreMap } from 'maplibre-gl'
import { useNavigate } from 'react-router-dom'
import { BaseDrawer } from './BaseDrawer'
import { ActionChip } from './ActionChip'
import { staggerContainerVariants, staggerChildVariants, accordionVariants } from '../../hooks/useDrawerMotion'
import { computeEntityView, EntityInput, EntityView } from '../../lib/entity/view'
import { API_ENDPOINTS, buildApiUrl } from '../../config/api'

/**
 * POIDetailsDrawer - Displays information about a selected Point of Interest
 * 
 * Design Philosophy:
 * - Header shows POI name + category badges prominently
 * - Summary tab displays key information in readable format
 * - Details tab shows all OSM tags organized by section
 * - Actions: Copy coords, Center map, Route to location, Open in OSM
 * - Glass aesthetic matches rest of drawer system
 * 
 * Tabs: Summary | Details | Links
 */

interface POIDetailsDrawerProps {
  entity: EntityInput | null
  open: boolean
  onOpenChange: (open: boolean) => void
  map: MapLibreMap | null
  onRouteToLocation?: (lat: number, lon: number) => void
  simulationId?: string | null
  enabledTabs?: Tab[] // Optional: specify which tabs to show
  selectedDatetime?: Date | null // For fetching agent locations at specific time
}

type Tab = 'summary' | 'details' | 'links'

const GLASS_CARD_STYLE: CSSProperties = Object.freeze({
  background: 'rgba(255, 255, 255, 0.03)',
  borderColor: 'rgba(255, 255, 255, 0.1)',
})

// Get category color for badges
const getCategoryColor = (category: string): { bg: string; text: string; border: string } => {
  const colors: Record<string, { bg: string; text: string; border: string }> = {
    'Agent': { bg: 'rgba(59, 130, 246, 0.2)', text: 'rgb(147, 197, 253)', border: 'rgba(59, 130, 246, 0.3)' },
    'amenity': { bg: 'rgba(59, 130, 246, 0.2)', text: 'rgb(147, 197, 253)', border: 'rgba(59, 130, 246, 0.3)' },
    'shop': { bg: 'rgba(34, 197, 94, 0.2)', text: 'rgb(134, 239, 172)', border: 'rgba(34, 197, 94, 0.3)' },
    'tourism': { bg: 'rgba(251, 146, 60, 0.2)', text: 'rgb(253, 186, 116)', border: 'rgba(251, 146, 60, 0.3)' },
    'leisure': { bg: 'rgba(168, 85, 247, 0.2)', text: 'rgb(216, 180, 254)', border: 'rgba(168, 85, 247, 0.3)' },
    'healthcare': { bg: 'rgba(239, 68, 68, 0.2)', text: 'rgb(252, 165, 165)', border: 'rgba(239, 68, 68, 0.3)' },
    'office': { bg: 'rgba(6, 182, 212, 0.2)', text: 'rgb(103, 232, 249)', border: 'rgba(6, 182, 212, 0.3)' },
    'craft': { bg: 'rgba(132, 204, 22, 0.2)', text: 'rgb(190, 242, 100)', border: 'rgba(132, 204, 22, 0.3)' },
    'religion': { bg: 'rgba(249, 115, 22, 0.2)', text: 'rgb(254, 215, 170)', border: 'rgba(249, 115, 22, 0.3)' },
    'historic': { bg: 'rgba(99, 102, 241, 0.2)', text: 'rgb(165, 180, 252)', border: 'rgba(99, 102, 241, 0.3)' },
    'building': { bg: 'rgba(234, 179, 8, 0.2)', text: 'rgb(253, 224, 71)', border: 'rgba(234, 179, 8, 0.3)' },
    'natural': { bg: 'rgba(16, 185, 129, 0.2)', text: 'rgb(110, 231, 183)', border: 'rgba(16, 185, 129, 0.3)' },
  }
  return colors[category] || { bg: 'rgba(156, 163, 175, 0.2)', text: 'rgb(209, 213, 219)', border: 'rgba(156, 163, 175, 0.3)' }
}

// Derive POI category from entity tags
const derivePoiCategory = (entity: EntityInput | null): string | null => {
  if (!entity) return null
  const tags: Record<string, any> = (entity.properties as any) || (entity as any).tags || {}
  const direct = tags.category as string | undefined
  if (direct && typeof direct === 'string') return direct
  const preferred = ['amenity', 'shop', 'tourism', 'leisure', 'healthcare', 'office', 'craft', 'religion', 'historic', 'natural', 'building', 'place']
  for (const key of preferred) {
    const val = tags[key]
    if (typeof val === 'string' && val) {
      return key
    }
  }
  return null
}

export function POIDetailsDrawer({ 
  entity, 
  open, 
  onOpenChange, 
  map,
  onRouteToLocation,
  simulationId,
  enabledTabs,
  selectedDatetime
}: POIDetailsDrawerProps) {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<Tab>('summary')
  const [view, setView] = useState<EntityView | null>(null)
  const [loading, setLoading] = useState(false)
  
  // Determine which tabs to show based on entity type
  const availableTabs: Tab[] = enabledTabs || (() => {
    if (!entity) return ['summary', 'details', 'links']
    // For agents, hide Links tab
    if (entity.type === 'agent') return ['summary', 'details']
    // For POIs and roads, show all tabs
    return ['summary', 'details', 'links']
  })()

  useEffect(() => {
    if (!entity) {
      setView(null)
      return
    }

    // For agents, fetch full data from API
    if (entity.type === 'agent') {
      const fetchAgentData = async () => {
        setLoading(true)
        try {
          const url = buildApiUrl(API_ENDPOINTS.AGENT_DETAILS(String(entity.id)), {
            simulation_id: simulationId || undefined,
          })
          const response = await fetch(url)
          if (!response.ok) throw new Error('Failed to fetch agent data')
          const data = await response.json()
          
          // Merge agent data into entity
          const enrichedEntity = {
            ...entity,
            agentData: {
              name: data.agent_data?.name,
              personal_summary: data.personal_summary,
              l2_agent_core: data.l2_data?.l2_agent_core,
              l2_location: data.l2_data?.l2_location,
              l2_geo: data.l2_data?.l2_geo,
              l2_political_part_1: data.l2_data?.l2_political_part_1,
              l2_political_part_2: data.l2_data?.l2_political_part_2,
              l2_political_part_3: data.l2_data?.l2_political_part_3,
              l2_other_part_1: data.l2_data?.l2_other_part_1,
              l2_other_part_2: data.l2_data?.l2_other_part_2,
              l2_other_part_3: data.l2_data?.l2_other_part_3,
              l2_other_part_4: data.l2_data?.l2_other_part_4,
            }
          }
          setView(computeEntityView(enrichedEntity))
          setActiveTab('summary')
        } catch (error) {
          console.error('Error fetching agent data:', error)
          // Fallback to basic view
          setView(computeEntityView(entity))
          setActiveTab('summary')
        } finally {
          setLoading(false)
        }
      }
      fetchAgentData()
    } else {
      // For POIs and roads, use entity directly
      setView(computeEntityView(entity))
      setActiveTab('summary')
    }
  }, [entity, simulationId])

  if (!entity || !view) return null

  // Get coordinates for actions
  const getCoordinates = (): [number, number] | null => {
    if (!entity.geometry) return null
    let coords: any = (entity.geometry as any).coordinates

    // Drill down through nested arrays (e.g. Polygon, MultiPolygon, LineString)
    // until we find a simple [lon, lat] pair.
    while (Array.isArray(coords) && coords.length > 0 && Array.isArray(coords[0])) {
      coords = coords[0]
    }

    if (
      Array.isArray(coords) &&
      coords.length >= 2 &&
      typeof coords[0] === 'number' &&
      typeof coords[1] === 'number'
    ) {
      const [lon, lat] = coords
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null
      return [lat, lon] // [lat, lon]
    }

    return null
  }

  const coordinates = getCoordinates()

  // Actions
  const copyCoordinates = () => {
    if (coordinates) {
      navigator.clipboard.writeText(`${coordinates[0].toFixed(6)}, ${coordinates[1].toFixed(6)}`)
    }
  }

  const centerOnLocation = async () => {
    if (!map) return
    
    // For agents, if we don't have coordinates, fetch from backend
    if (entity.type === 'agent' && (!coordinates || (coordinates[0] === 0 && coordinates[1] === 0))) {
      try {
        const agentId = String(entity.id)
        
        // Need to fetch the agent's current location at the selected datetime
        if (!simulationId || !selectedDatetime) {
          console.warn('Cannot center on agent: missing simulation ID or datetime')
          return
        }
        
        // Fetch agent locations for this simulation at the selected datetime
        const url = buildApiUrl(API_ENDPOINTS.AGENT_LOCATIONS(simulationId), {
          datetime: selectedDatetime.toISOString(),
        })
        
        const response = await fetch(url)
        if (!response.ok) {
          console.error('Failed to fetch agent locations for centering')
          return
        }
        
        const data = await response.json()
        const locations = data.locations || []
        
        // Find this specific agent's location
        const agentLocation = locations.find((loc: any) => loc.agent_id === agentId)
        
        if (agentLocation && agentLocation.latitude && agentLocation.longitude) {
          const currentZoom = Math.min(map.getZoom(), 18)
          map.flyTo({
            center: [Number(agentLocation.longitude), Number(agentLocation.latitude)],
            zoom: currentZoom,
            duration: 500
          })
        } else {
          console.warn('Agent location not found in current simulation frame')
        }
      } catch (error) {
        console.error('Error fetching agent location for centering:', error)
      }
      return
    }
    
    // For POIs and roads with coordinates
    if (coordinates) {
      // Center without changing zoom level (clamped to max zoom)
      const currentZoom = Math.min(map.getZoom(), 18)
      map.flyTo({
        center: [coordinates[1], coordinates[0]],
        zoom: currentZoom,
        duration: 500
      })
    }
  }

  const openInOSM = () => {
    if (coordinates) {
      window.open(`https://www.openstreetmap.org/#map=17/${coordinates[0]}/${coordinates[1]}`, '_blank')
    }
  }

  const routeToHere = () => {
    if (coordinates && onRouteToLocation) {
      onRouteToLocation(coordinates[0], coordinates[1])
    }
  }

  // Get badges
  const badgesToDisplay = (() => {
    const base = Array.isArray(view.badges) ? [...view.badges] : []
    if (view.type === 'poi') {
      const cat = derivePoiCategory(entity)
      if (cat && !base.includes(cat)) base.unshift(cat)
    }
    return base
  })()

  // Get icon and color based on entity type
  const getEntityIcon = () => {
    switch (view.type) {
      case 'agent':
        return { Icon: User, color: 'rgba(59, 100, 246, 0.2)', borderColor: 'rgba(59, 130, 246, 0.3)', iconColor: 'text-blue-400' }
      case 'road':
        return { Icon: GitBranch, color: 'rgba(234, 179, 8, 0.2)', borderColor: 'rgba(234, 179, 8, 0.3)', iconColor: 'text-yellow-400' }
      case 'boundary':
        return { Icon: MapPin, color: 'rgba(239, 68, 68, 0.2)', borderColor: 'rgba(239, 68, 68, 0.3)', iconColor: 'text-red-400' }
      default:
        return { Icon: MapPin, color: 'rgba(59, 130, 246, 0.2)', borderColor: 'rgba(59, 130, 246, 0.3)', iconColor: 'text-blue-400' }
    }
  }

  const { Icon: EntityIcon, color, borderColor, iconColor } = getEntityIcon()

  // Header component
  const header = (
    <div className="px-6 py-4 space-y-3">
      {/* Icon + Title */}
      <div className="flex items-start gap-3">
        <div 
          className="p-2.5 rounded-xl border flex-shrink-0"
          style={{
            background: color,
            borderColor: borderColor,
            backdropFilter: 'blur(8px)'
          }}
        >
          <EntityIcon className={`w-5 h-5 ${iconColor}`} />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-bold text-white truncate">{view.name}</h2>
          {view.type === 'agent' ? (
            <p className="text-xs text-gray-400 font-mono">{entity.id}</p>
          ) : view.type ? (
            <p className="text-xs text-gray-400 uppercase tracking-wider">{view.type}</p>
          ) : null}
        </div>
        
        {/* View Full Profile Button - Small, top right corner */}
        {view.type === 'agent' && (
          <button
            onClick={() => {
              const url = simulationId 
                ? `/agent/${entity.id}?simulation_id=${simulationId}`
                : `/agent/${entity.id}`
              navigate(url)
              onOpenChange(false)
            }}
            className="group flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all duration-200 text-xs font-medium"
            style={{
              background: 'rgba(59, 130, 246, 0.15)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              backdropFilter: 'blur(8px)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(59, 130, 246, 0.25)'
              e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)'
              e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.3)'
            }}
          >
            <span className="text-blue-300">View Profile</span>
            <ExternalLink className="w-3 h-3 text-blue-300" />
          </button>
        )}

        {view.type !== 'agent' && (
          <button
            onClick={() => {
              const tags: any = (entity as any).tags || (entity as any).properties || {}
              const rawId: any = (entity as any).id || tags.osm_id || tags.id || tags['@id']
              const normalizedId = typeof rawId === 'string' && rawId.includes('/') ? rawId.split('/').pop() : rawId
              if (!normalizedId) return
              const url = simulationId
                ? `/poi/${normalizedId}?simulation_id=${simulationId}`
                : `/poi/${normalizedId}`
              navigate(url)
              onOpenChange(false)
            }}
            className="group flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all duration-200 text-xs font-medium"
            style={{
              background: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.35)',
              backdropFilter: 'blur(8px)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(6, 182, 212, 0.25)'
              e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.5)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(6, 182, 212, 0.15)'
              e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.35)'
            }}
          >
            <span className="text-cyan-300">View POI</span>
            <ExternalLink className="w-3 h-3 text-cyan-300" />
          </button>
        )}
      </div>

      {/* Badges */}
      {badgesToDisplay.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {badgesToDisplay.map((badge, i) => {
            const colors = getCategoryColor(badge)
            return (
              <div
                key={i}
                className="px-3 py-1.5 rounded-lg border text-xs font-medium backdrop-blur-sm"
                style={{
                  background: colors.bg,
                  borderColor: colors.border,
                  color: colors.text,
                }}
              >
                {badge}
              </div>
            )
          })}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1">
        {availableTabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`
              px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider
              transition-all duration-200
              ${activeTab === tab 
                ? 'bg-white/10 text-white border border-white/20' 
                : 'bg-transparent text-gray-400 hover:text-gray-300 border border-transparent'
              }
            `}
          >
            {tab}
          </button>
        ))}
      </div>
    </div>
  )

  return (
    <BaseDrawer
      open={open}
      onClose={() => onOpenChange(false)}
      header={header}
    >
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      ) : (
        <motion.div
          variants={staggerContainerVariants}
          initial="hidden"
          animate="visible"
          className="px-6 py-6 space-y-6"
        >
          {/* Summary Tab */}
          {activeTab === 'summary' && (
          <>
            {/* Coordinates */}
            {coordinates && (
              <div>
                <div 
                  className="p-5 rounded-xl border backdrop-blur-sm"
                  style={GLASS_CARD_STYLE}
                >
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                    Coordinates
                  </p>
                  <p className="text-sm text-white font-mono mb-3">
                    {coordinates[0].toFixed(6)}, {coordinates[1].toFixed(6)}
                  </p>
                  
                  {/* Action chips */}
                  <div className="flex flex-wrap gap-2">
                    <ActionChip icon={Copy} label="Copy" onClick={copyCoordinates} />
                    <ActionChip icon={Crosshair} label="Center" onClick={centerOnLocation} />
                    {onRouteToLocation && (
                      <ActionChip icon={Navigation} label="Route" onClick={routeToHere} variant="primary" />
                    )}
                    <ActionChip icon={ExternalLink} label="OSM" onClick={openInOSM} />
                  </div>
                </div>
              </div>
            )}

            {/* Summary fields - render as collapsible sections */}
            {view.summary && view.summary.length > 0 && (
              <div>
                <div className="space-y-3">
                  {(() => {
                    // Separate personal summary from other fields
                    const personalSummary = view.summary.find(f => f.key === 'personal_summary')
                    const otherFields = view.summary.filter(f => f.key !== 'personal_summary')
                    
                    return (
                      <>
                        {/* Personal Summary - collapsible preview */}
                        {personalSummary && <PersonalSummaryCard summary={personalSummary.value} />}
                        
                        {/* Other fields - collapsible section */}
                        {otherFields.length > 0 && (
                          <SectionCard 
                            section={{
                              title: 'Summary Details',
                              tags: Object.fromEntries(
                                otherFields.map(f => [f.label, f.value])
                              )
                            }}
                            defaultOpen={true}
                          />
                        )}
                      </>
                    )
                  })()}
                </div>
              </div>
            )}
          </>
        )}

        {/* Details Tab - Show all data in categorized collapsible sections */}
        {activeTab === 'details' && (
          <div>
            {view.type === 'agent' ? (
              // For agents, show all sections as collapsible cards
              <div className="space-y-3">
                {view.sections.map((section, idx) => (
                  <SectionCard key={idx} section={section} />
                ))}
              </div>
            ) : (
              // For POIs/roads, organize into collapsible sections
              <div className="space-y-3">
                {(() => {
                  const tags = view.rawJsonTags || {}
                  const allEntries = Object.entries(tags).filter(([_, v]) => v !== undefined && v !== null && String(v).length > 0)
                  
                  if (allEntries.length === 0) {
                    return (
                      <div
                        className="p-6 text-center rounded-xl border backdrop-blur-sm"
                        style={GLASS_CARD_STYLE}
                      >
                        <p className="text-sm text-gray-400">No details available</p>
                      </div>
                    )
                  }

                  // Categorize fields into logical sections
                  const coreFields = ['osm_id', 'name', 'category', 'subcategory', 'type']
                  const addressFields = ['addr:street', 'addr:housenumber', 'addr:city', 'addr:state', 'addr:postcode', 'addr:country', 'addr:full']
                  const contactFields = ['phone', 'email', 'website', 'contact:phone', 'contact:email', 'contact:website']
                  const businessFields = ['opening_hours', 'payment:cash', 'payment:credit_cards', 'cuisine', 'amenity', 'shop', 'tourism']
                  const physicalFields = ['building', 'levels', 'height', 'material', 'roof:material', 'roof:shape']
                  
                  const sections: { title: string; tags: Record<string, any>; defaultOpen?: boolean }[] = []
                  
                  // Core Information
                  const coreData: Record<string, any> = {}
                  coreFields.forEach(key => {
                    if (tags[key] !== undefined) coreData[key] = tags[key]
                  })
                  if (Object.keys(coreData).length > 0) {
                    sections.push({ title: 'Core Information', tags: coreData, defaultOpen: true })
                  }
                  
                  // Address Information
                  const addressData: Record<string, any> = {}
                  addressFields.forEach(key => {
                    if (tags[key] !== undefined) addressData[key] = tags[key]
                  })
                  if (Object.keys(addressData).length > 0) {
                    sections.push({ title: 'Address', tags: addressData })
                  }
                  
                  // Contact Information
                  const contactData: Record<string, any> = {}
                  contactFields.forEach(key => {
                    if (tags[key] !== undefined) contactData[key] = tags[key]
                  })
                  if (Object.keys(contactData).length > 0) {
                    sections.push({ title: 'Contact', tags: contactData })
                  }
                  
                  // Business Details
                  const businessData: Record<string, any> = {}
                  businessFields.forEach(key => {
                    if (tags[key] !== undefined) businessData[key] = tags[key]
                  })
                  if (Object.keys(businessData).length > 0) {
                    sections.push({ title: 'Business Details', tags: businessData })
                  }
                  
                  // Physical Attributes
                  const physicalData: Record<string, any> = {}
                  physicalFields.forEach(key => {
                    if (tags[key] !== undefined) physicalData[key] = tags[key]
                  })
                  if (Object.keys(physicalData).length > 0) {
                    sections.push({ title: 'Physical Attributes', tags: physicalData })
                  }
                  
                  // All other fields
                  const categorizedKeys = new Set([
                    ...coreFields,
                    ...addressFields,
                    ...contactFields,
                    ...businessFields,
                    ...physicalFields
                  ])
                  const otherData: Record<string, any> = {}
                  allEntries.forEach(([key, value]) => {
                    if (!categorizedKeys.has(key)) {
                      otherData[key] = value
                    }
                  })
                  if (Object.keys(otherData).length > 0) {
                    sections.push({ title: 'Other Properties', tags: otherData })
                  }
                  
                  // Raw JSON section
                  if (Object.keys(tags).length > 0) {
                    sections.push({ 
                      title: 'Raw JSON', 
                      tags: { '_raw_json_': JSON.stringify(tags, null, 2) }
                    })
                  }
                  
                  return sections.map((section, idx) => (
                    <SectionCard 
                      key={idx} 
                      section={section}
                      defaultOpen={section.defaultOpen}
                      isRawJson={section.title === 'Raw JSON'}
                    />
                  ))
                })()}
              </div>
            )}
          </div>
        )}

        {/* Links Tab */}
        {activeTab === 'links' && (
          <div className="space-y-3">
            {view.links && view.links.length > 0 ? (
              view.links.map((link, idx) => (
                <motion.a
                  key={idx}
                  variants={staggerChildVariants}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-4 rounded-xl border backdrop-blur-sm hover:bg-white/10 transition-all group"
                  style={GLASS_CARD_STYLE}
                >
                  <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-blue-400 transition-colors" />
                  <span className="text-sm text-gray-300 group-hover:text-white break-all">
                    {link.label || link.href}
                  </span>
                </motion.a>
              ))
            ) : (
              <div
                className="p-6 text-center rounded-xl border backdrop-blur-sm"
                style={GLASS_CARD_STYLE}
              >
                <p className="text-sm text-gray-400">No external links available</p>
              </div>
            )}
          </div>
        )}
        </motion.div>
      )}
    </BaseDrawer>
  )
}

// Personal Summary card component with preview/expand
function PersonalSummaryCard({ summary }: { summary: string }) {
  const [expanded, setExpanded] = useState(false) // Default to collapsed
  const previewLines = 2
  const lines = summary.split('\n')
  const shouldTruncate = lines.length > previewLines
  const displayText = expanded || !shouldTruncate 
    ? summary 
    : lines.slice(0, previewLines).join('\n')

  return (
    <div 
      className="rounded-xl border overflow-hidden backdrop-blur-sm cursor-pointer"
      style={GLASS_CARD_STYLE}
      onClick={() => shouldTruncate && setExpanded(!expanded)}
    >
      {/* Header */}
      <div className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors">
        <h3 className="text-sm font-semibold text-white">Personal Summary</h3>
        {shouldTruncate && (
          <ChevronDown 
            className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} 
          />
        )}
      </div>
      
      {/* Content */}
      <motion.div
        variants={accordionVariants}
        initial="expanded"
        animate="expanded"
        className="overflow-hidden"
      >
        <div className="p-4 border-t border-white/5 relative">
          <div className="relative">
            <p
              className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap transition-opacity duration-300"
              style={
                !expanded && shouldTruncate
                  ? {
                      maskImage:
                        'linear-gradient(to bottom, white 60%, transparent 100%)',
                      WebkitMaskImage:
                        'linear-gradient(to bottom, white 60%, transparent 100%)'
                    }
                  : undefined
              }
            >
              {displayText}
            </p>
            {/* Fade out gradient when collapsed */}
            {!expanded && shouldTruncate && (
              <div
                className="absolute bottom-0 left-0 right-0 pointer-events-none"
                style={{
                  height: `${Math.max(40, Math.min(lines.slice(0, previewLines).join('\n').length * 0.4, 80))}px`, // dynamic: minimum 40px, max 80px, proportional to text chars
                  background:
                    'linear-gradient(to bottom, transparent 0%, rgba(255, 255, 255, 0.0) 100%)',
                  zIndex: 1
                }}
              />
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}


// Section card component for displaying grouped data
function SectionCard({ 
  section, 
  defaultOpen = false,
  isRawJson = false 
}: { 
  section: { title: string; tags: Record<string, any> }
  defaultOpen?: boolean
  isRawJson?: boolean
}) {
  const [expanded, setExpanded] = useState(defaultOpen)

  return (
    <div 
      className="rounded-xl border overflow-hidden backdrop-blur-sm"
      style={GLASS_CARD_STYLE}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
      >
        <h3 className="text-sm font-semibold text-white">{section.title}</h3>
        <div className="flex items-center gap-2">
          {!isRawJson && (
            <span className="text-xs text-gray-400">
              {Object.keys(section.tags).length} {Object.keys(section.tags).length === 1 ? 'field' : 'fields'}
            </span>
          )}
          <ChevronDown 
            className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} 
          />
        </div>
      </button>
      
      {/* Content */}
      <motion.div
        variants={accordionVariants}
        initial="collapsed"
        animate={expanded ? 'expanded' : 'collapsed'}
        className="overflow-hidden"
      >
        <div className="p-4 space-y-2 border-t border-white/5">
          {isRawJson ? (
            // Special rendering for raw JSON
            <pre className="text-xs font-mono text-gray-300 whitespace-pre-wrap break-words">
              {Object.values(section.tags)[0]}
            </pre>
          ) : (
            // Normal key-value rendering
            Object.entries(section.tags).map(([key, value]) => {
              const formatted = typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
              return (
                <div 
                  key={key}
                  className="flex items-start justify-between gap-3 py-2"
                >
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wide flex-shrink-0">
                    {key.replace(/_/g, ' ')}
                  </span>
                  <span className="text-sm text-gray-200 text-right break-all font-mono">
                    {formatted}
                  </span>
                </div>
              )
            })
          )}
        </div>
      </motion.div>
    </div>
  )
}
