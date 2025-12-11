// Centralized color system for the World_Sim dashboard
// This file makes it easy to change colors across the entire app

export const colors = {
  // Primary brand colors
  primary: {
    50: 'bg-indigo-50',
    100: 'bg-indigo-100',
    500: 'bg-indigo-500',
    600: 'bg-indigo-600',
    700: 'bg-indigo-700',
    800: 'bg-indigo-800',
    900: 'bg-indigo-900',
    text: {
      50: 'text-indigo-50',
      100: 'text-indigo-100',
      500: 'text-indigo-500',
      600: 'text-indigo-600',
      700: 'text-indigo-700',
      800: 'text-indigo-800',
      900: 'text-indigo-900',
    },
    border: {
      200: 'border-indigo-200',
      300: 'border-indigo-300',
      400: 'border-indigo-400',
      500: 'border-indigo-500',
      600: 'border-indigo-600',
      700: 'border-indigo-700',
      800: 'border-indigo-800',
    }
  },

  // Secondary colors
  secondary: {
    50: 'bg-slate-50',
    100: 'bg-slate-100',
    200: 'bg-slate-200',
    300: 'bg-slate-300',
    400: 'bg-slate-400',
    500: 'bg-slate-500',
    600: 'bg-slate-600',
    700: 'bg-slate-700',
    800: 'bg-slate-800',
    900: 'bg-slate-900',
    text: {
      50: 'text-slate-50',
      100: 'text-slate-100',
      200: 'text-slate-200',
      300: 'text-slate-300',
      400: 'text-slate-400',
      500: 'text-slate-500',
      600: 'text-slate-600',
      700: 'text-slate-700',
      800: 'text-slate-800',
      900: 'text-slate-900',
    },
    border: {
      200: 'border-slate-200',
      300: 'border-slate-300',
      400: 'border-slate-400',
      500: 'border-slate-500',
      600: 'border-slate-600',
      700: 'border-slate-700',
      800: 'border-slate-800',
    }
  },

  // Success colors
  success: {
    50: 'bg-emerald-50',
    100: 'bg-emerald-100',
    500: 'bg-emerald-500',
    600: 'bg-emerald-600',
    700: 'bg-emerald-700',
    800: 'bg-emerald-800',
    900: 'bg-emerald-900',
    text: {
      50: 'text-emerald-50',
      100: 'text-emerald-100',
      500: 'text-emerald-500',
      600: 'text-emerald-600',
      700: 'text-emerald-700',
      800: 'text-emerald-800',
      900: 'text-emerald-900',
    }
  },

  // Warning colors
  warning: {
    50: 'bg-amber-50',
    100: 'bg-amber-100',
    500: 'bg-amber-500',
    600: 'bg-amber-600',
    700: 'bg-amber-700',
    800: 'bg-amber-800',
    900: 'bg-amber-900',
    text: {
      50: 'text-amber-50',
      100: 'text-amber-100',
      500: 'text-amber-500',
      600: 'text-amber-600',
      700: 'text-amber-700',
      800: 'text-amber-800',
      900: 'text-amber-900',
    }
  },

  // Error colors
  error: {
    50: 'bg-rose-50',
    100: 'bg-rose-100',
    500: 'bg-rose-500',
    600: 'bg-rose-600',
    700: 'bg-rose-700',
    800: 'bg-rose-800',
    900: 'bg-rose-900',
    text: {
      50: 'text-rose-50',
      100: 'text-rose-100',
      500: 'text-rose-500',
      600: 'text-rose-600',
      700: 'text-rose-700',
      800: 'text-rose-800',
      900: 'text-rose-900',
    }
  },

  // Info colors
  info: {
    50: 'bg-sky-50',
    100: 'bg-sky-100',
    500: 'bg-sky-500',
    600: 'bg-sky-600',
    700: 'bg-sky-700',
    800: 'bg-sky-800',
    900: 'bg-sky-900',
    text: {
      50: 'text-sky-50',
      100: 'text-sky-100',
      500: 'text-sky-500',
      600: 'text-sky-600',
      700: 'text-sky-700',
      800: 'text-sky-800',
      900: 'text-sky-900',
    }
  },

  // Neutral colors
  neutral: {
    50: 'bg-gray-50',
    100: 'bg-gray-100',
    200: 'bg-gray-200',
    300: 'bg-gray-300',
    400: 'bg-gray-400',
    500: 'bg-gray-500',
    600: 'bg-gray-600',
    700: 'bg-gray-700',
    800: 'bg-gray-800',
    900: 'bg-gray-900',
    text: {
      50: 'text-gray-50',
      100: 'text-gray-100',
      200: 'text-gray-200',
      300: 'text-gray-300',
      400: 'text-gray-400',
      500: 'text-gray-500',
      600: 'text-gray-600',
      700: 'text-gray-700',
      800: 'text-gray-800',
      900: 'text-gray-900',
    },
    border: {
      200: 'border-gray-200',
      300: 'border-gray-300',
      400: 'border-gray-400',
      500: 'border-gray-500',
      600: 'border-gray-600',
      700: 'border-gray-700',
      800: 'border-gray-800',
    }
  },

  // White/Black
  white: 'bg-white',
  black: 'bg-black',
  transparent: 'bg-transparent',
  
  // Text colors
  text: {
    white: 'text-white',
    black: 'text-black',
    primary: 'text-gray-900 dark:text-white',
    secondary: 'text-gray-600 dark:text-gray-300',
    muted: 'text-gray-500 dark:text-gray-400',
  },

  // Background colors
  background: {
    primary: 'bg-transparent',
    secondary: 'bg-white/5 dark:bg-white/5',
    tertiary: 'bg-white/10 dark:bg-white/10',
  },

  // Border colors mapped to glass tokens
  border: {
    primary: 'border-soft',
    secondary: 'border-soft',
    accent: 'border-highlight',
  },

  // Surface colors (legacy tokens kept for compatibility)
  surface: {
    primary: 'surface-level-1',
    secondary: 'surface-level-2',
    tertiary: 'surface-level-3',
    hover: 'hover:bg-white/10',
  },

  // Interactive states
  interactive: {
    hover: {
      background: 'hover:bg-gray-50 dark:hover:bg-gray-800/50',
      text: 'hover:text-gray-700 dark:hover:text-gray-300',
      border: 'hover:border-gray-300 dark:hover:border-gray-600',
    },
    active: {
      background: 'active:bg-gray-100 dark:active:bg-gray-700',
      scale: 'active:scale-95',
    },
  },

  // Glass morphism colors
  glass: {
    text: 'text-white',
    background: 'bg-white/10 hover:bg-white/20',
    primary: {
      background: 'rgba(18, 32, 52, 0.65)',
      backdropFilter: 'blur(16px)',
      boxShadow: '0 18px 36px rgba(7, 13, 24, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.12)',
    },
    secondary: {
      background: 'rgba(23, 40, 62, 0.55)',
      backdropFilter: 'blur(18px)',
      boxShadow: '0 24px 48px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
    },
    modal: {
      background: 'rgba(5, 9, 15, 0.75)',
      backdropFilter: 'blur(22px)',
    },
  },
}

