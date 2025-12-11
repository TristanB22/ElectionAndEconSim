import React, { useEffect, useState } from 'react'
import { X, Calendar, Clock, User, Building2, DollarSign, Package, TrendingUp, Filter, Search, ChevronRight, ArrowLeft, Info } from 'lucide-react'
import axios from 'axios'
import { API_ENDPOINTS } from '../config/api'

interface Transaction {
  id: number
  event_id: string
  timestamp: string
  event_type: string
  from_entity: string
  to_entity: string
  amount: number
  currency: string
  sku: string
  quantity: number
  unit_price: number
  unit_cost: number
  buyer_type: string
  use_type: string
  sector: string
  subsector: string
  description: string
  metadata: any
}

interface TransactionModalProps {
  isOpen: boolean
  onClose: () => void
  simulationId: string
  startDate: string
  endDate: string
  accountName: string
  eventType?: string
}

export function TransactionModal({ 
  isOpen, 
  onClose, 
  simulationId, 
  startDate, 
  endDate, 
  accountName,
  eventType 
}: TransactionModalProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'timestamp' | 'amount'>('timestamp')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null)
  const [showTransactionDetail, setShowTransactionDetail] = useState(false)

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        if (showTransactionDetail) {
          setShowTransactionDetail(false)
          setSelectedTransaction(null)
        } else {
          onClose()
        }
      }
    }
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose, showTransactionDetail])

  const handleTransactionClick = (transaction: Transaction) => {
    setSelectedTransaction(transaction)
    setShowTransactionDetail(true)
  }

  const handleBackToList = () => {
    setShowTransactionDetail(false)
    setSelectedTransaction(null)
  }

  // Fetch transactions when modal opens
  useEffect(() => {
    if (isOpen && simulationId) {
      fetchTransactions()
    }
  }, [isOpen, simulationId, startDate, endDate, accountName, eventType])

  const fetchTransactions = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const startDateTime = `${startDate}T06:00:00`
      const endDateTime = `${endDate}T23:59:59`
      
      const response = await axios.get(API_ENDPOINTS.TRANSACTIONS, {
        params: {
          simulation_id: simulationId,
          start: startDateTime,
          end: endDateTime,
          event_type: eventType
        }
      })
      
      if (response.data && response.data.transactions) {
        setTransactions(response.data.transactions)
      } else {
        setTransactions([])
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch transactions')
      setTransactions([])
    } finally {
      setLoading(false)
    }
  }

  const filteredTransactions = transactions
    .filter(tx => 
      searchTerm === '' || 
      tx.event_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.from_entity.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.to_entity.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.sku?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.description?.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'timestamp') {
        return sortOrder === 'asc' 
          ? new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          : new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      } else {
        return sortOrder === 'asc' 
          ? a.amount - b.amount
          : b.amount - a.amount
      }
    })

  const totalAmount = filteredTransactions.reduce((sum, tx) => sum + tx.amount, 0)
  const totalQuantity = filteredTransactions.reduce((sum, tx) => sum + tx.quantity, 0)

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-7xl max-h-[95vh] mx-4 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center min-w-0 flex-1">
            {showTransactionDetail && (
              <button
                onClick={handleBackToList}
                className="mr-3 sm:mr-4 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors flex-shrink-0"
              >
                <ArrowLeft className="w-4 h-4 sm:w-5 sm:h-5 text-gray-600 dark:text-gray-400" />
              </button>
            )}
            <div className="min-w-0 flex-1">
              <h2 className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white truncate">
                {showTransactionDetail ? 'Transaction Details' : 'Transaction List'}
              </h2>
              <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mt-1 truncate">
                {showTransactionDetail 
                  ? `Transaction #${selectedTransaction?.id}` 
                  : `${accountName} • ${transactions.length} transactions`
                }
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors flex-shrink-0"
          >
            <X className="w-4 h-4 sm:w-5 sm:h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Summary Stats */}
        {!showTransactionDetail && (
          <div className="p-4 sm:p-6 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              <div className="bg-white dark:bg-gray-900 p-4 rounded-lg shadow-sm">
                <div className="flex items-center">
                  <DollarSign className="w-5 h-5 text-green-600 dark:text-green-400 mr-2" />
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Total Amount</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      ${totalAmount.toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white dark:bg-gray-900 p-4 rounded-lg shadow-sm">
                <div className="flex items-center">
                  <Package className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-2" />
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Total Quantity</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {totalQuantity.toFixed(0)}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white dark:bg-gray-900 p-4 rounded-lg shadow-sm">
                <div className="flex items-center">
                  <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400 mr-2" />
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Avg. Price</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      ${totalQuantity > 0 ? (totalAmount / totalQuantity).toFixed(2) : '0.00'}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white dark:bg-gray-900 p-4 rounded-lg shadow-sm">
                <div className="flex items-center">
                  <Calendar className="w-5 h-5 text-orange-600 dark:text-orange-400 mr-2" />
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Transactions</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {filteredTransactions.length}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Controls */}
        {!showTransactionDetail && (
          <div className="p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
              {/* Search */}
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500 w-4 h-4" />
                  <input
                    type="text"
                    placeholder="Search transactions..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                  />
                </div>
              </div>
              
              {/* Sort */}
              <div className="flex gap-2">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as 'timestamp' | 'amount')}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  <option value="timestamp">Sort by Time</option>
                  <option value="amount">Sort by Amount</option>
                </select>
                
                <button
                  onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  {sortOrder === 'asc' ? '↑' : '↓'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {showTransactionDetail ? (
            <div className="flex-1 overflow-y-auto">
              <TransactionDetailView transaction={selectedTransaction} />
            </div>
          ) : loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="text-red-600 dark:text-red-400 mb-2">⚠️</div>
                <p className="text-gray-600 dark:text-gray-400">{error}</p>
                <button
                  onClick={fetchTransactions}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : filteredTransactions.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="text-gray-400 dark:text-gray-500 mb-2">📊</div>
                <p className="text-gray-600 dark:text-gray-400">No transactions found</p>
                <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
                  Try adjusting your search or date range
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px]">
                  <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                    <tr>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Time
                      </th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Event
                      </th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        From → To
                      </th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        SKU
                      </th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Qty
                      </th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Amount
                      </th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Details
                      </th>
                    </tr>
                  </thead>
                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredTransactions.map((tx) => (
                    <tr 
                      key={tx.id} 
                      className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
                      onClick={() => handleTransactionClick(tx)}
                    >
                      <td className="px-3 sm:px-6 py-4 text-sm text-gray-900 dark:text-white">
                        <div className="flex items-center">
                          <Clock className="w-3 h-3 sm:w-4 sm:h-4 text-gray-400 dark:text-gray-500 mr-1 sm:mr-2 flex-shrink-0" />
                          <span className="text-xs sm:text-sm">{new Date(tx.timestamp).toLocaleString()}</span>
                        </div>
                      </td>
                      <td className="px-3 sm:px-6 py-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                          {tx.event_type.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-3 sm:px-6 py-4 text-sm text-gray-900 dark:text-white">
                        <div className="flex items-center min-w-0">
                          <User className="w-3 h-3 sm:w-4 sm:h-4 text-gray-400 dark:text-gray-500 mr-1 flex-shrink-0" />
                          <span className="font-mono text-xs truncate">{tx.from_entity}</span>
                          <span className="mx-1 sm:mx-2 text-gray-400 dark:text-gray-500 flex-shrink-0">→</span>
                          <Building2 className="w-3 h-3 sm:w-4 sm:h-4 text-gray-400 dark:text-gray-500 mr-1 flex-shrink-0" />
                          <span className="font-mono text-xs truncate">{tx.to_entity}</span>
                        </div>
                      </td>
                      <td className="px-3 sm:px-6 py-4 text-sm text-gray-900 dark:text-white">
                        <span className="truncate block max-w-[100px]">{tx.sku || '-'}</span>
                      </td>
                      <td className="px-3 sm:px-6 py-4 text-sm text-gray-900 dark:text-white">
                        {tx.quantity.toFixed(0)}
                      </td>
                      <td className="px-3 sm:px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                        ${tx.amount.toFixed(2)}
                      </td>
                      <td className="px-3 sm:px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        <div className="space-y-1">
                          {tx.buyer_type && (
                            <div className="text-xs">
                              <span className="font-medium">Buyer:</span> {tx.buyer_type}
                            </div>
                          )}
                          {tx.sector && (
                            <div className="text-xs">
                              <span className="font-medium">Sector:</span> {tx.sector}
                            </div>
                          )}
                          {tx.unit_price > 0 && (
                            <div className="text-xs">
                              <span className="font-medium">Unit Price:</span> ${tx.unit_price.toFixed(2)}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 sm:p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 rounded-b-lg">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 sm:gap-0">
            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 truncate">
              {showTransactionDetail 
                ? `Transaction #${selectedTransaction?.id} details`
                : `Showing ${filteredTransactions.length} of ${transactions.length} transactions`
              }
            </p>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 dark:bg-gray-700 text-white rounded-lg hover:bg-gray-700 dark:hover:bg-gray-600 transition-colors text-sm sm:text-base w-full sm:w-auto"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Transaction Detail View Component
function TransactionDetailView({ transaction }: { transaction: Transaction | null }) {
  if (!transaction) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-gray-400 dark:text-gray-500 mb-2">⚠️</div>
          <p className="text-gray-600 dark:text-gray-400">No transaction selected</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Transaction Header */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
              Transaction #{transaction.id}
            </h3>
            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mt-1 break-all">
              Event ID: {transaction.event_id}
            </p>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-xl sm:text-2xl font-bold text-green-600 dark:text-green-400">
              ${transaction.amount.toFixed(2)}
            </div>
            <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
              {transaction.currency}
            </div>
          </div>
        </div>
      </div>

      {/* Transaction Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Basic Information */}
        <div className="space-y-3 sm:space-y-4">
          <h4 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Info className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
            Basic Information
          </h4>
          <div className="space-y-2 sm:space-y-3">
            <div className="flex items-center">
              <Clock className="w-4 h-4 text-gray-400 dark:text-gray-500 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Timestamp</p>
                <p className="text-sm text-gray-900 dark:text-white">
                  {new Date(transaction.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
            
            <div className="flex items-center">
              <TrendingUp className="w-4 h-4 text-gray-400 dark:text-gray-500 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Event Type</p>
                <p className="text-sm text-gray-900 dark:text-white">
                  {transaction.event_type.replace('_', ' ')}
                </p>
              </div>
            </div>
            
            <div className="flex items-center">
              <Package className="w-4 h-4 text-gray-400 dark:text-gray-500 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">SKU</p>
                <p className="text-sm text-gray-900 dark:text-white">
                  {transaction.sku || 'N/A'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center">
              <DollarSign className="w-4 h-4 text-gray-400 dark:text-gray-500 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Quantity</p>
                <p className="text-sm text-gray-900 dark:text-white">
                  {transaction.quantity.toFixed(0)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Financial Information */}
        <div className="space-y-3 sm:space-y-4">
          <h4 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <DollarSign className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
            Financial Details
          </h4>
          <div className="space-y-2 sm:space-y-3">
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Amount:</span>
              <span className="text-sm font-bold text-gray-900 dark:text-white">
                ${transaction.amount.toFixed(2)}
              </span>
            </div>
            
            {transaction.unit_price > 0 && (
              <div className="flex justify-between">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Unit Price:</span>
                <span className="text-sm text-gray-900 dark:text-white">
                  ${transaction.unit_price.toFixed(2)}
                </span>
              </div>
            )}
            
            {transaction.unit_cost > 0 && (
              <div className="flex justify-between">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Unit Cost:</span>
                <span className="text-sm text-gray-900 dark:text-white">
                  ${transaction.unit_cost.toFixed(2)}
                </span>
              </div>
            )}
            
            {transaction.unit_price > 0 && transaction.unit_cost > 0 && (
              <div className="flex justify-between">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Profit Margin:</span>
                <span className="text-sm text-green-600 dark:text-green-400">
                  {((transaction.unit_price - transaction.unit_cost) / transaction.unit_price * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Entities and Classification */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Entities */}
        <div className="space-y-3 sm:space-y-4">
          <h4 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <User className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
            Entities
          </h4>
          <div className="space-y-2 sm:space-y-3">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">From Entity</p>
              <p className="text-sm text-gray-900 dark:text-white font-mono">
                {transaction.from_entity}
              </p>
            </div>
            
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">To Entity</p>
              <p className="text-sm text-gray-900 dark:text-white font-mono">
                {transaction.to_entity}
              </p>
            </div>
          </div>
        </div>

        {/* Classification */}
        <div className="space-y-3 sm:space-y-4">
          <h4 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Building2 className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
            Classification
          </h4>
          <div className="space-y-2 sm:space-y-3">
            {transaction.buyer_type && (
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Buyer Type</p>
                <p className="text-sm text-gray-900 dark:text-white">{transaction.buyer_type}</p>
              </div>
            )}
            
            {transaction.use_type && (
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Use Type</p>
                <p className="text-sm text-gray-900 dark:text-white">{transaction.use_type}</p>
              </div>
            )}
            
            {transaction.sector && (
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Sector</p>
                <p className="text-sm text-gray-900 dark:text-white">{transaction.sector}</p>
              </div>
            )}
            
            {transaction.subsector && (
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Subsector</p>
                <p className="text-sm text-gray-900 dark:text-white">{transaction.subsector}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Description and Metadata */}
      {(transaction.description || transaction.metadata) && (
        <div className="space-y-3 sm:space-y-4">
          <h4 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Info className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
            Additional Information
          </h4>
          
          {transaction.description && (
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Description</p>
              <p className="text-sm text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-800 p-3 rounded-lg break-words">
                {transaction.description}
              </p>
            </div>
          )}
          
          {transaction.metadata && (
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Metadata</p>
              <pre className="text-xs text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto break-words">
                {JSON.stringify(transaction.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
