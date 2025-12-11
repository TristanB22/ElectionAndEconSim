import React from 'react'
import { Popup } from 'maplibre-gl'

export interface BaseModalProps {
  lngLat: { lng: number; lat: number }
  title: string
  subtitle?: string
  osmId: number
  category: string
  subcategory?: string
  coordinates: [number, number]
  keyProperties: Array<{ key: string; value: string; icon?: string }>
  allProperties?: Array<{ key: string; value: string; icon?: string; link?: string }>
  rawTags?: Record<string, any>
  type: 'poi' | 'road'
  onClose: () => void
}

interface ModalPosition {
  anchor: 'top' | 'bottom' | 'left' | 'right'
  offset: [number, number]
  arrowPosition: 'top' | 'bottom' | 'left' | 'right'
}

interface ViewportBounds {
  left: number
  right: number
  top: number
  bottom: number
}

// Calculate optimal modal position based on viewport and click location
const calculateOptimalPosition = (
  lngLat: { lng: number; lat: number },
  map: any
): ModalPosition => {
  const modalWidth = 380
  const modalHeight = 400 // More conservative estimate
  const padding = 20 // Reduced padding for better fit
  const gap = 15 // Gap between modal and click point
  
  // Get map container dimensions
  const container = map.getContainer()
  const containerRect = container.getBoundingClientRect()
  
  // Convert lngLat to pixel coordinates
  const point = map.project(lngLat)
  
  // Calculate viewport bounds in pixels with more conservative margins
  const viewport: ViewportBounds = {
    left: padding,
    right: containerRect.width - padding,
    top: padding,
    bottom: containerRect.height - padding
  }
  
  // Calculate available space in each direction
  const spaceAbove = point.y - viewport.top
  const spaceBelow = viewport.bottom - point.y
  const spaceLeft = point.x - viewport.left
  const spaceRight = viewport.right - point.x
  
  // Calculate modal bounds for each position
  const calculateModalBounds = (anchor: string, offset: [number, number]) => {
    let modalX = point.x + offset[0]
    let modalY = point.y + offset[1]
    
    // Adjust for anchor position
    if (anchor === 'bottom') {
      modalY = point.y - modalHeight - gap
    } else if (anchor === 'top') {
      modalY = point.y + gap
    } else if (anchor === 'right') {
      modalX = point.x - modalWidth - gap
    } else if (anchor === 'left') {
      modalX = point.x + gap
    }
    
    return {
      left: modalX,
      right: modalX + modalWidth,
      top: modalY,
      bottom: modalY + modalHeight
    }
  }
  
  // Define positions with better spacing logic
  const positions = [
    {
      anchor: 'bottom' as const,
      offset: [0, -gap] as [number, number],
      arrowPosition: 'top' as const,
      space: spaceAbove,
      preference: 4,
      bounds: calculateModalBounds('bottom', [0, -gap])
    },
    {
      anchor: 'top' as const,
      offset: [0, gap] as [number, number],
      arrowPosition: 'bottom' as const,
      space: spaceBelow,
      preference: 3,
      bounds: calculateModalBounds('top', [0, gap])
    },
    {
      anchor: 'right' as const,
      offset: [-gap, 0] as [number, number],
      arrowPosition: 'left' as const,
      space: spaceLeft,
      preference: 2,
      bounds: calculateModalBounds('right', [-gap, 0])
    },
    {
      anchor: 'left' as const,
      offset: [gap, 0] as [number, number],
      arrowPosition: 'right' as const,
      space: spaceRight,
      preference: 1,
      bounds: calculateModalBounds('left', [gap, 0])
    }
  ]
  
  // First, try to find positions that fit completely within viewport
  const viablePositions = positions.filter(pos => {
    const bounds = pos.bounds
    return bounds.left >= viewport.left && 
           bounds.right <= viewport.right && 
           bounds.top >= viewport.top && 
           bounds.bottom <= viewport.bottom
  })
  
  if (viablePositions.length > 0) {
    // Sort by preference and space, choose the best one
    viablePositions.sort((a, b) => {
      if (a.preference !== b.preference) {
        return b.preference - a.preference
      }
      return b.space - a.space
    })
    
    return {
      anchor: viablePositions[0].anchor,
      offset: viablePositions[0].offset,
      arrowPosition: viablePositions[0].arrowPosition
    }
  }
  
  // If no position fits completely, try to adjust positions to fit
  const adjustedPositions = positions.map(pos => {
    const bounds = pos.bounds
    let adjustedOffset = [...pos.offset] as [number, number]
    
    // Calculate how much we need to adjust
    const leftOverflow = Math.max(0, viewport.left - bounds.left)
    const rightOverflow = Math.max(0, bounds.right - viewport.right)
    const topOverflow = Math.max(0, viewport.top - bounds.top)
    const bottomOverflow = Math.max(0, bounds.bottom - viewport.bottom)
    
    // Adjust horizontal position
    if (leftOverflow > 0) {
      adjustedOffset[0] += leftOverflow + 5 // 5px extra margin
    } else if (rightOverflow > 0) {
      adjustedOffset[0] -= rightOverflow + 5 // 5px extra margin
    }
    
    // Adjust vertical position
    if (topOverflow > 0) {
      adjustedOffset[1] += topOverflow + 5 // 5px extra margin
    } else if (bottomOverflow > 0) {
      adjustedOffset[1] -= bottomOverflow + 5 // 5px extra margin
    }
    
    return {
      ...pos,
      offset: adjustedOffset,
      bounds: calculateModalBounds(pos.anchor, adjustedOffset)
    }
  })
  
  // Filter adjusted positions that now fit
  const adjustedViable = adjustedPositions.filter(pos => {
    const bounds = pos.bounds
    return bounds.left >= viewport.left && 
           bounds.right <= viewport.right && 
           bounds.top >= viewport.top && 
           bounds.bottom <= viewport.bottom
  })
  
  if (adjustedViable.length > 0) {
    // Use the best adjusted position
    adjustedViable.sort((a, b) => {
      if (a.preference !== b.preference) {
        return b.preference - a.preference
      }
      return b.space - a.space
    })
    
    return {
      anchor: adjustedViable[0].anchor,
      offset: adjustedViable[0].offset,
      arrowPosition: adjustedViable[0].arrowPosition
    }
  }
  
  // If still no position fits, use the one with the least overflow
  const bestPosition = positions.reduce((best, current) => {
    const bestOverflow = Math.max(0, best.bounds.left - viewport.left) + 
                        Math.max(0, best.bounds.right - viewport.right) +
                        Math.max(0, best.bounds.top - viewport.top) + 
                        Math.max(0, best.bounds.bottom - viewport.bottom)
    
    const currentOverflow = Math.max(0, current.bounds.left - viewport.left) + 
                           Math.max(0, current.bounds.right - viewport.right) +
                           Math.max(0, current.bounds.top - viewport.top) + 
                           Math.max(0, current.bounds.bottom - viewport.bottom)
    
    return currentOverflow < bestOverflow ? current : best
  })
  
  // For the fallback position, try to center it as much as possible
  let finalOffset = [...bestPosition.offset] as [number, number]
  
  if (bestPosition.anchor === 'bottom' || bestPosition.anchor === 'top') {
    // Center horizontally
    const centerX = (viewport.left + viewport.right) / 2
    const modalCenterX = point.x + finalOffset[0] + modalWidth / 2
    finalOffset[0] += (centerX - modalCenterX)
  } else {
    // Center vertically
    const centerY = (viewport.top + viewport.bottom) / 2
    const modalCenterY = point.y + finalOffset[1] + modalHeight / 2
    finalOffset[1] += (centerY - modalCenterY)
  }
  
  return {
    anchor: bestPosition.anchor,
    offset: finalOffset,
    arrowPosition: bestPosition.arrowPosition
  }
}

