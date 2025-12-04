/**
 * Personal Summary Card Component
 * 
 * Displays LLM-generated personal summary with expandable functionality
 */

import React, { useState } from 'react'
import { Quote, ChevronDown } from 'lucide-react'
import { SPACING } from '../../spacing'
import { TYPOGRAPHY } from '../../typography'
import { ANIMATIONS } from '../../animations'

const BG = '#0B111A'
const TEXT = '#E6EDF6'
const MUTED = '#8FA0B8'
const BORDER = '#1C2836'
const ACCENT = '#3EA6FF'

interface PersonalSummaryCardProps {
  summary: string | null
  netWorth?: number | null
  previewLines?: number
}

export const PersonalSummaryCard: React.FC<PersonalSummaryCardProps> = ({
  summary,
  netWorth,
  previewLines = 3,
}) => {
  const [isExpanded, setIsExpanded] = useState(false)
  // net worth color accent removed for consistent theme

  if (!summary) {
    return (
      <div 
        className={`${SPACING.BORDER.RADIUS.CARD} ${SPACING.PADDING.MD} text-center`}
        style={{ background: BG, border: `1px solid ${BORDER}` }}
      >
        <Quote className="w-6 h-6 mx-auto mb-2" style={{ color: MUTED }} />
        <p style={{ color: MUTED, fontSize: 13 }}>No personal summary available for this agent.</p>
      </div>
    )
  }

  // Split summary into lines for preview
  const lines = summary.split('\n').filter(line => line.trim())
  const shouldTruncate = lines.length > previewLines
  const displayText = isExpanded 
    ? summary 
    : lines.slice(0, previewLines).join('\n') + (shouldTruncate ? '...' : '')

  return (
    <div 
      className={`relative ${SPACING.BORDER.RADIUS.CARD} overflow-hidden ${ANIMATIONS.TRANSITIONS.DEFAULT} mb-4`}
      style={{ background: BG, border: `1px solid ${BORDER}` }}
    >
      {/* Slim accent line for visual anchor */}
      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ background: ACCENT }} />

      <div className={`${SPACING.PADDING.LG} pl-8`}>
        {/* Header */}
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#0D1420', border: `1px solid ${BORDER}` }}>
            <Quote className="w-4 h-4" style={{ color: ACCENT }} />
          </div>
          <h3 style={{ color: TEXT, fontSize: 14, fontWeight: 600 }}>Personal Summary</h3>
        </div>

        {/* Summary Text */}
        <p className={`whitespace-pre-wrap mb-3`} style={{ color: TEXT, fontSize: 13, lineHeight: 1.6 }}>
          {displayText}
        </p>

        {/* Expand/Collapse Button */}
        {shouldTruncate && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={`flex items-center gap-2 ${ANIMATIONS.TRANSITIONS.HOVER}`}
            style={{ color: ACCENT, fontSize: 12 }}
          >
            <span>{isExpanded ? 'Show less' : 'Read more'}</span>
            <ChevronDown className={`w-4 h-4 ${ANIMATIONS.TRANSITIONS.DEFAULT} ${isExpanded ? 'rotate-180' : ''}`} />
          </button>
        )}
      </div>
    </div>
  )
}

