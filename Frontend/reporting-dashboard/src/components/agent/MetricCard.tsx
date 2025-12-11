/**
 * metric card component
 * 
 * enhanced card with subtle gradient backgrounds and hover lift effect.
 * differentiated by accent color for visual grouping (cyan/green/violet).
 */

import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface MetricCardProps {
  icon: React.ReactNode
  iconClassName?: string
  label: string
  value: string
  sublabel?: string
  contextLine?: string
  trend?: 'up' | 'down'
  trendValue?: string
  showProgress?: boolean
  progressPercent?: number
  accentColor?: 'cyan' | 'green' | 'violet'
  className?: string
}

export const MetricCard: React.FC<MetricCardProps> = ({
  icon,
  iconClassName = 'bg-sky-500/15 text-sky-100',
  label,
  value,
  sublabel,
  contextLine,
  trend,
  trendValue,
  showProgress = false,
  progressPercent = 0,
  accentColor = 'cyan',
  className = '',
}) => {
  const gradientMap = {
    cyan: 'from-cyan-500/20 to-slate-900/90',
    green: 'from-emerald-500/20 to-slate-900/90',
    violet: 'from-violet-500/20 to-slate-900/90',
  }

  const shadowMap = {
    cyan: 'hover:shadow-[0_0_15px_rgba(6,182,212,0.1)]',
    green: 'hover:shadow-[0_0_15px_rgba(16,185,129,0.1)]',
    violet: 'hover:shadow-[0_0_15px_rgba(139,92,246,0.1)]',
  }

  return (
    <div 
      className={`bg-gradient-to-br ${gradientMap[accentColor]} border border-slate-800 rounded-2xl p-4 md:p-5 transition-all duration-300 hover:border-slate-700 hover:-translate-y-0.5 ${shadowMap[accentColor]} ${className}`}
    >
      {/* icon circle - small colored surface */}
      <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-3 ${iconClassName}`}>
        {icon}
      </div>

      {/* label */}
      <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">
        {label}
      </div>

      {/* value with optional trend */}
      <div className="flex items-baseline gap-2 mb-1">
        <div className="text-2xl md:text-3xl font-semibold text-white">
          {value}
        </div>
        {trend && (
          <div className={`flex items-center gap-1 ${trend === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
            {trend === 'up' ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            {trendValue && <span className="text-xs font-medium">{trendValue}</span>}
          </div>
        )}
      </div>

      {/* context line (e.g., "↑ +2.4% YTD") */}
      {contextLine && (
        <div className="text-xs text-slate-400 mb-1">
          {contextLine}
        </div>
      )}

      {/* sublabel */}
      {sublabel && (
        <div className="text-xs text-slate-500">
          {sublabel}
        </div>
      )}

      {/* optional progress bar - very low contrast */}
      {showProgress && (
        <div className="mt-3 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className="h-full bg-sky-500 transition-all duration-300"
            style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
          />
        </div>
      )}
    </div>
  )
}

