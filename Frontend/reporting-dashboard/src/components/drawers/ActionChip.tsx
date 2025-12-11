import { LucideIcon } from 'lucide-react'
import { motion } from 'framer-motion'

/**
 * ActionChip - Consistent pill-style action button
 * 
 * Design Rationale:
 * - Compact, recognizable action buttons with icons + labels
 * - Hover state provides tactile feedback (lift + glow)
 * - Used throughout drawers for "Copy", "Center", "Swap", etc.
 * - Glass surface matches drawer aesthetic
 */

interface ActionChipProps {
  icon: LucideIcon
  label: string
  onClick: () => void
  variant?: 'default' | 'primary' | 'danger'
  disabled?: boolean
}

export function ActionChip({ 
  icon: Icon, 
  label, 
  onClick, 
  variant = 'default',
  disabled = false
}: ActionChipProps) {
  
  // Color schemes for different action types
  const variants = {
    default: {
      bg: 'bg-white/5',
      hover: 'hover:bg-white/10',
      border: 'border-white/10',
      hoverBorder: 'hover:border-white/20',
      text: 'text-gray-300',
      hoverText: 'hover:text-white'
    },
    primary: {
      bg: 'bg-blue-500/20',
      hover: 'hover:bg-blue-500/30',
      border: 'border-blue-400/30',
      hoverBorder: 'hover:border-blue-400/50',
      text: 'text-blue-300',
      hoverText: 'hover:text-blue-200'
    },
    danger: {
      bg: 'bg-red-500/20',
      hover: 'hover:bg-red-500/30',
      border: 'border-red-400/30',
      hoverBorder: 'hover:border-red-400/50',
      text: 'text-red-300',
      hoverText: 'hover:text-red-200'
    }
  }

  const colors = variants[variant]

  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02, y: disabled ? 0 : -1 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      onClick={onClick}
      disabled={disabled}
      className={`
        flex items-center gap-1.5 px-2.5 py-1.5
        rounded-lg border backdrop-blur-sm
        text-xs font-medium
        transition-all duration-200
        ${colors.bg} ${colors.hover}
        ${colors.border} ${colors.hoverBorder}
        ${colors.text} ${colors.hoverText}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      style={{
        backdropFilter: 'blur(8px)',
      }}
    >
      <Icon className="w-3 h-3 flex-shrink-0" />
      <span>{label}</span>
    </motion.button>
  )
}

