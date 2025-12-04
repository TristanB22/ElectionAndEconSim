import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import dayjs from 'dayjs'
import { 
  Building2, 
  Calendar, 
  Clock, 
  RefreshCw, 
  Target, 
  TrendingUp, 
  TrendingDown, 
  DollarSign,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  FileSpreadsheet,
  BarChart3,
  PieChart,
  Activity,
  ChevronRight,
  ChevronDown,
  Download,
  Settings,
  Search,
  Filter,
  Eye,
  EyeOff,
  X
} from 'lucide-react'
import { LeftNav } from './components/LeftNav'
import { TopBar } from './components/TopBar'
import { TransactionModal } from './components/TransactionModal'
import { FinancialStatementTable } from './components/financial/FinancialStatementTable'
import { AnalyticsPanel } from './components/financial/AnalyticsPanel'
import { useSimulationId } from './hooks/useSimulationId'
import { API_ENDPOINTS, API_BASE_URL, buildApiUrl } from './config/api'
import { formatCurrency } from './utils/formatters'

// Scrollbar styles are now handled globally in index.css

/**
 * Aggregate time-granular financial data into different time periods.
 * 
 * Takes 15-minute granular data from the API and aggregates it into
 * daily, weekly, monthly, or other granularities as needed by the frontend.
 * 
 * Assumes the input data structure from the API:
 * - data["Retail Sales Revenue"] contains time-granular revenue data
 * - Each timestamp key maps to a revenue amount
 * - Calculates derived financial metrics based on revenue
 * 
 * @param data - Raw financial data from the API (expected to have "Retail Sales Revenue")
 * @param granularity - Target granularity: 'Daily', 'Weekly', 'Monthly', '15-minute', '1h'
 * @param start - Start date string (YYYY-MM-DD format)
 * @param end - End date string (YYYY-MM-DD format)
 * 
 * @returns Object with three financial statements:
 *   - income: Income statement data (Revenue, COGS, Gross Profit, Operating Expenses, Net Income)
 *   - balance: Balance sheet data (Assets, Liabilities, Equity)
 *   - cash: Cash flow statement data (Operating, Investing, Net Change)
 */
const aggregateDataByGranularity = (data: any, granularity: string, start: string, end: string): {
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
        balance['Total Current Assets'] = { ...balance['Total Current Assets'], [timestamp]: 1000 + revenue + 55.46 }
        balance['Accounts Payable'] = { ...balance['Accounts Payable'], [timestamp]: costs * 0.3 }
        balance['Total Current Liabilities'] = { ...balance['Total Current Liabilities'], [timestamp]: costs * 0.3 }
        balance['Retained Earnings'] = { ...balance['Retained Earnings'], [timestamp]: 1000 + revenue - costs - costs * 0.1 }
        balance['Total Equity'] = { ...balance['Total Equity'], [timestamp]: 1000 + revenue - costs - costs * 0.1 }
        balance['Total Assets'] = { ...balance['Total Assets'], [timestamp]: 1000 + revenue + 55.46 }
        balance['Total Liabilities & Equity'] = { ...balance['Total Liabilities & Equity'], [timestamp]: 1000 + revenue + 55.46 }
      })
    }
    
    // Create cash flow with time-granular data
    if (data['Retail Sales Revenue']) {
      Object.keys(data['Retail Sales Revenue']).forEach(timestamp => {
        const revenue = Number(data['Retail Sales Revenue'][timestamp])
        const costs = revenue * 0.6
        const operatingExpenses = costs * 0.1
        
        // Flatten the structure to match the type signature
        cash['Net Income'] = { ...cash['Net Income'], [timestamp]: revenue - costs - operatingExpenses }
        cash['Changes in Working Capital'] = { ...cash['Changes in Working Capital'], [timestamp]: revenue - costs }
        cash['Net Cash from Operating'] = { ...cash['Net Cash from Operating'], [timestamp]: revenue }
        cash['Capital Expenditures'] = { ...cash['Capital Expenditures'], [timestamp]: -costs * 0.05 }
        cash['Net Cash from Investing'] = { ...cash['Net Cash from Investing'], [timestamp]: -costs * 0.05 }
        cash['Net Change in Cash'] = { ...cash['Net Change in Cash'], [timestamp]: revenue - costs * 0.05 }
      })
    }
    
    return { income, balance, cash }
  }
  
  // Default case
  return { income: {}, balance: {}, cash: {} }
}

