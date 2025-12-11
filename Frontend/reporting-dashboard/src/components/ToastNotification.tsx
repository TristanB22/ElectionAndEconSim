import { useEffect, useState } from 'react'
import { X, Info, CheckCircle, AlertCircle, AlertTriangle, User, MapPin, Search, Navigation } from 'lucide-react'
import { toastColors, agentColors } from '../styles/colors'

export type ToastType = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: string
  type: ToastType
  message: string
  persistent?: boolean
  duration?: number // milliseconds, default 3000
  metadata?: {
    isAgentToast?: boolean
    agentId?: string
    coordinates?: { lat: number; lon: number }
    icon?: 'search' | 'found' | 'navigation' | 'default'
  }
}

interface ToastNotificationProps {
  toasts: Toast[]
  onDismiss: (id: string) => void
}

export function ToastNotification({ toasts, onDismiss }: ToastNotificationProps) {
  const [dismissingToasts, setDismissingToasts] = useState<Set<string>>(new Set())
  const [expandedDiff, setExpandedDiff] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const timers: NodeJS.Timeout[] = []

    toasts.forEach(toast => {
      if (!toast.persistent && !dismissingToasts.has(toast.id)) {
        const duration = toast.duration || 3000
        const timer = setTimeout(() => {
          handleDismiss(toast.id)
        }, duration)
        timers.push(timer)
      }
    })

    return () => {
      timers.forEach(timer => clearTimeout(timer))
    }
  }, [toasts, dismissingToasts])

  const handleDismiss = (id: string) => {
    setDismissingToasts(prev => new Set(prev).add(id))
    // Wait for animation to complete before removing
    setTimeout(() => {
      onDismiss(id)
      setDismissingToasts(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }, 300)
  }

  const getIcon = (type: ToastType, metadata?: Toast['metadata']) => {
    // Agent-specific icons
    if (metadata?.isAgentToast) {
      switch (metadata.icon) {
        case 'search':
          return <Search className="w-5 h-5 flex-shrink-0" />
        case 'found':
          return <User className="w-5 h-5 flex-shrink-0" />
        case 'navigation':
          return <Navigation className="w-5 h-5 flex-shrink-0" />
        default:
          return <User className="w-5 h-5 flex-shrink-0" />
      }
    }
    
    // Default icons
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 flex-shrink-0" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 flex-shrink-0" />
      case 'error':
        return <AlertCircle className="w-5 h-5 flex-shrink-0" />
      default:
        return <Info className="w-5 h-5 flex-shrink-0" />
    }
  }

  const getColorConfig = (type: ToastType) => {
    switch (type) {
      case 'success':
        return toastColors.success
      case 'warning':
        return toastColors.warning
      case 'error':
        return toastColors.error
      default:
        return toastColors.info
    }
  }

  if (toasts.length === 0) return null
  const visibleToasts = toasts.slice(-3)

  return (
    <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-[9999] flex flex-col gap-3 pointer-events-none max-w-md w-full px-4">
      {visibleToasts.map((toast, index) => {
        const colorConfig = getColorConfig(toast.type)
        const isAgentToast = toast.metadata?.isAgentToast
        const agentUpdate = (toast.metadata as any)?.agentUpdate as undefined | {
          type: string
          agentId: string
          ts: string
          summary?: string
          fieldsChanged?: string[]
          diff?: Record<string, { old: any; new: any }>
        }
        
        // Enhanced styling for agent toasts
        if (isAgentToast) {
          return (
            <div
              key={toast.id}
              className={`
                pointer-events-auto
                rounded-2xl shadow-2xl border backdrop-blur-xl
                transition-all duration-300 ease-in-out
                ${dismissingToasts.has(toast.id) 
                  ? 'opacity-0 scale-95 -translate-y-2' 
                  : 'opacity-100 scale-100 translate-y-0'
                }
              `}
              style={{
                background: toast.type === 'success' 
                  ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.3) 100%)'
                  : toast.type === 'error'
                  ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.3) 100%)'
                  : 'linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(14, 165, 233, 0.3) 100%)',
                borderColor: toast.type === 'success'
                  ? 'rgba(16, 185, 129, 0.5)'
                  : toast.type === 'error'
                  ? 'rgba(239, 68, 68, 0.5)'
                  : 'rgba(6, 182, 212, 0.5)',
                backdropFilter: 'blur(20px) saturate(180%)',
                boxShadow: '0 10px 40px rgba(0, 0, 0, 0.4)',
                transitionDelay: `${index * 50}ms`
              }}
            >
              <div className="p-4">
                {/* Header with icon and agent ID */}
                <div className="flex items-start gap-3 mb-2">
                  <div 
                    className="p-2 rounded-lg"
                    style={{
                      background: toast.type === 'success'
                        ? 'rgba(16, 185, 129, 0.2)'
                        : toast.type === 'error'
                        ? 'rgba(239, 68, 68, 0.2)'
                        : 'rgba(59, 130, 246, 0.2)'
                    }}
                  >
                    {getIcon(toast.type, toast.metadata)}
                  </div>
                  <div className="flex-1 min-w-0">
                    {toast.metadata?.agentId && (
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold uppercase tracking-wider opacity-70">
                          Agent
                        </span>
                        <span className="text-sm font-mono font-bold px-2 py-0.5 rounded" style={{
                          background: 'rgba(255, 255, 255, 0.15)',
                          color: 'inherit'
                        }}>
                          {toast.metadata.agentId}
                        </span>
                      </div>
                    )}
                    <p className="text-sm font-medium leading-relaxed" style={{ color: colorConfig.text }}>
                      {toast.message}
                    </p>
                  </div>
                  {toast.persistent && (
                    <button
                      onClick={() => handleDismiss(toast.id)}
                      className="p-1 hover:bg-white/20 rounded transition-colors"
                      aria-label="Dismiss"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
                
                {/* Coordinates footer if available */}
                {toast.metadata?.coordinates && (
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t" style={{
                    borderColor: 'rgba(255, 255, 255, 0.15)'
                  }}>
                    <MapPin className="w-4 h-4 opacity-70" />
                    <span className="text-xs font-mono opacity-80">
                      {toast.metadata.coordinates.lat.toFixed(4)}, {toast.metadata.coordinates.lon.toFixed(4)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )
        }
        
        // Standardized agent.update payload rendering
        if (agentUpdate) {
          const title = `Agent updated • ${new Date(agentUpdate.ts).toLocaleString()}`
          const chips = (agentUpdate.fieldsChanged || []).slice(0, 6)
          const showMore = (agentUpdate.fieldsChanged || []).length > 6
          const toggle = () => setExpandedDiff(prev => ({ ...prev, [toast.id]: !prev[toast.id] }))
          const showDiff = !!expandedDiff[toast.id]
          return (
            <div
              key={toast.id}
              className={`pointer-events-auto rounded-2xl shadow-2xl border transition-all duration-300 ease-in-out ${dismissingToasts.has(toast.id) ? 'opacity-0 scale-95 -translate-y-2' : 'opacity-100 scale-100 translate-y-0'}`}
              style={{
                background: 'rgba(13, 20, 32, 0.9)',
                borderColor: 'rgba(28, 40, 54, 1)',
                color: '#E6EDF6',
                backdropFilter: 'blur(20px) saturate(180%)',
                boxShadow: '0 10px 40px rgba(0, 0, 0, 0.4)',
                transitionDelay: `${index * 50}ms`
              }}
            >
              <div className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold">{title}</div>
                    {agentUpdate.summary && (
                      <div className="text-xs opacity-80 mt-0.5">{agentUpdate.summary}</div>
                    )}
                    {chips.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {chips.map((f) => (
                          <span key={f} className="text-[11px] px-2 py-0.5 rounded-full border" style={{ borderColor: 'rgba(62,166,255,0.4)', color: '#CBE3FF' }}>{f}</span>
                        ))}
                        {showMore && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full border opacity-70" style={{ borderColor: 'rgba(62,166,255,0.25)', color: '#9FCBFF' }}>+{(agentUpdate.fieldsChanged!.length - 6)}</span>
                        )}
                      </div>
                    )}
                    {agentUpdate.diff && Object.keys(agentUpdate.diff).length > 0 && (
                      <button onClick={toggle} className="mt-2 text-[12px] underline opacity-80">{showDiff ? 'Hide changes' : 'Show changes'}</button>
                    )}
                    {showDiff && (
                      <div className="mt-2 border rounded-md text-[12px]" style={{ borderColor: 'rgba(255,255,255,0.12)' }}>
                        {Object.entries(agentUpdate.diff || {}).slice(0, 5).map(([k, v]) => (
                          <div key={k} className="grid grid-cols-3 gap-2 px-3 py-2 border-b last:border-b-0" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
                            <div className="col-span-1 opacity-80 truncate">{k}</div>
                            <div className="col-span-1 opacity-70 truncate">{String(v.old)}</div>
                            <div className="col-span-1 text-sky-300 truncate">{String(v.new)}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <button onClick={() => handleDismiss(toast.id)} className="p-1 hover:bg-white/10 rounded" aria-label="Dismiss">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )
        }

        // Standard toast styling
        return (
          <div
            key={toast.id}
            className={`
              pointer-events-auto
              flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-2xl border backdrop-blur-xl
              transition-all duration-300 ease-in-out
              ${dismissingToasts.has(toast.id) 
                ? 'opacity-0 scale-95 -translate-y-2' 
                : 'opacity-100 scale-100 translate-y-0'
              }
            `}
            style={{
              background: colorConfig.background,
              borderColor: colorConfig.border,
              color: colorConfig.text,
              backdropFilter: 'blur(20px) saturate(180%)',
              boxShadow: '0 10px 40px rgba(0, 0, 0, 0.4)',
              transitionDelay: `${index * 50}ms`
            }}
          >
            {getIcon(toast.type)}
            <p className="text-sm font-medium flex-1 min-w-0">{toast.message}</p>
            {toast.persistent && (
              <button
                onClick={() => handleDismiss(toast.id)}
                className="p-1 hover:bg-white/20 rounded transition-colors"
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}

// Hook for managing toasts
export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = (
    message: string, 
    type: ToastType = 'info', 
    options?: { 
      persistent?: boolean
      duration?: number
      metadata?: Toast['metadata']
    }
  ) => {
    const id = `toast-${Date.now()}-${Math.random()}`
    const newToast: Toast = {
      id,
      type,
      message,
      persistent: options?.persistent,
      duration: options?.duration,
      metadata: options?.metadata
    }
    setToasts(prev => [...prev, newToast])
    return id
  }

  const dismissToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }

  const clearAll = () => {
    setToasts([])
  }

  return {
    toasts,
    addToast,
    dismissToast,
    clearAll
  }
}

