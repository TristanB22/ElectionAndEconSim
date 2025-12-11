/**
 * POIPreviewCard - Quick preview tooltip that appears on POI hover
 * Shows basic information without opening the full drawer
 */

import React from 'react'
import { MapPin, Store, Building2, Utensils, Coffee } from 'lucide-react'
import { poiCategoryColors } from '../styles/colors'

interface POIPreviewCardProps {
  name: string
  category?: string
  subcategory?: string
  visible: boolean
  position: { x: number; y: number }
}

export const POIPreviewCard: React.FC<POIPreviewCardProps> = ({
  name,
  category,
  subcategory,
  visible,
  position,
}) => {
  if (!visible) return null

  // Get category icon
  const getCategoryIcon = () => {
    switch (category) {
      case 'shop':
        return <Store className="w-4 h-4" />
      case 'amenity':
        return <Coffee className="w-4 h-4" />
      case 'tourism':
        return <MapPin className="w-4 h-4" />
      case 'building':
        return <Building2 className="w-4 h-4" />
      case 'restaurant':
      case 'food':
        return <Utensils className="w-4 h-4" />
      default:
        return <MapPin className="w-4 h-4" />
    }
  }

  // Get category color
  const categoryColor = category && poiCategoryColors[category]
    ? poiCategoryColors[category]
    : poiCategoryColors.other

  return (
    <div
      className="fixed z-[9999] pointer-events-none transition-opacity duration-200"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        opacity: visible ? 1 : 0,
      }}
    >
      <div
        className="rounded-xl shadow-2xl border backdrop-blur-xl px-3 py-2 max-w-xs"
        style={{
          background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.85) 0%, rgba(0, 0, 0, 0.75) 100%)',
          borderColor: 'rgba(255, 255, 255, 0.15)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1)',
        }}
      >
        <div className="flex items-start gap-2.5">
          {/* Category icon with color */}
          <div
            className="flex-shrink-0 p-1.5 rounded-lg mt-0.5"
            style={{
              backgroundColor: `${categoryColor}20`,
              color: categoryColor,
            }}
          >
            {getCategoryIcon()}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white truncate leading-tight">
              {name || 'Unnamed Location'}
            </p>
            {(category || subcategory) && (
              <div className="flex items-center gap-1.5 mt-1">
                {category && (
                  <span
                    className="text-xs px-1.5 py-0.5 rounded font-medium"
                    style={{
                      backgroundColor: `${categoryColor}15`,
                      color: categoryColor,
                    }}
                  >
                    {category}
                  </span>
                )}
                {subcategory && (
                  <span className="text-xs text-gray-400">
                    {subcategory}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tooltip arrow */}
      <div
        className="absolute w-2 h-2 rotate-45"
        style={{
          top: '-4px',
          left: '16px',
          background: 'rgba(0, 0, 0, 0.85)',
          borderTop: '1px solid rgba(255, 255, 255, 0.15)',
          borderLeft: '1px solid rgba(255, 255, 255, 0.15)',
        }}
      />
    </div>
  )
}

