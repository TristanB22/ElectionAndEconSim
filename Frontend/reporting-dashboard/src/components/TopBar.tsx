import React from 'react'
import { RESPONSIVE } from '../responsive'
import { BLUR, SHADOWS } from '../styles/colors'
import { TYPOGRAPHY } from '../typography'
import { SPACING } from '../spacing'
import { SimulationCombobox } from './SimulationCombobox'

type Option = { label: string; value: string }

export function TopBar({
  simulationId,
  setSimulationId,
  simulationOptions,
  simulationLoading,
  onRefreshSimulations
}: {
  simulationId: string | null
  setSimulationId: (id: string | null) => void
  simulationOptions: Option[]
  simulationLoading: boolean
  onRefreshSimulations?: () => void
}) {
  // Check if there are no real simulations (filter out fallback "latest" options)
  const hasRealSimulations = simulationOptions.some(option => 
    option.value !== 'latest' && option.value !== 'current' && option.value !== 'previous'
  )
  const shouldShowEmptyState = !simulationLoading && !hasRealSimulations
  const displayOptions = shouldShowEmptyState ? [] : simulationOptions

  // Transform simulationOptions into the format expected by SimulationCombobox
  const simulations = displayOptions.map(opt => {
    // Split label into ID and timestamp if it contains " — "
    const parts = opt.label.split(' — ')
    return {
      id: opt.value,
      createdAtISO: parts.length > 1 ? parts[1] : new Date().toISOString()
    }
  })

  const handleSimulationChange = (id: string) => {
    console.log('[TopBar] Simulation changed to:', id)
    setSimulationId(id)
  }

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 glass-header ${SHADOWS.SOFT}`}>
      <div className={`${RESPONSIVE.CONTAINER}`}>
        <div className="flex items-center justify-between h-16">
          <div className={`flex items-center ${SPACING.GAP.MD}`}>
            <div className="flex flex-col">
              <a
                href="/"
                className={`${TYPOGRAPHY.STYLES.HEADING} ${TYPOGRAPHY.SIZE.XL} ${TYPOGRAPHY.COLORS.PRIMARY}`}
              >
                AtlasHorizon
              </a>
              <span className={`${TYPOGRAPHY.SIZE.XS} ${TYPOGRAPHY.COLORS.SECONDARY}`}>
                Geospatial Intelligence Platform
              </span>
            </div>
          </div>
          <div className={`flex items-center ${SPACING.GAP.LG} ${BLUR.SOFT}`}>
            <SimulationCombobox
              simulations={simulations}
              value={simulationId}
              onChange={handleSimulationChange}
              live={hasRealSimulations}
              loading={simulationLoading}
              onRefresh={onRefreshSimulations}
              emptyTitle="No simulations available"
              emptyDescription="Run a simulation or refresh to sync the latest data."
            />
          </div>
        </div>
      </div>
    </header>
  )
}
