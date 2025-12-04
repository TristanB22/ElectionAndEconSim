import React, { useMemo } from 'react'
import dayjs from 'dayjs'
import { Download } from 'lucide-react'
import { formatCurrency } from '../../utils/formatters'

// Keep this granularity type aligned with the values used in App.tsx.
export type Granularity =
  | '15-minute'
  | '1h'
  | 'Daily'
  | 'Weekly'
  | 'Monthly'
  | 'Quarterly'
  | 'Yearly'

export type FinancialStatementKind = 'income' | 'balance' | 'cash'

export interface FinancialStatementTableProps {
  data: Record<string, Record<string, number>>
  type: FinancialStatementKind
  title: string
  start: string
  end: string
  granularity: Granularity
  simulationId: string
  onAccountClick: (accountName: string, eventType?: string) => void
}

// Generate time intervals based on granularity
const generateTimeIntervals = (start: string, end: string, granularity: Granularity): string[] => {
  const startDate = dayjs(start)
  const endDate = dayjs(end)
  const intervals: string[] = []

  if (granularity === '15-minute') {
    let current = startDate.startOf('minute')
    while (current.isBefore(endDate.endOf('day')) || current.isSame(endDate.endOf('day'), 'minute')) {
      intervals.push(current.format('YYYY-MM-DDTHH:mm'))
      current = current.add(15, 'minute')
    }
  } else if (granularity === '1h') {
    let current = startDate.startOf('hour')
    while (current.isBefore(endDate.endOf('day')) || current.isSame(endDate.endOf('day'), 'hour')) {
      intervals.push(current.format('YYYY-MM-DDTHH:mm'))
      current = current.add(1, 'hour')
    }
  } else if (granularity === 'Daily') {
    let current = startDate.startOf('day')
    while (current.isBefore(endDate.endOf('day')) || current.isSame(endDate.endOf('day'), 'day')) {
      intervals.push(`${current.format('YYYY-MM-DD')}_to_${current.format('YYYY-MM-DD')}`)
      current = current.add(1, 'day')
    }
  } else if (granularity === 'Weekly') {
    let current = startDate.startOf('week')
    while (current.isBefore(endDate.endOf('week')) || current.isSame(endDate.endOf('week'), 'week')) {
      intervals.push(`${current.format('YYYY-MM-DD')}_to_${current.add(6, 'day').format('YYYY-MM-DD')}`)
      current = current.add(1, 'week')
    }
  } else if (granularity === 'Monthly') {
    let current = startDate.startOf('month')
    while (current.isBefore(endDate.endOf('month')) || current.isSame(endDate.endOf('month'), 'month')) {
      intervals.push(`${current.format('YYYY-MM')}_to_${current.endOf('month').format('YYYY-MM-DD')}`)
      current = current.add(1, 'month')
    }
  } else {
    // Default to daily
    let current = startDate.startOf('day')
    while (current.isBefore(endDate.endOf('day')) || current.isSame(endDate.endOf('day'), 'day')) {
      intervals.push(`${current.format('YYYY-MM-DD')}_to_${current.format('YYYY-MM-DD')}`)
      current = current.add(1, 'day')
    }
  }

  return intervals
}

// Format column headers to be more readable
const formatColumnHeader = (interval: string, granularity: Granularity): string => {
  if (granularity === '15-minute') {
    // Extract just the time part for 15-minute intervals
    const timeMatch = interval.match(/(\d{2}:\d{2})/)
    return timeMatch ? timeMatch[1] : interval
  } else if (granularity === '1h') {
    // Extract just the time part for hourly
    const timeMatch = interval.match(/(\d{2}:\d{2})/)
    return timeMatch ? timeMatch[1] : interval
  } else if (granularity === 'Daily') {
    // Extract just the date part for daily
    const dateMatch = interval.match(/(\d{4}-\d{2}-\d{2})_to_\1/)
    return dateMatch ? dateMatch[1] : interval
  } else if (granularity === 'Weekly') {
    // Show start date for weekly
    const dateMatch = interval.match(/(\d{4}-\d{2}-\d{2})_to/)
    return dateMatch ? `Week of ${dateMatch[1]}` : interval
  } else if (granularity === 'Monthly') {
    // Extract month-year for monthly
    const monthMatch = interval.match(/(\d{4}-\d{2})_to/)
    return monthMatch ? monthMatch[1] : interval
  }
  return interval
}

