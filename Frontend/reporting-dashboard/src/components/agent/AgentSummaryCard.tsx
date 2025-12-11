/**
 * agent summary card component
 * 
 * displays the agent's personal summary in an expandable card.
 * redesigned with a more sophisticated, editorial style.
 */

import React, { useState } from 'react'
import { FileText, ChevronDown, Sparkles } from 'lucide-react'

interface AgentSummaryCardProps {
  summary: string | null
  onGenerateSummary?: () => void
}

export const AgentSummaryCard: React.FC<AgentSummaryCardProps> = ({
  summary,
  onGenerateSummary,
}) => {
  const [isExpanded, setIsExpanded] = useState(false)
  
  const MAX_LENGTH = 320
  const shouldTruncate = summary && summary.length > MAX_LENGTH
  const displayText = shouldTruncate && !isExpanded 
    ? summary.substring(0, MAX_LENGTH) + '...' 
    : summary

  if (!summary) {
    return (
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900/90 via-slate-900/95 to-slate-900 border border-slate-800/80 rounded-2xl p-6 md:p-8">
        {/* subtle gradient accent */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-sky-500/30 to-transparent" />
        
        {/* header with icon */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/20 to-sky-600/10 border border-sky-500/20 flex items-center justify-center">
            <FileText className="w-5 h-5 text-sky-300" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Personal Summary</h3>
            <p className="text-xs text-slate-500">AI-generated profile</p>
          </div>
        </div>

        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          No personal summary has been generated for this agent yet.
        </p>
        
        {onGenerateSummary && (
          <button
            onClick={onGenerateSummary}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl bg-gradient-to-r from-sky-600 to-sky-500 hover:from-sky-500 hover:to-sky-400 text-white border border-sky-400/20 shadow-lg shadow-sky-500/20 transition-all"
          >
            <Sparkles className="w-4 h-4" />
            <span>Generate Summary</span>
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden bg-gradient-to-br from-slate-900/90 via-slate-900/95 to-slate-900 border border-slate-800/80 rounded-2xl p-6 md:p-8">
      {/* subtle gradient accent */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-sky-500/30 to-transparent" />
      
      {/* header with icon */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/20 to-sky-600/10 border border-sky-500/20 flex items-center justify-center">
          <FileText className="w-5 h-5 text-sky-300" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-white">Personal Summary</h3>
          <p className="text-xs text-slate-500">AI-generated profile</p>
        </div>
      </div>

      {/* summary text with editorial styling */}
      <div className="relative pl-4 border-l-2 border-sky-500/30">
        <p className="text-[15px] md:text-base text-slate-200 leading-relaxed whitespace-pre-wrap">
          {displayText}
        </p>
      </div>

      {shouldTruncate && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-sky-400 hover:text-sky-300 transition-colors group"
        >
          <span>{isExpanded ? 'Show less' : 'Read more'}</span>
          <ChevronDown className={`w-4 h-4 transition-transform group-hover:translate-y-0.5 ${isExpanded ? 'rotate-180' : ''}`} />
        </button>
      )}
    </div>
  )
}
