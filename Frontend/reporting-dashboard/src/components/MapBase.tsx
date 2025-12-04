import { useEffect, useRef } from 'react'
import maplibregl, { Map as MapLibreMap } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { API_ENDPOINTS, API_BASE_URL, ENABLE_MAP_LABELS } from '../config/api'

const DEFAULT_CENTER: [number, number] = [-98.5795, 39.8283] // US center
const DEFAULT_ZOOM = 4 // National view
const MAX_ZOOM = 18

// Using CartoDB tiles which are reliable and CORS-friendly

type MapBaseProps = { 
  onMap?: (map: MapLibreMap) => void 
  className?: string
}

export default function MapBase({ onMap, className = "w-full h-full" }: MapBaseProps) {
  const ref = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const initTimeoutRef = useRef<number | null>(null)
  const geoConfigRef = useRef<{ tiles: boolean; vector: boolean; pois: boolean } | null>(null)

  const initializeMap = () => {
    if (!ref.current || mapRef.current) return
    
    const container = ref.current
    
    // Ensure container has proper dimensions
    if (container.offsetWidth === 0 || container.offsetHeight === 0) {
      console.warn('Map container has no dimensions, retrying...')
      initTimeoutRef.current = setTimeout(initializeMap, 100)
      return
    }
    
    // Check if MapLibre GL is properly loaded
    if (!maplibregl || typeof maplibregl.Map !== 'function') {
      console.error('MapLibre GL not properly loaded')
      return
    }
    
    // Validate container
    if (!container || typeof container === 'string') {
      console.error('Invalid container type:', typeof container)
      return
    }
    
    try {
      // Initializing map
      
      // Use backend API for OpenStreetMap tiles with proxy-on-miss
      const mapSources: any = {
        'base-tiles': {
          type: 'raster',
          tiles: [
            `${API_BASE_URL}/api/map/tiles/{z}/{x}/{y}.png`
          ],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors'
        }
      }
      
      const mapLayers: any[] = [
        {
          id: 'base-tiles',
          type: 'raster',
          source: 'base-tiles',
          paint: {
            'raster-opacity': 1
          }
        }
      ]
      
      // Conditionally add labels source and layer based on config
      if (ENABLE_MAP_LABELS) {
        mapSources['labels'] = {
          type: 'raster',
          tiles: [
            'https://a.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png',
            'https://b.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png',
            'https://c.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png',
            'https://d.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png'
          ],
          tileSize: 256,
          attribution: '© CARTO'
        }
        
        mapLayers.push({
          id: 'labels',
          type: 'raster',
          source: 'labels',
          minzoom: 8,
          paint: {
            'raster-opacity': 1
          }
        })
      }
      
      const map = new maplibregl.Map({
        container: container,
        style: {
          version: 8,
          sources: mapSources,
          layers: mapLayers
        },
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        maxZoom: MAX_ZOOM
      })
      
      // Map created
      
      mapRef.current = map
      
      // Helper to ensure labels are always on top (only if labels are enabled)
      const ensureLabelsOnTop = () => {
        if (!ENABLE_MAP_LABELS) return
        
        try {
          if (map.getLayer('labels')) {
            // Move labels layer to top, above all other layers
            map.moveLayer('labels')
          }
        } catch (err) {
          // Ignore errors if layer doesn't exist
        }
      }

      map.on('load', async () => {
        // Map loaded
        // Ensure map is fully ready before calling onMap
        if (map.getCanvas() && map.isStyleLoaded()) {
          onMap?.(map)
        } else {
          console.warn('Map loaded but not fully ready, waiting for style...')
        }
        // Load geo config ONCE and cache
        try {
          const cfg = await fetch(API_ENDPOINTS.MAP_CONFIG).then(r => r.json())
          geoConfigRef.current = cfg
        } catch {
          geoConfigRef.current = { tiles: true, vector: false, pois: true }
        }

        // Ensure labels are on top initially
        ensureLabelsOnTop()
      })
      
      map.on('error', (e) => {
        console.error('MapLibre GL error:', e)
      })
      
      // Handle source loading
      map.on('sourcedata', (e) => {
        if (e.isSourceLoaded && e.sourceId === 'base-tiles') {
          // Base tiles loaded
        }
      })
      
      map.on('style.load', () => {
        // Map style loaded
        // Now the map should be fully ready
        if (map.getCanvas() && map.isStyleLoaded() && onMap) {
          // Map fully ready
          // Use setTimeout to ensure all internal MapLibre GL initialization is complete
          setTimeout(() => {
            onMap(map)
          }, 0)
        }
      })
      
    } catch (error) {
      console.error('Failed to initialize map:', error)
      // Retry after a short delay
      initTimeoutRef.current = setTimeout(initializeMap, 500)
    }
  }

  useEffect(() => {
    // Clear any existing timeout
    if (initTimeoutRef.current) {
      clearTimeout(initTimeoutRef.current)
      initTimeoutRef.current = null
    }
    
    // Use requestAnimationFrame to ensure DOM is ready
    const rafId = requestAnimationFrame(() => {
      initializeMap()
    })
    
    return () => {
      cancelAnimationFrame(rafId)
      if (initTimeoutRef.current) {
        clearTimeout(initTimeoutRef.current)
        initTimeoutRef.current = null
      }
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [onMap])

  return <div className={className} ref={ref} />
}
