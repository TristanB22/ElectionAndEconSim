export type SortKey = 'knowledge_strength' | 'display_name' | 'category_display_name' | 'familiarity_score' | 'distance_km_from_home' | 'visit_frequency' | 'recency_days' | 'number_of_times_visited' | 'times_seen'

export const PLACE_LIST_CONFIG = {
  defaultSortKey: 'knowledge_strength' as SortKey,
  defaultSortDir: 'desc' as 'asc' | 'desc',
  // Column order and metadata
  columns: [
    { key: 'display_name', label: 'Name', align: 'left', width: 'w-72' },
    { key: 'category_display_name', label: 'Category', align: 'left', width: 'w-40' },
    { key: 'knowledge_strength', label: 'Knowledge', align: 'center', width: 'w-48', sortable: true },
    { key: 'familiarity_score', label: 'Familiarity', align: 'right', width: 'w-28', sortable: true },
    { key: 'distance_km_from_home', label: 'Distance', align: 'right', width: 'w-24', sortable: true },
    { key: 'visit_frequency', label: 'Visits/mo', align: 'right', width: 'w-24', sortable: true },
    { key: 'encounters', label: 'Encounters', align: 'right', width: 'w-28' },
    { key: 'last_seen', label: 'Last Seen', align: 'left', width: 'w-40', sortable: true },
  ],
  // Category chips to render as quick filters (fallback to dynamic categories)
  quickCategories: [
    'Restaurant', 'Café', 'Fast Food', 'Grocery Store', 'Supermarket', 'Gas Station', 'Pharmacy', 'Park', 'School', 'Bank'
  ],
  // Style tokens
  styles: {
    rowHover: 'hover:bg-neutral-800/50',
    rowStripe: 'even:bg-neutral-900/30',
    container: 'bg-[#0b0e11] border border-neutral-700 rounded-2xl',
    barGradient: 'bg-gradient-to-r from-cyan-400 to-blue-500',
    barBg: 'bg-slate-800',
  },
  // Distance heat coloring thresholds in km
  distanceBucketsKm: [0.5, 1, 2, 5, 10],
}

export function distanceClass(km?: number) {
  if (km == null) return 'text-slate-300'
  const v = Number(km)
  if (v <= 0.5) return 'text-teal-300'
  if (v <= 1) return 'text-teal-200'
  if (v <= 2) return 'text-teal-100'
  if (v <= 5) return 'text-slate-300'
  return 'text-slate-400'
}

export function formatEncounters(seen?: number, visited?: number) {
  const s = Number(seen ?? 0)
  const v = Number(visited ?? 0)
  return `${s}x seen / ${v}x visited`
}