export const createBaseModal = (props: BaseModalProps, map?: any): Popup => {
  const {
    lngLat,
    title,
    subtitle,
    osmId,
    category,
    subcategory,
    coordinates,
    keyProperties,
    allProperties = [],
    rawTags = {},
    type,
    onClose
  } = props

  // Helper function to render key properties
  const renderKeyProperties = () => {
    if (keyProperties.length === 0) return ''
    
    return keyProperties
      .slice(0, 6) // Limit to 6 most important properties
      .map(({ key, value, icon }) => {
        const isLink = key === 'website' || key === 'phone'
        
        return `
          <div class="flex items-center gap-2 py-1">
            <span class="text-xs font-medium text-gray-300 w-16 flex-shrink-0">${key}:</span>
            <span class="text-xs text-gray-200 truncate">
              ${isLink ? 
                (key === 'website' ? 
                  `<a href="${value}" target="_blank" class="text-blue-400 hover:text-blue-300">${value}</a>` :
                  `<a href="tel:${value}" class="text-blue-400 hover:text-blue-300">${value}</a>`
                ) : 
                value
              }
            </span>
          </div>
        `
      }).join('')
  }

  // Helper function to render all properties
  const renderAllProperties = () => {
    if (allProperties.length === 0) return ''
    
    
    // Group properties by type
    const priorityFields = allProperties.filter(p => 
      ['name', 'amenity', 'shop', 'tourism', 'leisure', 'building', 'brand', 'operator', 'highway', 'ref', 'oneway', 'maxspeed', 'surface', 'lanes'].includes(p.key)
    )
    const addressFields = allProperties.filter(p => p.key.startsWith('addr:'))
    const contactFields = allProperties.filter(p => 
      ['phone', 'email', 'website', 'opening_hours'].includes(p.key)
    )
    const additionalFields = allProperties.filter(p => 
      !priorityFields.includes(p) && !addressFields.includes(p) && !contactFields.includes(p)
    )

    let sections = []
    
    // Priority info section
    if (priorityFields.length > 0) {
      sections.push(`
        <div class="mb-4">
          <h4 class="text-sm font-semibold text-gray-200 dark:text-gray-200 mb-3 border-b border-gray-700 dark:border-gray-700 pb-1">
            Details
          </h4>
          <div class="space-y-2">
            ${priorityFields.map(field => `
              <div class="flex items-start gap-3 py-1">
                <span class="text-xs font-medium text-gray-400 dark:text-gray-400 min-w-0 flex-shrink-0 w-20">${field.key}</span>
                <span class="text-xs text-gray-200 dark:text-gray-200 truncate flex-1">${field.value}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `)
    }

    // Address section
    if (addressFields.length > 0) {
      sections.push(`
        <div class="mb-4">
          <h4 class="text-sm font-semibold text-gray-200 dark:text-gray-200 mb-3 border-b border-gray-700 dark:border-gray-700 pb-1">
            Address
          </h4>
          <div class="space-y-2">
            ${addressFields.map(field => `
              <div class="flex items-start gap-3 py-1">
                <span class="text-xs font-medium text-gray-400 dark:text-gray-400 min-w-0 flex-shrink-0 w-20">${field.key}</span>
                <span class="text-xs text-gray-200 dark:text-gray-200 truncate flex-1">${field.value}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `)
    }

    // Contact section
    if (contactFields.length > 0) {
      sections.push(`
        <div class="mb-4">
          <h4 class="text-sm font-semibold text-gray-200 dark:text-gray-200 mb-3 border-b border-gray-700 dark:border-gray-700 pb-1">
            Contact
          </h4>
          <div class="space-y-2">
            ${contactFields.map(field => `
              <div class="flex items-start gap-3 py-1">
                <span class="text-xs font-medium text-gray-400 dark:text-gray-400 min-w-0 flex-shrink-0 w-20">${field.key}</span>
                ${field.link ? 
                  `<a href="${field.link}" target="_blank" class="text-xs text-blue-400 hover:text-blue-300 dark:text-blue-400 dark:hover:text-blue-300 transition-colors truncate flex-1">${field.value}</a>` :
                  `<span class="text-xs text-gray-200 dark:text-gray-200 truncate flex-1">${field.value}</span>`
                }
              </div>
            `).join('')}
          </div>
        </div>
      `)
    }

    // Additional info section
    if (additionalFields.length > 0) {
      sections.push(`
        <div class="mb-4">
          <h4 class="text-sm font-semibold text-gray-200 dark:text-gray-200 mb-3 border-b border-gray-700 dark:border-gray-700 pb-1">
            Additional Info
          </h4>
          <div class="space-y-2 max-h-32 overflow-y-auto">
            ${additionalFields.map(field => `
              <div class="flex items-start gap-3 py-1">
                <span class="text-xs font-medium text-gray-400 dark:text-gray-400 min-w-0 flex-shrink-0 w-20">${field.key}</span>
                ${field.link ? 
                  `<a href="${field.link}" target="_blank" class="text-xs text-blue-400 hover:text-blue-300 dark:text-blue-400 dark:hover:text-blue-300 transition-colors truncate flex-1">${field.value}</a>` :
                  `<span class="text-xs text-gray-200 dark:text-gray-200 truncate flex-1">${field.value}</span>`
                }
              </div>
            `).join('')}
          </div>
        </div>
      `)
    }

    return sections.join('')
  }

  // Render raw tags
  const renderRawTags = () => {
    try {
      const entries = Object.entries(rawTags || {})
      if (entries.length === 0) return ''
      
      const sorted = entries.sort((a, b) => a[0].localeCompare(b[0]))
      return `
        <div class="mb-4">
          <h4 class="text-sm font-semibold text-gray-200 dark:text-gray-200 mb-3 border-b border-gray-700 dark:border-gray-700 pb-1">
            Raw Tags
          </h4>
          <div class="space-y-1 max-h-48 overflow-y-auto">
            ${sorted.map(([k, v]) => {
              const value = Array.isArray(v) ? v.join(', ') : (typeof v === 'object' ? JSON.stringify(v) : String(v))
              return `
                <div class="flex items-center justify-between p-2 rounded bg-gray-800/40 border border-gray-700/40">
                  <div class="text-[11px] text-gray-300 font-mono mr-2 truncate">${k}</div>
                  <div class="text-[11px] text-gray-100 ml-2 truncate max-w-[220px]">${value}</div>
                </div>
              `
            }).join('')}
          </div>
        </div>
      `
    } catch (e) {
      return ''
    }
  }

  // Get type-specific styling
  const getTypeInfo = () => {
    if (type === 'poi') {
      return {
        label: 'POI Details',
        color: 'blue'
      }
    } else {
      return {
        label: 'Road Details', 
        color: 'amber'
      }
    }
  }

  const typeInfo = getTypeInfo()

  // Calculate optimal position if map is provided
  let position: ModalPosition
  try {
    position = map ? calculateOptimalPosition(lngLat, map) : {
      anchor: 'bottom' as const,
      offset: [0, 20] as [number, number],
      arrowPosition: 'top' as const // Arrow points down toward click point
    }
  } catch (error) {
    // Fallback if positioning calculation fails
    console.warn('Modal positioning calculation failed, using fallback:', error)
    position = {
      anchor: 'bottom' as const,
      offset: [0, 20] as [number, number],
      arrowPosition: 'top' as const // Arrow points down toward click point
    }
  }

  // Generate arrow CSS based on position - ensuring 90-degree angles and consistent size
  const getArrowCSS = (arrowPosition: string) => {
    const arrowSize = 12 // Consistent arrow size
    
    // Reset all arrow styles first
    const baseArrow = `
      .maplibregl-popup-tip {
        border: none !important;
        width: 0 !important;
        height: 0 !important;
        position: absolute !important;
        z-index: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        background: none !important;
      }
    `
    
    switch (arrowPosition) {
      case 'top':
        return baseArrow + `
          .maplibregl-popup-tip {
            border-bottom: ${arrowSize}px solid rgba(17, 24, 39, 0.95) !important;
            border-left: ${arrowSize}px solid transparent !important;
            border-right: ${arrowSize}px solid transparent !important;
            border-top: none !important;
            left: 50% !important;
            top: 100% !important;
            transform: translateX(-50%) !important;
          }
          .dark .maplibregl-popup-tip {
            border-bottom-color: rgba(17, 24, 39, 0.95) !important;
          }
        `
      case 'bottom':
        return baseArrow + `
          .maplibregl-popup-tip {
            border-top: ${arrowSize}px solid rgba(17, 24, 39, 0.95) !important;
            border-left: ${arrowSize}px solid transparent !important;
            border-right: ${arrowSize}px solid transparent !important;
            border-bottom: none !important;
            left: 50% !important;
            bottom: 100% !important;
            transform: translateX(-50%) !important;
          }
          .dark .maplibregl-popup-tip {
            border-top-color: rgba(17, 24, 39, 0.95) !important;
          }
        `
      case 'left':
        return baseArrow + `
          .maplibregl-popup-tip {
            border-right: ${arrowSize}px solid rgba(17, 24, 39, 0.95) !important;
            border-top: ${arrowSize}px solid transparent !important;
            border-bottom: ${arrowSize}px solid transparent !important;
            border-left: none !important;
            left: 100% !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
          }
          .dark .maplibregl-popup-tip {
            border-right-color: rgba(17, 24, 39, 0.95) !important;
          }
        `
      case 'right':
        return baseArrow + `
          .maplibregl-popup-tip {
            border-left: ${arrowSize}px solid rgba(17, 24, 39, 0.95) !important;
            border-top: ${arrowSize}px solid transparent !important;
            border-bottom: ${arrowSize}px solid transparent !important;
            border-right: none !important;
            right: 100% !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
          }
          .dark .maplibregl-popup-tip {
            border-left-color: rgba(17, 24, 39, 0.95) !important;
          }
        `
      default:
        return baseArrow
    }
  }

  return new Popup({
    closeButton: false,
    closeOnClick: true,
    className: 'poi-popup-container',
    maxWidth: '380px',
    offset: position.offset,
    anchor: position.anchor
  }).setLngLat(lngLat).setHTML(`
    <div class="bg-gray-900 dark:bg-gray-900 rounded-xl shadow-2xl border border-gray-700 dark:border-gray-700" style="background: rgba(17,24,39,0.95); backdrop-filter: blur(12px);">
      <div class="p-5">
        <div class="mb-4">
          <div class="flex items-start justify-between mb-3">
            <h3 class="text-lg font-semibold text-white dark:text-white truncate pr-2 leading-tight">${title}</h3>
            <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-mono bg-gray-800 dark:bg-gray-800 text-gray-300 dark:text-gray-300 flex-shrink-0">#${osmId}</span>
          </div>
          ${subtitle ? `<div class="text-sm text-gray-300 dark:text-gray-300 mb-3">${subtitle}</div>` : ''}
          <div class="flex items-center gap-2 mb-3">
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-800 dark:bg-gray-800 text-gray-300 dark:text-gray-300">
              ${category}
            </span>
            ${subcategory && subcategory !== category ? `
              <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-700 dark:bg-gray-700 text-gray-400 dark:text-gray-400">
                ${subcategory}
              </span>
            ` : ''}
          </div>
          <div class="text-xs text-gray-400 dark:text-gray-400 flex items-center gap-4 border-t border-gray-700 dark:border-gray-700 pt-2">
            <span class="font-medium">${typeInfo.label}</span>
            <span class="font-mono">${coordinates[1].toFixed(4)}, ${coordinates[0].toFixed(4)}</span>
          </div>
        </div>
        
        <!-- Key Properties -->
        <div class="space-y-2 max-h-64 overflow-y-auto">
          ${renderKeyProperties()}
        </div>

        <!-- All Properties -->
        <div class="mt-2">
          ${renderAllProperties()}
        </div>
        
        <!-- Footer -->
        <div class="mt-4 pt-3 border-t border-gray-700 dark:border-gray-700 text-xs text-gray-400 dark:text-gray-400 text-center">
          Press <kbd class="px-2 py-1 bg-gray-800 dark:bg-gray-800 text-gray-300 dark:text-gray-300 rounded text-xs font-mono">Esc</kbd> or click outside to close
        </div>
      </div>
    </div>
    
    <style>
      kbd {
        font-family: ui-monospace, SFMono-Regular, monospace;
      }
      ${getArrowCSS(position.arrowPosition)}
      
      /* Ensure popup container positioning works correctly */
      .maplibregl-popup {
        pointer-events: auto !important;
      }
      
      .maplibregl-popup-content {
        pointer-events: auto !important;
      }
      
      /* Ensure arrow is properly positioned and overrides MapLibre defaults */
      .maplibregl-popup-tip {
        pointer-events: none !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
      }
      
      /* Override any MapLibre GL default arrow styles */
      .maplibregl-popup .maplibregl-popup-tip {
        border: none !important;
        background: none !important;
        box-shadow: none !important;
      }
    </style>
  `)
}
