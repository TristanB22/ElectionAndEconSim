/**
 * mapControls.ts - Shared styling constants for map control components
 * 
 * Ensures visual consistency between Location Filter, Timeline, and other map overlays
 */

export const MAP_CONTROL_STYLES = {
  // Glassmorphism background (matching Location Filter)
  background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.6) 0%, rgba(0, 0, 0, 0.5) 100%)',
  
  // Border and effects
  border: 'border border-white/10',
  backdropBlur: 'backdrop-blur-2xl',
  shadow: 'shadow-2xl',
  borderRadius: 'rounded-2xl',
  
  // Typography hierarchy - consistent across all controls
  text: {
    // Primary title/label
    title: 'text-xs font-semibold text-white/90 tracking-wide',
    
    // Secondary info/subtitle
    subtitle: 'text-xs text-white/50 font-mono',
    
    // Badge/pill elements
    badge: 'text-[10px] sm:text-[11px] px-2 py-0.5 rounded-md backdrop-blur-sm border border-white/20 font-mono',
    badgeBg: 'bg-white/10',
    badgeText: 'text-white/80',
    
    // Time displays
    timeDisplay: 'text-[10px] sm:text-[11px] text-white/70',
    timeDisplayLarge: 'text-[10px] sm:text-[11px] text-white/70',
  },
  
  // Interactive elements
  button: {
    base: 'transition-all duration-200',
    hover: 'hover:bg-white/10',
    active: 'active:scale-95',
    disabled: 'disabled:opacity-50 disabled:cursor-not-allowed',
  },
  
  // Spacing system
  padding: {
    compact: 'px-3 sm:px-4 py-2',
    standard: 'px-4 py-3',
    comfortable: 'px-5 py-4',
  },
  
  gap: {
    tight: 'gap-1.5 sm:gap-2',
    standard: 'gap-2 sm:gap-3',
    comfortable: 'gap-3 sm:gap-4',
  },
  
  // Animations
  transition: 'transition-all duration-300 ease-out',
  
  // Active indicators (pulsing dots, etc)
  activeDot: 'w-2 h-2 rounded-full bg-blue-400 animate-pulse shadow-lg shadow-blue-500/50',
  
  // Z-index layers
  zIndex: {
    base: 'z-30',
    elevated: 'z-40',
  },
} as const

/**
 * Helper function to create consistent glassmorphism style object
 */
export function createMapControlStyle(variant: 'primary' | 'secondary' = 'primary') {
  return {
    background: MAP_CONTROL_STYLES.background,
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
  }
}

/**
 * Consistent layout positioning for bottom controls
 */
export const BOTTOM_CONTROL_LAYOUT = {
  // Vertical position from bottom
  bottom: 'bottom-6',
  
  // Common positioning classes
  leftAligned: 'left-6',
  rightAligned: 'right-6',
  centered: 'left-1/2 -translate-x-1/2',
  
  // Max widths for different control types
  maxWidth: {
    filter: 'max-w-[340px]',
    timeline: 'max-w-[1000px]',
    compact: 'max-w-md',
  },
} as const









