import { ReactNode } from 'react'
import { motion, AnimatePresence, type Variants } from 'framer-motion'

/**
 * BaseDrawer - Foundation for all drawer components in AtlasHorizon
 * 
 * Design Philosophy:
 * - Glassmorphic surface language: semi-transparent with blur for depth
 * - Floating panel that doesn't obscure the map completely
 * - Consistent motion system across all drawer types
 * - Modular: can be extended for different content types
 * 
 * Visual Tokens:
 * - Background: rgba(20, 22, 28, 0.55) - dark with 55% opacity
 * - Border: 1px rgba(255,255,255,0.12) - subtle inner stroke
 * - Blur: 12px with 140% saturation for depth
 * - Shadow: layered for floating effect
 * - Border radius: 20px outer, 12px inner elements
 */

interface BaseDrawerProps {
  open: boolean
  onClose: () => void
  children: ReactNode
  width?: string // Default: 560px, can override for different drawer types
  header?: ReactNode
  footer?: ReactNode
  animate?: boolean // Enable/disable animations
}

export function BaseDrawer({ 
  open, 
  onClose, 
  children, 
  width = '560px',
  header,
  footer,
  animate = true
}: BaseDrawerProps) {
  
  // Motion variants for smooth, faster spring-like entrance/exit
  // Tuning: slightly higher stiffness and lower damping for snappier feel
  // Note: No opacity animation - drawer is fully visible during slide for immediate readability
  const drawerVariants: Variants = {
    closed: {
      x: '100%',
      transition: {
        type: 'spring',
        stiffness: 700,
        damping: 36
      }
    },
    open: {
      x: 0,
      transition: {
        type: 'spring',
        stiffness: 700,
        damping: 36
      }
    }
  }

  // Backdrop: slight darkening for focus (10% black overlay)
  const backdropVariants: Variants = {
    closed: { opacity: 0 },
    open: { opacity: 1 }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop - dims map slightly for drawer focus (with blur) */}
          <motion.div
            variants={backdropVariants}
            initial="closed"
            animate="open"
            exit="closed"
            onClick={onClose}
            className="fixed inset-0 bg-black/10 z-40"
            // style={{
            //   backdropFilter: 'blur(4px)',
            //   WebkitBackdropFilter: 'blur(4px)'
            // }}
            transition={{ duration: 0.12 }}
          />

          {/* Main Drawer Panel */}
          <motion.div
            variants={animate ? drawerVariants : undefined}
            initial={animate ? 'closed' : undefined}
            animate={animate ? 'open' : undefined}
            exit={animate ? 'closed' : undefined}
            className="fixed top-0 right-0 h-full z-50 max-w-[90vw]"
            style={{ width }}
          >
            {/* Glass slab container (with blur) */}
            <div 
              className="h-full flex flex-col"
              style={{
                background: 'rgba(20, 22, 28, 0.55)',
                // Add backdrop blur for "glass" effect
                backdropFilter: 'blur(16px)',
                WebkitBackdropFilter: 'blur(16px)',
                borderLeft: '1px solid rgba(255, 255, 255, 0.12)',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35), 0 0 1px rgba(255, 255, 255, 0.05) inset',
              }}
            >
              {/* Optional Header - sticky at top */}
              {header && (
                <div className="flex-shrink-0 border-b border-white/10">
                  {header}
                </div>
              )}

              {/* Scrollable Content Area */}
              <div className="flex-1 overflow-y-auto">
                {children}
              </div>

              {/* Optional Footer - sticky at bottom */}
              {footer && (
                <div className="flex-shrink-0 border-t border-white/10">
                  {footer}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

