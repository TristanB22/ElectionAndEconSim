import React from 'react'
import { Eye, EyeOff, Copy } from 'lucide-react'

const BG = '#0B111A'
const TEXT = '#E6EDF6'
const MUTED = '#8FA0B8'
const BORDER = '#1C2836'
const ACCENT = '#3EA6FF'
const RADIUS = 16

export interface IdentifierItem {
  label: string
  value: string
}

export const SensitiveDataCard: React.FC<{ items: IdentifierItem[] }> = ({ items }) => {
  const [open, setOpen] = React.useState(false)
  const count = items.length
  if (count === 0) return null

  const truncate = (v: string) => (v.length > 12 ? `${v.slice(0, 6)}…${v.slice(-4)}` : v)

  return (
    <div
      style={{
        background: BG,
        border: `1px solid ${BORDER}`,
        borderRadius: RADIUS,
        padding: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3 style={{ color: TEXT, fontSize: 13, fontWeight: 600 }}>Identifiers (sensitive)</h3>
        <button
          onClick={() => setOpen(o => !o)}
          style={{
            color: ACCENT,
            fontSize: 12,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          {open ? <EyeOff size={14} /> : <Eye size={14} />} {open ? 'Hide' : `Show identifiers (${count})`}
        </button>
      </div>
      {open && (
        <div style={{ marginTop: 12, display: 'grid', rowGap: 8 }}>
          {items.map((it, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderTop: `1px solid ${BORDER}`,
                paddingTop: 8,
              }}
            >
              <div style={{ color: MUTED, fontSize: 12 }}>{it.label}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ color: TEXT, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 12 }}>
                  {truncate(it.value)}
                </div>
                <button
                  onClick={() => navigator.clipboard.writeText(it.value)}
                  title="Copy"
                  style={{ color: MUTED }}
                >
                  <Copy size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SensitiveDataCard


