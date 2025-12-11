import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { log } from '../config/log'
import { Map as MapLibreMap, Popup } from 'maplibre-gl'
import { usePopupManager } from '../hooks/usePopupManager'
import { createBaseModal, BaseModalProps } from './BaseMapModal'
import { SelectedItem } from './InfoSidebar'
import { LAYOUT } from '../layout'
import { colors, poiCategoryColors } from '../styles/colors'
import { ANIMATIONS } from '../animations'
import { TYPOGRAPHY } from '../typography'
import { SPACING } from '../spacing'
import { RESPONSIVE } from '../responsive'
import { createGlassMorphismStyle } from '../glassMorphism'
import { API_ENDPOINTS, buildApiUrl } from '../config/api'
import { MAP_ANIMATIONS } from '../config/mapAnimations'
import { POIPreviewCard } from './POIPreviewCard'
import { MAP_CONTROL_STYLES, createMapControlStyle } from '../styles/mapControls'
import { Filter, MapPin, Users } from 'lucide-react'
// Generate a stable per-window session ID
const WINDOW_SESSION_ID = (() => {
  try {
    const key = 'reportingWindowSessionId'
    let id = sessionStorage.getItem(key)
    if (!id) {
      id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
      sessionStorage.setItem(key, id)
    }
    return id
  } catch {
    // Fallback if sessionStorage unavailable
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
  }
})()
let GEO_CONFIG: { tiles: boolean; vector: boolean; pois: boolean } | null = null
async function loadGeoConfig() {
  if (GEO_CONFIG) return GEO_CONFIG
  try {
    const res = await fetch(API_ENDPOINTS.MAP_CONFIG)
    GEO_CONFIG = await res.json()
  } catch {
    GEO_CONFIG = { tiles: true, vector: true, pois: true }
  }
  return GEO_CONFIG
}

interface LightweightPoi {
  type: 'Feature'
  properties: {
    osm_id: number
    category: string
    subcategory: string
  }
  geometry: {
    type: 'Point'
    coordinates: [number, number]
  }
}

interface PoiDetails {
  type: 'Feature'
  properties: {
    id: number
    osm_id: number
    name: string
    category: string
    subcategory: string
    brand: string
    street: string
    city: string
    state: string
    postcode: string
    country: string
    phone: string
    website: string
    email: string
    opening_hours: string
    properties: any
    created_at: string
    updated_at: string
    last_verified: string
    source: string
    region: string
    confidence_score: number
    is_verified: boolean
    is_active: boolean
    display_name?: string
  }
  geometry: {
    type: 'Point'
    coordinates: [number, number]
  }
}

interface FrontendHeatmapLayerProps {
  map: MapLibreMap | null
  region?: string
  onItemSelect?: (item: SelectedItem) => void
  pointsEnabled: boolean
  heatmapEnabled: boolean
  disableInteraction?: boolean
  roadsLoading?: boolean
  visibleAgentsCount?: number
}

// Cache for POI data to avoid repeated API calls
const poiDataCache = new Map<string, { data: LightweightPoi[], timestamp: number }>()
const poiDetailsCache = new Map<number, { data: PoiDetails, timestamp: number }>()
const loadingPois = new Set<number>() // Track POIs currently being fetched
const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes
const DETAILS_CACHE_DURATION = 10 * 60 * 1000 // 10 minutes

// Category preferences storage
const CATEGORY_PREFS_KEY = 'poiCategoryPreferences'

function loadCategoryPreferences(): Set<string> {
  try {
    const saved = sessionStorage.getItem(CATEGORY_PREFS_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      return new Set(parsed)
    }
  } catch (e) {
    // Failed to load category preferences
  }
  
  // Default: all categories enabled EXCEPT 'other' and 'building' (buildings off by default)
  return new Set([
    'amenity', 'shop', 'tourism', 'leisure', 'healthcare', 'office', 'craft', 'religion', 'historic', 'place'
  ])
}

function saveCategoryPreferences(categories: Set<string>) {
  try {
    sessionStorage.setItem(CATEGORY_PREFS_KEY, JSON.stringify(Array.from(categories)))
  } catch (e) {
    // Failed to save category preferences
  }
}

// Global popup reference for escape key handling
let globalPopup: Popup | null = null

// Global escape key handler
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && globalPopup) {
    globalPopup.remove()
    globalPopup = null
  }
})

