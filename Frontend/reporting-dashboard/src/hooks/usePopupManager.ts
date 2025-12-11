import { useRef, useCallback } from 'react'
import { Popup } from 'maplibre-gl'

// Global popup manager to ensure only one popup is open at a time
class PopupManager {
  private static instance: PopupManager
  private currentPopup: Popup | null = null

  static getInstance(): PopupManager {
    if (!PopupManager.instance) {
      PopupManager.instance = new PopupManager()
    }
    return PopupManager.instance
  }

  showPopup(popup: Popup): void {
    // Close any existing popup
    this.closeCurrentPopup()
    
    // Set new popup as current
    this.currentPopup = popup
  }

  closeCurrentPopup(): void {
    if (this.currentPopup) {
      this.currentPopup.remove()
      this.currentPopup = null
    }
  }

  getCurrentPopup(): Popup | null {
    return this.currentPopup
  }
}

export const usePopupManager = () => {
  const manager = PopupManager.getInstance()

  const showPopup = useCallback((popup: Popup) => {
    manager.showPopup(popup)
  }, [manager])

  const closeCurrentPopup = useCallback(() => {
    manager.closeCurrentPopup()
  }, [manager])

  return {
    showPopup,
    closeCurrentPopup,
    getCurrentPopup: () => manager.getCurrentPopup()
  }
}
