import { LucideIcon } from 'lucide-react'
import { motion } from 'framer-motion'
import { ReactNode } from 'react'

/**
 * MetricCard - Display key metrics in glassmorphic cards
 * 
 * Design Rationale:
 * - Prominent display for important data (distance, duration, etc.)
 * - Gradient background provides visual hierarchy
 * - Hover interaction adds depth perception
 * - Icon + label + value structure is scannable
 * 
 * Layout: 12px border radius (inner element standard)
 * Padding: 20px (2.5 * 8px grid)
 */

interface MetricCardProps {
  icon: LucideIcon
  label: string
  value: ReactNode
  subtitle?: string
  variant?: 'blue' | 'green' | 'orange' | 'purple' | 'gray'
}

export function MetricCard({ 
  icon: Icon, 
  label, 
  value, 
  subtitle,
  variant = 'blue'
}: MetricCardProps) {
  
  // Color schemes for different metric types
  // Using subtle gradients for depth without overwhelming
  const variants = {
    blue: {
      bg: 'from-blue-950/40 to-blue-900/20',
      border: 'border-blue-400/30',
      hoverBorder: 'hover:border-blue-400/50',
      icon: 'text-blue-400',
      label: 'text-blue-300',
      glow: 'from-blue-500/5'
    },
    green: {
      bg: 'from-green-950/40 to-green-900/20',
      border: 'border-green-400/30',
      hoverBorder: 'hover:border-green-400/50',
      icon: 'text-green-400',
      label: 'text-green-300',
      glow: 'from-green-500/5'
    },
    orange: {
      bg: 'from-orange-950/40 to-orange-900/20',
      border: 'border-orange-400/30',
      hoverBorder: 'hover:border-orange-400/50',
      icon: 'text-orange-400',
      label: 'text-orange-300',
      glow: 'from-orange-500/5'
    },
    purple: {
      bg: 'from-purple-950/40 to-purple-900/20',
      border: 'border-purple-400/30',
      hoverBorder: 'hover:border-purple-400/50',
      icon: 'text-purple-400',
      label: 'text-purple-300',
      glow: 'from-purple-500/5'
    },
    gray: {
      bg: 'from-gray-800/40 to-gray-900/20',
      border: 'border-gray-400/30',
      hoverBorder: 'hover:border-gray-400/50',
      icon: 'text-gray-400',
      label: 'text-gray-300',
      glow: 'from-gray-500/5'
    }
  }

  const colors = variants[variant]

  return (
    <motion.div
      whileHover={{ scale: 1.01, y: -2 }}
      className={`
        relative group overflow-hidden
        rounded-xl border backdrop-blur-sm
        p-5
        transition-all duration-200
        bg-gradient-to-br ${colors.bg}
        ${colors.border} ${colors.hoverBorder}
      `}
      style={{
        backdropFilter: 'blur(8px)',
      }}
    >
      {/* Hover glow effect - subtle depth on interaction */}
      <div className={`
        absolute inset-0 
        bg-gradient-to-br ${colors.glow} to-transparent
        opacity-0 group-hover:opacity-100
        transition-opacity duration-200
      `} />

      {/* Content */}
      <div className="relative">
        {/* Icon + Label */}
        <div className="flex items-center gap-2 mb-2">
          <Icon className={`w-4 h-4 ${colors.icon}`} />
          <span className={`text-xs font-semibold uppercase tracking-wider ${colors.label}`}>
            {label}
          </span>
        </div>

        {/* Value */}
        <div className="text-3xl font-bold text-white">
          {value}
        </div>

        {/* Optional subtitle */}
        {subtitle && (
          <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
        )}
      </div>
    </motion.div>
  )
}

