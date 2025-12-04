import * as React from 'react'
import { ChevronsUpDown, Activity, Copy, RefreshCcw, AlertTriangle } from 'lucide-react'

type Simulation = {
  id: string
  createdAtISO: string
}

function middleTruncate(s: string, keep = 6) {
  if (s.length <= keep * 2 + 1) return s
  return `${s.slice(0, keep)}…${s.slice(-keep)}`
}

function isoToRelative(iso: string) {
  try {
    const d = new Date(iso).getTime()
    const now = Date.now()
    const diff = Math.max(0, now - d)
    const mins = Math.round(diff / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.round(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    const days = Math.round(hrs / 24)
    return `${days}d ago`
  } catch {
    return ''
  }
}

export function SimulationCombobox({
  simulations,
  value,
  onChange,
  live = true,
  loading = false,
  onRefresh,
  emptyTitle = 'No simulations available',
  emptyDescription = 'Run a simulation or refresh to sync the latest data.'
}: {
  simulations: Simulation[]
  value: string | null
  onChange: (id: string) => void
  live?: boolean
  loading?: boolean
  onRefresh?: () => void
  emptyTitle?: string
  emptyDescription?: string
}) {
  const [open, setOpen] = React.useState(false)
  const buttonRef = React.useRef<HTMLButtonElement | null>(null)
  const containerRef = React.useRef<HTMLDivElement | null>(null)
  const listRef = React.useRef<HTMLUListElement | null>(null)
  const [query, setQuery] = React.useState('')
  const [active, setActive] = React.useState<string | null>(null)
  const [copied, setCopied] = React.useState(false)
  const hasSimulations = simulations.length > 0
  
  // Track when we last updated relative time display to prevent flickering
  const [, forceUpdate] = React.useReducer(x => x + 1, 0)
  const lastUpdateTimeRef = React.useRef<number>(Date.now())

  const items = React.useMemo(() => {
    if (!query) return simulations
    const q = query.toLowerCase()
    return simulations.filter(d => d.id.toLowerCase().includes(q))
  }, [simulations, query])

  const selected = React.useMemo(() => {
    if (!hasSimulations) return undefined
    if (value) {
      const found = simulations.find(d => d.id === value)
      if (found) return found
    }
    return simulations[0]
  }, [simulations, value, hasSimulations])

  // Memoize the label and subtitle to prevent flickering
  const selectedLabel = React.useMemo(() => {
    return selected ? middleTruncate(selected.id, 6) : 'select simulation'
  }, [selected])

  // Cache the relative time calculation and only update periodically (every 30 seconds)
  const selectedSubRef = React.useRef<string>('')
  const selectedSub = React.useMemo(() => {
    if (!selected) {
      selectedSubRef.current = ''
      return ''
    }
    
    const now = Date.now()
    const timeSinceLastUpdate = now - lastUpdateTimeRef.current
    
    // Only recalculate if >30 seconds have passed OR if selection changed
    if (timeSinceLastUpdate > 30000 || !selectedSubRef.current.includes(selected.id.slice(0, 5))) {
      selectedSubRef.current = `${selected.createdAtISO} • ${isoToRelative(selected.createdAtISO)}`
      lastUpdateTimeRef.current = now
    }
    
    return selectedSubRef.current
  }, [selected])
  
  // Update relative time every 60 seconds (less aggressive than every render)
  React.useEffect(() => {
    const interval = setInterval(() => {
      if (selected) {
        lastUpdateTimeRef.current = 0 // Force recalculation on next render
        forceUpdate()
      }
    }, 60000) // Update every 60 seconds instead of every render
    return () => clearInterval(interval)
  }, [selected])

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open) return
    const idx = items.findIndex(i => i.id === active) ?? -1
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = items[Math.min(idx + 1, items.length - 1)]
      if (next) setActive(next.id)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const prev = items[Math.max(idx - 1, 0)]
      if (prev) setActive(prev.id)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (active) {
        onChange(active)
        setOpen(false)
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setOpen(false)
    }
  }

  React.useEffect(() => {
    if (!open) return
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node
      if (containerRef.current && !containerRef.current.contains(target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        className={[
          'inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium',
          live ? 'bg-emerald-500/10 text-emerald-300' : 'bg-slate-700/60 text-slate-300',
          'border border-white/10 shadow-sm'
        ].join(' ')}
        aria-pressed={live}
      >
        <span className="relative inline-flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-300" />
        </span>
        Live
      </button>

      {hasSimulations ? (
        <div className="flex items-center gap-2">
          <div className="relative" ref={containerRef}>
            <button
              ref={buttonRef}
              type="button"
              role="combobox"
              aria-expanded={open}
              aria-controls="simulation-combobox-list"
              onClick={() => setOpen(v => !v)}
              disabled={loading}
              className="group inline-flex items-center gap-2 rounded-2xl bg-slate-800/60 px-3 py-2 text-slate-200 border border-white/10 shadow-sm hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 disabled:opacity-50 disabled:cursor-not-allowed"
              title={selected?.id ?? ''}
            >
              <Activity className={`h-4 w-4 text-cyan-300 ${loading ? 'animate-spin' : ''}`} aria-hidden />
              <div className="flex flex-col text-left">
                <span className="font-mono text-sm leading-4">{selectedLabel}</span>
                {selectedSub && (
                  <span className="text-[11px] leading-4 text-slate-400">{selectedSub}</span>
                )}
              </div>
              <ChevronsUpDown className="ml-2 h-4 w-4 text-slate-400" aria-hidden />
            </button>

            {open && (
              <div
                className="absolute right-0 z-50 mt-2 w-[26rem] rounded-2xl border border-white/10 bg-slate-900/95 shadow-2xl backdrop-blur"
                onKeyDown={onKeyDown}
              >
              <div className="border-b border-white/10 p-2">
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="filter simulations by id…"
                  className="w-full rounded-xl bg-slate-800/70 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 outline-none focus:ring-2 ring-cyan-400/40"
                />
              </div>
              <ul
                id="simulation-combobox-list"
                role="listbox"
                className="max-h-72 overflow-y-auto py-2"
                ref={listRef}
                tabIndex={-1}
              >
                {items.length === 0 ? (
                  <li className="px-4 py-3 text-sm text-slate-400">No simulations match that filter.</li>
                ) : (
                  items.map(sim => (
                    <li
                      key={sim.id}
                      role="option"
                      aria-selected={selected?.id === sim.id}
                      className={[
                        'cursor-pointer px-4 py-3 text-sm transition-colors',
                        selected?.id === sim.id ? 'bg-slate-800 text-slate-100' : 'text-slate-300 hover:bg-slate-800/70',
                        active === sim.id ? 'ring-1 ring-cyan-400/60' : ''
                      ].join(' ')}
                      onClick={() => {
                        onChange(sim.id)
                        setOpen(false)
                      }}
                      onMouseEnter={() => setActive(sim.id)}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs">{middleTruncate(sim.id, 8)}</span>
                        <span className="text-[11px] text-slate-400">{isoToRelative(sim.createdAtISO)}</span>
                      </div>
                      <div className="mt-1 text-[11px] text-slate-500">{sim.createdAtISO}</div>
                    </li>
                  ))
                )}
              </ul>
            </div>
          )}
          </div>
          
          {/* Action buttons - outside main button to avoid nesting */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="p-2 rounded-md hover:bg-slate-800/60 border border-white/10 focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
              onClick={(e) => {
                e.stopPropagation()
                if (selected?.id) {
                  navigator.clipboard.writeText(selected.id)
                  setCopied(true)
                  window.setTimeout(() => setCopied(false), 1200)
                }
              }}
              aria-label="copy simulation id"
              title="copy simulation id"
            >
              <Copy
                className={`h-4 w-4 transition-colors ${copied ? 'text-emerald-300' : 'text-slate-300'} ${copied ? '' : 'duration-1000 ease-out'}`}
                aria-hidden
              />
            </button>
            {onRefresh && (
              <button
                type="button"
                className="p-2 rounded-md hover:bg-slate-800/60 border border-white/10 focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
                onClick={(e) => {
                  e.stopPropagation()
                  onRefresh?.()
                }}
                aria-label="refresh simulations"
                title="refresh"
              >
                <RefreshCcw className="h-4 w-4 text-slate-300" aria-hidden />
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="flex min-w-[22rem] max-w-[28rem] items-center gap-3 rounded-2xl border border-white/10 bg-slate-800/60 px-3 py-2 text-slate-200 shadow-sm backdrop-blur-sm">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-amber-400/40 bg-amber-500/10">
            <AlertTriangle className="h-4 w-4 text-amber-300" aria-hidden />
          </div>
          <div className="flex flex-col text-left">
            <span className="leading-5 text-[13px] font-semibold tracking-tight text-slate-100">{emptyTitle}</span>
            {emptyDescription && (
              <span className="leading-4 text-[11px] text-slate-400">{emptyDescription}</span>
            )}
          </div>
          {onRefresh && (
            <button
              type="button"
              onClick={() => onRefresh?.()}
              className="ml-auto inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
              title="Refresh available simulations"
            >
              <RefreshCcw className="h-4 w-4 text-slate-200" aria-hidden />
              Refresh
            </button>
          )}
        </div>
      )}
    </div>
  )
}
