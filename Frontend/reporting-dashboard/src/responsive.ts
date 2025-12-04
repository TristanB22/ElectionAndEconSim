// responsive.ts - Responsive design utilities and patterns
export const RESPONSIVE = {
  // Breakpoint utilities
  BREAKPOINTS: {
    SM: 'sm:',
    MD: 'md:',
    LG: 'lg:',
    XL: 'xl:',
  },
  // Common responsive patterns
  CONTAINER: 'w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8',
  SIDEBAR: 'w-full sm:w-80 lg:w-96',
  GRID: {
    SINGLE: 'grid-cols-1',
    DOUBLE: 'grid-cols-1 md:grid-cols-2',
    TRIPLE: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    QUAD: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  },
  // Responsive spacing
  SPACING: {
    MOBILE: 'p-4',
    TABLET: 'p-6',
    DESKTOP: 'p-8',
  },
  // Responsive text
  TEXT: {
    MOBILE: 'text-sm',
    TABLET: 'text-base',
    DESKTOP: 'text-lg',
  },
  // Responsive sizing
  SIZE: {
    MOBILE: 'w-full',
    TABLET: 'w-full md:w-auto',
    DESKTOP: 'w-full lg:w-auto',
  },
} as const
