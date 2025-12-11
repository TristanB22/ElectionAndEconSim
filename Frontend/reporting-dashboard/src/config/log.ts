// Centralized logger with runtime-configurable enable flag
// Usage: import { log } from '../config/log'; log.debug('msg', data)

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const LOG_ENABLED = ((): boolean => {
  try {
    const v = localStorage.getItem('wsim_debug_logs')
    if (v === 'true') return true
    if (v === 'false') return false
  } catch {}
  // Default: enabled in development, disabled in production
  return process.env.NODE_ENV !== 'production'
})()

function emit(level: LogLevel, args: any[]) {
  if (!LOG_ENABLED) return
  const prefix = '[WSIM]'
  if (level === 'debug') return console.log(prefix, ...args)
  if (level === 'info') return console.info(prefix, ...args)
  if (level === 'warn') return console.warn(prefix, ...args)
  return console.error(prefix, ...args)
}

export const log = {
  enabled: LOG_ENABLED,
  debug: (...args: any[]) => emit('debug', args),
  info: (...args: any[]) => emit('info', args),
  warn: (...args: any[]) => emit('warn', args),
  error: (...args: any[]) => emit('error', args),
  setEnabled: (value: boolean) => {
    try { localStorage.setItem('wsim_debug_logs', String(value)) } catch {}
    // note: requires a reload to take effect because we snapshot at import time
  }
}


