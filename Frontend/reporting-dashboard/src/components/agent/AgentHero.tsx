/**
 * Agent Hero Component
 * 
 * Displays agent identity and key stats in a glassmorphic banner
 */

import React from 'react'
import { User, MapPin, Users, Calendar, DollarSign } from 'lucide-react'
import { SPACING } from '../../spacing'
import { TYPOGRAPHY } from '../../typography'
import { ANIMATIONS } from '../../animations'
import { 
  formatCurrency, 
  formatCompactNumber, 
  getNetWorthColors, 
  getPartyColors, 
  getInitials 
} from '../../utils/agentUtils'

interface AgentHeroProps {
  agentId: string
  name: string | null
  age: number | null
  gender: string | null
  city: string | null
  state: string | null
  netWorth: number | null
  householdSize: number | null
  party: string | null
}

export const AgentHero: React.FC<AgentHeroProps> = ({
  agentId,
  name,
  age,
  gender,
  city,
  state,
  netWorth,
  householdSize,
  party,
}) => {
  const netWorthColors = getNetWorthColors(netWorth)
  const partyColors = getPartyColors(party)
  const initials = getInitials(name)
  const location = city && state ? `${city}, ${state}` : city || state || 'Unknown'

  return (
    <div 
      className={`relative overflow-hidden ${SPACING.BORDER.RADIUS.LG} border border-white/10 mb-8 ${ANIMATIONS.TRANSITIONS.DEFAULT}`}
      style={{
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(99, 102, 241, 0.04))',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      }}
    >
      {/* Background Pattern */}
      <div 
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: `radial-gradient(circle at 2px 2px, rgba(255, 255, 255, 0.15) 1px, transparent 0)`,
          backgroundSize: '32px 32px',
        }}
      />

      <div className={`relative ${SPACING.PADDING.LG} flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6`}>
        {/* Left Side - Identity */}
        <div className="flex items-center gap-4">
          {/* Avatar with colored ring */}
          <div className="relative">
            <div 
              className="w-20 h-20 rounded-full flex items-center justify-center text-2xl font-bold text-white"
              style={{
                background: netWorthColors.gradient,
                boxShadow: `0 0 0 4px ${netWorthColors.ring}20, 0 8px 16px rgba(0, 0, 0, 0.2)`,
              }}
            >
              {initials}
            </div>
            {/* Status indicator */}
            <div 
              className="absolute bottom-0 right-0 w-6 h-6 bg-emerald-500 rounded-full border-4 border-white dark:border-gray-900"
              title="Active"
            />
          </div>

          {/* Name and ID */}
          <div>
            <h1 className={`${TYPOGRAPHY.SIZE.XL} ${TYPOGRAPHY.WEIGHT.BOLD} ${TYPOGRAPHY.COLORS.PRIMARY} mb-1`}>
              {name || 'Unnamed Agent'}
            </h1>
            <div className="flex items-center gap-3 text-sm">
              <span className={`${TYPOGRAPHY.STYLES.MONO} ${TYPOGRAPHY.COLORS.MUTED}`}>
                ID: {agentId}
              </span>
              {location !== 'Unknown' && (
                <>
                  <span className={TYPOGRAPHY.COLORS.MUTED}>•</span>
                  <div className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    <span className={TYPOGRAPHY.COLORS.SECONDARY}>{location}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right Side - Quick Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          {/* Age & Gender */}
          {(age || gender) && (
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 mb-1">
                <User className="w-4 h-4 text-blue-500" />
              </div>
              <div className={`${TYPOGRAPHY.SIZE.LG} ${TYPOGRAPHY.WEIGHT.BOLD} ${TYPOGRAPHY.COLORS.PRIMARY}`}>
                {age || '?'}
              </div>
              <div className={`${TYPOGRAPHY.SIZE.XS} ${TYPOGRAPHY.COLORS.MUTED}`}>
                {gender || 'Unknown'}
              </div>
            </div>
          )}

          {/* Net Worth */}
          {netWorth !== null && (
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 mb-1">
                <DollarSign className={`w-4 h-4 ${netWorthColors.text}`} />
              </div>
              <div className={`${TYPOGRAPHY.SIZE.LG} ${TYPOGRAPHY.WEIGHT.BOLD} ${netWorthColors.text}`}>
                {formatCompactNumber(netWorth)}
              </div>
              <div className={`${TYPOGRAPHY.SIZE.XS} ${TYPOGRAPHY.COLORS.MUTED}`}>
                Net Worth
              </div>
            </div>
          )}

          {/* Household Size */}
          {householdSize !== null && (
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 mb-1">
                <Users className="w-4 h-4 text-purple-500" />
              </div>
              <div className={`${TYPOGRAPHY.SIZE.LG} ${TYPOGRAPHY.WEIGHT.BOLD} ${TYPOGRAPHY.COLORS.PRIMARY}`}>
                {householdSize}
              </div>
              <div className={`${TYPOGRAPHY.SIZE.XS} ${TYPOGRAPHY.COLORS.MUTED}`}>
                Household
              </div>
            </div>
          )}

          {/* Party Affiliation */}
          {party && (
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 mb-1">
                <Calendar className={`w-4 h-4 ${partyColors.text}`} />
              </div>
              <div className={`${TYPOGRAPHY.SIZE.SM} ${TYPOGRAPHY.WEIGHT.SEMIBOLD} ${partyColors.text}`}>
                {party.length > 12 ? party.substring(0, 12) + '...' : party}
              </div>
              <div className={`${TYPOGRAPHY.SIZE.XS} ${TYPOGRAPHY.COLORS.MUTED}`}>
                Party
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

