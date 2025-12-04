// glassMorphism.ts - Glass morphism effect utilities
export const GLASS_EFFECTS = {
  PRIMARY: {
    background: 'rgba(0, 0, 0, 0.5)',
    backdropFilter: 'blur(24px)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
  },
  SECONDARY: {
    background: 'rgba(0, 0, 0, 0.6)',
    backdropFilter: 'blur(24px)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
  },
  MODAL: {
    background: 'rgba(0, 0, 0, 0.7)',
    backdropFilter: 'blur(8px)',
  },
  PANEL: {
    background: 'rgba(0, 0, 0, 0.4)',
    backdropFilter: 'blur(16px)',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
  },
  // Compact controls (buttons, timeline, etc) - consistent styling
  CONTROL: {
    background: 'rgba(20, 22, 28, 0.55)',
    borderColor: 'rgba(255, 255, 255, 0.12)',
    backdropFilter: 'blur(12px) saturate(140%)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
  },
} as const

// Helper function to create glass morphism className
export const createGlassMorphism = (variant: keyof typeof GLASS_EFFECTS = 'PRIMARY') => {
  const effect = GLASS_EFFECTS[variant]
  return `backdrop-blur-xl border border-white/20`
}

// Helper function to create glass morphism style object
export const createGlassMorphismStyle = (variant: keyof typeof GLASS_EFFECTS = 'PRIMARY') => {
  const effect = GLASS_EFFECTS[variant]
  return {
    background: effect.background,
    backdropFilter: effect.backdropFilter,
    boxShadow: effect.boxShadow,
  }
}
