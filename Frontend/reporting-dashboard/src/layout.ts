// layout.ts - Centralized layout dimensions and responsive values
export const LAYOUT = {
  // Viewport-based dimensions
  MODAL: {
    MAX_HEIGHT: '90vh',
    MAX_HEIGHT_COMPACT: '85vh',
    MAX_HEIGHT_MOBILE: '95vh',
    MAX_WIDTH: '95vw',
    MAX_WIDTH_DESKTOP: '90vw',
    SCROLL_HEIGHT: 'calc(90vh - 180px)',
  },
  // Component sizes
  SIDEBAR: {
    WIDTH: '400px', // responsive: '300px' on mobile, '450px' on desktop
    COMPACT_WIDTH: '320px',
  },
  // Category panel
  CATEGORY_PANEL: {
    WIDTH: '320px',
    HEIGHT: 'auto',
    MAX_HEIGHT: '70vh',
  },
  // Map controls
  CONTROLS: {
    TOP_RIGHT: {
      TOP: '1rem',
      RIGHT: '1rem',
    },
    BOTTOM_LEFT: {
      BOTTOM: '1rem',
      LEFT: '1rem',
    },
  },
  // Map page layout
  MAP_PAGE: {
    PADDING_X: '1rem',      // Horizontal padding from screen edges
    PADDING_Y: '0.75rem',   // Vertical padding
    LEFT_NAV_OFFSET: '5rem', // Space for left navigation (increased for page selector)
  },
  // Drawer dimensions
  DRAWER: {
    WIDTH: 520, // Width in pixels (matches EntityDetailDrawer)
  },
  // Grid layouts
  GRID: {
    SINGLE: 'grid-cols-1',
    DOUBLE: 'grid-cols-1 md:grid-cols-2',
    TRIPLE: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
  },
  // Agent visualization
  AGENT: {
    MARKER_SIZE: 8,           // Circle radius in pixels
    MIN_ZOOM: 8,              // Minimum zoom level to show agents
    CLUSTER_RADIUS: 50,       // Clustering radius in pixels
  },
  // Simulation timeline
  TIMELINE: {
    HEIGHT: '66px',           // Timeline panel height aligned with location filter header
    BOTTOM_OFFSET: '1.5rem',  // Match bottom-6 spacing of location filter panel
    MAX_WIDTH: '800px',       // Maximum width
  },
} as const
