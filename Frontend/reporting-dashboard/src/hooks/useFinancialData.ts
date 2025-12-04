import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { API_ENDPOINTS } from '../config/api'

export type FinancialGranularity =
  | '15-minute'
  | '1h'
  | 'Daily'
  | 'Weekly'
  | 'Monthly'
  | 'Quarterly'
  | 'Yearly'

export interface UseFinancialDataArgs {
  start: string
  end: string
  startTime: string
  endTime: string
  granularity: FinancialGranularity
  simulationId: string | null
  firmId: string
}

export interface UseFinancialDataResult {
  income: Record<string, Record<string, number>>
  balance: Record<string, Record<string, number>>
  cash: Record<string, Record<string, number>>
  verify: any
  loading: boolean
  showLoading: boolean
  error: string | null
  hasRealData: boolean
  fetchFinancialData: () => Promise<void>
}

/**
 * Aggregate time-granular financial data into different time periods.
 *
 * This logic is lifted directly from the original App.tsx implementation
 * so behaviour remains identical, just relocated.
 */
const aggregateDataByGranularity = (
  data: any,
  granularity: FinancialGranularity,
  start: string,
  end: string,
): {
  income: Record<string, Record<string, number>>
  balance: Record<string, Record<string, number>>
  cash: Record<string, Record<string, number>>
} => {
  // Sum up all revenue for the period
  let totalRevenue = 0
  if (data['Retail Sales Revenue']) {
    for (const amount of Object.values(data['Retail Sales Revenue'])) {
      totalRevenue += Number(amount)
    }
  }

  // Estimate costs as 60% of revenue
  const totalCosts = totalRevenue * 0.6

  if (granularity === 'Daily') {
    // Aggregate by day
    const periodId = `${start}_to_${end}`

    return {
      income: {
        Revenue: { [periodId]: totalRevenue },
        'Cost of Goods Sold': { [periodId]: totalCosts },
        'Gross Profit': { [periodId]: totalRevenue - totalCosts },
        'Operating Expenses': { [periodId]: totalCosts * 0.1 }, // 10% of COGS for other expenses
        'Net Income': { [periodId]: totalRevenue - totalCosts - totalCosts * 0.1 },
      },
      balance: {
        Cash: { [periodId]: 1000 + totalRevenue },
        Inventory: { [periodId]: 55.46 },
        'Total Current Assets': { [periodId]: 1000 + totalRevenue + 55.46 },
        'Accounts Payable': { [periodId]: totalCosts * 0.3 }, // 30% of COGS as AP
        'Total Current Liabilities': { [periodId]: totalCosts * 0.3 },
        'Retained Earnings': { [periodId]: 1000 + totalRevenue - totalCosts - totalCosts * 0.1 },
        'Total Equity': { [periodId]: 1000 + totalRevenue - totalCosts - totalCosts * 0.1 },
        'Total Assets': { [periodId]: 1000 + totalRevenue + 55.46 },
        'Total Liabilities & Equity': { [periodId]: 1000 + totalRevenue + 55.46 },
      },
      cash: {
        'Net Income': { [periodId]: totalRevenue - totalCosts - totalCosts * 0.1 },
        'Changes in Working Capital': { [periodId]: totalRevenue - totalCosts },
        'Net Cash from Operating': { [periodId]: totalRevenue },
        'Capital Expenditures': { [periodId]: -totalCosts * 0.05 }, // 5% of COGS for CapEx
        'Net Cash from Investing': { [periodId]: -totalCosts * 0.05 },
        'Net Change in Cash': { [periodId]: totalRevenue - totalCosts * 0.05 },
      },
    }
  } else if (granularity === 'Weekly') {
    // Aggregate by week
    const periodId = `Week of ${start}`

    return {
      income: {
        Revenue: { [periodId]: totalRevenue },
        'Cost of Goods Sold': { [periodId]: totalCosts },
        'Gross Profit': { [periodId]: totalRevenue - totalCosts },
        'Operating Expenses': { [periodId]: totalCosts * 0.1 },
        'Net Income': { [periodId]: totalRevenue - totalCosts - totalCosts * 0.1 },
      },
      balance: {
        Cash: { [periodId]: 1000 + totalRevenue },
        Inventory: { [periodId]: 55.46 },
        'Total Current Assets': { [periodId]: 1000 + totalRevenue + 55.46 },
        'Accounts Payable': { [periodId]: totalCosts * 0.3 },
        'Total Current Liabilities': { [periodId]: totalCosts * 0.3 },
        'Retained Earnings': { [periodId]: 1000 + totalRevenue - totalCosts - totalCosts * 0.1 },
        'Total Equity': { [periodId]: 1000 + totalRevenue - totalCosts - totalCosts * 0.1 },
        'Total Assets': { [periodId]: 1000 + totalRevenue + 55.46 },
        'Total Liabilities & Equity': { [periodId]: 1000 + totalRevenue + 55.46 },
      },
      cash: {
        'Net Income': { [periodId]: totalRevenue - totalCosts - totalCosts * 0.1 },
        'Changes in Working Capital': { [periodId]: totalRevenue - totalCosts },
        'Net Cash from Operating': { [periodId]: totalRevenue },
        'Capital Expenditures': { [periodId]: -totalCosts * 0.05 },
        'Net Cash from Investing': { [periodId]: -totalCosts * 0.05 },
        'Net Change in Cash': { [periodId]: totalRevenue - totalCosts * 0.05 },
      },
    }
  } else if (granularity === 'Monthly') {
    // Aggregate by month
    const monthYear = start.substring(0, 7) // YYYY-MM
    const periodId = monthYear

    return {
      income: {
        Revenue: { [periodId]: totalRevenue },
        'Cost of Goods Sold': { [periodId]: totalCosts },
        'Gross Profit': { [periodId]: totalRevenue - totalCosts },
        'Operating Expenses': { [periodId]: totalCosts * 0.1 },
        'Net Income': { [periodId]: totalRevenue - totalCosts - totalCosts * 0.1 },
      },
      balance: {
        Cash: { [periodId]: 1000 + totalRevenue },
        Inventory: { [periodId]: 55.46 },
        'Total Current Assets': { [periodId]: 1000 + totalRevenue + 55.46 },
        'Accounts Payable': { [periodId]: totalCosts * 0.3 },
        'Total Current Liabilities': { [periodId]: totalCosts * 0.3 },
        'Retained Earnings': { [periodId]: 1000 + totalRevenue - totalCosts - totalCosts * 0.1 },
        'Total Equity': { [periodId]: 1000 + totalRevenue - totalCosts - totalCosts * 0.1 },
        'Total Assets': { [periodId]: 1000 + totalRevenue + 55.46 },
        'Total Liabilities & Equity': { [periodId]: 1000 + totalRevenue + 55.46 },
      },
      cash: {
        'Net Income': { [periodId]: totalRevenue - totalCosts - totalCosts * 0.1 },
        'Changes in Working Capital': { [periodId]: totalRevenue - totalCosts },
        'Net Cash from Operating': { [periodId]: totalRevenue },
        'Capital Expenditures': { [periodId]: -totalCosts * 0.05 },
        'Net Cash from Investing': { [periodId]: -totalCosts * 0.05 },
        'Net Change in Cash': { [periodId]: totalRevenue - totalCosts * 0.05 },
      },
    }
  } else if (granularity === '15-minute' || granularity === '1h') {
    // For time-granular data, convert to the expected format
    const income: Record<string, Record<string, number>> = {}
    const balance: Record<string, Record<string, number>> = {}
    const cash: Record<string, Record<string, number>> = {}

    // Convert time-granular data to income statement format
    if (data['Retail Sales Revenue']) {
      income['Revenue'] = data['Retail Sales Revenue']
      income['Cost of Goods Sold'] = {}
      income['Gross Profit'] = {}
      income['Operating Expenses'] = {}
      income['Net Income'] = {}

      // Calculate line items for each time slot
      Object.keys(data['Retail Sales Revenue']).forEach(timestamp => {
        const revenue = Number(data['Retail Sales Revenue'][timestamp])
        const costs = revenue * 0.6
        const operatingExpenses = costs * 0.1

        income['Cost of Goods Sold'][timestamp] = costs
        income['Gross Profit'][timestamp] = revenue - costs
        income['Operating Expenses'][timestamp] = operatingExpenses
        income['Net Income'][timestamp] = revenue - costs - operatingExpenses
      })
    }

    // Create balance sheet with time-granular data
    if (data['Retail Sales Revenue']) {
      Object.keys(data['Retail Sales Revenue']).forEach(timestamp => {
        const revenue = Number(data['Retail Sales Revenue'][timestamp])
        const costs = revenue * 0.6

        // Flatten the structure to match the type signature
        balance['Cash'] = { ...balance['Cash'], [timestamp]: 1000 + revenue }
        balance['Inventory'] = { ...balance['Inventory'], [timestamp]: 55.46 }
        balance['Total Current Assets'] = {
          ...balance['Total Current Assets'],
          [timestamp]: 1000 + revenue + 55.46,
        }
        balance['Accounts Payable'] = { ...balance['Accounts Payable'], [timestamp]: costs * 0.3 }
        balance['Total Current Liabilities'] = {
          ...balance['Total Current Liabilities'],
          [timestamp]: costs * 0.3,
        }
        balance['Retained Earnings'] = {
          ...balance['Retained Earnings'],
          [timestamp]: 1000 + revenue - costs - costs * 0.1,
        }
        balance['Total Equity'] = {
          ...balance['Total Equity'],
          [timestamp]: 1000 + revenue - costs - costs * 0.1,
        }
        balance['Total Assets'] = { ...balance['Total Assets'], [timestamp]: 1000 + revenue + 55.46 }
        balance['Total Liabilities & Equity'] = {
          ...balance['Total Liabilities & Equity'],
          [timestamp]: 1000 + revenue + 55.46,
        }
      })
    }

    // Create cash flow with time-granular data
    if (data['Retail Sales Revenue']) {
      Object.keys(data['Retail Sales Revenue']).forEach(timestamp => {
        const revenue = Number(data['Retail Sales Revenue'][timestamp])
        const costs = revenue * 0.6
        const operatingExpenses = costs * 0.1

        // Flatten the structure to match the type signature
        cash['Net Income'] = {
          ...cash['Net Income'],
          [timestamp]: revenue - costs - operatingExpenses,
        }
        cash['Changes in Working Capital'] = {
          ...cash['Changes in Working Capital'],
          [timestamp]: revenue - costs,
        }
        cash['Net Cash from Operating'] = {
          ...cash['Net Cash from Operating'],
          [timestamp]: revenue,
        }
        cash['Capital Expenditures'] = {
          ...cash['Capital Expenditures'],
          [timestamp]: -costs * 0.05,
        }
        cash['Net Cash from Investing'] = {
          ...cash['Net Cash from Investing'],
          [timestamp]: -costs * 0.05,
        }
        cash['Net Change in Cash'] = {
          ...cash['Net Change in Cash'],
          [timestamp]: revenue - costs * 0.05,
        }
      })
    }

    return { income, balance, cash }
  }

  // Default case
  return { income: {}, balance: {}, cash: {} }
}

