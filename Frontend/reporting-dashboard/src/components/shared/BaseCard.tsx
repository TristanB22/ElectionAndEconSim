import React from 'react'
import { SPACING } from '../../spacing'

export interface BaseCardProps {
  children: React.ReactNode
  className?: string
  variant?: 'default' | 'glass' | 'minimal'
  padding?: keyof typeof SPACING.PADDING
  radius?: keyof typeof SPACING.BORDER.RADIUS
}

export const BaseCard = ({
  children,
  className = '',
  variant = 'default',
  padding = 'MD',
  radius = 'CARD',
}: BaseCardProps) => {
  const variants = {
    default: 'bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700',
    glass: 'backdrop-blur-xl border border-white/20 rounded-xl shadow-xl',
    minimal: 'bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700',
  }

  const paddingClass = SPACING.PADDING[padding]
  const radiusClass = SPACING.BORDER.RADIUS[radius]

  return (
    <div className={`${variants[variant]} ${paddingClass} ${radiusClass} ${className}`}>
      {children}
    </div>
  )
}
