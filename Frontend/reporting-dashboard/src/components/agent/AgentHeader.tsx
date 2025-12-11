/**
 * agent header component
 * 
 * compact title bar with action toolbar.
 * shows avatar, name, id, location, and small status badges.
 * clean neutral design with cyan accent border.
 */

import React from 'react'
import { MapPin, Calendar, Map, Link2 } from 'lucide-react'
import { getInitials, getPartyColors } from '../../utils/agentUtils'

interface AgentHeaderProps {
  agentId: string
  name: string | null
  city: string | null
  state: string | null
  age: number | null
  gender: string | null
  party: string | null
  simulationId?: string | null
  onViewOnMap?: () => void
  onCopyLink?: () => void
}

export const AgentHeader: React.FC<AgentHeaderProps> = ({
  agentId,
  name,
  city,
  state,
  age,
  gender,
  party,
  simulationId,
  onViewOnMap,
  onCopyLink,
}) => {
  const initials = getInitials(name)
  const location = city && state ? `${city}, ${state}` : city || state || null
  const partyColors = party ? getPartyColors(party) : null

  return (
    <div className="bg-slate-950/50 border-b border-slate-800 border-t-2 border-t-cyan-500/30 px-4 lg:px-6 py-4">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4">
          {/* avatar - neutral circle */}
          <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-sm font-semibold text-slate-300">
            {initials}
          </div>

          {/* name and metadata */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-lg md:text-xl font-semibold text-white truncate">
                {name || 'Unnamed Agent'}
              </h1>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
              <span className="font-mono">{agentId}</span>
              {location && (
                <>
                  <span>•</span>
                  <div className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    <span>{location}</span>
                  </div>
                </>
              )}
              {simulationId && (
                <>
                  <span>•</span>
                  <span>Data as of {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                </>
              )}
            </div>
          </div>

          {/* status badges */}
          <div className="hidden md:flex items-center gap-2">
            {age && (
              <div className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-300 flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{age}{gender ? `, ${gender.charAt(0)}` : ''}</span>
              </div>
            )}
            {party && partyColors && (
              <div className={`px-2 py-1 rounded ${partyColors.bg} text-xs ${partyColors.text}`}>
                {party.length > 12 ? party.substring(0, 12) + '...' : party}
              </div>
            )}
          </div>

          {/* action toolbar */}
          <div className="flex items-center gap-1.5">
            {onViewOnMap && (
              <button
                onClick={onViewOnMap}
                className="p-2 rounded-lg bg-slate-800/50 border border-slate-700 text-slate-300 hover:bg-slate-800 hover:border-slate-600 transition-all"
                title="View on Map"
              >
                <Map className="w-4 h-4" />
              </button>
            )}
            {onCopyLink && (
              <button
                onClick={onCopyLink}
                className="p-2 rounded-lg bg-slate-800/50 border border-slate-700 text-slate-300 hover:bg-slate-800 hover:border-slate-600 transition-all"
                title="Copy Link"
              >
                <Link2 className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

