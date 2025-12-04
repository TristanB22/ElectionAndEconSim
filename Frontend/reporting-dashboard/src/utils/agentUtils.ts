/**
 * Agent Profile Utility Functions
 * 
 * Helper functions for formatting and processing agent data
 */

import { agentProfileColors } from '../styles/colors'

/**
 * Format currency values
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

/**
 * Format large numbers with K/M/B suffixes
 */
export function formatCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(value)
}

/**
 * Format percentage values
 */
export function formatPercentage(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value / 100)
}

/**
 * Determine net worth tier based on value
 */
export function getNetWorthTier(netWorth: number | null | undefined): 'high' | 'medium' | 'low' {
  if (netWorth === null || netWorth === undefined) return 'low'
  
  if (netWorth >= 1000000) return 'high'      // $1M+
  if (netWorth >= 250000) return 'medium'     // $250K - $1M
  return 'low'                                 // < $250K
}

/**
 * Get colors for net worth tier
 */
export function getNetWorthColors(netWorth: number | null | undefined) {
  const tier = getNetWorthTier(netWorth)
  return agentProfileColors.netWorth[tier]
}

/**
 * Normalize party name for color lookup
 */
export function normalizePartyName(party: string | null | undefined): 'democrat' | 'republican' | 'independent' | 'other' {
  if (!party) return 'other'
  
  const normalized = party.toLowerCase()
  if (normalized.includes('democrat') || normalized.includes('dem')) return 'democrat'
  if (normalized.includes('republican') || normalized.includes('rep')) return 'republican'
  if (normalized.includes('independent') || normalized.includes('ind')) return 'independent'
  return 'other'
}

/**
 * Get colors for party affiliation
 */
export function getPartyColors(party: string | null | undefined) {
  const normalized = normalizePartyName(party)
  return agentProfileColors.party[normalized]
}

/**
 * Get status colors
 */
export function getStatusColors(status: string | null | undefined) {
  if (!status) return agentProfileColors.status.pending
  
  const normalized = status.toLowerCase()
  if (normalized === 'success' || normalized === 'completed') return agentProfileColors.status.success
  if (normalized === 'failed' || normalized === 'error') return agentProfileColors.status.failed
  return agentProfileColors.status.pending
}

/**
 * Calculate age from birthdate or return provided age
 */
export function calculateAge(birthdate: string | null | undefined, providedAge: number | null | undefined): number | null {
  if (providedAge) return providedAge
  if (!birthdate) return null
  
  try {
    const birth = new Date(birthdate)
    const today = new Date()
    let age = today.getFullYear() - birth.getFullYear()
    const monthDiff = today.getMonth() - birth.getMonth()
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--
    }
    
    return age
  } catch {
    return null
  }
}

/**
 * Format address into single line
 */
export function formatAddress(
  address: string | null | undefined,
  city: string | null | undefined,
  state: string | null | undefined,
  zip: string | null | undefined
): string {
  const parts = [address, city, state, zip].filter(Boolean)
  return parts.length > 0 ? parts.join(', ') : 'N/A'
}

/**
 * Get initials from name
 */
export function getInitials(name: string | null | undefined): string {
  if (!name) return '?'
  
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase()
  
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string | null | undefined, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

/**
 * Format date to locale string
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return 'N/A'
  
  try {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return 'Invalid Date'
  }
}

/**
 * Format datetime to locale string
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return 'N/A'
  
  try {
    return new Date(date).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return 'Invalid Date'
  }
}

/**
 * Get relative time string (e.g., "2 hours ago")
 */
export function getRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return 'N/A'
  
  try {
    const now = new Date()
    const then = new Date(date)
    const diffMs = now.getTime() - then.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)
    const diffHour = Math.floor(diffMin / 60)
    const diffDay = Math.floor(diffHour / 24)
    
    if (diffSec < 60) return 'just now'
    if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`
    if (diffHour < 24) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`
    if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`
    
    return formatDate(date)
  } catch {
    return 'Invalid Date'
  }
}

