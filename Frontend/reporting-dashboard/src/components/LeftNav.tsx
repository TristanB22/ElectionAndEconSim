import React, { useState } from 'react'
import { Home as HomeIcon, Building2, BarChart3, Layers, PlayCircle, Database, Settings as SettingsIcon, Map, Users } from 'lucide-react'
import { TYPOGRAPHY } from '../typography'
import { SPACING } from '../spacing'
import { ANIMATIONS } from '../animations'

type Item = { label: string; href: string; icon: React.ReactNode }

const baseItems: Item[] = [
  { label: 'Home', href: '/', icon: <HomeIcon className="w-4 h-4" /> },
  { label: 'Firms', href: '/firm', icon: <Building2 className="w-4 h-4" /> },
  { label: 'GDP', href: '/gdp', icon: <BarChart3 className="w-4 h-4" /> },
  { label: 'Map', href: '/map', icon: <Map className="w-4 h-4" /> },
  { label: 'Scenarios', href: '#', icon: <Layers className="w-4 h-4" /> },
  { label: 'Runs', href: '#', icon: <PlayCircle className="w-4 h-4" /> },
  { label: 'Datasets', href: '#', icon: <Database className="w-4 h-4" /> },
  { label: 'Settings', href: '/settings', icon: <SettingsIcon className="w-4 h-4" /> },
]

export function LeftNav({ simulationId }: { simulationId?: string | null }) {
  const [hovering, setHovering] = useState<boolean>(false)
  const pathname = typeof window !== 'undefined' ? window.location.pathname : '/'

  const expanded = hovering

  const items: Item[] = React.useMemo(() => {
    const arr = [...baseItems]
    const agentsHref = simulationId ? `/agents?simulation_id=${simulationId}` : '/agents'
    // add All Agents shortcut near Map
    arr.splice(4, 0, { label: 'All Agents', href: agentsHref, icon: <Users className="w-4 h-4" /> })
    return arr
  }, [simulationId])

  return (
    <aside 
      className="hidden lg:block"
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
    >
      <div 
        className={`fixed left-0 top-16 z-50 h-[calc(100vh-4rem)] ${ANIMATIONS.TRANSITIONS.DEFAULT} transform-gpu`}
        style={{
          width: expanded ? '240px' : '55px',
          background: 'rgba(20, 22, 28, 0.65)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: expanded 
            ? '4px 0 32px rgba(0, 0, 0, 0.3), inset -1px 0 0 rgba(255, 255, 255, 0.05)'
            : '2px 0 16px rgba(0, 0, 0, 0.2)'
        }}
      >        
        {/* Navigation items */}
        <nav className="flex flex-col gap-1 p-2 pt-4">
          {items.map(it => {
            const active = pathname === it.href
            
            return (
              <a
                key={it.label}
                href={it.href}
                className={`relative flex items-center rounded-lg transition-all duration-200 group h-10 overflow-hidden ${
                  active
                    ? 'bg-gradient-to-r from-blue-500/20 to-indigo-500/20 text-blue-300'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                }`}
                style={active ? {
                  boxShadow: 'inset 0 0 20px rgba(59, 130, 246, 0.2), 0 0 12px rgba(59, 130, 246, 0.25)'
                } : {}}
                title={!expanded ? it.label : undefined}
              >
                {/* Icon container - FIXED at left-3, never moves */}
                <div 
                  className="absolute left-3 top-1/2 -translate-y-1/2 flex items-center justify-center flex-shrink-0"
                  style={{ width: '16px', height: '16px' }}
                >
                  <div className={`transition-transform duration-200 ${
                    active ? 'scale-110' : 'group-hover:scale-105'
                  }`}>
                    {it.icon}
                  </div>
                </div>
                
                {/* Label - positioned relative to icon, fades in/out */}
                <div 
                  className={`absolute left-12 top-1/2 -translate-y-1/2 font-medium text-sm whitespace-nowrap transition-opacity duration-200 ${
                    expanded 
                      ? 'opacity-100 delay-75' 
                      : 'opacity-0 pointer-events-none'
                  }`}
                >
                  {it.label}
                </div>
                
                {/* Hover tooltip for collapsed state */}
                {!expanded && (
                  <div 
                    className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2 py-1.5 text-xs font-medium rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-200 whitespace-nowrap z-[60]"
                    style={{
                      background: 'rgba(15, 23, 42, 0.95)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      backdropFilter: 'blur(12px)',
                      WebkitBackdropFilter: 'blur(12px)',
                      color: 'rgb(226, 232, 240)',
                      boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)'
                    }}
                  >
                    {it.label}
                  </div>
                )}
              </a>
            )
          })}
        </nav>
      </div>
    </aside>
  )
}


