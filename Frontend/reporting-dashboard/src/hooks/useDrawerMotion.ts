import { Variants } from 'framer-motion'

/**
 * useDrawerMotion - Centralized motion primitives for drawer system
 * 
 * Design Rationale:
 * - Single source of truth for all drawer animations
 * - Spring-based motion feels natural and responsive
 * - Staggered reveals create hierarchy without overwhelming
 * 
 * Timing:
 * - Stiffness: 400 - responsive without being jarring
 * - Damping: 40 - smooth deceleration
 * - Stagger: 0.05s between child elements
 */

/**
 * Content section fade-in and slide-up
 * Used for drawer content that appears after the drawer slides in
 */
export const contentVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 20,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 40,
    }
  }
}

/**
 * Staggered children animation
 * Parent container that staggers child reveals
 * Note: No opacity on container - content visible immediately for readability
 */
export const staggerContainerVariants: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.03,
      delayChildren: 0,
    }
  }
}

/**
 * Individual stagger child
 * Each child slides up in sequence with subtle movement
 * Note: Reduced opacity range and minimal y movement for faster perceived load
 */
export const staggerChildVariants: Variants = {
  hidden: {
    opacity: 0.7,
    y: 4,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 600,
      damping: 50,
    }
  }
}

/**
 * Pulse effect for header updates
 * Used when route recalculates or data refreshes
 */
export const pulseVariants: Variants = {
  initial: { scale: 1 },
  pulse: {
    scale: [1, 1.02, 1],
    transition: {
      duration: 0.3,
      times: [0, 0.5, 1],
    }
  }
}

/**
 * Accordion expand/collapse
 * Smooth height animation for collapsible sections
 * Note: Reduced opacity animation for immediate content visibility
 */
export const accordionVariants: Variants = {
  collapsed: {
    height: 0,
    opacity: 0,
    transition: {
      height: {
        type: 'spring',
        stiffness: 500,
        damping: 40,
      },
      opacity: {
        duration: 0.15,
      }
    }
  },
  expanded: {
    height: 'auto',
    opacity: 1,
    transition: {
      height: {
        type: 'spring',
        stiffness: 500,
        damping: 40,
      },
      opacity: {
        duration: 0.15,
        delay: 0,
      }
    }
  }
}