export const useFinancialData = ({
  start,
  end,
  startTime,
  endTime,
  granularity,
  simulationId,
  firmId,
}: UseFinancialDataArgs): UseFinancialDataResult => {
  const [income, setIncome] = useState<Record<string, Record<string, number>>>({})
  const [balance, setBalance] = useState<Record<string, Record<string, number>>>({})
  const [cash, setCash] = useState<Record<string, Record<string, number>>>({})
  const [verify, setVerify] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadingDelay, setLoadingDelay] = useState<number | null>(null)
  const [showLoading, setShowLoading] = useState(false)
  const [hasRealData, setHasRealData] = useState<boolean>(false)

  const startLoading = useCallback(() => {
    setLoading(true)
    setError(null)

    // Clear any existing delay
    setLoadingDelay(prevDelay => {
      if (prevDelay) {
        clearTimeout(prevDelay)
      }
      // Show loading after 300ms delay to prevent flashing
      const delay = window.setTimeout(() => {
        setShowLoading(true)
      }, 300)
      return delay
    })
  }, [])

  const stopLoading = useCallback(() => {
    setLoading(false)
    setShowLoading(false)

    setLoadingDelay(prevDelay => {
      if (prevDelay) {
        clearTimeout(prevDelay)
      }
      return null
    })
  }, [])

  const fetchFinancialData = useCallback(async () => {
    if (!start || !end || !granularity) return

    // Always use simulationId for time-granular data
    if (!simulationId) return

    startLoading()

    try {
      // Combine date and time for the API call
      const startDateTime = `${start}T${startTime}`
      const endDateTime = `${end}T${endTime}`

      // Always use the time-granular endpoint and aggregate on the frontend
      const apiGranularity = '15m' // Default to 15-minute for maximum detail

      const response = await axios.get(API_ENDPOINTS.FINANCIAL_STATEMENTS, {
        params: {
          simulation_id: simulationId,
          start: startDateTime,
          end: endDateTime,
          granularity: apiGranularity,
        },
      })

      if (response.data) {
        // Check if we have real data or empty data
        const hasData = Object.keys(response.data).length > 0

        if (hasData) {
          // Aggregate the data based on the selected granularity
          const aggregatedData = aggregateDataByGranularity(response.data, granularity, start, end)

          // Set all three statements for all granularities
          setIncome(aggregatedData.income)
          setBalance(aggregatedData.balance)
          setCash(aggregatedData.cash)
          setVerify(null)
          setHasRealData(true)
          setError(null)
        } else {
          // No real data available
          setIncome({})
          setBalance({})
          setCash({})
          setVerify(null)
          setHasRealData(false)
          setError(
            'No financial data available for the selected simulation and date range. Please run a simulation first or check your date selection.',
          )
        }
      } else {
        setIncome({})
        setBalance({})
        setCash({})
        setVerify(null)
        setHasRealData(false)
        setError('No financial data available for the selected simulation and date range.')
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to fetch financial data')
    } finally {
      stopLoading()
    }
  }, [start, end, startTime, endTime, granularity, simulationId, startLoading, stopLoading])

  // Fetch data when firm, start, end, granularity, or simulation changes
  useEffect(() => {
    if (start && end) {
      // For time-granular data, we need simulationId
      if ((granularity === '15-minute' || granularity === '1h') && simulationId) {
        fetchFinancialData()
      }
      // For traditional granularity, we need firmId
      else if (granularity !== '15-minute' && granularity !== '1h' && firmId) {
        fetchFinancialData()
      }
    }
  }, [start, end, granularity, simulationId, firmId, fetchFinancialData])

  return {
    income,
    balance,
    cash,
    verify,
    loading,
    showLoading,
    error,
    hasRealData,
    fetchFinancialData,
  }
}


