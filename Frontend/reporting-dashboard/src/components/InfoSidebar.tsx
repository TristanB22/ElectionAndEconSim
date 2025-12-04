import React, { useState } from 'react'
import { Users, TrendingUp, Clock, Zap } from 'lucide-react'
import { BaseCard, BaseModal } from './shared'
import { LAYOUT } from '../layout'
import { colors } from '../styles/colors'
import { ANIMATIONS } from '../animations'
import { TYPOGRAPHY } from '../typography'
import { SPACING } from '../spacing'

export interface SelectedItem {
  type: 'poi' | 'road'
  data: any
  coordinates: [number, number]
  timestamp: number
}

interface InfoSidebarProps {
  selectedItem: SelectedItem | null
  onClose: () => void
  onOpenDetailDrawer?: () => void
  onOpenRoadDetailDrawer?: () => void
}

// Reusable component for property rows
const PropertyRow = ({ label, value, icon, type = 'text' }: { 
  label: string
  value: string | number | undefined | null
  icon?: React.ReactNode
  type?: 'text' | 'link' | 'phone' | 'email' | 'coordinates'
}) => {
  if (!value || value === '') return null

  const renderValue = () => {
    switch (type) {
      case 'link':
        return (
          <a 
            href={value as string} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:underline transition-colors"
          >
            {value as string}
          </a>
        )
      case 'phone':
        return (
          <a 
            href={`tel:${value}`} 
            className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:underline transition-colors"
          >
            {value as string}
          </a>
        )
      case 'email':
        return (
          <a 
            href={`mailto:${value}`} 
            className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:underline transition-colors"
          >
            {value as string}
          </a>
        )
      case 'coordinates':
        return (
          <span className="font-mono text-sm text-gray-600 dark:text-gray-400">
            {value as string}
          </span>
        )
      default:
        return <span className="text-gray-900 dark:text-gray-100">{value as string}</span>
    }
  }

  return (
    <div className={`flex items-start ${SPACING.GAP.MD} ${SPACING.PADDING.SM} ${SPACING.BORDER.RADIUS.SM} ${colors.interactive.hover.background} ${ANIMATIONS.TRANSITIONS.HOVER}`}>
      {icon && (
        <div className="flex-shrink-0 w-5 h-5 text-gray-400 dark:text-gray-500 mt-0.5">
          {icon}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className={`${TYPOGRAPHY.SIZE.XS} ${TYPOGRAPHY.WEIGHT.MEDIUM} ${TYPOGRAPHY.COLORS.MUTED} uppercase tracking-wide mb-1`}>
          {label}
        </div>
        <div className="text-sm">
          {renderValue()}
        </div>
      </div>
    </div>
  )
}

// Section component for organized content
const InfoSection = ({ title, children, defaultExpanded = true }: {
  title: string
  children: React.ReactNode
  defaultExpanded?: boolean
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center justify-between text-left"
      >
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {title}
        </h3>
        <svg 
          className={`w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isExpanded && (
        <div className="p-2">
          {children}
        </div>
      )}
    </div>
  )
}

// Simulation Intelligence Badge - shows agent activity and economic data
const SimulationIntelligence = ({ type }: { type: 'poi' | 'road' }) => {
  // Mock data - in production, this would come from props/API
  const agentCount = Math.floor(Math.random() * 50) + 5
  const recentActivity = Math.floor(Math.random() * 20)
  const confidence = (Math.random() * 0.3 + 0.7).toFixed(2)
  
  return (
    <div className="grid grid-cols-2 gap-3 mb-4">
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2 mb-1">
          <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <span className="text-xs font-medium text-blue-600 dark:text-blue-400">Agent Knowledge</span>
        </div>
        <div className="text-lg font-bold text-blue-900 dark:text-blue-100">{agentCount}</div>
        <div className="text-xs text-blue-600 dark:text-blue-400">agents aware</div>
      </div>
      
      <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-3 border border-emerald-200 dark:border-emerald-800">
        <div className="flex items-center gap-2 mb-1">
          <TrendingUp className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Recent Activity</span>
        </div>
        <div className="text-lg font-bold text-emerald-900 dark:text-emerald-100">{recentActivity}</div>
        <div className="text-xs text-emerald-600 dark:text-emerald-400">events today</div>
      </div>
    </div>
  )
}

// Category badge component
const CategoryBadge = ({ category, subcategory, type }: {
  category: string
  subcategory?: string
  type: 'poi' | 'road'
}) => {
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

  return (
    <div className="flex flex-wrap gap-2">
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getCategoryColor(category)}`}>
        {category}
      </span>
      {subcategory && subcategory !== category && (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
          {subcategory}
        </span>
      )}
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
        type === 'poi' 
          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' 
          : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
      }`}>
        {type.toUpperCase()}
      </span>
    </div>
  )
}

export default function InfoSidebar({ selectedItem, onClose, onOpenDetailDrawer, onOpenRoadDetailDrawer }: InfoSidebarProps) {
  const [showFullModal, setShowFullModal] = useState(false)
  
  // Handle Esc key - only close modal if open, otherwise don't close sidebar
  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showFullModal) {
          e.preventDefault()
          e.stopPropagation()
          setShowFullModal(false)
        }
        // Don't close sidebar - user must click X button
      }
    }
    
    window.addEventListener('keydown', handleEsc, { capture: true })
    return () => window.removeEventListener('keydown', handleEsc, { capture: true })
  }, [showFullModal])
  
  if (!selectedItem) {
    return (
      <BaseCard className="w-full h-full flex flex-col" variant="default">
        <div className={`${SPACING.PADDING.LG} border-b ${colors.border.primary}`}>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Location Intelligence</h2>
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/30 dark:to-blue-800/30 rounded-2xl flex items-center justify-center">
              <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Select a Location</h3>
            <p className={`${TYPOGRAPHY.SIZE.SM} ${TYPOGRAPHY.COLORS.MUTED} max-w-xs`}>
              Click on a point of interest to view intelligence data
            </p>
          </div>
        </div>
      </BaseCard>
    )
  }

  const { type, data, coordinates } = selectedItem
  const isPOI = type === 'poi'

  // Extract common properties
  const name = data.properties?.name || data.name || 'Unnamed Location'
  const osmId = data.properties?.osm_id || data.osm_id
  const category = data.properties?.category || data.category || 'other'
  const subcategory = data.properties?.subcategory || data.subcategory || 'unknown'

  // Get POI-specific properties
  const poiProperties = isPOI ? [
    { key: 'Brand', value: data.properties?.brand, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm2 6a2 2 0 114 0 2 2 0 01-4 0zm8 0a2 2 0 114 0 2 2 0 01-4 0z" clipRule="evenodd" /></svg> },
    { key: 'Street', value: data.properties?.street, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" /></svg> },
    { key: 'City', value: data.properties?.city, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" /></svg> },
    { key: 'State', value: data.properties?.state, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" /></svg> },
    { key: 'Postcode', value: data.properties?.postcode, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" /></svg> },
    { key: 'Phone', value: data.properties?.phone, type: 'phone' as const, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" /></svg> },
    { key: 'Website', value: data.properties?.website, type: 'link' as const, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" /></svg> },
    { key: 'Email', value: data.properties?.email, type: 'email' as const, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" /><path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" /></svg> },
    { key: 'Opening Hours', value: data.properties?.opening_hours, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" /></svg> }
  ].filter(({ value }) => value !== undefined && value !== null && value !== '') : []

  // Get road-specific properties
  const roadProperties = !isPOI ? [
    { key: 'Highway Type', value: data.properties?.highway, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" /></svg> },
    { key: 'Reference', value: data.properties?.ref, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" /></svg> },
    { key: 'One Way', value: data.properties?.oneway === 'yes' ? 'Yes' : data.properties?.oneway === 'no' ? 'No' : data.properties?.oneway, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" /></svg> },
    { key: 'Max Speed', value: data.properties?.maxspeed, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clipRule="evenodd" /></svg> },
    { key: 'Surface', value: data.properties?.surface, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" /></svg> },
    { key: 'Lanes', value: data.properties?.lanes, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" /></svg> },
    { key: 'Bridge', value: data.properties?.bridge === 'yes' ? 'Yes' : data.properties?.bridge === 'no' ? 'No' : data.properties?.bridge, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" /></svg> },
    { key: 'Tunnel', value: data.properties?.tunnel === 'yes' ? 'Yes' : data.properties?.tunnel === 'no' ? 'No' : data.properties?.tunnel, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" /></svg> },
    { key: 'Access', value: data.properties?.access, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" /></svg> },
    { key: 'Layer', value: data.properties?.layer, icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" /></svg> }
  ].filter(({ value }) => value !== undefined && value !== null && value !== '') : []

  // Get additional properties
  const additionalProperties = data.properties?.properties ? (() => {
    const props = data.properties.properties
    let processedProps = props
    if (typeof props === 'string') {
      try {
        processedProps = JSON.parse(props)
      } catch (e) {
        processedProps = {}
      }
    }
    return Object.entries(processedProps).slice(0, 10)
  })() : []

  // Compact Flash Facts View
  return (
    <>
      {/* Compact Sidebar - Flash Facts */}
      <BaseCard className="w-full h-full flex flex-col" variant="default">
        {/* Compact Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1 truncate">
            {name}
          </h2>
              <CategoryBadge category={category} subcategory={subcategory} type={type} />
            </div>
          <button
            onClick={onClose}
              className="ml-2 p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-700/50 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
          </div>

        {/* Flash Facts Content */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-3">
            {/* Simulation Intelligence - Removed (was showing fake data) */}
            
            {/* Key Facts - Condensed */}
            <div className="space-y-2">
              {/* Address */}
              {(data.properties?.street || data.properties?.city) && (
                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <svg className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                    </svg>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {data.properties?.street || 'Unknown Street'}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
                        {data.properties?.city}, {data.properties?.state} {data.properties?.postcode}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Coordinates */}
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
                <div className="space-y-2">
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">COORDINATES</span>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="flex items-center gap-1 min-w-0">
                      <span className="text-xs text-gray-500 dark:text-gray-400 font-medium flex-shrink-0">Lat</span>
                      <span className="text-xs font-mono text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded truncate">
                        {coordinates[1].toFixed(4)}°
                      </span>
                    </div>
                    <div className="flex items-center gap-1 min-w-0">
                      <span className="text-xs text-gray-500 dark:text-gray-400 font-medium flex-shrink-0">Lon</span>
                      <span className="text-xs font-mono text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded truncate">
                        {coordinates[0].toFixed(4)}°
                      </span>
                    </div>
                  </div>
        </div>
      </div>

              {/* ID */}
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400">OSM ID</span>
                  <span className="text-sm font-mono text-gray-900 dark:text-white">#{osmId}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer - View Details Button */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          {isPOI && onOpenDetailDrawer ? (
            <button
              onClick={onOpenDetailDrawer}
              className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              View Details
            </button>
          ) : (!isPOI && onOpenRoadDetailDrawer) ? (
            <button
              onClick={onOpenRoadDetailDrawer}
              className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              View Details
            </button>
          ) : (
            <button
              onClick={() => setShowFullModal(true)}
              className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              View Full Details
            </button>
          )}
        </div>
      </BaseCard>

      {/* Full Details Modal */}
      {showFullModal && (
        <BaseModal
          isOpen={showFullModal}
          onClose={() => setShowFullModal(false)}
          maxWidth="MAX_WIDTH_DESKTOP"
        >
            {/* Modal Header */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                    {name}
                  </h2>
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-3">
                    <span className="inline-flex items-center px-3 py-1 rounded-lg text-sm font-mono bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 w-fit">
                      #{osmId}
                    </span>
                    <div className="grid grid-cols-2 gap-3 min-w-0">
                      <div className="flex items-center gap-1 min-w-0">
                        <span className="text-xs text-gray-500 dark:text-gray-400 font-medium flex-shrink-0">Lat</span>
                        <span className="text-xs font-mono text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded truncate">
                          {coordinates[1].toFixed(6)}°
                        </span>
                      </div>
                      <div className="flex items-center gap-1 min-w-0">
                        <span className="text-xs text-gray-500 dark:text-gray-400 font-medium flex-shrink-0">Lon</span>
                        <span className="text-xs font-mono text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded truncate">
                          {coordinates[0].toFixed(6)}°
                        </span>
                      </div>
                    </div>
                  </div>
                  <CategoryBadge category={category} subcategory={subcategory} type={type} />
                </div>
                <button
                  onClick={() => setShowFullModal(false)}
                  className="ml-4 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-700/50 rounded-lg transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

          {/* Modal Content - Fixed scrolling */}
          <div className={`overflow-y-auto ${SPACING.PADDING.MODAL} ${SPACING.GAP.CARD}`} style={{ maxHeight: LAYOUT.MODAL.SCROLL_HEIGHT }}>
            {/* Simulation Intelligence - Removed for now (was showing fake data) */}

            {/* Basic Information - Only show if has data */}
            {((isPOI && poiProperties.length > 0) || (!isPOI && roadProperties.length > 0)) && (
              <InfoSection title="Basic Information" defaultExpanded={true}>
                <div className={SPACING.GAP.SM}>
                  {isPOI ? poiProperties.map(({ key, value, icon, type }) => (
                    <PropertyRow key={key} label={key} value={value} icon={icon} type={type} />
                  )) : roadProperties.map(({ key, value, icon }) => (
                    <PropertyRow key={key} label={key} value={value} icon={icon} />
                  ))}
                </div>
              </InfoSection>
            )}

            {/* Contact Information (POI only) - Only show if has contact data */}
            {isPOI && poiProperties.some(p => ['Phone', 'Website', 'Email'].includes(p.key)) && (
              <InfoSection title="Contact Information" defaultExpanded={true}>
                <div className={SPACING.GAP.SM}>
                  {poiProperties.filter(p => ['Phone', 'Website', 'Email'].includes(p.key)).map(({ key, value, icon, type }) => (
                    <PropertyRow key={key} label={key} value={value} icon={icon} type={type} />
                  ))}
                </div>
              </InfoSection>
            )}

            {/* Additional Properties - Only show if has data */}
            {additionalProperties.length > 0 && (
              <InfoSection title="Additional Properties" defaultExpanded={true}>
                <div className={SPACING.GAP.SM}>
                  {additionalProperties.map(([key, value]) => (
                    <PropertyRow
                      key={key}
                      label={key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      value={typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    />
                  ))}
        </div>
              </InfoSection>
            )}
      </div>

          {/* Modal Footer */}
          <div className={`${SPACING.PADDING.MD} border-t ${colors.border.primary} ${colors.surface.secondary} flex items-center justify-between`}>
            <div className={`${TYPOGRAPHY.SIZE.XS} ${TYPOGRAPHY.COLORS.MUTED}`}>
              Press <kbd className={`${SPACING.PADDING.XS} ${colors.surface.primary} ${TYPOGRAPHY.COLORS.SECONDARY} ${SPACING.BORDER.RADIUS.SM} ${TYPOGRAPHY.STYLES.MONO} ${colors.border.secondary}`}>Esc</kbd> to close
      </div>
            <button
              onClick={() => setShowFullModal(false)}
              className={`${SPACING.PADDING.MD} ${colors.surface.tertiary} ${colors.interactive.hover.background} ${TYPOGRAPHY.COLORS.PRIMARY} ${SPACING.BORDER.RADIUS.BUTTON} ${ANIMATIONS.TRANSITIONS.HOVER}`}
            >
              Close
            </button>
    </div>
        </BaseModal>
      )}
    </>
  )
}
