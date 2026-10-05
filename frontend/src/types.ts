export type Position = 'QB' | 'RB' | 'WR' | 'TE' | 'DST'
export type Slot = 'QB' | 'RB' | 'WR' | 'TE' | 'FLEX' | 'DST'

export interface Player {
  id: string
  name: string
  position: Position
  team: string
  opp: string
  salary: number
  projection: number
  floor: number
  ceiling: number
  value: number
  small_field_own: number
  large_field_own: number
}

export interface LineupPlayer {
  id: string
  name: string
  position: Position
  slot: Slot
  team: string
  opp: string
  salary: number
  projection: number
  floor: number
  ceiling: number
  score: number
}

export interface Lineup {
  rank: number
  players: LineupPlayer[]
  total_salary: number
  leftover_salary: number
  total_projection: number
  total_floor: number
  total_ceiling: number
  total_score: number
}

export interface OptimizeResponse {
  lineups: Lineup[]
  salary_cap: number
  aggression: number
}
