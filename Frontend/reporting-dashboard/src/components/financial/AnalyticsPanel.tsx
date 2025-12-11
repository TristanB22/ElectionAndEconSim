import React, { useMemo } from 'react'
import dayjs from 'dayjs'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Building2,
  Calendar,
  ChevronRight,
  Clock,
  DollarSign,
  Download,
  PieChart,
  Target,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { API_ENDPOINTS, buildApiUrl } from '../../config/api'
import { formatCurrency } from '../../utils/formatters'

interface AnalyticsPanelProps {
  income: Record<string, Record<string, number>>
  balance: Record<string, Record<string, number>>
  cash: Record<string, Record<string, number>>
  firmName: string
  startDate: string
  endDate: string
  granularity: string
  firmId: string
}

// Excel export functionality using Python backend
const exportToExcel = async (firmId: string, startDate: string, endDate: string, granularity: string) => {
  try {
    // Call the Python backend to generate Excel file
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.EXPORT_EXCEL, {
        firm_id: firmId,
        start: startDate,
        end: endDate,
        granularity,
      }),
      {
        method: 'GET',
      },
    )

    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`)
    }

    // Get the blob from the response
    const blob = await response.blob()

    // Create download link
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // Set filename from response headers or use default
    const contentDisposition = response.headers.get('content-disposition')
    let filename = `Financial_Report_${startDate}_${endDate}.xlsx`

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="(.+)"/)
      if (filenameMatch) {
        filename = filenameMatch[1]
      }
    }

    link.download = filename
    link.style.display = 'none'

    // Trigger download
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    // Clean up
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Export failed:', error)
    alert('Failed to export Excel file. Please try again.')
  }
}

export function AnalyticsPanel({
  income,
  balance,
  cash,
  firmName,
  startDate,
  endDate,
  granularity,
  firmId,
}: AnalyticsPanelProps) {
  const metrics = useMemo(() => {
    if (!income || !balance || !cash) return null

    // Get all periods from the income statement
    const incomePeriods = Object.keys(income['Revenue'] || {})
    const balancePeriods = Object.keys(balance['Total Assets'] || {})

    if (!incomePeriods.length || !balancePeriods.length) {
      return null
    }

    // Find the period that matches the selected date range
    // Periods are sorted chronologically, so use the most recent one within the range
    const selectedPeriod = incomePeriods[incomePeriods.length - 1] // Use the last (most recent) period

    // Get values from the selected period
    // The data structure is: income[lineItem][period], not income[period][lineItem]
    const revenue = Math.abs(income['Revenue']?.[selectedPeriod] ?? 0)
    const expenses = Math.abs(income['Expenses']?.[selectedPeriod] ?? 0)
    const netIncome = income['Net Income']?.[selectedPeriod] ?? 0

    // Calculate assets, liabilities, and equity from the balance sheet data
    // The new API structure has items like "Assets - Cash", "Assets - Inventory", etc.
    let assets = 0
    let liabilities = 0
    let equity = 0

    Object.entries(balance).forEach(([key, value]) => {
      if (key.startsWith('Assets -')) {
        assets += Math.abs((value as any)[selectedPeriod] ?? 0)
      } else if (key.startsWith('Liabilities -')) {
        liabilities += Math.abs((value as any)[selectedPeriod] ?? 0)
      } else if (key.startsWith('Equity -')) {
        equity += Math.abs((value as any)[selectedPeriod] ?? 0)
      } else if (key === 'Total Assets') {
        assets = Math.abs((value as any)[selectedPeriod] ?? 0)
      } else if (key === 'Total Liabilities') {
        liabilities = Math.abs((value as any)[selectedPeriod] ?? 0)
      } else if (key === 'Total Equity') {
        equity = Math.abs((value as any)[selectedPeriod] ?? 0)
      }
    })

    // Calculate additional metrics
    const grossMargin = revenue > 0 ? ((revenue - expenses) / revenue) * 100 : 0
    const roa = assets > 0 ? (netIncome / assets) * 100 : 0 // Return on Assets
    const debtToAssets = assets > 0 ? (liabilities / assets) * 100 : 0

    return {
      revenue,
      expenses,
      netIncome,
      assets,
      liabilities,
      equity,
      grossMargin,
      roa,
      debtToAssets,
      period: selectedPeriod,
    }
  }, [income, balance, cash])

  if (!metrics) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="col-span-full surface-level-2 border-soft radius-lg shadow-soft-layer p-8 text-center">
          <BarChart3 className="w-12 h-12 mx-auto mb-4 text-slate-400" />
          <p className="text-lg font-medium text-slate-200">No Analytics Data Available</p>
          <p className="text-sm text-slate-400/80">Financial data is required to display analytics</p>
        </div>
      </div>
    )
  }

  const MetricCard = ({
    title,
    value,
    icon: Icon,
    accent,
    trend,
  }: {
    title: string
    value: string | number
    icon: any
    accent: 'emerald' | 'sky' | 'violet' | 'amber' | 'cyan' | 'rose' | 'neutral'
    trend?: 'up' | 'down' | 'neutral'
  }) => {
    const accents = {
      emerald: {
        chip: 'border border-[rgba(16,185,129,0.45)] bg-[rgba(16,185,129,0.12)] text-emerald-200',
        icon: 'text-emerald-300',
      },
      sky: {
        chip: 'border border-[rgba(56,189,248,0.4)] bg-[rgba(56,189,248,0.12)] text-sky-200',
        icon: 'text-sky-300',
      },
      violet: {
        chip: 'border border-[rgba(139,92,246,0.4)] bg-[rgba(139,92,246,0.12)] text-violet-200',
        icon: 'text-violet-300',
      },
      amber: {
        chip: 'border border-[rgba(251,191,36,0.4)] bg-[rgba(251,191,36,0.12)] text-amber-200',
        icon: 'text-amber-300',
      },
      cyan: {
        chip: 'border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.12)] text-cyan-200',
        icon: 'text-cyan-300',
      },
      rose: {
        chip: 'border border-[rgba(244,114,182,0.4)] bg-[rgba(244,114,182,0.12)] text-rose-200',
        icon: 'text-rose-300',
      },
      neutral: {
        chip: 'chip-neutral',
        icon: 'text-slate-200',
      },
    } as const

    const palette = accents[accent] ?? accents.neutral
    const trendTone =
      trend === 'up'
        ? 'text-emerald-300'
        : trend === 'down'
          ? 'text-rose-300'
          : 'text-slate-400'

    return (
      <div className="surface-level-2 border-soft radius-lg shadow-soft-layer p-5 transition-all duration-150 hover:border-highlight hover:-translate-y-0.5">
        <div className="flex items-center justify-between mb-4">
          <div className={`w-11 h-11 radius-sm flex items-center justify-center ${palette.chip}`}>
            <Icon className={`w-5 h-5 ${palette.icon}`} />
          </div>
          {trend && (
            <div className={`flex items-center gap-1 text-xs font-medium ${trendTone}`}>
              {trend === 'up' && <TrendingUp className="w-3.5 h-3.5" />}
              {trend === 'down' && <TrendingDown className="w-3.5 h-3.5" />}
              {trend === 'neutral' && <Activity className="w-3.5 h-3.5" />}
            </div>
          )}
        </div>
        <p className="text-xs uppercase tracking-[0.16em] text-slate-400 mb-1">{title}</p>
        <p className="text-2xl font-semibold text-slate-100">{value}</p>
      </div>
    )
  }

  const startLabel = startDate ? dayjs(startDate).format('MMM D, YYYY') : '—'
  const endLabel = endDate ? dayjs(endDate).format('MMM D, YYYY') : '—'

  return (
    <div className="space-y-6">
      {/* Identity + Period */}
      <div className="surface-level-2 border-soft radius-lg shadow-soft-layer p-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 radius-lg border border-highlight bg-white/10 flex items-center justify-center text-sky-200">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Active Firm</p>
              <h2 className="text-2xl font-semibold text-slate-100">{firmName}</h2>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="chip-neutral flex items-center gap-2 px-3 py-2 text-xs uppercase tracking-[0.16em] text-slate-300">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>{startLabel}</span>
              <ChevronRight className="w-3 h-3 text-slate-500" />
              <span>{endLabel}</span>
            </div>
            <div className="chip-neutral flex items-center gap-2 px-3 py-2 text-xs uppercase tracking-[0.16em] text-slate-300">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>{granularity}</span>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 chip-neutral flex items-center justify-center">
              <Calendar className="w-4 h-4 text-sky-300" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Analysis Period</p>
              <p className="text-lg font-semibold text-slate-100">{metrics.period}</p>
            </div>
          </div>
          <button
            onClick={() => exportToExcel(firmId, startDate, endDate, granularity)}
            className="inline-flex items-center gap-2 px-4 py-2 radius-sm bg-gradient-to-r from-sky-500/70 to-cyan-400/70 text-white border border-highlight transition-all duration-150 hover:scale-[1.01]"
          >
            <Download className="w-4 h-4" />
            Export Report
          </button>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Revenue"
          value={formatCurrency(metrics.revenue)}
          icon={TrendingUp}
          accent="emerald"
          trend="up"
        />

        <MetricCard
          title="Net Income"
          value={formatCurrency(metrics.netIncome)}
          icon={metrics.netIncome >= 0 ? TrendingUp : TrendingDown}
          accent={metrics.netIncome >= 0 ? 'emerald' : 'rose'}
          trend={metrics.netIncome >= 0 ? 'up' : 'down'}
        />

        <MetricCard
          title="Gross Margin"
          value={`${metrics.grossMargin.toFixed(1)}%`}
          icon={BarChart3}
          accent="violet"
          trend="neutral"
        />

        <MetricCard
          title="Total Assets"
          value={formatCurrency(metrics.assets)}
          icon={PieChart}
          accent="sky"
          trend="neutral"
        />
      </div>

      {/* Additional Ratios */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Return on Assets"
          value={`${metrics.roa.toFixed(2)}%`}
          icon={Target}
          accent="emerald"
          trend={metrics.roa > 0 ? 'up' : 'down'}
        />

        <MetricCard
          title="Debt to Assets"
          value={`${metrics.debtToAssets.toFixed(1)}%`}
          icon={AlertTriangle}
          accent="amber"
          trend="neutral"
        />

        <MetricCard
          title="Equity"
          value={formatCurrency(metrics.equity)}
          icon={DollarSign}
          accent="cyan"
          trend="neutral"
        />
      </div>
    </div>
  )
}


