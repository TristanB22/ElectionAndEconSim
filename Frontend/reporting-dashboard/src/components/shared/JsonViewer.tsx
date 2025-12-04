import React from 'react'
import { Copy, Search } from 'lucide-react'

const BG = '#0B111A'
const TEXT = '#E6EDF6'
const MUTED = '#8FA0B8'
const BORDER = '#1C2836'
const RADIUS = 16

function stringify(obj: any) {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

export const JsonViewer: React.FC<{ data: any; title?: string }>
  = ({ data, title = 'All data (JSON)' }) => {
  const [filter, setFilter] = React.useState('')
  const raw = stringify(data)
  const matches = filter.trim()
    ? raw.split('\n').filter(line => line.toLowerCase().includes(filter.toLowerCase()))
    : null
  const display = matches ? matches.join('\n') : raw

  return (
    <div
      style={{
        background: BG,
        border: `1px solid ${BORDER}`,
        borderRadius: RADIUS,
        padding: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3 style={{ color: TEXT, fontSize: 13, fontWeight: 600 }}>{title}</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ position: 'relative' }}>
            <input
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="Filter: key or value"
              style={{
                background: '#0D1420',
                border: `1px solid ${BORDER}`,
                borderRadius: 8,
                color: TEXT,
                fontSize: 12,
                padding: '6px 8px 6px 24px',
              }}
            />
            <Search size={14} style={{ position: 'absolute', left: 6, top: 7, color: MUTED }} />
          </div>
          <button
            onClick={() => navigator.clipboard.writeText(raw)}
            style={{ color: MUTED, display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}
            title="Copy JSON"
          >
            <Copy size={14} /> Copy
          </button>
        </div>
      </div>
      <div
        style={{
          background: '#0D1420',
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          maxHeight: 420,
          overflow: 'auto',
          padding: 12,
        }}
      >
        <pre style={{ color: TEXT, fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>{display}</pre>
      </div>
    </div>
  )
}

export default JsonViewer


