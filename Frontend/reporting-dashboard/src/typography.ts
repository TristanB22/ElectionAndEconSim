// typography.ts - Centralized typography system
export const TYPOGRAPHY = {
  // Text sizes (responsive)
  SIZE: {
    XS: 'text-[11px] sm:text-xs tracking-[0.08em]',
    SM: 'text-sm sm:text-[15px]',
    BASE: 'text-base sm:text-lg',
    LG: 'text-lg sm:text-xl',
    XL: 'text-xl sm:text-2xl',
    HEADING: 'text-2xl sm:text-3xl font-semibold',
  },
  // Font weights
  WEIGHT: {
    NORMAL: 'font-normal',
    MEDIUM: 'font-medium',
    SEMIBOLD: 'font-semibold',
    BOLD: 'font-bold',
  },
  // Text styles
  STYLES: {
    MONO: 'font-mono tracking-tight',
    SANS: 'text-geometric',
    HEADING: 'text-geometric font-semibold tracking-tight',
    BODY: 'text-geometric leading-relaxed',
    CAPTION: 'text-xs text-gray-400 uppercase tracking-[0.16em]',
  },
  // Text colors (responsive)
  COLORS: {
    PRIMARY: 'text-slate-100',
    SECONDARY: 'text-slate-300/80',
    MUTED: 'text-slate-400/70',
    ACCENT: 'text-sky-400',
    SUCCESS: 'text-emerald-600 dark:text-emerald-400',
    WARNING: 'text-amber-600 dark:text-amber-400',
    ERROR: 'text-red-600 dark:text-red-400',
  },
} as const