// Common color combinations for specific use cases
export const colorSchemes = {
  // Button schemes
  button: {
    primary: {
      base: `${colors.primary[600]} hover:${colors.primary[700]} text-white border ${colors.primary.border[600]}`,
      outline: `bg-white dark:${colors.background.secondary} hover:${colors.primary[50]} dark:hover:${colors.primary[900]} text-${colors.primary[600]} border ${colors.primary.border[600]}`
    },
    secondary: {
      base: `${colors.secondary[600]} hover:${colors.secondary[700]} text-white border ${colors.secondary.border[600]}`,
      outline: `bg-white dark:${colors.background.secondary} hover:${colors.secondary[50]} dark:hover:${colors.secondary[900]} text-${colors.secondary[600]} border ${colors.secondary.border[600]}`
    }
  },

  // Card schemes
  card: {
    primary: `surface-level-2`,
    secondary: `surface-level-1`,
  },

  // Input schemes
  input: {
    base: `${colors.border.secondary} ${colors.background.primary} focus:ring-2 focus:ring-${colors.primary[500]} focus:border-${colors.primary[500]}`,
  }
}

// Dark mode specific overrides
export const darkMode = {
  // Override colors for dark mode if needed
  card: {
    primary: 'bg-slate-900 border-slate-700',
    secondary: 'bg-slate-800 border-slate-600',
  },
  
  button: {
    primary: {
      outline: 'bg-slate-800 hover:bg-slate-700 text-indigo-400 border-indigo-600',
    }
  }
}

