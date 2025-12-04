// Utility to normalize agent data into a UI-ready model with derived fields
// Implements schema_to_ui mapping, value formatting, and redaction rules

export type SchemaToUi = Record<string, any>

export interface NormalizedAgentModel {
  snapshot: {
    netWorthUsd: number | null
    homeValueUsd: number | null
    householdSize: number | null
    adults: number | null
    children: number | null
  }
  residence: {
    address: string | null
    lat: number | null
    lon: number | null
    dwellingType: string | null
    homeSqft: number | null
    zip5?: string | null
  }
  civicVoter: Record<string, any>
  consumerIncome: Record<string, any>
  identifiers: { label: string; value: string }[]
  allData: any
  sources?: Record<string, { source?: string; confidence?: number }>
}

export function zip5(raw: string | number | null | undefined): string | null {
  if (raw == null) return null
  const s = String(raw).replace(/\D/g, '')
  if (s.length === 0) return null
  return s.padStart(5, '0').slice(0, 5)
}

export function coords6dp(v: number | string | null | undefined): number | null {
  if (v == null || v === '' || v === '—') return null
  const n = Number(v)
  if (Number.isNaN(n)) return null
  return Number(n.toFixed(6))
}

export function estRangeMid(range: string | null | undefined): number | null {
  if (!range) return null
  // Examples: "$750,000 - $999,999", "750000-999999"
  const m = String(range).match(/([\d,\.]+)\s*[–-]\s*\$?([\d,\.]+)/)
  if (!m) return null
  const a = Number(m[1].replace(/[,\s]/g, ''))
  const b = Number(m[2].replace(/[,\s]/g, ''))
  if (Number.isNaN(a) || Number.isNaN(b)) return null
  return Math.round((a + b) / 2)
}

function scrub(value: any): any | null {
  if (value == null) return null
  const s = typeof value === 'string' ? value.trim() : value
  if (s === '' || s === '—' || s === 'null' || s === 'undefined' || s === '0.0') return null
  return value
}

