// Shared formatting utilities for the reporting dashboard
// Keep these pure and UI-agnostic so they can be reused across pages/components.

/**
 * Compact currency formatter used in the financial statements UI.
 *
 * Examples:
 *  - 1_500_000   -> "$1.5M"
 *  - 12_300      -> "$12.3K"
 *  - 950         -> "$950.00"
 *  - -2_000_000  -> "-$2.0M"
 */
export const formatCurrency = (value: number): string => {
  const absValue = Math.abs(value)
  const sign = value < 0 ? '-' : ''

  if (absValue >= 1_000_000_000) {
    return `${sign}$${(absValue / 1_000_000_000).toFixed(1)}B`
  } else if (absValue >= 1_000_000) {
    return `${sign}$${(absValue / 1_000_000).toFixed(1)}M`
  } else if (absValue >= 10_000) {
    return `${sign}$${(absValue / 1_000).toFixed(1)}K`
  } else if (absValue >= 1_000) {
    return `${sign}$${(absValue / 1_000).toFixed(2)}K`
  } else if (absValue >= 100) {
    return `${sign}$${absValue.toFixed(1)}`
  } else {
    return `${sign}$${absValue.toFixed(2)}`
  }
}


