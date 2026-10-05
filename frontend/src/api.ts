import type { OptimizeResponse, Player } from './types'

async function getError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data.detail === 'string') return data.detail
    return JSON.stringify(data.detail ?? data)
  } catch {
    return res.statusText
  }
}

export async function uploadPlayers(file: File): Promise<Player[]> {
  const body = new FormData()
  body.append('file', file)
  const res = await fetch('/api/players/upload', { method: 'POST', body })
  if (!res.ok) throw new Error(await getError(res))
  const data = await res.json()
  return data.players as Player[]
}

export async function loadSamplePlayers(): Promise<Player[]> {
  const res = await fetch('/api/players/sample')
  if (!res.ok) throw new Error(await getError(res))
  const data = await res.json()
  return data.players as Player[]
}

export async function optimizeLineups(payload: {
  players: Player[]
  salary_cap: number
  aggression: number
  locked_ids: string[]
  excluded_ids: string[]
  num_lineups: number
  min_unique: number
  min_floor: number | null
}): Promise<OptimizeResponse> {
  const res = await fetch('/api/optimize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await getError(res))
  return res.json()
}
