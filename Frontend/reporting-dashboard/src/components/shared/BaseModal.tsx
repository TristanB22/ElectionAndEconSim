import React from 'react'
import { LAYOUT } from '../../layout'
import { ANIMATIONS } from '../../animations'

export interface BaseModalProps {
  children: React.ReactNode
  isOpen: boolean
  onClose: () => void
  maxWidth?: keyof typeof LAYOUT.MODAL
  className?: string
  closeOnBackdropClick?: boolean
}

export const BaseModal = ({
  children,
  isOpen,
  onClose,
  maxWidth = 'MAX_WIDTH_DESKTOP',
  className = '',
  closeOnBackdropClick = true,
}: BaseModalProps) => {
  if (!isOpen) return null

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && closeOnBackdropClick) {
      onClose()
    }
  }

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 ${ANIMATIONS.TRANSITIONS.MODAL}`}
      onClick={handleBackdropClick}
    >
      <div
        className={`bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 ${LAYOUT.MODAL[maxWidth]} w-full max-h-[90vh] overflow-hidden ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}
