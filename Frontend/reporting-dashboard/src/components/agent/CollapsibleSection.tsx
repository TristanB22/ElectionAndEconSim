/**
 * Collapsible Section Component
 * 
 * Glassmorphic collapsible section for organizing agent data
 */

import React, { useState } from 'react'
import { ChevronDown, LucideIcon } from 'lucide-react'
import { SPACING } from '../../spacing'
import { TYPOGRAPHY } from '../../typography'
import { ANIMATIONS } from '../../animations'

interface CollapsibleSectionProps {
  title: string
  icon?: LucideIcon
  children: React.ReactNode
  defaultOpen?: boolean
  className?: string
}

export const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  icon: Icon,
  children,
  defaultOpen = false,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div 
      className={`${SPACING.BORDER.RADIUS.CARD} border border-gray-200 dark:border-gray-700 overflow-hidden ${ANIMATIONS.TRANSITIONS.DEFAULT} ${className}`}
      style={{
        background: 'rgba(255, 255, 255, 0.5) dark:rgba(0, 0, 0, 0.2)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
      }}
    >
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between ${SPACING.PADDING.MD} ${ANIMATIONS.TRANSITIONS.HOVER} hover:bg-gray-50 dark:hover:bg-gray-800/50`}
      >
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <Icon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
          )}
          <h3 className={`${TYPOGRAPHY.SIZE.BASE} ${TYPOGRAPHY.WEIGHT.SEMIBOLD} ${TYPOGRAPHY.COLORS.PRIMARY}`}>
            {title}
          </h3>
        </div>
        <ChevronDown 
          className={`w-5 h-5 ${TYPOGRAPHY.COLORS.MUTED} ${ANIMATIONS.TRANSITIONS.DEFAULT} ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Content */}
      {isOpen && (
        <div className={`${SPACING.PADDING.MD} pt-0 border-t border-gray-200 dark:border-gray-700`}>
          {children}
        </div>
      )}
    </div>
  )
}

interface DataGridProps {
  data: Array<{
    label: string
    value: string | number | null | undefined
    icon?: LucideIcon
  }>
  columns?: 1 | 2
  lined?: boolean
}

export const DataGrid: React.FC<DataGridProps> = ({ data, columns = 2, lined = true }) => {
  return (
    <div className={`grid grid-cols-1 ${columns === 2 ? 'md:grid-cols-2' : ''} ${lined ? 'divide-x divide-slate-800' : ''} gap-y-0`}>
      {data.map((item, index) => (
        <div 
          key={index}
          className={`flex items-start justify-between py-2 px-3 ${lined ? 'border-b border-slate-800/50 last:border-0' : ''}`}
        >
          <div className="flex items-center gap-2">
            {item.icon && (
              <item.icon className="w-3.5 h-3.5 text-slate-500" />
            )}
            <span className="text-sm text-slate-400 text-right">
              {item.label}
            </span>
          </div>
          <span className="text-sm text-white text-left max-w-xs ml-3">
            {item.value !== null && item.value !== undefined && String(item.value).trim() !== '' ? String(item.value) : '—'}
          </span>
        </div>
      ))}
    </div>
  )
}

