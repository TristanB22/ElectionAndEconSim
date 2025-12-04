// Utility to normalize POI data into a UI-ready model with derived fields
// Implements schema_to_ui mapping, value formatting, and field extraction

export type SchemaToUi = Record<string, any>

export interface NormalizedPoiModel {
  identity: {
    osmId: number | string | null
    name: string | null
    displayName: string | null
    category: string | null
    subcategory: string | null
  }
  location: {
    lat: number | null
    lon: number | null
    address: string | null
    city: string | null
    state: string | null
    postcode: string | null
    country: string | null
  }
  contact: {
    phone: string | null
    website: string | null
    email: string | null
  }
  amenities: Record<string, any>
  hours: string | null
  allData: any
}

function scrub(value: any): any | null {
  if (value == null) return null
  const s = typeof value === 'string' ? value.trim() : value
  if (s === '' || s === '—' || s === 'null' || s === 'undefined') return null
  return value
}

export function normalizePoi(poiJson: any, schemaToUi: SchemaToUi = {}): NormalizedPoiModel {
  const props = poiJson?.properties || poiJson || {}
  const geometry = poiJson?.geometry
  const coords = Array.isArray(geometry?.coordinates) ? geometry.coordinates : [null, null]

  const out: NormalizedPoiModel = {
    identity: {
      osmId: null,
      name: null,
      displayName: null,
      category: null,
      subcategory: null,
    },
    location: {
      lat: null,
      lon: null,
      address: null,
      city: null,
      state: null,
      postcode: null,
      country: null,
    },
    contact: {
      phone: null,
      website: null,
      email: null,
    },
    amenities: {},
    hours: null,
    allData: poiJson,
  }

  // Identity
  out.identity.osmId = scrub(props.osm_id || props.id || props['@id'])
  out.identity.name = scrub(props.name)
  out.identity.displayName = scrub(props.display_name || props.name)
  out.identity.category = scrub(props.category || props.amenity || props.shop || props.tourism || props.leisure)
  out.identity.subcategory = scrub(props.subcategory || props.healthcare || props.cuisine)

  // Location
  out.location.lat = coords[1] != null ? Number(Number(coords[1]).toFixed(6)) : null
  out.location.lon = coords[0] != null ? Number(Number(coords[0]).toFixed(6)) : null
  
  // Address components
  const street = scrub(props['addr:street'] || props['addr:housenumber'])
  const city = scrub(props['addr:city'])
  const state = scrub(props['addr:state'])
  const postcode = scrub(props['addr:postcode'] || props['addr:postcode'])
  const country = scrub(props['addr:country'])
  
  out.location.city = city
  out.location.state = state
  out.location.postcode = postcode
  out.location.country = country
  
  // Build full address
  const addrParts: string[] = []
  if (street) addrParts.push(String(street))
  const cityState = [city, state].filter(Boolean).join(', ')
  if (cityState) addrParts.push(cityState + (postcode ? ` ${postcode}` : ''))
  if (country && !cityState) addrParts.push(String(country))
  out.location.address = addrParts.length ? addrParts.join(', ') : null

  // Contact
  out.contact.phone = scrub(props.phone || props['contact:phone'])
  out.contact.website = scrub(props.website || props['contact:website'])
  out.contact.email = scrub(props.email || props['contact:email'])

  // Hours
  out.hours = scrub(props.opening_hours || props.hours)

  // Amenities (collect relevant fields)
  const amenityKeys = ['wheelchair', 'outdoor_seating', 'takeaway', 'delivery', 'parking', 'wifi', 'payment:cash', 'payment:credit_cards']
  amenityKeys.forEach(key => {
    const val = scrub(props[key])
    if (val != null) out.amenities[key] = val
  })

  // Healthcare specialties
  if (props['healthcare:speciality']) {
    out.amenities.speciality = scrub(props['healthcare:speciality'])
  }

  return out
}

export const DEFAULT_POI_SCHEMA: SchemaToUi = {
  // Can be extended for specific category mappings
}