// Agent-specific colors
export const agentColors = {
  marker: {
    glow: 'rgba(96,165,250,0.55)', // blue glow
    fill: '#3b82f6',               // blue-500 core body
    ring: '#2563eb',               // blue-600 outer ring
    core: '#dbeafe',               // blue-100 inner highlight
    stroke: '#1e3a8a',             // blue-900 stroke accent
    hover: '#60a5fa',              // blue-400 hover halo
    selected: '#a855f7',           // purple-500 selected state
    selectedGlow: 'rgba(168,85,247,0.55)', // purple glow halo
  },
  cluster: {
    fill: '#93c5fd',        // blue-300 - lighter for clusters
    stroke: '#1e40af',      // blue-800
    text: '#1e3a8a',        // blue-900 - cluster count text
  },
}

// Toast notification colors - centralized configuration for consistent styling
export const toastColors = {
  success: {
    background: 'rgba(16, 185, 129, 0.95)',  // green-500 with opacity
    border: '#10b981',                        // green-500
    text: '#ffffff',
  },
  warning: {
    background: 'rgba(245, 158, 11, 0.95)',  // amber-500 with opacity
    border: '#f59e0b',                        // amber-500
    text: '#ffffff',
  },
  error: {
    background: 'rgba(239, 68, 68, 0.95)',   // red-500 with opacity
    border: '#ef4444',                        // red-500
    text: '#ffffff',
  },
  info: {
    background: 'rgba(59, 130, 246, 0.95)',  // blue-500 with opacity
    border: '#3b82f6',                        // blue-500
    text: '#ffffff',
  },
}

// POI category colors - matching drawer tag color families (using vibrant -500/-600 variants for map visibility)
export const poiCategoryColors: Record<string, { color: string; label: string }> = {
  amenity:    { color: '#3b82f6', label: 'Amenity' },        // blue-500 - matches drawer blue color family
  shop:       { color: '#22c55e', label: 'Shop' },           // green-500 - matches drawer green color family
  tourism:    { color: '#f59e0b', label: 'Tourism' },       // amber-500 - matches drawer amber color family
  leisure:    { color: '#a855f7', label: 'Leisure' },       // purple-500 - matches drawer purple color family
  healthcare: { color: '#ef4444', label: 'Healthcare' },    // red-500 - matches drawer red color family
  office:     { color: '#06b6d4', label: 'Office' },          // cyan-500 - matches drawer cyan color family
  craft:      { color: '#84cc16', label: 'Craft' },         // lime-500 - matches drawer lime color family
  religion:   { color: '#f97316', label: 'Religion' },      // orange-500 - matches drawer orange color family
  historic:   { color: '#6366f1', label: 'Historic' },       // indigo-500 - matches drawer indigo color family
  building:   { color: '#eab308', label: 'Building' },       // yellow-500 - matches drawer yellow color family
  place:      { color: '#14b8a6', label: 'Place' },          // teal-500 - matches drawer teal color family
  other:      { color: '#6b7280', label: 'Other' },          // gray-500 - matches drawer gray color family
}

// Agent profile colors - for net worth, party affiliation, etc.
export const agentProfileColors = {
  netWorth: {
    high: {
      gradient: 'linear-gradient(135deg, #10b981, #059669)',
      text: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-900/20',
      border: 'border-emerald-200 dark:border-emerald-700',
      ring: '#10b981',
    },
    medium: {
      gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)',
      text: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-700',
      ring: '#3b82f6',
    },
    low: {
      gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
      text: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-900/20',
      border: 'border-amber-200 dark:border-amber-700',
      ring: '#f59e0b',
    },
  },
  party: {
    democrat: {
      color: '#3b82f6',
      text: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-100 dark:bg-blue-900/30',
    },
    republican: {
      color: '#ef4444',
      text: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-100 dark:bg-red-900/30',
    },
    independent: {
      color: '#8b5cf6',
      text: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-100 dark:bg-purple-900/30',
    },
    other: {
      color: '#6b7280',
      text: 'text-gray-600 dark:text-gray-400',
      bg: 'bg-gray-100 dark:bg-gray-900/30',
    },
  },
  status: {
    success: {
      text: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-100 dark:bg-emerald-900/30',
    },
    pending: {
      text: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-100 dark:bg-amber-900/30',
    },
    failed: {
      text: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-100 dark:bg-red-900/30',
    },
  },
}

export const LAYERS = {
  LEVEL_0: 'layer-0',
  LEVEL_1: 'surface-level-1',
  LEVEL_2: 'surface-level-2',
  LEVEL_3: 'surface-level-3 border-highlight',
} as const

export const SHADOWS = {
  SOFT: 'shadow-soft-layer',
  FLOATING: 'shadow-floating-layer',
} as const

export const BLUR = {
  SOFT: 'backdrop-blur-md',
  MEDIUM: 'backdrop-blur-lg',
  STRONG: 'backdrop-blur-xl',
} as const