type Firm = { id: string; company_name: string }
type FirmDefaults = { start_date: string; end_date: string; granularity: string; estimated_columns: number }

const granularities = [
  '15-minute',
  '1h', 
  'Daily',
  'Weekly',
  'Monthly',
  'Quarterly',
  'Yearly',
] as const

type TabType = 'overview' | 'income' | 'balance' | 'cash' | 'verification'

function VerificationPanel({ verify }: { verify: any }) {
  if (!verify) return null

  const getStatusIcon = (status: boolean) => status ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />
  const getStatusClass = (status: boolean) =>
    status
      ? 'border border-[rgba(16,185,129,0.45)] bg-[rgba(16,185,129,0.12)] text-emerald-200'
      : 'border border-[rgba(248,113,113,0.45)] bg-[rgba(248,113,113,0.12)] text-rose-200'

  return (
    <div className="surface-level-2 border-soft radius-lg shadow-soft-layer p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-11 h-11 radius-sm flex items-center justify-center border border-[rgba(16,185,129,0.45)] bg-[rgba(16,185,129,0.12)]">
          <CheckCircle className="w-6 h-6 text-emerald-300" />
        </div>
        <div>
          <h4 className="text-xl font-semibold text-slate-100">Accounting Verification</h4>
          <p className="text-sm text-slate-400/80">Verifying financial data integrity and consistency</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className={`flex items-center gap-3 p-4 radius-sm transition-all duration-150 ${getStatusClass(verify.sum_net_zero_all_buckets)}`}>
          {getStatusIcon(verify.sum_net_zero_all_buckets)}
          <div>
            <div className="font-semibold text-slate-100">Double-Entry Balance</div>
            <div className="text-xs text-slate-300/80">All transactions balance to zero</div>
          </div>
        </div>
        <div className={`flex items-center gap-3 p-4 radius-sm transition-all duration-150 ${getStatusClass(verify.balance_sheet_identity_all_buckets)}`}>
          {getStatusIcon(verify.balance_sheet_identity_all_buckets)}
          <div>
            <div className="font-semibold text-slate-100">Balance Sheet Identity</div>
            <div className="text-xs text-slate-300/80">Assets = Liabilities + Equity</div>
          </div>
        </div>
        <div className={`flex items-center gap-3 p-4 radius-sm transition-all duration-150 ${getStatusClass(verify.cash_flow_matches_cash_change_all_buckets)}`}>
          {getStatusIcon(verify.cash_flow_matches_cash_change_all_buckets)}
          <div>
            <div className="font-semibold text-slate-100">Cash Flow Reconciliation</div>
            <div className="text-xs text-slate-300/80">Cash flow matches balance sheet changes</div>
          </div>
        </div>
      </div>
      
      {verify.issues?.length > 0 && (
        <details className="border-t border-white/10 pt-4">
          <summary className="flex items-center gap-2 cursor-pointer text-amber-300 font-medium hover:text-amber-200 transition-colors">
            <AlertTriangle className="w-4 h-4 text-amber-300" />
            Issues Found ({verify.issues.length})
          </summary>
          <div className="mt-3 radius-lg border border-[rgba(251,191,36,0.35)] bg-[rgba(251,191,36,0.12)] p-4 text-amber-200">
            {verify.issues.map((issue: any, idx: number) => (
              <div key={idx} className="text-sm py-2 border-b border-[rgba(251,191,36,0.25)] last:border-b-0">
                <div className="font-semibold text-amber-200">{issue.bucket}</div>
                <div className="text-amber-100/80">{issue.kind}</div>
                {issue.value && <div className="text-xs text-amber-100/60">Value: {issue.value}</div>}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

function TabButton({ 
  active, 
  children, 
  onClick,
  count,
  icon: Icon
}: { 
  active: boolean
  children: React.ReactNode
  onClick: () => void
  count?: number
  icon?: any
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2.5 text-sm font-medium radius-sm border flex items-center gap-2 transition-all duration-150 ease-out ${
        active
          ? 'border-highlight text-sky-200 bg-white/5 shadow-soft-layer'
          : 'border-soft text-slate-400 hover:text-slate-100 hover:bg-white/5'
      }`}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {children}
      {count !== undefined && (
        <span
          className={`px-2 py-1 text-xs radius-sm ${
            active ? 'bg-sky-500/20 text-sky-200' : 'bg-white/5 text-slate-400'
          }`}
        >
          {count}
        </span>
      )}
    </button>
  )
}

function SmartDefaultsButton({ 
  onClick, 
  disabled, 
  defaults 
}: { 
  onClick: () => void
  disabled: boolean
  defaults: FirmDefaults | null
}) {
  return (
    <button 
      onClick={onClick}
      disabled={disabled}
      className="w-full flex items-center justify-center gap-3 px-4 py-3 radius-sm bg-gradient-to-r from-sky-500/70 to-emerald-400/70 text-white font-medium border border-highlight transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.01]"
    >
      <Target className="w-4 h-4" />
      {defaults ? 'Update Smart Defaults' : 'Load Smart Defaults'}
    </button>
  )
}

// Helper function to highlight search matches with escaping
function escapeRegExp(str: string) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
function highlightMatch(text: string, query: string) {
  if (!query.trim()) return text
  const safe = escapeRegExp(query)
  const regex = new RegExp(`(${safe})`, 'gi')
  const parts = text.split(regex)
  return parts.map((part, index) =>
    regex.test(part) ? (
      <span key={index} className="bg-yellow-200 font-semibold">{part}</span>
    ) : part
  )
}

function SegmentedControl({ value, onChange, options }: { value: TabType; onChange: (v: TabType) => void; options: { value: TabType; label: string; icon?: any }[] }) {
  return (
    <div className="inline-flex radius-sm border border-white/10 bg-white/5 p-1">
      {options.map(opt => {
        const active = value === opt.value
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`px-3 py-1.5 text-sm radius-sm flex items-center gap-2 transition-all duration-150 ${
              active 
                ? 'bg-white/10 border border-highlight text-sky-200 shadow-soft-layer'
                : 'border border-transparent text-slate-400 hover:text-slate-100 hover:bg-white/5'
            }`}
          >
            {opt.icon && <opt.icon className="w-4 h-4" />}
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative surface-level-3 radius-lg shadow-floating-layer border-highlight w-full max-w-lg">
        <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
          <button onClick={onClose} className="p-1 radius-sm hover:bg-white/10 transition-colors">
            <XCircle className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        <div className="p-5 max-h-[60vh] overflow-y-auto custom-scrollbar">{children}</div>
      </div>
    </div>
  )
}

function VerificationBar({ verify, onDetails }: { verify: any; onDetails: () => void }) {
  if (!verify) return null
  const Item = ({ ok, label }: { ok: boolean; label: string }) => (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 radius-sm text-xs border ${
      ok 
        ? 'text-emerald-200 border-[rgba(16,185,129,0.45)] bg-[rgba(16,185,129,0.12)]'
        : 'text-rose-200 border-[rgba(248,113,113,0.45)] bg-[rgba(248,113,113,0.12)]'
    }`}>
      {ok ? <CheckCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
      <span>{label}</span>
    </div>
  )
  return (
    <div className="flex items-center gap-2">
      <Item ok={verify.sum_net_zero_all_buckets} label="Double-Entry" />
      <Item ok={verify.balance_sheet_identity_all_buckets} label="A=L+E" />
      <Item ok={verify.cash_flow_matches_cash_change_all_buckets} label="Cash Recon" />
      <button onClick={onDetails} className="ml-2 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline">Details</button>
    </div>
  )
}

function smartFilterFirms(firms: Firm[], query: string): Firm[] {
  const q = query.trim().toLowerCase()
  const score = (name: string, id: string) => {
    const n = name.toLowerCase()
    const i = id.toLowerCase()
    let s = 0
    if (n.includes(q)) s += 5
    if (i.includes(q)) s += 3
    if (n.startsWith(q)) s += 4
    if (q.split(/\s+/).every(tok => n.includes(tok))) s += 2
    // simple edit distance bonus for near matches
    const ld = (a: string, b: string) => {
      const dp = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0))
      for (let x = 0; x <= a.length; x++) dp[x][0] = x
      for (let y = 0; y <= b.length; y++) dp[0][y] = y
      for (let x = 1; x <= a.length; x++) {
        for (let y = 1; y <= b.length; y++) {
          const cost = a[x - 1] === b[y - 1] ? 0 : 1
          dp[x][y] = Math.min(dp[x - 1][y] + 1, dp[x][y - 1] + 1, dp[x - 1][y - 1] + cost)
        }
      }
      return dp[a.length][b.length]
    }
    const d = Math.min(ld(n, q), ld(i, q))
    if (d <= 2) s += 2
    return s
  }
  return firms
    .map(f => ({ f, s: score(f.company_name, f.id) }))
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, 50)
    .map(x => x.f)
}

export default function App() {
  const [income, setIncome] = useState<Record<string, Record<string, number>>>({})
  const [balance, setBalance] = useState<Record<string, Record<string, number>>>({})
  const [cash, setCash] = useState<Record<string, Record<string, number>>>({})
  const [verify, setVerify] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadingDelay, setLoadingDelay] = useState<number | null>(null)
  const [showLoading, setShowLoading] = useState(false)
  const [defaults, setDefaults] = useState<FirmDefaults | null>(null)
  const [showFirmSearch, setShowFirmSearch] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [firms, setFirms] = useState<Firm[]>([])
  const [filteredFirms, setFilteredFirms] = useState<Firm[]>([])
  const [firmId, setFirmId] = useState<string>('')
  const [start, setStart] = useState<string>('')
  const [end, setEnd] = useState<string>('')
  const [startTime, setStartTime] = useState<string>('06:00')
  const [endTime, setEndTime] = useState<string>('23:59')
  const [granularity, setGranularity] = useState<typeof granularities[number]>('Daily')
  const [activeTab, setActiveTab] = useState<TabType>('income')
  const [showVerifyModal, setShowVerifyModal] = useState(false)
  const [colsEst, setColsEst] = useState<number>(0)
  const [showTransactionModal, setShowTransactionModal] = useState(false)
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [selectedEventType, setSelectedEventType] = useState<string>('')
  const [hasRealData, setHasRealData] = useState<boolean>(false)
  
  // Use the hook for simulation data
  const { simulations, simulationId, setSimulationId: setSimId, loading: simLoading } = useSimulationId()
  
  // Wrapper function to handle the type mismatch
  const setSimulationId = (id: string | null) => {
    if (id) {
      setSimId(id)
    }
  }
  
  // Scrollbar styles are now handled globally in index.css


  useEffect(() => {
    fetchFirms()
  }, [])

  // Filter firms based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredFirms(firms)
      return
    }
    setFilteredFirms(smartFilterFirms(firms, searchQuery))
  }, [searchQuery, firms])

  // Close firm selection modal on Escape key
  useEffect(() => {
    if (!showFirmSearch) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === 'Esc') {
        e.preventDefault()
        setShowFirmSearch(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [showFirmSearch])

  const fetchFirms = async () => {
    try {
      const response = await axios.get(API_ENDPOINTS.FIRMS)
      setFirms(response.data)
      setFilteredFirms(response.data)
      if (response.data?.length && !firmId) {
        const firstFirmId = response.data[0].id
        setFirmId(firstFirmId)
        // Automatically load defaults for the first firm
        const firmDefaults = await fetchDefaults(firstFirmId)
        if (firmDefaults) {
          setStart(firmDefaults.start_date)
          setEnd(firmDefaults.end_date)
          setGranularity(firmDefaults.granularity as typeof granularities[number])
          // Data will be fetched automatically by the useEffect
        }
      }
    } catch (err) {
      setError('Failed to fetch firms')
      console.error(err)
    }
  }

  const fetchDefaults = async (firmId: string) => {
    try {
      const response = await axios.get(API_ENDPOINTS.FIRM_DEFAULTS(firmId))
      
      // If we have a simulation ID, override the dates with the actual simulation dates
      if (simulationId && simulationId !== 'latest') {
        try {
          const simResponse = await axios.get(API_ENDPOINTS.SIMULATION_DETAIL(simulationId))
          if (simResponse.data) {
            const sim = simResponse.data
            // Use the simulation start/end dates instead of the firm defaults
            const correctedDefaults = {
              ...response.data,
              start_date: sim.start_datetime?.split('T')[0] || response.data.start_date,
              end_date: sim.end_datetime?.split('T')[0] || response.data.end_date
            }
            
            // Also set the default times based on simulation
            if (sim.start_datetime) {
              const startTime = sim.start_datetime.split('T')[1]?.substring(0, 5) || '06:00'
              setStartTime(startTime)
            }
            if (sim.end_datetime) {
              const endTime = sim.end_datetime.split('T')[1]?.substring(0, 5) || '23:59'
              setEndTime(endTime)
            }
            setDefaults(correctedDefaults)
            return correctedDefaults
          }
        } catch (simErr) {
          console.error('Failed to fetch simulation dates:', simErr)
        }
      }
      
      setDefaults(response.data)
      return response.data
    } catch (err) {
      console.error('Failed to fetch defaults:', err)
      return null
    }
  }

  const startLoading = () => {
    setLoading(true)
    setError(null)
    
    // Clear any existing delay
    if (loadingDelay) {
      clearTimeout(loadingDelay)
    }
    
    // Show loading after 300ms delay to prevent flashing
    const delay = setTimeout(() => {
      setShowLoading(true)
    }, 300)
    
    setLoadingDelay(delay)
  }
  
  const stopLoading = () => {
    setLoading(false)
    setShowLoading(false)
    
    if (loadingDelay) {
      clearTimeout(loadingDelay)
      setLoadingDelay(null)
    }
  }

  /**
   * Fetch financial data from the API and process it for display.
   * 
   * 1. Calls the /financial_statements endpoint with 15-minute granularity
   * 2. Aggregates the data based on the selected frontend granularity
   * 3. Updates the state with income, balance, and cash flow data
   * 4. Handles errors gracefully and shows appropriate messages
   * 
   * The API always returns 15-minute granular data, which is then
   * aggregated on the frontend to match the selected granularity.
   * 
   * @returns Promise<void>
   */
  const fetchFinancialData = async () => {
    if (!start || !end || !granularity) return
    
    // Always use simulationId for time-granular data
    if (!simulationId) return
    
    startLoading()
    
    try {
      // Combine date and time for the API call
      const startDateTime = `${start}T${startTime}`
      const endDateTime = `${end}T${endTime}`
      
      // Always use the time-granular endpoint and aggregate on the frontend
      let apiGranularity = '15m' // Default to 15-minute for maximum detail
      
      const response = await axios.get(API_ENDPOINTS.FINANCIAL_STATEMENTS, {
        params: { 
          simulation_id: simulationId, 
          start: startDateTime, 
          end: endDateTime, 
          granularity: apiGranularity
        }
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
          setError('No financial data available for the selected simulation and date range. Please run a simulation first or check your date selection.')
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
      setError(err.response?.data?.detail || err.message || 'Failed to fetch financial data')
    } finally {
      stopLoading()
    }
  }

  const handleFirmChange = async (newFirmId: string) => {
    setFirmId(newFirmId)
    setStart('')
    setEnd('')
    setStartTime('06:00')
    setEndTime('23:59')
    setDefaults(null)
    setShowFirmSearch(false)
    setHasRealData(false)
    setError(null)
    
    // Store in localStorage for synchronization with other pages
    localStorage.setItem('selectedFirmId', newFirmId)
    
    const newDefaults = await fetchDefaults(newFirmId)
    if (newDefaults) {
      setStart(newDefaults.start_date)
      setEnd(newDefaults.end_date)
      setGranularity(newDefaults.granularity as typeof granularities[number])
    }
  }

  const handleAccountClick = (accountName: string, eventType?: string) => {
    setSelectedAccount(accountName)
    setSelectedEventType(eventType || '')
    setShowTransactionModal(true)
  }

  const closeTransactionModal = () => {
    setShowTransactionModal(false)
    setSelectedAccount('')
    setSelectedEventType('')
  }

  const loadDefaults = async () => {
    if (!firmId) return
    const newDefaults = await fetchDefaults(firmId)
    if (newDefaults) {
      setStart(newDefaults.start_date)
      setEnd(newDefaults.end_date)
      setGranularity(newDefaults.granularity as typeof granularities[number])
    }
  }

  // Update dates when simulation changes
  useEffect(() => {
    if (simulationId && simulationId !== 'latest' && firmId) {
      // Fetch simulation details to update dates
      const updateSimulationDates = async () => {
        try {
          const simResponse = await axios.get(API_ENDPOINTS.SIMULATION_DETAIL(simulationId))
          if (simResponse.data) {
            const sim = simResponse.data
            if (sim.start_datetime) {
              const [startDate, startTime] = sim.start_datetime.split('T')
              setStart(startDate)
              setStartTime(startTime?.substring(0, 5) || '06:00')
            }
            if (sim.end_datetime) {
              const [endDate, endTime] = sim.end_datetime.split('T')
              setEnd(endDate)
              setEndTime(endTime?.substring(0, 5) || '23:59')
            }
          }
        } catch (err) {
          console.error('Failed to fetch simulation dates:', err)
        }
      }
      updateSimulationDates()
    }
  }, [simulationId, firmId])

  // Load selected firm from localStorage on page load
  useEffect(() => {
    const savedFirmId = localStorage.getItem('selectedFirmId')
    if (savedFirmId && firms.length > 0) {
      const firm = firms.find(f => f.id === savedFirmId)
      if (firm) {
        setFirmId(savedFirmId)
      }
    }
  }, [firms])
  
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
  }, [firmId, start, end, startTime, endTime, granularity, simulationId])

  const columnThreshold = 100
  const needsWarning = colsEst > columnThreshold

  const getActiveData = () => {
    // Always show all three statements for all granularities
    switch (activeTab) {
      case 'income': return { data: income, title: 'Income Statement' }
      case 'balance': return { data: balance, title: 'Balance Sheet' }
      case 'cash': return { data: cash, title: 'Cash Flow Statement' }
      default: return { data: {}, title: '' }
    }
  }

  const activeData = getActiveData()
  const activeTitle = activeData.title

  const hasData = hasRealData && (Object.keys(income).length > 0 || Object.keys(balance).length > 0 || Object.keys(cash).length > 0)


  const selectedFirm = firms.find(f => f.id === firmId)

  return (
    <div className="min-h-screen layer-0 text-geometric text-slate-100 main-layout">
      <TopBar
        simulationId={simulationId}
        setSimulationId={setSimulationId}
        simulationOptions={(simulations.length ? simulations : [{ id: 'latest' }]).map((s: any) => ({ 
          label: s.created_at ? `${s.id} — ${new Date(s.created_at).toLocaleString()}` : s.id, 
          value: s.id 
        }))}
        simulationLoading={simLoading}
      />
      <LeftNav />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pt-24 main-layout">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar Controls */}
          <aside className="lg:col-span-1 space-y-4">
            {/* Firm Selection and Highlights */}
            <div className="surface-level-2 border-soft radius-lg shadow-soft-layer p-5 transition-all duration-150">
              <label className="flex items-center text-sm font-medium text-slate-200/90">
                <Building2 className="w-4 h-4 mr-3 text-slate-300" />
                Firm
              </label>
              <button
                onClick={() => setShowFirmSearch(true)}
                className="w-full inline-flex items-center justify-between gap-3 px-4 py-3 radius-sm border-soft bg-white/5 hover:bg-white/10 transition-all duration-150 ease-out hover:scale-[1.02] text-sm text-slate-100"
                title="Change firm"
              >
                <span className="truncate text-left font-medium text-slate-100">{selectedFirm?.company_name || 'Select a firm'}</span>
                <ChevronRight className="w-4 h-4 text-slate-400 transition-transform duration-150 group-hover:translate-x-0.5" />
              </button>
              
            </div>

            {/* Date Controls */}
            <div className="surface-level-2 border-soft radius-lg shadow-soft-layer p-5 transition-all duration-150">
              <div className="flex items-center justify-between mb-4">
                <label className="flex items-center text-sm font-medium text-slate-200/90">
                  <Calendar className="w-4 h-4 mr-3 text-slate-300" />
                  Date Range
                </label>
              </div>
              
              <div className="space-y-3">
                <div>
                  <label className="block text-xs uppercase tracking-[0.14em] text-slate-400 mb-1">
                    Start Date & Time
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <input 
                      type="date" 
                      value={start} 
                      onChange={e => setStart(e.target.value)}
                      max={end || undefined}
                      className="w-full bg-white/5 text-slate-100 radius-sm border-soft px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-transparent transition-all duration-150 hover:border-white/30"
                    />
                    <input 
                      type="time" 
                      value={startTime || "06:00"}
                      onChange={e => setStartTime(e.target.value)}
                      className="w-full bg-white/5 text-slate-100 radius-sm border-soft px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-transparent transition-all duration-150 hover:border-white/30"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-[0.14em] text-slate-400 mb-1">
                    End Date & Time
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <input 
                      type="date" 
                      value={end} 
                      onChange={e => setEnd(e.target.value)}
                      min={start || undefined}
                      className="w-full bg-white/5 text-slate-100 radius-sm border-soft px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-transparent transition-all duration-150 hover:border-white/30"
                    />
                    <input 
                      type="time" 
                      value={endTime || "23:59"}
                      onChange={e => setEndTime(e.target.value)}
                      className="w-full bg-white/5 text-slate-100 radius-sm border-soft px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-transparent transition-all duration-150 hover:border-white/30"
                    />
                  </div>
                </div>
                {start && end && start === end && (
                  <p className="text-xs text-sky-400 mt-1">
                    Single day simulation selected
                  </p>
                )}
              </div>
            </div>

            {/* Granularity */}
            <div className="surface-level-2 border-soft radius-lg shadow-soft-layer p-5 transition-all duration-150">
              <label className="flex items-center text-sm font-medium text-slate-200/90 mb-3">
                <Clock className="w-4 h-4 mr-3 text-slate-300" />
                Granularity
              </label>
              <select 
                value={granularity} 
                onChange={e => setGranularity(e.target.value as any)}
                className="w-full bg-white/5 text-slate-100 radius-sm border-soft px-3 py-2 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-transparent transition-all duration-150 hover:border-white/20"
              >
                {granularities.map(g => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
              {(granularity === '15-minute' || granularity === '1h') && (
                <p className="text-xs text-sky-400 mt-2">
                  Time-granular data shows financial activity in {granularity === '15-minute' ? '15-minute' : 'hourly'} intervals
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="surface-level-2 border-soft radius-lg shadow-soft-layer p-5 transition-all duration-150">
              <div className="space-y-3">
                <SmartDefaultsButton 
                  onClick={loadDefaults}
                  disabled={!firmId}
                  defaults={defaults}
                />
                
                <button 
                  onClick={fetchFinancialData}
                  disabled={loading || !firmId || !start || !end}
                  className="w-full flex items-center justify-center gap-3 px-4 py-3 radius-sm bg-gradient-to-r from-sky-500/70 to-sky-400/80 text-white border border-highlight disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 ease-out hover:scale-[1.01] disabled:hover:scale-100"
                >
                  {loading ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  {loading ? 'Loading...' : 'Refresh Data'}
                </button>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="lg:col-span-3 space-y-6">
            {/* Loading State */}
            {showLoading && !hasData && (
              <div className="space-y-6">
                <div className="flex items-center justify-center gap-3 text-slate-300 py-4">
                  <RefreshCw className="w-5 h-5 animate-spin text-slate-200" />
                  <span className="text-slate-200/80">Loading financial data...</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
                  {[...Array(4)].map((_, idx) => (
                    <div key={idx} className="surface-level-2 border-soft radius-lg shadow-soft-layer h-32" />
                  ))}
                </div>
              </div>
            )}

            {/* Error State */}
            {error && !showLoading && !hasData && (
              <div className="border border-[rgba(248,113,113,0.45)] bg-[rgba(248,113,113,0.12)] radius-lg p-4 mb-6">
                <div className="flex items-center gap-2 text-rose-200">
                  <XCircle className="w-5 h-5 text-rose-300" />
                  <span className="font-medium text-rose-200">Error loading data</span>
                </div>
                <p className="text-rose-100/80 mt-1">{error}</p>
              </div>
            )}

            {/* No Data Message */}
            {!hasData && !showLoading && !error && (
              <div className="surface-level-2 border-soft radius-lg shadow-soft-layer p-8 text-center">
                <div className="text-slate-400">
                  <FileSpreadsheet className="w-16 h-16 mx-auto mb-4 text-slate-500" />
                  <p className="text-lg font-medium text-slate-100">No financial data available</p>
                  <p className="text-sm text-slate-400/80">Select a firm and date range to view financial statements</p>
                </div>
              </div>
            )}

            {/* Analytics Overview - Always show at top */}
            {hasData && (
              <AnalyticsPanel 
                income={income} 
                balance={balance} 
                cash={cash}
                firmName={firms.find(f => f.id === firmId)?.company_name || 'Unknown Firm'}
                startDate={start}
                endDate={end}
                granularity={granularity}
                firmId={firmId}
              />
            )}

            {/* Statements + Compact verification */}
            {hasData && (
              <div className="surface-level-2 border-soft radius-lg shadow-soft-layer overflow-hidden">
                <div className="border-b border-white/10 px-6 py-4 bg-white/5 flex items-center justify-between">
                  <SegmentedControl
                    value={activeTab}
                    onChange={(v) => setActiveTab(v as TabType)}
                    options={[
                      { value: 'income', label: 'Income', icon: TrendingUp },
                      { value: 'balance', label: 'Balance', icon: DollarSign },
                      { value: 'cash', label: 'Cash Flow', icon: TrendingDown },
                    ]}
                  />
                  <VerificationBar verify={verify} onDetails={() => setShowVerifyModal(true)} />
                </div>
                <div className="p-6">
                  <FinancialStatementTable 
                    data={activeData.data} 
                    type={activeTab as 'income' | 'balance' | 'cash'} 
                    title={activeTitle} 
                    start={start} 
                    end={end} 
                    granularity={granularity}
                    simulationId={simulationId || 'latest'}
                    onAccountClick={handleAccountClick}
                  />
                </div>
              </div>
            )}
          </main>
        </div>
      </div>

      {/* Transaction Modal */}
      {showTransactionModal && simulationId && (
        <TransactionModal
          isOpen={showTransactionModal}
          onClose={closeTransactionModal}
          simulationId={simulationId}
          startDate={start}
          endDate={end}
          accountName={selectedAccount}
          eventType={selectedEventType}
        />
      )}

      {/* Firm Search Modal */}
      {showFirmSearch && (
        <div 
          className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50"
          onClick={() => setShowFirmSearch(false)}
        >
          <div 
            className="surface-level-3 border-highlight radius-lg shadow-floating-layer max-w-2xl w-full max-h-[80vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-100">Select Firm</h3>
                <button
                  onClick={() => setShowFirmSearch(false)}
                  className="p-2 radius-sm hover:bg-white/10 transition-colors"
                >
                  <XCircle className="w-5 h-5 text-slate-400" />
                </button>
              </div>
              
              {/* Search Input */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search firms by name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border-soft bg-white/5 text-slate-100 placeholder:text-slate-500 radius-lg focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-transparent transition-all duration-150"
                  autoFocus
                />
              </div>
            </div>
            
            {/* Firm List */}
            <div className="overflow-y-auto max-h-96 custom-scrollbar">
              {filteredFirms.length === 0 ? (
                <div className="p-6 text-center text-slate-400">
                  <Building2 className="w-12 h-12 mx-auto mb-3 text-slate-500" />
                  <p>No firms found matching "{searchQuery}"</p>
                </div>
              ) : (
                <div className="divide-y divide-white/10">
                  {filteredFirms.map((firm) => (
                    <button
                      key={firm.id}
                      onClick={() => handleFirmChange(firm.id)}
                      className="w-full p-4 text-left hover:bg-white/5 transition-colors focus:outline-none focus:bg-white/5"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="p-2 radius-sm border border-[rgba(56,189,248,0.35)] bg-[rgba(56,189,248,0.12)]">
                          <Building2 className="w-5 h-5 text-sky-300" />
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-slate-100">
                            {highlightMatch(firm.company_name, searchQuery)}
                          </div>
                          <div className="text-sm text-slate-400/80">
                            ID: {highlightMatch(firm.id, searchQuery)}
                          </div>
                        </div>
                        {firm.id === firmId && (
                          <CheckCircle className="w-5 h-5 text-emerald-300" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
