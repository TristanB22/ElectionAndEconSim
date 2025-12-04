/**
 * Key Metrics Dashboard Component
 * 
 * Displays the three most important financial/demographic metrics
 */

import React from 'react'
import { Home, DollarSign, Users, TrendingUp, Building2 } from 'lucide-react'
import { SPACING } from '../../spacing'
import { TYPOGRAPHY } from '../../typography'
import { ANIMATIONS } from '../../animations'
import { formatCurrency, formatCompactNumber, getNetWorthColors } from '../../utils/agentUtils'

interface MetricCardProps {
  title: string
  value: string
  subtitle?: string
  icon: React.ReactNode
  gradient: string
  textColor: string
  bgColor: string
  borderColor: string
  progress?: number
  trend?: 'up' | 'down' | 'neutral'
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  gradient,
  textColor,
  bgColor,
  borderColor,
  progress,
  trend,
}) => {
  return (
    <div
      className={`${SPACING.BORDER.RADIUS.CARD} border ${borderColor} ${bgColor} ${SPACING.PADDING.LG} ${ANIMATIONS.TRANSITIONS.CARD} hover:shadow-xl hover:-translate-y-1 cursor-default`}
      style={{
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
      }}
    >
      {/* Icon */}
      <div 
        className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
        style={{
          background: gradient,
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div className="text-white">
          {icon}
        </div>
      </div>

      {/* Title */}
      <div className={`${TYPOGRAPHY.SIZE.SM} ${TYPOGRAPHY.WEIGHT.MEDIUM} ${TYPOGRAPHY.COLORS.MUTED} mb-2`}>
        {title}
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-2 mb-2">
        <div className={`text-3xl ${TYPOGRAPHY.WEIGHT.BOLD} ${textColor}`}>
          {value}
        </div>
        {trend && (
          <TrendingUp 
            className={`w-5 h-5 ${
              trend === 'up' ? 'text-emerald-500' : 
              trend === 'down' ? 'text-red-500 rotate-180' : 
              'text-gray-400'
            }`}
          />
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <div className={`${TYPOGRAPHY.SIZE.XS} ${TYPOGRAPHY.COLORS.MUTED} mb-3`}>
          {subtitle}
        </div>
      )}

      {/* Progress Bar */}
      {progress !== undefined && (
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full ${ANIMATIONS.TRANSITIONS.DEFAULT}`}
            style={{
              width: `${Math.min(100, Math.max(0, progress))}%`,
              background: gradient,
            }}
          />
        </div>
      )}
    </div>
  )
}

interface KeyMetricsDashboardProps {
  netWorth: number | null
  homeValue: number | null
  squareFootage: number | null
  purchaseYear: number | null
  householdSize: number | null
  adults: number | null
  children: number | null
  maritalStatus: string | null
}

export const KeyMetricsDashboard: React.FC<KeyMetricsDashboardProps> = ({
  netWorth,
  homeValue,
  squareFootage,
  purchaseYear,
  householdSize,
  adults,
  children,
  maritalStatus,
}) => {
  const netWorthColors = getNetWorthColors(netWorth)

  // Calculate net worth percentile (simplified - could be based on real data)
  const netWorthPercentile = netWorth 
    ? Math.min(100, Math.max(0, (netWorth / 2000000) * 100))
    : 0

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 ${SPACING.GAP.GRID} mb-8`}>
      {/* Net Worth Card */}
      <MetricCard
        title="Net Worth"
        value={netWorth !== null ? formatCompactNumber(netWorth) : 'N/A'}
        subtitle={netWorth !== null ? formatCurrency(netWorth) : undefined}
        icon={<DollarSign className="w-6 h-6" />}
        gradient={netWorthColors.gradient}
        textColor={netWorthColors.text}
        bgColor={netWorthColors.bg}
        borderColor={netWorthColors.border}
        progress={netWorthPercentile}
        trend={netWorth && netWorth > 500000 ? 'up' : netWorth && netWorth > 100000 ? 'neutral' : undefined}
      />

      {/* Home Value Card */}
      <MetricCard
        title="Primary Residence"
        value={homeValue !== null ? formatCompactNumber(homeValue) : 'N/A'}
        subtitle={
          squareFootage 
            ? `${squareFootage.toLocaleString()} sq ft${purchaseYear ? ` • Built ${purchaseYear}` : ''}`
            : purchaseYear 
            ? `Built ${purchaseYear}` 
            : undefined
        }
        icon={<Home className="w-6 h-6" />}
        gradient="linear-gradient(135deg, #3b82f6, #2563eb)"
        textColor="text-blue-600 dark:text-blue-400"
        bgColor="bg-blue-50 dark:bg-blue-900/20"
        borderColor="border-blue-200 dark:border-blue-700"
      />

      {/* Household Card */}
      <MetricCard
        title="Household"
        value={householdSize !== null ? householdSize.toString() : 'N/A'}
        subtitle={
          adults !== null || children !== null
            ? `${adults || 0} adult${adults !== 1 ? 's' : ''}, ${children || 0} child${children !== 1 ? 'ren' : ''}`
            : maritalStatus || undefined
        }
        icon={<Users className="w-6 h-6" />}
        gradient="linear-gradient(135deg, #8b5cf6, #7c3aed)"
        textColor="text-purple-600 dark:text-purple-400"
        bgColor="bg-purple-50 dark:bg-purple-900/20"
        borderColor="border-purple-200 dark:border-purple-700"
      />
    </div>
  )
}