export function normalizeAgent(agentJson: any, schemaToUi: SchemaToUi): NormalizedAgentModel {
  const l2Flat = agentJson?.l2_data_flat || {}
  const l2 = agentJson?.l2_data || {}
  const out: NormalizedAgentModel = {
    snapshot: {
      netWorthUsd: null,
      homeValueUsd: null,
      householdSize: null,
      adults: null,
      children: null,
    },
    residence: {
      address: null,
      lat: null,
      lon: null,
      dwellingType: null,
      homeSqft: null,
      zip5: null,
    },
    civicVoter: {},
    consumerIncome: {},
    identifiers: [],
    allData: agentJson,
    sources: {},
  }

  // Helper to get value from map paths (flat first, then nested path "a.b.c")
  const getPath = (path: string): any => {
    if (!path) return null
    if (l2Flat[path] !== undefined) return l2Flat[path]
    const segs = path.split('.')
    let ref: any = agentJson
    for (const seg of segs) {
      if (ref == null) return null
      ref = ref[seg]
    }
    return ref ?? null
  }

  const mapField = (valueOrPaths: string | string[]): any => {
    if (Array.isArray(valueOrPaths)) {
      for (const p of valueOrPaths) {
        const v = scrub(getPath(p))
        if (v != null) return v
      }
      return null
    }
    return scrub(getPath(valueOrPaths))
  }

  // Residence
  const resMap = schemaToUi?.Residence || {}
  // Address: street, city, state ZIP (deduped)
  const street = scrub(
    (['l2_data.l2_location.Residence_Addresses_AddressLine', 'l2_data_flat.Residence_Addresses_AddressLine'] as string[])
      .map(p => scrub(getPath(p)))
      .find(Boolean)
  )
  const city = scrub(getPath('l2_data.l2_location.Residence_Addresses_City') || l2Flat['Residence_Addresses_City'])
  const state = scrub(getPath('l2_data.l2_location.Residence_Addresses_State') || l2Flat['Residence_Addresses_State'])
  const zipRaw = scrub(getPath('l2_data.l2_location.Residence_Addresses_Zip') || l2Flat['Residence_Addresses_Zip'])
  const zip = zip5(zipRaw as any)
  const addressParts: string[] = []
  if (street) addressParts.push(String(street))
  const cityState = [city, state].filter(Boolean).join(', ')
  if (cityState) addressParts.push(cityState + (zip ? ` ${zip}` : ''))
  out.residence.address = addressParts.length ? addressParts.join(', ') : null
  out.residence.lat = coords6dp(mapField(resMap.lat))
  out.residence.lon = coords6dp(mapField(resMap.lon))
  if (Array.isArray(resMap.dwellingType)) {
    const dt = resMap.dwellingType
      .map((p: string) => scrub(getPath(p)))
      .find(Boolean)
    out.residence.dwellingType = (dt as any) ?? null
  } else {
    out.residence.dwellingType = (mapField(resMap.dwellingType) as any) ?? null
  }
  const sqft = mapField(resMap.homeSqft)
  out.residence.homeSqft = sqft != null ? Number(sqft) : null
  // Zip normalization if present in flat keys
  const zipFlat = l2Flat['Residence_Addresses_Zip'] || l2?.l2_location?.Residence_Addresses_Zip
  out.residence.zip5 = zip5(zipFlat)

  // Snapshot
  const snapMap = schemaToUi?.Snapshot || {}
  const homeValueRaw = mapField(snapMap.homeValueUsd)
  const homeValueRange = scrub(l2Flat['ConsumerData_PASS_Prospector_Home_Value_Mortgage_File']) || scrub(l2?.l2_other_part_3?.ConsumerData_PASS_Prospector_Home_Value_Mortgage_File)
  const homeValue = typeof homeValueRaw === 'number' ? homeValueRaw : estRangeMid(String(homeValueRange || ''))
  out.snapshot.homeValueUsd = homeValue ?? null
  out.snapshot.householdSize = mapField(snapMap.householdSize) != null ? Number(mapField(snapMap.householdSize)) : null
  out.snapshot.adults = mapField(snapMap.adults) != null ? Math.floor(Number(mapField(snapMap.adults))) : null
  out.snapshot.children = mapField(snapMap.children) != null ? Math.floor(Number(mapField(snapMap.children))) : null

  // Mortgage estimate and net worth derivation
  const mortgageAmount = scrub(l2Flat['Mortgage_Amount']) || scrub(l2?.l2_other_part_3?.Mortgage_Amount)
  const liquidEstimate = scrub(l2Flat['Liquid_Savings']) || null
  const assessed = scrub(l2Flat['Residence_Addresses_Tax_Assessed_Value']) || null
  const hv = homeValue ?? (assessed != null ? Number(assessed) : null)
  const netWorth = (hv != null ? Number(hv) : 0) - (mortgageAmount != null ? Number(mortgageAmount) : 0) + (liquidEstimate != null ? Number(liquidEstimate) : 0)
  out.snapshot.netWorthUsd = hv == null && mortgageAmount == null && liquidEstimate == null ? null : Math.round(netWorth)

  // Civic/Voter (basic common fields)
  out.civicVoter = {
    party: scrub(l2Flat['Parties_Description']) ?? scrub(l2?.l2_political_part_1?.Parties_Description) ?? null,
    precinct: scrub(l2Flat['Voters_PrecinctName']) ?? scrub(l2?.l2_agent_core?.Voters_PrecinctName) ?? null,
    voterId: agentJson?.agent_id ?? null,
    registrationDate: scrub(l2Flat['Voters_RegistrationDate']) ?? scrub(l2?.l2_agent_core?.Voters_RegistrationDate) ?? null,
  }

  // Consumer & Income
  out.consumerIncome = {
    estimatedIncomeUsd: scrub(l2Flat['ConsumerData_Estimated_Income_Amount']) ?? scrub(l2?.l2_other_part_1?.ConsumerData_Estimated_Income_Amount) ?? null,
    incomeRange: scrub(l2Flat['ConsumerData_Estimated_HH_Income']) ?? scrub(l2?.l2_other_part_1?.ConsumerData_Estimated_HH_Income) ?? null,
    creditBand: scrub(l2Flat['ConsumerData_Credit_Rating']) ?? scrub(l2?.l2_other_part_1?.ConsumerData_Credit_Rating) ?? null,
    presenceOfChildren: scrub(l2Flat['ConsumerData_Presence_of_Children']) ?? scrub(l2?.l2_other_part_1?.ConsumerData_Presence_of_Children) ?? null,
    maritalStatus: scrub(l2Flat['ConsumerData_Marital_Status']) ?? scrub(l2?.l2_other_part_1?.ConsumerData_Marital_Status) ?? null,
    education: scrub(l2Flat['ConsumerData_Education_of_Person']) ?? scrub(l2?.l2_other_part_1?.ConsumerData_Education_of_Person) ?? null,
    occupation: scrub(l2Flat['ConsumerData_Occupation']) ?? scrub(l2?.l2_other_part_1?.ConsumerData_Occupation) ?? null,
    interests: null, // to be bucketed by caller if needed
  }

  // Sensitive identifiers: MAIDs/IPs (best-effort lookup from flat keys)
  const sensitive: { label: string; value: string }[] = []
  Object.entries(l2Flat).forEach(([k, v]) => {
    if (v == null) return
    const key = k.toLowerCase()
    if (key.includes('maid') || key.includes('advertising_id') || key.match(/\bip(v?4|v?6)?\b/)) {
      const s = String(v)
      if (s.length >= 6) sensitive.push({ label: k, value: s })
    }
  })
  out.identifiers = sensitive

  return out
}

// Default schema_to_ui map (can be overridden by caller)
export const DEFAULT_SCHEMA_TO_UI: SchemaToUi = {
  Residence: {
    address: [
      'l2_data.l2_location.Residence_Addresses_AddressLine',
      'l2_data_flat.Residence_Addresses_AddressLine',
      'l2_data.l2_location.Residence_Addresses_City',
      'l2_data.l2_location.Residence_Addresses_State',
      'l2_data.l2_location.Residence_Addresses_Zip',
    ],
    lat: 'l2_data.l2_geo.latitude',
    lon: 'l2_data.l2_geo.longitude',
    dwellingType: [
      'l2_data.l2_other_part_3.ConsumerData_Dwelling_Type',
      'l2_data.l2_location.Residence_Addresses_Property_Type',
      'l2_data_flat.ConsumerData_Dwelling_Type',
    ],
    homeSqft: 'l2_data.l2_location.Residence_Addresses_Property_Home_Square_Footage',
  },
  Snapshot: {
    netWorth: 'derived.netWorthUsd',
    householdSize: 'l2_data.l2_other_part_1.ConsumerData_Number_Of_Persons_in_HH',
    adults: 'l2_data.l2_other_part_1.ConsumerData_Number_Of_Adults_in_HH',
    children: 'l2_data.l2_other_part_1.ConsumerData_Number_Of_Children_in_HH',
    homeValueUsd: 'l2_data.l2_other_part_3.ConsumerData_PASS_Prospector_Home_Value_Mortgage_File',
  },
}


