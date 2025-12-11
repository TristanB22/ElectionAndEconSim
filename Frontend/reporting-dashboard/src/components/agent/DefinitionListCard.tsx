import React from 'react'

type Item = { label: string; value: React.ReactNode | null | undefined }

interface DefinitionListCardProps {
  title: string
  items: Item[]
  columns?: 1 | 2
}

const BG = '#0B111A'
const TEXT = '#E6EDF6'
const MUTED = '#8FA0B8'
const BORDER = '#1C2836'
const RADIUS = 16

export const DefinitionListCard: React.FC<DefinitionListCardProps> = ({ title, items, columns = 2 }) => {
  const visible = items.filter(i => i.value !== null && i.value !== undefined && String(i.value).trim() !== '')
  if (visible.length === 0) return null

  return (
    <div
      style={{
        background: BG,
        border: `1px solid ${BORDER}`,
        borderRadius: RADIUS,
        padding: 16,
      }}
    >
      <h3
        style={{
          color: TEXT,
          fontSize: 13,
          fontWeight: 600,
          marginBottom: 12,
        }}
      >
        {title}
      </h3>
      <dl
        style={{
          display: 'grid',
          gridTemplateColumns: columns === 2 ? '1fr 1fr' : '1fr',
          columnGap: 16,
          rowGap: 8,
        }}
      >
        {visible.map((item, idx) => (
          <div key={idx} style={{ display: 'contents' }}>
            <dt style={{ color: MUTED, fontSize: 13 }}>{item.label}</dt>
            <dd style={{ color: TEXT, fontSize: 13, overflowWrap: 'anywhere' }}>{item.value as any}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export default DefinitionListCard