export default function FrontendHeatmapLayer({ map, region = 'maine', onItemSelect, pointsEnabled, heatmapEnabled, disableInteraction = false, roadsLoading = false, visibleAgentsCount = 0 }: FrontendHeatmapLayerProps) {
  const [allPois, setAllPois] = useState<LightweightPoi[]>([])
  const [heatmapData, setHeatmapData] = useState<any[]>([]) // Separate state for heatmap data from MySQL
  const [loading, setLoading] = useState(false) // For main POI fetching
  const [loadingOther, setLoadingOther] = useState(false) // For "other" POI fetching
  const [error, setError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(0)
  const [showHeatmap, setShowHeatmap] = useState(false) // Will be set based on zoom level
  const [bounds, setBounds] = useState<[number, number, number, number] | null>(null)
  const [poiDetails, setPoiDetails] = useState<Map<number, PoiDetails>>(new Map<number, PoiDetails>())
  
  // Create hash map for O(1) POI lookup by osm_id
  const poiLookupMap = useMemo(() => {
    const lookup = new Map<number, LightweightPoi>()
    for (const poi of allPois) {
      lookup.set(poi.properties.osm_id, poi)
    }
    return lookup
  }, [allPois])
  const { showPopup, closeCurrentPopup } = usePopupManager()
  const [enabledCategories, setEnabledCategories] = useState<Set<string>>(loadCategoryPreferences())
  const [availableCategories, setAvailableCategories] = useState<Map<string, { count: number, color: string, label: string, subcategories: Map<string, number> }>>(new Map())
  const [showCategoryModal, setShowCategoryModal] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [enabledSubcategories, setEnabledSubcategories] = useState<Set<string>>(new Set())
  const [showCategorySelector, setShowCategorySelector] = useState(true)
  const [categoryPanelExpanded, setCategoryPanelExpanded] = useState(false)
  const modalRef = useRef<HTMLDivElement>(null)
  
  const heatmapLayerId = 'frontend-heatmap'
  const pointLayerId = 'frontend-points'
  const sourceId = 'frontend-poi-source'
  const markerLayerId = 'frontend-poi-markers'
  const markerLayerIdHover = 'frontend-poi-markers-hover'
  const rAF = useRef(0)
  const popup = useRef<Popup | null>(null)
  const lastClickTime = useRef(0)
  const HEATMAP_MEMORY_CACHE = useRef<{ features: any[] } | null>(null)
  const heatmapAbortController = useRef<AbortController | null>(null)
  const heatmapTimeoutRef = useRef<number | null>(null)
  const heatmapFetchInProgress = useRef<boolean>(false)
  const heatmapFetchAttempts = useRef<number>(0)
  
  // POI Preview Card State
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewData, setPreviewData] = useState<{ name: string; category?: string; subcategory?: string } | null>(null)
  const [previewPosition, setPreviewPosition] = useState({ x: 0, y: 0 })
  const previewTimeoutRef = useRef<number | null>(null)

  // Ensure heatmap source/layer exist and are correctly ordered for visibility toggles
  const ensureHeatmapLayer = useCallback((mapObj: MapLibreMap) => {
    try {
      // Ensure GeoJSON source exists
      if (!mapObj.getSource(sourceId)) {
        mapObj.addSource(sourceId, {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [] }
        } as any)
      }

      // Ensure heatmap layer exists (place below roads if present, else below labels)
      if (!mapObj.getLayer(heatmapLayerId)) {
        const beforeId = mapObj.getLayer('ws-roads-line') ? 'ws-roads-line' : (mapObj.getLayer('labels') ? 'labels' : undefined)
        mapObj.addLayer({
          id: heatmapLayerId,
          type: 'heatmap',
          source: sourceId,
          paint: {
            'heatmap-weight': [
              'interpolate',
              ['linear'],
              ['get', 'weight'],
              0, 0,
              1, 1
            ],
            'heatmap-intensity': [
              'interpolate',
              ['linear'],
              ['zoom'],
              0, 2.5,
              2, 3,
              4, 3.5,
              6, 4,
              8, 4.5,
              10, 5,
              12, 5.5,
              15, 6
            ],
            'heatmap-color': [
              'interpolate',
              ['linear'],
              ['heatmap-density'],
              0, 'rgba(0, 0, 255, 0)',
              0.2, 'rgba(0, 0, 255, 0.3)',
              0.4, 'rgba(0, 255, 0, 0.4)',
              0.6, 'rgba(255, 255, 0, 0.5)',
              0.8, 'rgba(255, 165, 0, 0.6)',
              1, 'rgba(255, 0, 0, 0.7)'
            ],
            'heatmap-radius': [
              'interpolate',
              ['linear'],
              ['zoom'],
              0, 1,
              2, 4,
              4, 8,
              6, 10,
              8, 14,
              10, 18,
              12, 10,
              15, 10
            ],
            'heatmap-opacity': [
              'interpolate',
              ['linear'],
              ['zoom'],
              0, 0.3,
              2, 0.35,
              4, 0.4,
              6, 0.35,
              8, 0.3,
              10, 0.25,
              12, 0.2,
              15, 0.15
            ]
          }
        } as any, beforeId as any)
      } else {
        // Maintain desired order on re-activation
        try {
          if (mapObj.getLayer('ws-roads-line')) {
            mapObj.moveLayer(heatmapLayerId, 'ws-roads-line')
          } else if (mapObj.getLayer('labels')) {
            mapObj.moveLayer(heatmapLayerId, 'labels')
          }
        } catch {}
      }
    } catch {}
  }, [])

  // New: client cache for merged POIs and request dedupe
  const [poiCache] = useState<Map<number, LightweightPoi>>(new Map())
  const [lastRequestKey, setLastRequestKey] = useState<string>('')
  
  // Debouncing for POI requests
  const poiRequestTimeout = useRef<number | null>(null)
  const currentAbortController = useRef<AbortController | null>(null)
  const lastQueuedKeyRef = useRef<string>('')
  const heatmapDataFetched = useRef<boolean>(false)
  const mapLoadHandled = useRef<boolean>(false)
  const markerImagesLoadedRef = useRef<boolean>(false)
  
  // Heatmap now uses the same PostGIS data as individual POIs

  // Map specific OSM categories to static categories (memoized for performance)
  // Updated to match backend category names exactly
  const mapToStaticCategory = useCallback((osmCategory: string): string => {
    // Backend now returns OSM category names directly (amenity, shop, tourism, etc.)
    // No longer using generic names like "services", "commerce", etc.
    if (['amenity', 'shop', 'tourism', 'leisure', 'healthcare', 'office', 'craft', 'religion', 'historic', 'building', 'place', 'other'].includes(osmCategory)) {
      return osmCategory
    }
    
    // Fallback: if we get an old-style category name, map it to new names
    if (osmCategory === 'services') return 'amenity'
    if (osmCategory === 'commerce') return 'shop'
    if (osmCategory === 'recreation') return 'leisure'
    if (osmCategory === 'business') return 'office'
    if (osmCategory === 'places') return 'place'
    
    return 'other'
  }, [])

  // Analyze POIs and create category mappings
  const analyzeCategories = useCallback((pois: LightweightPoi[]) => {
    const staticCategoryMap = new Map<string, { count: number, subcategories: Map<string, number> }>()
    
    // Count POIs by static category and track subcategories
    pois.forEach(poi => {
      const osmCategory = poi.properties.category || 'other'
      const staticCategory = mapToStaticCategory(osmCategory)
      
      if (!staticCategoryMap.has(staticCategory)) {
        staticCategoryMap.set(staticCategory, { count: 0, subcategories: new Map() })
      }
      
      const categoryData = staticCategoryMap.get(staticCategory)!
      categoryData.count++
      categoryData.subcategories.set(osmCategory, (categoryData.subcategories.get(osmCategory) || 0) + 1)
    })
    
    // Define static category styling - using centralized config
    const getCategoryStyle = (category: string) => {
      return poiCategoryColors[category] || poiCategoryColors.other
    }
    
    // Ensure 'other' always appears in the selector, even if count is zero
    if (!staticCategoryMap.has('other')) {
      staticCategoryMap.set('other', { count: 0, subcategories: new Map() })
    }

    // Create category map with counts and styles (include zero-count categories for UI presence)
    const categories = new Map<string, { count: number, color: string, label: string, subcategories: Map<string, number> }>()
    staticCategoryMap.forEach(({ count, subcategories }, category) => {
      const style = getCategoryStyle(category)
      categories.set(category, { count, ...style, subcategories })
    })
    
    setAvailableCategories(categories)
  }, [])

  // Toggle category visibility
  const toggleCategory = (category: string) => {
    setEnabledCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(category)) {
        newSet.delete(category)
      } else {
        newSet.add(category)
      }
      // Save preferences to sessionStorage
      saveCategoryPreferences(newSet)
      return newSet
    })
  }

  // Close modal function
  const closeModal = () => {
    setShowCategoryModal(false)
    setSelectedCategory(null)
  }

  // Handle escape key and click outside
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showCategoryModal) {
        closeModal()
      }
    }

    const handleClickOutside = (e: MouseEvent) => {
      if (showCategoryModal && modalRef.current && !modalRef.current.contains(e.target as Node)) {
        closeModal()
      }
    }

    if (showCategoryModal) {
      document.addEventListener('keydown', handleEscape)
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showCategoryModal])


  // Create spatial index for efficient POI queries
  const spatialIndex = useMemo(() => {
    if (allPois.length === 0) return new Map<string, LightweightPoi[]>()
    
    const index = new Map<string, LightweightPoi[]>()
    
    // Index POIs by static category for fast filtering
    for (const poi of allPois) {
      const staticCategory = mapToStaticCategory(poi.properties.category || 'other')
      if (!index.has(staticCategory)) {
        index.set(staticCategory, [])
      }
      index.get(staticCategory)!.push(poi)
    }
    
    return index
  }, [allPois])

  // Create bounds-based spatial index for even faster queries
  const boundsIndex = useMemo(() => {
    if (!bounds || allPois.length === 0) return new Map<string, LightweightPoi[]>()
    
    const [minLon, minLat, maxLon, maxLat] = bounds
    const index = new Map<string, LightweightPoi[]>()
    
    // Pre-filter POIs by bounds and index by category
    for (const poi of allPois) {
      const [lon, lat] = poi.geometry.coordinates
      
      // Only index POIs that are within bounds
      if (lon >= minLon && lon <= maxLon && lat >= minLat && lat <= maxLat) {
        const staticCategory = mapToStaticCategory(poi.properties.category || 'other')
        if (!index.has(staticCategory)) {
          index.set(staticCategory, [])
        }
        index.get(staticCategory)!.push(poi)
      }
    }
    
    return index
  }, [allPois, bounds])

  // Base candidate POIs for counting and rendering (bounded by zoom/limit, but
  // independent of which categories are currently enabled). Ensures category
  // counts and visible points are computed from the same underlying set, and
  // that toggling a category does not change the counts.
  const candidatePois = useMemo(() => {
    if (!bounds || allPois.length === 0) return []

    const MAX_VISIBLE_POINTS = 150000
    const baseLimit = 100000
    const zoomScale = zoom >= 15 ? 2 : zoom >= 12 ? 1.5 : 1
    const zoomBasedLimit = Math.min(MAX_VISIBLE_POINTS, Math.floor(baseLimit * zoomScale))

    const result: LightweightPoi[] = []
    let count = 0

    // Iterate through all categories in the bounds index, regardless of whether
    // they are currently enabled in the UI.
    for (const [staticCategory, pois] of boundsIndex.entries()) {
      for (const poi of pois) {
        if (count >= zoomBasedLimit) break

        const osmCategory = poi.properties.category || 'other'
        const enhancedPoi = {
          ...poi,
          properties: {
            ...poi.properties,
            static_category: staticCategory,
            category: osmCategory,
          },
        }
        result.push(enhancedPoi as any)
        count++
      }
      if (count >= zoomBasedLimit) break
    }

    return result
  }, [boundsIndex, bounds, allPois.length, zoom])

  // Whenever the base candidate POIs for this view change (i.e. new data
  // loaded or bounds/zoom changed enough to change the truncated set),
  // recompute the category metadata used by the LOCATION FILTER.
  useEffect(() => {
    analyzeCategories(candidatePois)
  }, [candidatePois, analyzeCategories])

  // Visible POIs are a filtered view of the candidate set based on enabled
  // categories and any subcategory filters.
  const visiblePois = useMemo(() => {
    if (candidatePois.length === 0) return []

    return candidatePois.filter(p => {
      const staticCategory = (p as any).properties.static_category
      const osmCategory = (p as any).properties.category || 'other'

      if (!enabledCategories.has(staticCategory)) {
        return false
      }
      if (enabledSubcategories.size > 0 && !enabledSubcategories.has(osmCategory)) {
        return false
      }
      return true
    })
  }, [candidatePois, enabledCategories, enabledSubcategories])

  // Generate heatmap data - use dedicated heatmap data from MySQL
  const heatmapDataForMap = useMemo(() => {
    // Heatmap should ONLY show at zoom < 10 when enabled
    if (!showHeatmap || !heatmapEnabled || zoom >= 10) {
      return null
    }
    
    // Use dedicated heatmap data from MySQL table
    if (heatmapData.length === 0) {
      return null
    }
    
    // Convert heatmap data to map format
    const heatmapFeatures = heatmapData.map(point => ({
      type: 'Feature' as const,
      properties: {
        weight: 1
      },
      geometry: point.geometry
    }))
    
    return {
      type: 'FeatureCollection' as const,
      features: heatmapFeatures
    }
  }, [showHeatmap, heatmapEnabled, zoom, heatmapData])

  // Generate individual POI data for visible POIs
  const pointData = useMemo(() => {
    // Only show POIs when:
    // 1. Layers are enabled
    // 2. Zoom level is >= 10 (POI level)
    // 3. Heatmap is not being shown (should be false at z >= 10)
    // 4. We have visible POIs to show
    if (!pointsEnabled || zoom < 10 || showHeatmap || visiblePois.length === 0) {
      // POI data: null
      return null
    }
    
    // POI data generated
    return {
      type: 'FeatureCollection' as const,
      features: visiblePois
    }
  }, [visiblePois, showHeatmap, pointsEnabled, zoom])

  // Update map layers when data or category filters change
  useEffect(() => {
    if (!map || !map.isStyleLoaded()) return

    // (Global map click handler moved to its own effect below)

    // Anti-flicker: reuse source and update data instead of removing/adding
    const dataToUse = showHeatmap ? heatmapDataForMap : pointData
    const existingSource = map.getSource(sourceId) as any
    if (!existingSource) {
      map.addSource(sourceId, {
        type: 'geojson',
        data: dataToUse || { type: 'FeatureCollection', features: [] }
      })
    } else {
      existingSource.setData(dataToUse || { type: 'FeatureCollection', features: [] })
    }

    const shouldShowHeatmapLayer = Boolean(showHeatmap && heatmapEnabled)
    const shouldShowPointLayer = Boolean(!showHeatmap && pointsEnabled && pointData)
    
    // Explicitly control heatmap layer visibility
    if (showHeatmap && heatmapEnabled) {
      // Ensure layer exists and is properly ordered
      ensureHeatmapLayer(map)
      // Always set to visible when heatmap mode is active (even if data not loaded yet)
      if (map.getLayer(heatmapLayerId)) {
        map.setLayoutProperty(heatmapLayerId, 'visibility', 'visible')
      }
      // Hide point layers
      if (map.getLayer(`${pointLayerId}-shadow`)) map.setLayoutProperty(`${pointLayerId}-shadow`, 'visibility', 'none')
      if (map.getLayer(`${pointLayerId}-glow`)) map.setLayoutProperty(`${pointLayerId}-glow`, 'visibility', 'none')
      if (map.getLayer(pointLayerId)) map.setLayoutProperty(pointLayerId, 'visibility', 'none')
      if (map.getLayer(markerLayerId)) map.setLayoutProperty(markerLayerId, 'visibility', 'none')
    } else if (shouldShowHeatmapLayer) {
      // This block is now redundant but kept for clarity
      if (map.getLayer(heatmapLayerId)) map.setLayoutProperty(heatmapLayerId, 'visibility', 'visible')
      if (map.getLayer(`${pointLayerId}-shadow`)) map.setLayoutProperty(`${pointLayerId}-shadow`, 'visibility', 'none')
      if (map.getLayer(`${pointLayerId}-glow`)) map.setLayoutProperty(`${pointLayerId}-glow`, 'visibility', 'none')
      if (map.getLayer(pointLayerId)) map.setLayoutProperty(pointLayerId, 'visibility', 'none')
      if (map.getLayer(markerLayerId)) map.setLayoutProperty(markerLayerId, 'visibility', 'none')
    } else if (shouldShowPointLayer) {
      // Ensure marker images are present and marker layer exists
      ensureMarkerImages(map)
      if (!map.getLayer(markerLayerId)) {
      map.addLayer({
          id: markerLayerId,
          type: 'symbol',
        source: sourceId,
          layout: {
            'icon-image': [
              'match', ['get', 'static_category'],
              'amenity', 'poi-marker-amenity',
              'shop', 'poi-marker-shop',
              'tourism', 'poi-marker-tourism',
              'leisure', 'poi-marker-leisure',
              'healthcare', 'poi-marker-healthcare',
              'office', 'poi-marker-office',
              'craft', 'poi-marker-craft',
              'religion', 'poi-marker-religion',
              'historic', 'poi-marker-historic',
              'building', 'poi-marker-building',
              'place', 'poi-marker-place',
              'other', 'poi-marker-other',
              'poi-marker-default'
            ],
            'icon-allow-overlap': true,
            'icon-ignore-placement': true,
            'icon-anchor': 'center',
            'icon-size': [
              'interpolate', ['linear'], ['zoom'],
              10, 0.47,
              12, 0.53,
              14, 0.6,
              16, 0.67
          ]
        }
      })
      }
      
      // Add hover layer for POI glow effect (similar to agents)
      if (!map.getLayer(markerLayerIdHover)) {
        map.addLayer({
          id: markerLayerIdHover,
          type: 'symbol',
          source: sourceId,
          layout: {
            'icon-image': [
              'match', ['get', 'static_category'],
              'amenity', 'poi-marker-amenity-hover',
              'shop', 'poi-marker-shop-hover',
              'tourism', 'poi-marker-tourism-hover',
              'leisure', 'poi-marker-leisure-hover',
              'healthcare', 'poi-marker-healthcare-hover',
              'office', 'poi-marker-office-hover',
              'craft', 'poi-marker-craft-hover',
              'religion', 'poi-marker-religion-hover',
              'historic', 'poi-marker-historic-hover',
              'building', 'poi-marker-building-hover',
              'place', 'poi-marker-place-hover',
              'other', 'poi-marker-other-hover',
              'poi-marker-default-hover'
            ],
            'icon-allow-overlap': true,
            'icon-ignore-placement': true,
            'icon-anchor': 'center',
            'icon-size': [
              'interpolate', ['linear'], ['zoom'],
              10, 0.56, // 1.2x scale
              12, 0.64,
              14, 0.72,
              16, 0.8
            ]
          },
          paint: {
            'icon-opacity': 0 // Hidden by default
          },
          filter: ['==', 'osm_id', ''] // Empty filter by default
        })
      }

      // Always move markers to top, above roads
      try { 
        map.moveLayer(markerLayerIdHover)
        map.moveLayer(markerLayerId, markerLayerIdHover)
      } catch {}

      // Apply category-based filters at the layer level as an extra safety net.
      const enabledCategoryList = Array.from(enabledCategories)
      const baseFilter =
        enabledCategoryList.length > 0
          ? (['in', 'static_category', ...enabledCategoryList] as any)
          : (['in', 'static_category', '__none__'] as any) // hide all if nothing enabled

      if (map.getLayer(markerLayerId)) {
        map.setFilter(markerLayerId, baseFilter)
      }
      if (map.getLayer(markerLayerIdHover)) {
        map.setFilter(markerLayerIdHover, baseFilter)
      }

      // Toggle visibility
      if (map.getLayer(heatmapLayerId)) map.setLayoutProperty(heatmapLayerId, 'visibility', 'none')
      if (map.getLayer(`${pointLayerId}-shadow`)) map.setLayoutProperty(`${pointLayerId}-shadow`, 'visibility', 'none')
      if (map.getLayer(`${pointLayerId}-glow`)) map.setLayoutProperty(`${pointLayerId}-glow`, 'visibility', 'none')
      if (map.getLayer(pointLayerId)) map.setLayoutProperty(pointLayerId, 'visibility', 'none')
      if (map.getLayer(markerLayerId)) map.setLayoutProperty(markerLayerId, 'visibility', 'visible')
      
      // REMOVED: All click handlers moved to Map.tsx global handler
      // This section is kept for reference but handlePointClick is no longer used
      if (false && shouldShowPointLayer) {
        const handlePointClick = async (e: any) => {
          // Block ALL interaction if in route planning mode
          if (disableInteraction) {
            log.debug('[POI CLICK BLOCKED] disableInteraction is true - ignoring click')
            e.preventDefault()
            e.stopPropagation()
            return false
          }
          
          // POI Click Handler with detailed logging for performance tracking
          // Logs: POI ID, process steps, data sources, and timestamps
          const feature = e.features?.[0]
          if (!feature) {
            return
          }

          // Debounce rapid clicks (prevent multiple requests within 100ms)
          const now = Date.now()
          if (now - lastClickTime.current < 100) {
            return
          }
          lastClickTime.current = now

          const osmId = feature.properties.osm_id
          const poiName = feature.properties.name || 'Unnamed POI'
          const category = feature.properties.category || 'other'
          
          // Check if we have POI data loaded - if not, try to load it immediately
          if (allPois.length === 0 && bounds) {
            debouncedFetchPOIs(bounds, zoom, true) // immediate = true
            return
          }
          
          // Check if we already have the details in state
          if (poiDetails.has(osmId)) {
            if (onItemSelect) {
              const selectedItem: SelectedItem = {
                type: 'poi',
                data: poiDetails.get(osmId)!,
                coordinates: [e.lngLat.lng, e.lngLat.lat],
                timestamp: now
              }
              onItemSelect(selectedItem)
            }
            return
          }

          // Check if the feature already has detailed data (from include_details=true)
          if (feature.properties.street || feature.properties.phone || feature.properties.website || feature.properties.email) {
            log.debug(`[POI CLICK] POI #${osmId} has detailed data in feature - Processing from spatial query - Timestamp: ${new Date(now).toISOString()}`)
            
            // Convert the feature to PoiDetails format
            const details: PoiDetails = {
              type: 'Feature',
              properties: {
                id: osmId,
                osm_id: osmId,
                name: feature.properties.name || '',
                category: feature.properties.category || 'other',
                subcategory: feature.properties.subcategory || 'unknown',
                brand: feature.properties.brand || '',
                street: feature.properties.street || '',
                city: feature.properties.city || '',
                state: feature.properties.state || '',
                postcode: feature.properties.postcode || '',
                country: feature.properties.country || '',
                phone: feature.properties.phone || '',
                website: feature.properties.website || '',
                email: feature.properties.email || '',
                opening_hours: feature.properties.opening_hours || '',
                properties: (() => {
                  const props = feature.properties.properties || {}
                  // If it's a string, try to parse it as JSON
                  if (typeof props === 'string') {
                    try {
                      return JSON.parse(props)
                    } catch (e) {
                      return {}
                    }
                  }
                  return props
                })(),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                last_verified: new Date().toISOString(),
                source: 'osm',
                region: 'maine',
                confidence_score: 0.8,
                display_name: feature.properties.name || `${feature.properties.category} ${feature.properties.subcategory}`.trim(),
                is_verified: true,
                is_active: true
              },
              geometry: feature.geometry
            }
            
            log.debug(`[POI CLICK] Successfully processed POI #${osmId} from spatial data - Caching and displaying - Timestamp: ${new Date(now).toISOString()}`)
            
            // Cache the details
            poiDetailsCache.set(osmId, { data: details, timestamp: now })
            setPoiDetails(prev => new Map(prev).set(osmId, details))
            
            if (onItemSelect) {
              const selectedItem: SelectedItem = {
                type: 'poi',
                data: details,
                coordinates: [e.lngLat.lng, e.lngLat.lat],
                timestamp: now
              }
              onItemSelect(selectedItem)
            }
            return
          }

          // Check cache first
          const cached = poiDetailsCache.get(osmId)
          
          if (cached && (now - cached.timestamp) < DETAILS_CACHE_DURATION) {
            setPoiDetails(prev => new Map(prev).set(osmId, cached.data))
            
            if (onItemSelect) {
              const selectedItem: SelectedItem = {
                type: 'poi',
                data: cached.data,
                coordinates: [e.lngLat.lng, e.lngLat.lat],
                timestamp: now
              }
              onItemSelect(selectedItem)
            }
            return
          }

          // Prevent duplicate requests for the same POI
          if (loadingPois.has(osmId)) {
            return
          }

          // Mark as loading
          loadingPois.add(osmId)

          // Fallback: Fetch POI details using STR-tree endpoint (for backward compatibility)
          try {
            const response = await fetch(API_ENDPOINTS.POIS_DETAIL(osmId), {
              headers: { 'X-Client-Session': WINDOW_SESSION_ID }
            })
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}`)
            }
            
            const details: PoiDetails = await response.json()
            
            // Preserve category/subcategory from map feature if MySQL DB has "other"
            // The spatial query has correct categorization from PostGIS, but MySQL may have stale data
            if (details.properties.category === 'other' && feature.properties.category && feature.properties.category !== 'other') {
              log.debug(`[POI CLICK] Overriding MySQL category "${details.properties.category}" with map category "${feature.properties.category}"`)
              details.properties.category = feature.properties.category
              details.properties.subcategory = feature.properties.subcategory || details.properties.subcategory
            }
            
            // Cache the details
            poiDetailsCache.set(osmId, { data: details, timestamp: now })
            
            setPoiDetails(prev => new Map(prev).set(osmId, details))
            
            if (onItemSelect) {
              const selectedItem: SelectedItem = {
                type: 'poi',
                data: details,
                coordinates: [e.lngLat.lng, e.lngLat.lat],
                timestamp: now
              }
              onItemSelect(selectedItem)
            }
          } catch (err) {
            // Failed to fetch POI details
          } finally {
            // Remove from loading set
            loadingPois.delete(osmId)
          }
        }


        // NO LAYER-SCOPED EVENT HANDLERS - all click handling moved to Map.tsx global handler
        // This prevents MapLibre listener registry corruption (e2.filter is not a function error)
        log.debug(`[POI LAYER] Layer configured - interaction handled globally`)
        
        // Close popup when map starts moving
        const handleMoveStart = () => {
          if (popup.current) {
            popup.current.remove()
            popup.current = null
          }
          if (globalPopup) {
            globalPopup.remove()
            globalPopup = null
          }
        }
        map?.on('movestart', handleMoveStart)

        // (Global map click handler is attached in a separate one-time effect)
      }
    }
    else {
      // Neither heatmap nor point mode is active
      // Explicitly hide heatmap layer
      if (map.getLayer(heatmapLayerId)) map.setLayoutProperty(heatmapLayerId, 'visibility', 'none')
      // Explicitly hide point layers
      if (map.getLayer(`${pointLayerId}-shadow`)) map.setLayoutProperty(`${pointLayerId}-shadow`, 'visibility', 'none')
      if (map.getLayer(`${pointLayerId}-glow`)) map.setLayoutProperty(`${pointLayerId}-glow`, 'visibility', 'none')
      if (map.getLayer(pointLayerId)) map.setLayoutProperty(pointLayerId, 'visibility', 'none')
      if (map.getLayer(markerLayerId)) map.setLayoutProperty(markerLayerId, 'visibility', 'none')
    }

    // Cleanup function — no layer-scoped handlers to remove
    return () => {}
  }, [map, heatmapDataForMap, pointData, showHeatmap, onItemSelect, pointsEnabled, heatmapEnabled, disableInteraction, ensureHeatmapLayer, enabledCategories])

  // Re-assert heatmap once when toggled to ON with a loaded style (no long-lived listener)
  useEffect(() => {
    if (!map) return
    try {
      if (heatmapEnabled && showHeatmap && map.isStyleLoaded()) {
        ensureHeatmapLayer(map)
        if (map.getLayer(heatmapLayerId)) {
          map.setLayoutProperty(heatmapLayerId, 'visibility', 'visible')
        }
        const src: any = map.getSource(sourceId)
        if (src && heatmapDataForMap) {
          src.setData(heatmapDataForMap)
        }
      }
    } catch {}
  }, [map, heatmapEnabled, showHeatmap, heatmapDataForMap, ensureHeatmapLayer])

  // Periodic re-assertion: every 5s ensure POIs are visible and on top (handles late-render issues)
  useEffect(() => {
    if (!map) return
    const intervalId = window.setInterval(() => {
      try {
        // Only act when POIs should be visible
        if (pointsEnabled && zoom >= 10 && !showHeatmap) {
          // Re-ensure images and layer exist
          ensureMarkerImages(map)
          if (!map.getLayer(markerLayerId)) {
            // Trigger main effect by nudging source; else, add layer directly
            const src: any = map.getSource(sourceId)
            if (src && pointData) src.setData(pointData)
          }
          // Move layer to top and make visible
          try { 
            map.moveLayer(markerLayerIdHover)
            map.moveLayer(markerLayerId, markerLayerIdHover)
          } catch {}
          if (map.getLayer(markerLayerId)) {
            map.setLayoutProperty(markerLayerId, 'visibility', 'visible')
          }
          if (map.getLayer(markerLayerIdHover)) {
            map.setLayoutProperty(markerLayerIdHover, 'visibility', 'visible')
          }
        } else {
          // Hide POIs when they should not be shown (zoom < 10 or heatmap is active)
          if (map.getLayer(markerLayerId)) {
            map.setLayoutProperty(markerLayerId, 'visibility', 'none')
          }
          if (map.getLayer(markerLayerIdHover)) {
            map.setLayoutProperty(markerLayerIdHover, 'visibility', 'none')
          }
        }
      } catch {}
    }, 5000)
    return () => { try { clearInterval(intervalId) } catch {} }
  }, [map, pointsEnabled, zoom, showHeatmap, pointData])
  
  // POI Hover interactions - show preview card and highlight marker
  useEffect(() => {
    if (!map || !pointsEnabled || zoom < 10 || showHeatmap || disableInteraction) return
    
    const handleMouseMove = (e: any) => {
      if (!e.features || e.features.length === 0) {
        // Clear hover state
        if (previewTimeoutRef.current) {
          clearTimeout(previewTimeoutRef.current)
          previewTimeoutRef.current = null
        }
        setPreviewVisible(false)
        try {
          map.setFilter(markerLayerIdHover, ['==', 'osm_id', ''])
          map.setPaintProperty(markerLayerIdHover, 'icon-opacity', 0)
        } catch {}
        return
      }
      
      const feature = e.features[0]
      const osmId = feature.properties.osm_id
      const name = feature.properties.name || 'Unnamed Location'
      const category = feature.properties.category || feature.properties.static_category
      const subcategory = feature.properties.subcategory
      
      // Get POI geographic coordinates and convert to screen coordinates
      const coordinates = feature.geometry.coordinates
      const screenPoint = map.project([coordinates[0], coordinates[1]])
      
      // Update hover layer to highlight this POI
      try {
        map.setFilter(markerLayerIdHover, ['==', 'osm_id', osmId])
        map.setPaintProperty(markerLayerIdHover, 'icon-opacity', 1)
      } catch {}
      
      // Show preview card after debounce
      if (previewTimeoutRef.current) {
        clearTimeout(previewTimeoutRef.current)
      }
      previewTimeoutRef.current = window.setTimeout(() => {
        setPreviewData({ name, category, subcategory })
        setPreviewPosition({
          x: screenPoint.x + MAP_ANIMATIONS.HOVER.previewOffsetX,
          y: screenPoint.y + MAP_ANIMATIONS.HOVER.previewOffsetY
        })
        setPreviewVisible(true)
      }, MAP_ANIMATIONS.HOVER.debounceMs)
    }
    
    const handleMouseLeave = () => {
      if (previewTimeoutRef.current) {
        clearTimeout(previewTimeoutRef.current)
        previewTimeoutRef.current = null
      }
      setPreviewVisible(false)
      try {
        map.setFilter(markerLayerIdHover, ['==', 'osm_id', ''])
        map.setPaintProperty(markerLayerIdHover, 'icon-opacity', 0)
      } catch {}
    }
    
    // Attach listeners
    map.on('mousemove', markerLayerId, handleMouseMove)
    map.on('mouseleave', markerLayerId, handleMouseLeave)
    
    return () => {
      map.off('mousemove', markerLayerId, handleMouseMove)
      map.off('mouseleave', markerLayerId, handleMouseLeave)
      if (previewTimeoutRef.current) {
        clearTimeout(previewTimeoutRef.current)
      }
    }
  }, [map, pointsEnabled, zoom, showHeatmap, disableInteraction, markerLayerId, markerLayerIdHover])

  // One-time global map click: close popup when clicking on bare map (not features)
  useEffect(() => {
    if (!map) return

    const handleGlobalMapClick = (e: any) => {
      if (popup.current && !e.features?.length) {
        popup.current.remove()
        popup.current = null
      }
    }

    map.on('click', handleGlobalMapClick as any)
    return () => {
      try { map.off('click', handleGlobalMapClick as any) } catch {}
    }
  }, [map])

  // Handle map movement: only fire on moveend
  useEffect(() => {
    if (!map) return
    
    const onMoveEnd = () => {
      cancelAnimationFrame(rAF.current)
      rAF.current = requestAnimationFrame(() => {
        try {
          const z = Math.floor(map.getZoom())
          const b = map.getBounds()
          const newBounds: [number, number, number, number] = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]
          setZoom(z)
          setBounds(newBounds)
          
          // Close any open POI popup when map moves/zooms
          closeCurrentPopup()
        } catch (error) {
          // Error getting map zoom/bounds
        }
      })
    }
    
    // Wait for map to be fully loaded before setting initial state
    const onMapLoad = () => {
      if (mapLoadHandled.current) {
        return
      }
      mapLoadHandled.current = true
      
      // Ensure map has valid dimensions before calculating bounds
      const container = map.getContainer()
      if (container && container.offsetWidth > 0 && container.offsetHeight > 0) {
        onMoveEnd()
      }
    }
    
    if (map.isStyleLoaded()) {
      onMapLoad()
    } else {
      map.on('styledata', onMapLoad)
    }
    
    map.on('moveend', onMoveEnd)
    map.on('resize', onMoveEnd) // Handle screen size changes
    
    return () => { 
      map.off('moveend', onMoveEnd)
      map.off('resize', onMoveEnd)
      map.off('styledata', onMapLoad)
      cancelAnimationFrame(rAF.current)
      mapLoadHandled.current = false // Reset flag on cleanup
    }
  }, [map, closeCurrentPopup])

  // Initialize zoom from map immediately if available
  useEffect(() => {
    if (!map) return
    try {
      const initialZoom = Math.floor(map.getZoom())
      if (initialZoom > 0 && zoom === 0) {
        setZoom(initialZoom)
      }
    } catch (e) {
      // Map not ready yet
    }
  }, [map, zoom])

  // Update display mode based on zoom and unified toggle (no data fetching)
  useEffect(() => {
    // Show heatmap for z < 10 when enabled; points for z >= 10
    const shouldShowHeatmap = heatmapEnabled && zoom < 10 && zoom > 0 // zoom > 0 ensures we have a real zoom value
    setShowHeatmap(shouldShowHeatmap)
  }, [zoom, heatmapEnabled])

  // Track last fetched POI bounds to enable smart subset detection
  const lastFetchedPOIBoundsRef = useRef<{ bounds: [number, number, number, number], zoom: number } | null>(null)
  const lastFetchedPOIDataRef = useRef<any[]>([])
  
  // Check if newBounds is completely contained within fetchedBounds
  const isSubsetOfBounds = (newBounds: [number, number, number, number], fetchedBounds: [number, number, number, number]): boolean => {
    const [newMinLon, newMinLat, newMaxLon, newMaxLat] = newBounds
    const [fetchedMinLon, fetchedMinLat, fetchedMaxLon, fetchedMaxLat] = fetchedBounds
    
    // Check if new bounds are completely inside fetched bounds (with small tolerance)
    const tolerance = 0.0001
    return newMinLon >= (fetchedMinLon - tolerance) &&
           newMinLat >= (fetchedMinLat - tolerance) &&
           newMaxLon <= (fetchedMaxLon + tolerance) &&
           newMaxLat <= (fetchedMaxLat + tolerance)
  }
  
  // Filter POI data to specific bounds
  const filterPOIDataToBounds = useCallback((poiData: any[], bounds: [number, number, number, number]) => {
    const [minLon, minLat, maxLon, maxLat] = bounds
    return poiData.filter((poi: any) => {
      if (!poi.geometry || !poi.geometry.coordinates) return false
      const [lon, lat] = poi.geometry.coordinates
      return lon >= minLon && lon <= maxLon && lat >= minLat && lat <= maxLat
    })
  }, [])

  // Debounced POI fetching function
  const debouncedFetchPOIs = useCallback((currentBounds: [number, number, number, number], currentZoom: number, immediate = false) => {
    // Cancel any existing request
    if (currentAbortController.current) {
      currentAbortController.current.abort()
    }
    
    // Clear any existing timeout
    if (poiRequestTimeout.current) {
      clearTimeout(poiRequestTimeout.current)
    }
    
    // Check if new bounds are subset of last fetched bounds (viewport shrunk/subset)
    const lastFetched = lastFetchedPOIBoundsRef.current
    if (lastFetched && lastFetched.zoom === currentZoom && isSubsetOfBounds(currentBounds, lastFetched.bounds)) {
      // New view is subset of cached data - just filter, no fetch needed
      const filteredPOIs = filterPOIDataToBounds(lastFetchedPOIDataRef.current, currentBounds)
      setAllPois(filteredPOIs)
      return
    }
    
    // If immediate is true, skip debouncing for urgent requests
    const debounceTime = immediate ? 0 : 300
    // Dedupe by bounds+zoom key
    const key = `${currentZoom}:${currentBounds.map(v => v.toFixed(4)).join(',')}`
    if (!immediate && lastQueuedKeyRef.current === key) {
      return
    }
    lastQueuedKeyRef.current = key
    
    // Set timeout for debouncing (or immediate execution)
    poiRequestTimeout.current = setTimeout(async () => {
      if (!pointsEnabled) {
        return
      }
      // Create new abort controller for this request
      const abortController = new AbortController()
      currentAbortController.current = abortController
      
      async function fetchPois() {
        if (!currentBounds) return
        const cfg = await loadGeoConfig()
        if (!cfg || !cfg.pois) {
          setAllPois([])
          return
        }
        const [minLon, minLat, maxLon, maxLat] = currentBounds
        
        // For heatmap at low zoom, expand bounds to get better distribution
        const boundsExpansion = currentZoom < 8 ? 0.5 : currentZoom < 10 ? 0.2 : 0.1 // Expand bounds more at lower zoom
        const expandedMinLat = minLat - boundsExpansion
        const expandedMinLon = minLon - boundsExpansion
        const expandedMaxLat = maxLat + boundsExpansion
        const expandedMaxLon = maxLon + boundsExpansion
        
        // Increased point limits to allow up to 50k points
        const desiredMaxPoints = currentZoom < 8 ? 500000 : currentZoom < 11 ? 1000000 : 5000000
        
        // Build base query params
        const baseParams = {
          min_lat: expandedMinLat.toString(),
          min_lon: expandedMinLon.toString(),
          max_lat: expandedMaxLat.toString(),
          max_lon: expandedMaxLon.toString(),
          max_points: desiredMaxPoints.toString(),
          include_details: 'true'
        }
        
        try {
          setLoading(true)
          setLoadingOther(true)
          setError(null)
          
          // Build query strings
          const mainQs = new URLSearchParams({
            ...baseParams,
            exclude_other: 'true'
          })
          const otherQs = new URLSearchParams({
            ...baseParams,
            include_only_other: 'true'
          })

          // Always fetch both main and "other" in parallel so category counts
          // reflect the full dataset for this view, regardless of which
          // categories are currently enabled.
            const [mainResp, otherResp] = await Promise.all([
              fetch(`${API_ENDPOINTS.POIS_SPATIAL}?${mainQs}`, {
                signal: abortController.signal,
                headers: { 'X-Client-Session': WINDOW_SESSION_ID }
              }),
              fetch(`${API_ENDPOINTS.POIS_SPATIAL}?${otherQs}`, {
                signal: abortController.signal,
                headers: { 'X-Client-Session': WINDOW_SESSION_ID }
              })
            ])

            if (!mainResp.ok) throw new Error(`HTTP ${mainResp.status}`)
            const mainData = await mainResp.json()
            const mainFeatures = mainData?.features || []

            let otherFeatures: any[] = []
            if (otherResp.ok) {
              const otherData = await otherResp.json()
              otherFeatures = otherData?.features || []
            }

            if (abortController.signal.aborted) return
          const allFeatures: any[] = [...mainFeatures, ...otherFeatures]
          
          // Only update state if request wasn't aborted
          if (!abortController.signal.aborted) {
            // Track the bounds and data we just fetched
            lastFetchedPOIBoundsRef.current = { bounds: currentBounds, zoom: currentZoom }
            lastFetchedPOIDataRef.current = allFeatures
            setAllPois(allFeatures)
          }
        } catch (e: any) {
          // Don't show error if request was aborted
          if (!abortController.signal.aborted) {
            setError(e?.message || 'Failed to load POIs')
          }
        } finally {
          // Only update loading state if request wasn't aborted
          if (!abortController.signal.aborted) {
            setLoading(false)
            setLoadingOther(false)
          }
        }
      }
      fetchPois()
    }, debounceTime) // Configurable debounce time
  }, [analyzeCategories, pointsEnabled, filterPOIDataToBounds])

  // Debounced heatmap data fetching function (for low zoom levels) - resilient, not cancelled by map moves
  const debouncedFetchHeatmapData = useCallback((immediate = false) => {
    // If we already have cached data, no need to fetch again
    if (HEATMAP_MEMORY_CACHE.current && HEATMAP_MEMORY_CACHE.current.features?.length) {
      if (heatmapData.length === 0) {
        setHeatmapData(HEATMAP_MEMORY_CACHE.current.features)
      }
      return
    }

    // If a fetch is already in progress, do not start another
    if (heatmapFetchInProgress.current) {
      return
    }

    // Clear only the heatmap timeout (do not touch POI timeout)
    if (heatmapTimeoutRef.current) {
      clearTimeout(heatmapTimeoutRef.current)
    }

    const debounceTime = immediate ? 0 : 300

    const fetchWithRetry = async () => {
      heatmapFetchInProgress.current = true
      heatmapFetchAttempts.current = 0
        setLoading(true)
        setError(null)
        
      const url = API_ENDPOINTS.POIS_HEATMAP

      while (heatmapFetchAttempts.current < 3) {
        try {
          // Do NOT pass AbortController here so moves do not cancel it
          const response = await fetch(url)
          if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
          const heatmapPoints = data.features || []
          HEATMAP_MEMORY_CACHE.current = { features: heatmapPoints }
          setHeatmapData(heatmapPoints)
          setLoading(false)
          heatmapFetchInProgress.current = false
          return
      } catch (e: any) {
          heatmapFetchAttempts.current += 1
          if (heatmapFetchAttempts.current >= 3) {
            setError(`Failed to load heatmap data: ${e?.message || 'unknown error'}`)
          setLoading(false)
            heatmapFetchInProgress.current = false
            return
          }
          // Exponential backoff with jitter
          const backoffMs = 300 * Math.pow(2, heatmapFetchAttempts.current - 1) + Math.round(Math.random() * 150)
          await new Promise(res => setTimeout(res, backoffMs))
        }
      }
    }

    heatmapTimeoutRef.current = setTimeout(() => {
      fetchWithRetry()
    }, debounceTime)
  }, [heatmapData.length])

  // When re-enabling heatmap at low zoom, fetch if cache is empty
  useEffect(() => {
    if (heatmapEnabled && zoom < 10) {
      const hasCached = Boolean(HEATMAP_MEMORY_CACHE.current && HEATMAP_MEMORY_CACHE.current.features && HEATMAP_MEMORY_CACHE.current.features.length)
      if (!hasCached && (!heatmapData || heatmapData.length === 0)) {
        debouncedFetchHeatmapData(true)
      } else if (hasCached && heatmapData.length === 0) {
        setHeatmapData(HEATMAP_MEMORY_CACHE.current!.features)
      }
    }
  }, [heatmapEnabled, zoom, debouncedFetchHeatmapData])

  // Load heatmap from memory cache on initial mount, fetch if absent
  useEffect(() => {
    if (!map || !map.isStyleLoaded()) return
    
    if (HEATMAP_MEMORY_CACHE.current && HEATMAP_MEMORY_CACHE.current.features?.length) {
      setHeatmapData(HEATMAP_MEMORY_CACHE.current.features)
    } else if (heatmapEnabled) {
      // Only fetch if heatmap is enabled
      debouncedFetchHeatmapData(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, heatmapEnabled])

  // Fetch POIs when bounds/zoom change using appropriate data source
  // Use heatmap table for low zoom (z < 10), spatial queries for high zoom (z >= 10)
  useEffect(() => {
    if (!bounds) return
    
    // For high zoom, fetch POIs only when points are enabled
    if (zoom >= 10 && pointsEnabled) {
        debouncedFetchPOIs(bounds, zoom)
      }

    // When fully zoomed out, clear volatile POI data
      if (zoom < 3) {
        setAllPois([])
        setAvailableCategories(new Map())
    }
    
    // Cleanup debounce on unmount/update
    return () => {
      if (poiRequestTimeout.current) {
        clearTimeout(poiRequestTimeout.current)
      }
      }
  }, [bounds, zoom, pointsEnabled, debouncedFetchPOIs])

  useEffect(() => {
    if (!map) return
    const handleForceRefresh = () => {
      if (!pointsEnabled) return
      const activeBounds =
        bounds ??
        (() => {
          try {
            const b = map.getBounds()
            return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] as [number, number, number, number]
          } catch {
            return null
          }
        })()

      if (!activeBounds) return
      const currentZoom = Math.floor(map.getZoom())
      debouncedFetchPOIs(activeBounds, currentZoom, true)
    }

    map.on('force-refresh-pois' as any, handleForceRefresh)
    return () => {
      map.off('force-refresh-pois' as any, handleForceRefresh)
    }
  }, [map, bounds, debouncedFetchPOIs, pointsEnabled])

  // Handle escape key to close popup
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (popup.current) {
          popup.current.remove()
          popup.current = null
        }
        if (globalPopup) {
          globalPopup.remove()
          globalPopup = null
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (popup.current) {
        popup.current.remove()
        popup.current = null
      }
      if (globalPopup) {
        globalPopup.remove()
        globalPopup = null
      }
    }
  }, [])

  // // Helper: draw a simple location pin on a canvas for the given color
  // function createMarkerCanvas(hexColor: string, size = 28): HTMLCanvasElement {
  //   const canvas = document.createElement('canvas')
  //   canvas.width = size
  //   canvas.height = size
  //   const ctx = canvas.getContext('2d')!
  //   ctx.clearRect(0, 0, size, size)
  //   // Convert hex to rgba
  //   const color = hexColor
  //   // Draw pin (circle + pointer)
  //   const cx = size / 2
  //   const cy = size / 2 - 3
  //   const r = size * 0.28
  //   // Pointer triangle
  //   ctx.beginPath()
  //   ctx.moveTo(cx, cy + r)
  //   ctx.lineTo(cx - r * 0.7, cy + r * 2.1)
  //   ctx.lineTo(cx + r * 0.7, cy + r * 2.1)
  //   ctx.closePath()
  //   ctx.fillStyle = color
  //   ctx.fill()
  //   // Outer circle
  //   ctx.beginPath()
  //   ctx.arc(cx, cy, r, 0, Math.PI * 2)
  //   ctx.fillStyle = color
  //   ctx.fill()
  //   // Inner dot
  //   ctx.beginPath()
  //   ctx.arc(cx, cy, r * 0.45, 0, Math.PI * 2)
  //   ctx.fillStyle = '#ffffff'
  //   ctx.globalAlpha = 0.85
  //   ctx.fill()
  //   ctx.globalAlpha = 1
  //   // Halo
  //   ctx.beginPath()
  //   ctx.arc(cx, cy, r + 1.5, 0, Math.PI * 2)
  //   ctx.strokeStyle = 'rgba(0,0,0,0.35)'
  //   ctx.lineWidth = 1
  //   ctx.stroke()
  //   return canvas
  // }

  // // helper: draw a modern SVG-path-based poi pin for the given color (hollow center, slightly taller)
  // function createMarkerCanvas(hexColor: string, size = 28): HTMLCanvasElement {
  //   const canvas = document.createElement('canvas')
  //   canvas.width = size
  //   // Make canvas a bit taller (about 10% more than before)
  //   canvas.height = Math.round(size * (17 / 14)) // previously 16/14 ratio, now 18/14
  //   const ctx = canvas.getContext('2d')!
  //   ctx.clearRect(0, 0, size, canvas.height)

  //   // Updated SVG viewBox: 0 0 14 18 (was 0 0 14 16)
  //   const scaleX = size / 14
  //   const scaleY = canvas.height / 18

  //   // Center horizontally and align so the tip sits at bottom center
  //   ctx.save()
  //   ctx.translate(0, 0)
  //   ctx.scale(scaleX, scaleY)

  //   // Adjusted path to be slightly taller by stretching vertically,
  //   // e.g., lengthen the base segment and drop the tip further down.
  //   // We'll shift the bottom point from y=15 to y=17.
  //   // Hollow center circle also moves down a bit.

  //   // Draw marker body path (stretched)
  //   const path = new Path2D('M7 1.5a5 5 0 0 1 5 5c0 2.1-1.2 3.8-3.7 8.3L7 17l-1.3-2.2C3.2 10.8 2 9.1 2 6.5a5 5 0 0 1 5-5z')
  //   ctx.fillStyle = hexColor
  //   ctx.fill(path)

  //   // Hollow center: punch a transparent hole at the "center" with globalCompositeOperation
  //   ctx.globalCompositeOperation = 'destination-out'
  //   ctx.beginPath()
  //   // Move the center dot slightly lower to maintain visual balance (from 6.2 to 7.3)
  //   ctx.arc(7, 7.3, 2.15, 0, Math.PI * 2)
  //   ctx.fill()
  //   ctx.globalCompositeOperation = 'source-over'

  //   // Stroke for contrast
  //   ctx.strokeStyle = '#111827'
  //   ctx.lineWidth = 1.1
  //   ctx.stroke(path)

  //   ctx.restore()

  //   return canvas
  // }



  // helper: draw a simple small circle of the given color with a thin black outline, half the previous size
  function createMarkerCanvas(hexColor: string, size = 7, withGlow = false): HTMLCanvasElement {
    // Half the previous size (was 14)
    const canvas = document.createElement('canvas')
    // Use high-DPI rendering for crisp markers (2x pixel ratio)
    const pixelRatio = 2
    const actualSize = withGlow ? size * 1.5 : size

    // Set canvas dimensions for high-DPI
    canvas.width = actualSize * pixelRatio
    canvas.height = actualSize * pixelRatio

    const ctx = canvas.getContext('2d', { alpha: true })!

    // Scale context for high-DPI rendering
    ctx.scale(pixelRatio, pixelRatio)

    // Enable anti-aliasing and smooth edges
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'

    ctx.clearRect(0, 0, actualSize, actualSize)

    const center = actualSize / 2
    const radius = (withGlow ? size * 0.5 - 1 : size / 2 - 1)

    // Draw glow effect for hover
    if (withGlow) {
      ctx.save()
      const glowRadius = radius * 1.8
      const gradient = ctx.createRadialGradient(center, center, radius * 0.8, center, center, glowRadius)
      gradient.addColorStop(0, hexColor + 'DD')
      gradient.addColorStop(0.5, hexColor + '88')
      gradient.addColorStop(1, hexColor + '00')
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(center, center, glowRadius, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }

    // Draw main marker circle with anti-aliased edges
    ctx.save()
    ctx.beginPath()
    ctx.arc(center, center, radius, 0, Math.PI * 2)
    ctx.fillStyle = hexColor
    ctx.fill()

    // Reduce stroke width proportionally
    ctx.lineWidth = withGlow ? 1.25 : 1
    ctx.strokeStyle = withGlow ? '#ffffff' : 'rgba(17, 24, 39, 0.8)'
    ctx.stroke()
    ctx.restore()

    return canvas
  }

  // Forward declare to satisfy TypeScript hoisting
  function ensureMarkerImages(map: MapLibreMap) {
    if (!map || !(map as any).style) return
    if (markerImagesLoadedRef.current) return
    
    // Use centralized color configuration
    const entries = Object.entries(poiCategoryColors)
    for (const [cat, { color }] of entries) {
      // Normal marker - half the previous size (was 28, now 14)
      const id = `poi-marker-${cat}`
      if (!map.hasImage(id)) {
        const canvas = createMarkerCanvas(color, 14, false)
        const ctx = canvas.getContext('2d')!
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height)
        try {
          map.addImage(id, { 
            data: imgData.data as unknown as Uint8ClampedArray, 
            width: canvas.width, 
            height: canvas.height,
            pixelRatio: 2 // Tell MapLibre this is a high-DPI image
          } as any)
        } catch {}
      }
      
      // Hover marker with glow - half the previous size (was 28, now 14)
      const hoverId = `poi-marker-${cat}-hover`
      if (!map.hasImage(hoverId)) {
        const hoverCanvas = createMarkerCanvas(color, 14, true)
        const hoverCtx = hoverCanvas.getContext('2d')!
        const hoverImgData = hoverCtx.getImageData(0, 0, hoverCanvas.width, hoverCanvas.height)
        try {
          map.addImage(hoverId, { 
            data: hoverImgData.data as unknown as Uint8ClampedArray, 
            width: hoverCanvas.width, 
            height: hoverCanvas.height,
            pixelRatio: 2 // Tell MapLibre this is a high-DPI image
          } as any)
        } catch {}
      }
    }
    
    // default markers (use 'other' category color as default) - half the previous size (was 28, now 14)
    if (!map.hasImage('poi-marker-default')) {
      const canvas = createMarkerCanvas(poiCategoryColors.other.color, 14, false)
      const ctx = canvas.getContext('2d')!
      const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      try {
        map.addImage('poi-marker-default', { 
          data: imgData.data as unknown as Uint8ClampedArray, 
          width: canvas.width, 
          height: canvas.height,
          pixelRatio: 2
        } as any)
      } catch {}
    }
    if (!map.hasImage('poi-marker-default-hover')) {
      const hoverCanvas = createMarkerCanvas(poiCategoryColors.other.color, 14, true)
      const hoverCtx = hoverCanvas.getContext('2d')!
      const hoverImgData = hoverCtx.getImageData(0, 0, hoverCanvas.width, hoverCanvas.height)
      try {
        map.addImage('poi-marker-default-hover', { 
          data: hoverImgData.data as unknown as Uint8ClampedArray, 
          width: hoverCanvas.width, 
          height: hoverCanvas.height,
          pixelRatio: 2
        } as any)
      } catch {}
    }
    markerImagesLoadedRef.current = true
  }

  // Guard clause - don't render if map is not valid
  if (!map) {
    return null
  }

  // Show error indicator
  if (error) {
    return (
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
        POI Error: {error}
      </div>
    )
  }

  // Always show category selector and other controls
  return (
    <>
      {/* Loading overlay - show when loading POIs */}
      {(loading || loadingOther) && !roadsLoading && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 bg-black/50 text-white px-4 py-2 rounded-lg shadow-lg text-sm flex items-center gap-2">
          <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>
            {loading && loadingOther ? 'Loading all locations…' : 
             loading ? 'Loading main locations…' : 
             'Loading additional locations…'}
          </span>
        </div>
      )}

      {/* Bottom-left category selector - Matches Timeline styling */}
      {/* Always present on large screens, hidden on small screens where zoom is shown in timeline */}
      <div 
        className={`absolute ${MAP_CONTROL_STYLES.borderRadius} ${MAP_CONTROL_STYLES.shadow} ${MAP_CONTROL_STYLES.border} ${MAP_CONTROL_STYLES.backdropBlur} ${MAP_CONTROL_STYLES.transition} origin-bottom hidden lg:block pointer-events-auto`}
        onMouseEnter={() => zoom >= 10 && setCategoryPanelExpanded(true)}
        onMouseLeave={() => setCategoryPanelExpanded(false)}
        style={{
          ...createMapControlStyle('primary'),
          bottom: '1.5rem',
          left: '1.5rem',
          zIndex: 40,
          maxWidth: '340px',
          maxHeight: categoryPanelExpanded && zoom >= 10 ? '70vh' : '66px',
          overflow: 'hidden',
          pointerEvents: 'auto',
        }}
      >
        {/* Compact header - always visible */}
        <div className="px-4 h-[66px] flex items-center gap-3 cursor-pointer">
          <div className={`${MAP_CONTROL_STYLES.activeDot} flex-shrink-0`} style={{ minWidth: '0.5rem', minHeight: '0.5rem' }}></div>
          <div className="flex-1 min-w-0 flex flex-col">
            <div className="flex items-center gap-2">
              <div className={MAP_CONTROL_STYLES.text.title}>LOCATION FILTER</div>
              <div className={`${MAP_CONTROL_STYLES.text.badge} ${MAP_CONTROL_STYLES.text.badgeBg} ${MAP_CONTROL_STYLES.text.badgeText}`}>z{zoom}</div>
        </div>
            {zoom >= 10 ? (
              <div className={`${MAP_CONTROL_STYLES.text.subtitle} whitespace-nowrap overflow-hidden text-ellipsis flex items-center gap-3`}>
                <span className="inline-flex items-center gap-1">
                  <Filter className="w-3 h-3" />
                  {Array.from(availableCategories.keys()).filter(cat => enabledCategories.has(cat)).length}
                  /
                  {availableCategories.size}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {visiblePois.length.toLocaleString()}
                </span>
                {zoom >= LAYOUT.AGENT.MIN_ZOOM && visibleAgentsCount > 0 && (
                  <span className="inline-flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {visibleAgentsCount.toLocaleString()}
                  </span>
                )}
              </div>
            ) : zoom >= LAYOUT.AGENT.MIN_ZOOM ? (
              <div className={MAP_CONTROL_STYLES.text.subtitle}>
                {visibleAgentsCount > 0 ? (
                  <span>{visibleAgentsCount.toLocaleString()} agent{visibleAgentsCount !== 1 ? 's' : ''} in frame</span>
                ) : (
                  <span>Zoom in for more info</span>
                )}
              </div>
            ) : (
              <div className={MAP_CONTROL_STYLES.text.subtitle}>
                Zoom in for more info
              </div>
            )}
      </div>
          {/* Expand indicator - only show if zoom >= 10 */}
          {zoom >= 10 && (
            <svg 
              className={`w-4 h-4 text-white/50 transition-transform duration-300 flex-shrink-0 ${categoryPanelExpanded ? 'rotate-180' : ''}`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          )}
        </div>
        
        {/* Streamlined category list - shown on hover (only when zoom >= 10) */}
        {zoom >= 10 && (
          <div 
            className={`transition-opacity duration-300 ${categoryPanelExpanded ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
          >
            <div className="border-t border-white/10"></div>
            <div className="px-3 py-3 space-y-1.5 max-h-[calc(70vh-56px)] overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.2) transparent' }}>
            {Array.from(availableCategories.entries())
              .sort(([,a], [,b]) => b.count - a.count)
              .map(([category, { count, color, label, subcategories }]) => {
              const isEnabled = enabledCategories.has(category)
                const hasSubcategories = category !== 'other' && subcategories && subcategories.size > 1
                
              return (
                <button
                  key={category}
                  onClick={() => {
                      if (hasSubcategories) {
                      setSelectedCategory(category)
                      setShowCategoryModal(true)
                    } else {
                      toggleCategory(category)
                    }
                  }}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all duration-200 group ${
                    isEnabled
                        ? 'bg-white/15 hover:bg-white/20 border border-white/20'
                        : 'bg-transparent hover:bg-white/5 border border-transparent hover:border-white/10'
                    }`}
                  >
                    {/* Color indicator */}
                    <div 
                      className={`w-2 h-2 rounded-full flex-shrink-0 transition-all duration-200 ${
                        isEnabled ? 'shadow-lg scale-110' : 'opacity-50'
                      }`}
                      style={{ 
                        backgroundColor: color,
                        boxShadow: isEnabled ? `0 0 8px ${color}` : 'none'
                      }}
                    />
                    
                    {/* Label and count */}
                    <div className="flex-1 flex items-center justify-between min-w-0">
                      <span className={`text-sm font-medium truncate transition-colors ${
                        isEnabled ? 'text-white' : 'text-white/60 group-hover:text-white/80'
                      }`}>
                        {label}
                      </span>
                      <span className={`text-xs font-mono ml-2 flex-shrink-0 ${
                        isEnabled ? 'text-white/70' : 'text-white/40'
                      }`}>
                        {count.toLocaleString()}
                      </span>
                  </div>
                    
                    {/* Expand arrow for subcategories */}
                    {hasSubcategories && (
                      <svg 
                        className={`w-3.5 h-3.5 flex-shrink-0 transition-all ${
                          isEnabled ? 'text-white/70' : 'text-white/30 group-hover:text-white/50'
                        }`} 
                        fill="currentColor" 
                        viewBox="0 0 20 20"
                      >
                        <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                      </svg>
                  )}
                </button>
              )
            })}
            </div>
          </div>
        )}
      </div>

      {/* Category Detail Modal - Modern glass morphism */}
      {showCategoryModal && selectedCategory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div 
            ref={modalRef}
            className={`rounded-2xl shadow-2xl border border-white/20 max-w-3xl w-full mx-4 max-h-[85vh] overflow-hidden transform ${ANIMATIONS.TRANSITIONS.MODAL} scale-100 backdrop-blur-xl`}
            style={createGlassMorphismStyle('SECONDARY')}
          >
            {/* Header */}
            <div className={`${SPACING.PADDING.LG} border-b border-white/10 backdrop-blur-sm`} style={{background: 'rgba(0, 0, 0, 0.2)'}}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {availableCategories.get(selectedCategory) && (
                    <>
                      <div className={`w-6 h-6 rounded-full ${availableCategories.get(selectedCategory)!.color} shadow-lg`}></div>
                      <div>
                        <h2 className="text-2xl font-bold text-white drop-shadow">
                          {availableCategories.get(selectedCategory)!.label}
                        </h2>
                        <p className="text-sm text-white/70 mt-1 drop-shadow">
                          {availableCategories.get(selectedCategory)!.count.toLocaleString()} POIs • {availableCategories.get(selectedCategory)!.subcategories?.size || 0} subcategories
                        </p>
                      </div>
                    </>
                  )}
                </div>
                <button
                  onClick={closeModal}
                  className={`${SPACING.PADDING.SM} ${colors.glass.text} hover:text-white hover:bg-white/10 ${SPACING.BORDER.RADIUS.SM} ${ANIMATIONS.TRANSITIONS.DEFAULT} backdrop-blur-sm border border-white/20`}
                  title="Close (Esc)"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Content Area */}
            <div className="p-6 max-h-96 overflow-y-auto">
              {availableCategories.get(selectedCategory)?.subcategories && (
                <div className="space-y-6">
                  {/* Instructions and Controls */}
                  <div className="bg-blue-500/20 border border-blue-400/30 rounded-lg p-4 backdrop-blur-sm">
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-lg shadow-blue-500/50">
                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <h3 className="text-sm font-semibold text-white mb-1 drop-shadow">
                          Subcategory Selection
                        </h3>
                        <p className="text-sm text-white/80 drop-shadow">
                          <strong>Filter by specific types:</strong> Select subcategories to show/hide on the map. 
                          Changes apply immediately.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Bulk Actions */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-white/80 drop-shadow">
                        Quick Actions:
                      </span>
                      <button
                        onClick={() => {
                          const categoryData = availableCategories.get(selectedCategory)
                          if (categoryData?.subcategories) {
                            const allSubcategories = Array.from(categoryData.subcategories.keys())
                            setEnabledSubcategories(new Set(allSubcategories))
                          }
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 border border-green-400/30 text-white text-sm font-medium rounded-lg transition-all duration-200 backdrop-blur-sm shadow-lg shadow-green-500/20"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        Select All
                      </button>
                      <button
                        onClick={() => setEnabledSubcategories(new Set())}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 border border-red-400/30 text-white text-sm font-medium rounded-lg transition-all duration-200 backdrop-blur-sm shadow-lg shadow-red-500/20"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                        Clear All
                      </button>
                    </div>
                    {enabledSubcategories.size > 0 && (
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        <span className="font-medium text-blue-600 dark:text-blue-400">{enabledSubcategories.size}</span> selected
                      </div>
                    )}
                  </div>
                  
                  {/* Subcategory List */}
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                      </svg>
                      Available Subcategories
                    </h4>
                    {availableCategories.get(selectedCategory)?.subcategories && Array.from(availableCategories.get(selectedCategory)!.subcategories.entries())
                      .sort(([,a], [,b]) => (b as number) - (a as number))
                      .map(([subcategory, count]) => {
                        const isEnabled = enabledSubcategories.has(subcategory)
                        const categoryData = availableCategories.get(selectedCategory)
                        const percentage = categoryData ? Math.round(((count as number) / categoryData.count) * 100) : 0
                        return (
                          <div 
                            key={subcategory} 
                            className={`group flex items-center justify-between p-4 rounded-xl cursor-pointer transition-all duration-200 border-2 ${
                              isEnabled 
                                ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700 shadow-md' 
                                : 'bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border-transparent hover:border-gray-200 dark:hover:border-gray-600'
                            }`}
                            onClick={() => {
                              const newSubcategories = new Set(enabledSubcategories)
                              if (isEnabled) {
                                newSubcategories.delete(subcategory)
                              } else {
                                newSubcategories.add(subcategory)
                              }
                              setEnabledSubcategories(newSubcategories)
                            }}
                          >
                            <div className="flex items-center gap-4">
                              <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-200 ${
                                isEnabled 
                                  ? 'bg-blue-600 border-blue-600 shadow-sm' 
                                  : 'border-gray-300 dark:border-gray-600 group-hover:border-blue-400'
                              }`}>
                                {isEnabled && (
                                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                  </svg>
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                                    {subcategory.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                                  </span>
                                  {isEnabled && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200">
                                      Selected
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 mt-1">
                                  <div className="text-xs text-gray-500 dark:text-gray-400">
                                    {count.toLocaleString()} POIs
                                  </div>
                                  <div className="text-xs text-gray-400 dark:text-gray-500">
                                    •
                                  </div>
                                  <div className="text-xs text-gray-500 dark:text-gray-400">
                                    {percentage}% of category
                                  </div>
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                <div 
                                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                                  style={{ width: `${percentage}%` }}
                                ></div>
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 w-8 text-right">
                                {percentage}%
                              </div>
                            </div>
                          </div>
                        )
                      })}
                  </div>
                  
                  {enabledSubcategories.size > 0 && (
                    <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                      <div className="text-sm text-blue-800 dark:text-blue-200">
                        <strong>{enabledSubcategories.size}</strong> subcategories selected
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Footer */}
            <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => {
                      toggleCategory(selectedCategory)
                      closeModal()
                    }}
                    className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                      enabledCategories.has(selectedCategory) 
                        ? 'bg-red-600 hover:bg-red-700 text-white shadow-md hover:shadow-lg' 
                        : 'bg-green-600 hover:bg-green-700 text-white shadow-md hover:shadow-lg'
                    }`}
                  >
                    {enabledCategories.has(selectedCategory) ? (
                      <>
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                        Hide Category
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        Show Category
                      </>
                    )}
                  </button>
                  {enabledSubcategories.size > 0 && (
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      <span>
                        <span className="font-semibold text-blue-600 dark:text-blue-400">{enabledSubcategories.size}</span> subcategories selected
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Press <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">Esc</kbd> or click outside to close
                  </div>
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg transition-all duration-200 hover:shadow-md"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* POI Preview Card on Hover */}
      {previewData && (
        <POIPreviewCard
          name={previewData.name}
          category={previewData.category}
          subcategory={previewData.subcategory}
          visible={previewVisible}
          position={previewPosition}
        />
      )}
    </>
  )
}
