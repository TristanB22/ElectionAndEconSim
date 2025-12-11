/**
 * mapAnimations.ts - Centralized map animation configurations
 * 
 * Consistent animation parameters for map interactions:
 * - flyTo transitions (POI/agent/road selection)
 * - Hover effects
 * - Camera movements
 */

export const MAP_ANIMATIONS = {
  // Camera transitions
  FLY_TO: {
    duration: 800,
    essential: true, // This animation is considered essential with respect to prefers-reduced-motion
    zoom: {
      poi: 16,      // Zoom level for POI selection
      agent: 15,    // Zoom level for agent selection
      road: 14,     // Zoom level for road selection
      default: 13   // Default zoom if current zoom is lower
    },
    easing: (t: number) => t * (2 - t), // ease-out quadratic
  },
  
  // Hover effects
  HOVER: {
    debounceMs: 150,      // Delay before showing preview
    fadeInDuration: 200,  // Preview card fade-in
    previewOffsetX: 12,   // Pixels from cursor
    previewOffsetY: 12,
  },
  
  // POI marker animations
  POI_MARKER: {
    hoverScale: 1.2,
    hoverGlowIntensity: 0.6,
    transitionDuration: 200,
  },
  
  // Smooth panning
  EASE_TO: {
    duration: 500,
    easing: (t: number) => t * (2 - t),
  }
} as const

export type MapAnimationConfig = typeof MAP_ANIMATIONS