export function FinancialStatementTable({
  data,
  type,
  title,
  start,
  end,
  granularity,
  simulationId,
  onAccountClick,
}: FinancialStatementTableProps) {
  const formatValue = (value: number) => formatCurrency(value)

  // Map account names to event types for transaction filtering
  const getEventTypeForAccount = (accountName: string): string | undefined => {
    const eventTypeMap: Record<string, string> = {
      Revenue: 'final_consumption',
      'Retail Sales Revenue': 'final_consumption',
      'Cost of Goods Sold': 'inventory_purchase',
      'Inventory Purchase Cost': 'inventory_purchase',
      'Capital Investment': 'capital_investment',
      'Labor Cost': 'labor_cost',
      'Rent Expense': 'rent_expense',
    }
    return eventTypeMap[accountName]
  }

  const handleRowClick = (rowName: string) => {
    // Skip calculated fields that don't have direct transactions
    if (rowName === 'Operating Expenses' || rowName === 'Gross Profit' || rowName === 'Net Income') {
      return
    }

    const eventType = getEventTypeForAccount(rowName)
    onAccountClick(rowName, eventType)
  }

  // Generate time intervals for columns
  const timeIntervals = useMemo(
    () => generateTimeIntervals(start, end, granularity),
    [start, end, granularity],
  )

  // Get all unique row names
  const rowNames = Object.keys(data)

  if (rowNames.length === 0) {
    return (
      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 text-center text-gray-500 dark:text-gray-400">
        No {type} data available for the selected period
      </div>
    )
  }

  const summary = useMemo(() => {
    if (!rowNames.length) return null

    const lastCol = timeIntervals[timeIntervals.length - 1]
    const totals: Record<string, number> = {}

    rowNames.forEach(row => {
      totals[row] = data[row]?.[lastCol] ?? 0
    })

    return totals
  }, [data, rowNames, timeIntervals])

  const getRowStyle = (rowName: string) => {
    // Only add left borders for major section headers, not every row
    if (type === 'balance') {
      if (rowName === 'Total Assets')
        return 'border-l-2 border-l-[rgba(16,185,129,0.75)] bg-white/5 font-semibold text-slate-100'
      if (rowName === 'Total Current Liabilities')
        return 'border-l-2 border-l-[rgba(248,113,113,0.75)] bg-white/5 font-semibold text-slate-100'
      if (rowName === 'Total Equity')
        return 'border-l-2 border-l-[rgba(56,189,248,0.75)] bg-white/5 font-semibold text-slate-100'
    }
    if (type === 'cash') {
      if (rowName === 'Net Change in Cash')
        return 'border-l-2 border-l-[rgba(56,189,248,0.75)] bg-white/5 font-semibold text-slate-100'
    }
    if (type === 'income') {
      if (rowName === 'Net Income')
        return 'border-l-2 border-l-[rgba(16,185,129,0.75)] bg-white/5 font-semibold text-slate-100'
    }

    // Default style - no left border for regular rows
    return 'hover:bg-white/5 transition-colors duration-150'
  }

  const handleExport = () => {
    // Convert table data to CSV format
    const csvData: (string | number)[][] = []
    csvData.push(['Item', ...timeIntervals, ...(summary ? ['Total'] : [])])

    rowNames.forEach(row => {
      const rowData: (string | number)[] = [row]
      timeIntervals.forEach(col => {
        rowData.push((data[row]?.[col] ?? 0).toString())
      })
      if (summary) {
        rowData.push((summary[row] ?? 0).toString())
      }
      csvData.push(rowData)
    })

    const csvContent = csvData.map(row => row.join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="surface-level-2 border-soft radius-lg shadow-soft-layer overflow-hidden">
      <div className="px-6 py-4 border-b border-white/10 bg-white/5">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 px-3 py-2 text-xs font-medium chip-neutral hover:border-highlight hover:text-sky-200 transition-colors"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      <div className="overflow-x-auto custom-scrollbar">
        <table className="min-w-full divide-y divide-white/10">
          <thead className="bg-white/5">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-[0.18em] border-b border-white/10">
                Item
              </th>
              {timeIntervals.map(c => (
                <th
                  key={c}
                  className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-[0.18em] border-b border-white/10"
                >
                  {formatColumnHeader(c, granularity)}
                </th>
              ))}
              {summary && (
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-300 uppercase tracking-[0.18em] border-b border-white/10 bg-white/5">
                  Total
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {rowNames.map(r => (
              <tr
                key={r}
                className={`${getRowStyle(r)} transition-colors duration-150 ${
                  r !== 'Operating Expenses' && r !== 'Gross Profit' && r !== 'Net Income' ? 'cursor-pointer' : ''
                }`}
                onClick={() => handleRowClick(r)}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-200">{r}</td>
                {timeIntervals.map(c => (
                  <td key={c} className="px-6 py-4 whitespace-nowrap text-sm text-right font-mono text-slate-100">
                    {formatValue(data[r]?.[c] ?? 0)}
                  </td>
                ))}
                {summary && (
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-mono font-semibold text-slate-100 bg-white/5">
                    {formatValue(summary[r] ?? 0)}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}


