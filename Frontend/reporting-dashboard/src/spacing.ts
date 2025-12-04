// spacing.ts - Centralized spacing constants
export const SPACING = {
  // Padding
  PADDING: {
    XS: 'p-2',
    SM: 'p-4',
    MD: 'p-5',
    LG: 'p-6',
    XL: 'p-8',
    CARD: 'p-5',
    MODAL: 'p-6 lg:p-8',
  },
  // Margins
  MARGIN: {
    XS: 'm-2',
    SM: 'm-4',
    MD: 'm-6',
    LG: 'm-8',
    XL: 'm-10',
    AUTO: 'mx-auto',
  },
  // Gaps
  GAP: {
    XS: 'gap-1.5',
    SM: 'gap-2.5',
    MD: 'gap-4',
    LG: 'gap-6',
    XL: 'gap-8',
    CARD: 'gap-4',
    GRID: 'gap-6',
  },
  // Borders
  BORDER: {
    RADIUS: {
      SM: 'radius-sm',
      MD: 'radius-md',
      LG: 'radius-lg',
      CARD: 'radius-lg',
      MODAL: 'radius-lg',
      BUTTON: 'radius-sm',
      INPUT: 'radius-sm',
    },
    WIDTH: {
      DEFAULT: 'border',
      THIN: 'border-2',
      THICK: 'border-4',
    },
  },
} as const
