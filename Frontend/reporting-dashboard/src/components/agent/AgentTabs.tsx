/**
 * agent tabs component
 * 
 * glass-morphism bubble design with sticky behavior.
 * clear navigation with icon-leading tabs and accent underlines.
 */

import React from 'react'

export type AgentTabId = 'overview' | 'cognition' | 'balance-sheet' | 'activity' | 'places' | 'relationships'

interface AgentTab {
  id: AgentTabId
  label: string
  icon: React.ReactNode
}

interface AgentTabsProps {
  tabs: AgentTab[]
  activeTab: AgentTabId
  onTabChange: (tab: AgentTabId) => void
}

export const AgentTabs: React.FC<AgentTabsProps> = ({
  tabs,
  activeTab,
  onTabChange,
}) => {
  return (
    <div className="max-w-6xl mx-auto px-4 lg:px-6 py-4">
      <div className="w-full flex justify-center">
        <div className="inline-flex bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`relative flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-slate-800/80 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <span className="w-4 h-4">{tab.icon}</span>
            <span>{tab.label}</span>
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-cyan-500 rounded-full"></span>
            )}
          </button>
        ))}
        </div>
      </div>
    </div>
  )
}
