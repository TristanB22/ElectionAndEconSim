/**
 * Routing types for Valhalla integration
 */

export type RoutingMode = 
  | 'auto'
  | 'pedestrian'
  | 'bicycle'
  | 'bus'
  | 'transit'
  | 'truck'
  | 'motor_scooter'

export interface Route {
  coordinates: [number, number][]  // [[lon, lat], ...]
  distance_km: number
  distance_miles: number
  duration_minutes: number
  has_toll: boolean
  has_highway: boolean
  mode: RoutingMode
  mode_label: string
  directions?: string[]
}

export interface RouteRequest {
  start_lat: number
  start_lon: number
  end_lat: number
  end_lon: number
  mode?: RoutingMode
  include_directions?: boolean
  units?: 'miles' | 'kilometers'
}

export interface ModeOption {
  id: RoutingMode
  label: string
}

