/**
 * POIDetailDrawer - Palantir-style intel drawer for POI information
 * 
 * Displays raw OSM data intelligently without normalizing into a fixed schema.
 */

import React, { useState, useEffect } from 'react'
import { X, ExternalLink, Copy, MapPin, Clock, CreditCard, Phone, Mail, Globe, ChevronDown, ChevronUp, Code } from 'lucide-react'
import { computePoiView, formatOpeningHours, formatFieldValue, PoiView, PoiSummaryField, PoiLink } from '../../lib/poi/view'
import { colors } from '../../styles/colors'
import { TYPOGRAPHY } from '../../typography'
import { SPACING } from '../../spacing'
import { ANIMATIONS } from '../../animations'

export interface POIDetailDrawerProps {
  poi: {
    id: string | number
    geometry?: {
      type: string
      coordinates: [number, number]
    }
    properties?: Record<string, any>
    tags?: Record<string, string>
  } | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Tab = 'summary' | 'details' | 'links'


/**
 * Summary Field Component
 */
const SummaryField: React.FC<{ field: PoiSummaryField }> = ({ field }) => {
  const getIcon = () => {
    switch (field.type) {
      case 'phone': return <Phone className="w-4 h-4" />
      case 'email': return <Mail className="w-4 h-4" />
      case 'link': return <Globe className="w-4 h-4" />
      case 'address': return <MapPin className="w-4 h-4" />
      case 'hours': return <Clock className="w-4 h-4" />
      case 'payment': return <CreditCard className="w-4 h-4" />
      default: return null
    }
  }

  // Safety check: ensure field.value is a string
  const displayValue = typeof field.value === 'object' 
    ? JSON.stringify(field.value) 
    : String(field.value)

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
      {getIcon() && (
        <div className="text-gray-400 dark:text-gray-500 mt-0.5">
          {getIcon()}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
          {field.label}
        </div>
        <div className="text-sm text-gray-900 dark:text-white">
          {field.type === 'hours' ? formatOpeningHours(displayValue) : displayValue}
        </div>
      </div>
    </div>
  )
}


/**
 * Main Drawer Component
 */
export const POIDetailDrawer: React.FC<POIDetailDrawerProps> = ({ poi, open, onOpenChange }) => {
  const [activeTab, setActiveTab] = useState<Tab>('summary')
  const [poiView, setPoiView] = useState<PoiView | null>(null)
  const [showDetails, setShowDetails] = useState(true) // Details section default open
  const [showRawJson, setShowRawJson] = useState(false) // Raw JSON default closed
  const [copiedAddress, setCopiedAddress] = useState(false)

  // Compute POI view when poi changes
  useEffect(() => {
    if (poi) {
      const tags = poi.tags || poi.properties || {}
      const osmId = poi.id || tags.osm_id || tags['@id']
      const coordinates = poi.geometry?.coordinates


      const view = computePoiView(tags, osmId, coordinates)
      setPoiView(view)
      // Reset to summary tab when opening new POI
      setActiveTab('summary')
    } else {
      setPoiView(null)
    }
  }, [poi])

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onOpenChange(false)
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [open, onOpenChange])

  // Copy address to clipboard
  const copyAddress = () => {
    const addressField = poiView?.summary.find(f => f.type === 'address')
    if (addressField) {
      navigator.clipboard.writeText(addressField.value)
      setCopiedAddress(true)
      setTimeout(() => setCopiedAddress(false), 2000)
    }
  }

  // Copy GeoJSON
  const copyGeoJSON = () => {
    if (poi) {
      const geoJSON = JSON.stringify({
        type: 'Feature',
        properties: poi.tags || poi.properties || {},
        geometry: poi.geometry
      }, null, 2)
      navigator.clipboard.writeText(geoJSON)
    }
  }

  // Open in OSM
  const openInOSM = () => {
    if (poi && poi.geometry) {
      const [lon, lat] = poi.geometry.coordinates
      window.open(`https://www.openstreetmap.org/#map=19/${lat}/${lon}`, '_blank')
    }
  }

  if (!open || !poi || !poiView) return null

  const name = poi.properties?.name || poi.tags?.name || 'Unnamed Location'

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity duration-300"
        onClick={() => onOpenChange(false)}
      />

      {/* Drawer */}
      <div
        className={`fixed right-0 top-0 h-full w-full sm:w-[500px] lg:w-[600px] bg-white dark:bg-gray-900 shadow-2xl z-50 transform transition-transform duration-300 ease-out flex flex-col ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
          <div className="flex-1 min-w-0">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3 truncate">
              {name}
            </h2>
            <div className="flex items-center gap-2 flex-wrap">
              {/* Category - check properties first, then tags, then raw OSM tags */}
              {(() => {
                const category = poi.properties?.category || poi.tags?.category || 
                  poi.tags?.amenity || poi.tags?.shop || poi.tags?.tourism || poi.tags?.leisure || 
                  poi.tags?.building || poi.tags?.office || poi.tags?.craft || poi.tags?.religion || 
                  poi.tags?.historic || poi.tags?.natural || poi.tags?.place
                
                // Get color based on category (matching InfoSidebar colors)
                const getCategoryColor = (cat: string) => {
                  const colors: Record<string, string> = {
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
                    'highway': 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
                    'other': 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
                  }
                  return colors[cat] || colors['other']
                }
                
                return category && (
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getCategoryColor(category)}`}>
                    {category}
                  </span>
                )
              })()}
              
              {/* Subcategory - check properties first, then tags */}
              {(() => {
                const subcategory = poi.properties?.subcategory || poi.tags?.subcategory
                return subcategory && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                    {subcategory}
                  </span>
                )
              })()}
              
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                POI
              </span>
            </div>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="ml-4 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-700/50 rounded-lg transition-colors flex-shrink-0"
            title="Close (Esc)"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          {(['summary', 'details', 'links'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-white dark:bg-gray-900'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Summary Tab */}
          {activeTab === 'summary' && (
            <div className="space-y-4">
              {/* Action Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={openInOSM}
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open in OSM
                </button>
                <button
                  onClick={copyAddress}
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  disabled={!poiView.summary.find(f => f.type === 'address')}
                >
                  <Copy className="w-4 h-4" />
                  {copiedAddress ? 'Copied!' : 'Copy Address'}
                </button>
              </div>

              {/* Summary Fields */}
              <div className="space-y-3">
                {poiView.summary.map((field) => (
                  <SummaryField key={field.key} field={field} />
                ))}
              </div>
            </div>
          )}

          {/* Details Tab */}
          {activeTab === 'details' && (
            <div className="space-y-4">
              {/* Single Details Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                      All Details
                    </h3>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {Object.keys(poiView.rawTags).length} fields
                    </span>
                  </div>
                  {showDetails ? (
                    <ChevronUp className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  )}
                </button>
                {showDetails && (
                  <div className="p-4 bg-white dark:bg-gray-900 space-y-4">
                    {/* All Details in Gray Cards */}
                    <div className="space-y-3">
                      {Object.entries(poiView.rawTags).map(([key, value]) => {
                        // Safety check: ensure value is a string
                        const displayValue = typeof value === 'object'
                          ? JSON.stringify(value, null, 2)
                          : String(value)

                        return (
                          <div key={key} className="flex items-start justify-between gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                            <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide flex-shrink-0">
                              {key.replace(/^(addr:|contact:|payment:)/, '').replace(/_/g, ' ')}
                            </span>
                            <span className="text-sm text-gray-900 dark:text-white text-right break-all">
                              {formatFieldValue(key, displayValue)}
                            </span>
                          </div>
                        )
                      })}
                    </div>

                    {/* Raw JSON Section at bottom */}
                    <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                      <button
                        onClick={() => setShowRawJson(!showRawJson)}
                        className="w-full flex items-center justify-between p-3 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Code className="w-4 h-4 text-gray-400" />
                          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Raw OSM Tags (JSON)
                          </h4>
                        </div>
                        {showRawJson ? (
                          <ChevronUp className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                      {showRawJson && (
                        <div className="mt-3 p-3 bg-gray-900 dark:bg-black rounded-lg">
                          <pre className="text-xs text-green-400 font-mono overflow-x-auto">
                            {JSON.stringify(poiView.rawTags, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Links Tab */}
          {activeTab === 'links' && (
            <div className="space-y-4">
              {poiView.links.length > 0 ? (
                <>
                  {poiView.links.map((link, idx) => (
                    <a
                      key={idx}
                      href={link.href}
                      target={link.type === 'website' ? '_blank' : undefined}
                      rel={link.type === 'website' ? 'noopener noreferrer' : undefined}
                      className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
                    >
                      <div className="text-gray-400 group-hover:text-blue-500 transition-colors">
                        {link.type === 'website' && <Globe className="w-5 h-5" />}
                        {link.type === 'phone' && <Phone className="w-5 h-5" />}
                        {link.type === 'email' && <Mail className="w-5 h-5" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                          {link.label}
                        </div>
                        <div className="text-sm text-blue-600 dark:text-blue-400 group-hover:underline truncate">
                          {link.value}
                        </div>
                      </div>
                      <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-blue-500 transition-colors flex-shrink-0" />
                    </a>
                  ))}

                  {/* Copy GeoJSON Button */}
                  <button
                    onClick={copyGeoJSON}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors mt-4"
                  >
                    <Copy className="w-4 h-4" />
                    Copy as GeoJSON
                  </button>
                </>
              ) : (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <Globe className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">No contact links available for this location</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 px-6 py-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
            Press <kbd className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-gray-700 dark:text-gray-300 font-mono border border-gray-300 dark:border-gray-600">Esc</kbd> to close
          </div>
        </div>
      </div>
    </>
  )
}

