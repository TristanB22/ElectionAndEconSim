import React from 'react'

export const LoadingSpinner: React.FC<{ size?: number; className?: string }> = ({ size = 24, className = '' }) => {
  const px = `${size}px`
  return (
    <div className={`relative inline-block ${className}`} style={{ width: px, height: px }}>
      <div className="absolute inset-0 rounded-full border-2 border-slate-800/40" />
      <div className="absolute inset-0 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin" />
    </div>
  )
}

export default LoadingSpinner

