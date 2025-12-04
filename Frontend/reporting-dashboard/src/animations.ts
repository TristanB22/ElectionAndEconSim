// animations.ts - Centralized animation and transition constants
export const ANIMATIONS = {
  // Timing
  DURATION: {
    FAST: 'duration-120',
    NORMAL: 'duration-150',
    SLOW: 'duration-200',
    SLOWER: 'duration-300',
  },
  // Common patterns
  TRANSITIONS: {
    DEFAULT: 'transition-all duration-150 ease-out',
    HOVER: 'transition-colors duration-150 ease-out',
    MODAL: 'transition-all duration-200 ease-out',
    BUTTON: 'transition-all duration-140 ease-out',
    CARD: 'transition-all duration-160 ease-out',
    PANEL: 'transition-all duration-200 ease-out',
  },
  // Hover effects
  HOVER: {
    LIFT: 'hover:scale-105 hover:shadow-lg',
    FADE: 'hover:opacity-80',
    SLIDE: 'hover:translate-x-1',
    GLOW: 'hover:shadow-lg hover:shadow-current/25',
  },
  // Animation classes
  ANIMATE: {
    FADE_IN: 'animate-fade-in',
    SLIDE_UP: 'animate-slide-up',
    BOUNCE: 'animate-bounce',
    PULSE: 'animate-pulse',
  },
} as const
