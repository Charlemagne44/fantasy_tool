import { useEffect, useMemo, useState } from 'react'
import { loadSamplePlayers, optimizeLineups, uploadPlayers } from './api'
import type { Lineup, Player, Position } from './types'
import './App.css'

/** Controlled number input that allows clearing/retyping without snapping to 0. */
function NumberField({
  value,
  onChange,
  min,
  max,
  step,
  disabled,
}: {
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  step?: number
  disabled?: boolean
}) {
  const [text, setText] = useState(String(value))

  useEffect(() => {
    setText(String(value))
  }, [value])

  function commit(raw: string) {
    if (raw.trim() === '' || raw === '-' || raw === '.') {
      setText(String(value))
      return
    }
    let next = Number(raw)
    if (!Number.isFinite(next)) {
      setText(String(value))
      return
    }
    if (min != null) next = Math.max(min, next)
    if (max != null) next = Math.min(max, next)
    onChange(next)
    setText(String(next))
  }

  return (
    <input
      type="number"
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      value={text}
      onChange={(e) => {
        const raw = e.target.value
        setText(raw)
        if (raw.trim() === '' || raw === '-' || raw === '.') return
        const next = Number(raw)
        if (!Number.isFinite(next)) return
        if (min != null && next < min) return
        if (max != null && next > max) return
        onChange(next)
      }}
      onBlur={() => commit(text)}
    />
  )
}

type SortKey =
  | 'name'
  | 'position'
  | 'team'
  | 'salary'
  | 'projection'
  | 'floor'
  | 'ceiling'
  | 'small_field_own'
  | 'large_field_own'

const POSITIONS: Array<Position | 'ALL'> = ['ALL', 'QB', 'RB', 'WR', 'TE', 'DST']

function formatSalary(n: number): string {
  return `$${n.toLocaleString()}`
}

function exportLineups(lineups: Lineup[]) {
  const rows = [
    [
      'rank',
      'slot',
      'name',
      'position',
      'team',
      'salary',
      'projection',
      'floor',
      'ceiling',
      'score',
    ].join(','),
  ]
  for (const lu of lineups) {
    for (const p of lu.players) {
      rows.push(
        [
          lu.rank,
          p.slot,
          `"${p.name}"`,
          p.position,
          p.team,
          p.salary,
          p.projection,
          p.floor,
          p.ceiling,
          p.score,
        ].join(','),
      )
    }
  }
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'lineups.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function App() {
  const [players, setPlayers] = useState<Player[]>([])
  const [locked, setLocked] = useState<Set<string>>(new Set())
  const [excluded, setExcluded] = useState<Set<string>>(new Set())
  const [salaryCap, setSalaryCap] = useState(50000)
  const [aggression, setAggression] = useState(0)
  const [numLineups, setNumLineups] = useState(1)
  const [minUnique, setMinUnique] = useState(1)
  const [minFloorEnabled, setMinFloorEnabled] = useState(false)
  const [minFloor, setMinFloor] = useState(80)
  const [query, setQuery] = useState('')
  const [posFilter, setPosFilter] = useState<Position | 'ALL'>('ALL')
  const [sortKey, setSortKey] = useState<SortKey>('projection')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [lineups, setLineups] = useState<Lineup[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    let list = players.filter((p) => {
      if (posFilter !== 'ALL' && p.position !== posFilter) return false
      if (!q) return true
      return (
        p.name.toLowerCase().includes(q) ||
        p.team.toLowerCase().includes(q) ||
        p.opp.toLowerCase().includes(q)
      )
    })
    list = [...list].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
      }
      return sortDir === 'asc'
        ? Number(av) - Number(bv)
        : Number(bv) - Number(av)
    })
    return list
  }, [players, query, posFilter, sortKey, sortDir])

  async function onUpload(file: File | null) {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const next = await uploadPlayers(file)
      setPlayers(next)
      setLocked(new Set())
      setExcluded(new Set())
      setLineups([])
      setStatus(`Loaded ${next.length} players from ${file.name}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  async function onSample() {
    setBusy(true)
    setError(null)
    try {
      const next = await loadSamplePlayers()
      setPlayers(next)
      setLocked(new Set())
      setExcluded(new Set())
      setLineups([])
      setStatus(`Loaded ${next.length} players from sample ETR slate`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load sample')
    } finally {
      setBusy(false)
    }
  }

  async function onOptimize() {
    if (!players.length) {
      setError('Load a player pool first')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await optimizeLineups({
        players,
        salary_cap: salaryCap,
        aggression,
        locked_ids: [...locked],
        excluded_ids: [...excluded],
        num_lineups: numLineups,
        min_unique: minUnique,
        min_floor: minFloorEnabled ? minFloor : null,
      })
      setLineups(res.lineups)
      setStatus(`Built ${res.lineups.length} lineup${res.lineups.length === 1 ? '' : 's'}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Optimize failed')
    } finally {
      setBusy(false)
    }
  }

  function toggleLock(id: string) {
    setLocked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else {
        next.add(id)
        setExcluded((ex) => {
          const copy = new Set(ex)
          copy.delete(id)
          return copy
        })
      }
      return next
    })
  }

  function toggleExclude(id: string) {
    setExcluded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else {
        next.add(id)
        setLocked((lk) => {
          const copy = new Set(lk)
          copy.delete(id)
          return copy
        })
      }
      return next
    })
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'name' || key === 'team' || key === 'position' ? 'asc' : 'desc')
    }
  }

  return (
    <div className="app">
      <header className="top">
        <div>
          <p className="eyebrow">DraftKings Classic</p>
          <h1>Lineup</h1>
          <p className="sub">
            Build lineups from ETR floor, median, and ceiling projections.
          </p>
        </div>
        <div className="top-actions">
          <label className="file-btn">
            Upload CSV
            <input
              type="file"
              accept=".csv,text/csv"
              disabled={busy}
              onChange={(e) => onUpload(e.target.files?.[0] ?? null)}
            />
          </label>
          <button type="button" className="ghost" disabled={busy} onClick={onSample}>
            Sample slate
          </button>
        </div>
      </header>

      {(error || status) && (
        <div className={`banner ${error ? 'error' : 'ok'}`}>
          {error ?? status}
        </div>
      )}

      <section className="controls">
        <label>
          Salary cap
          <NumberField
            step={100}
            min={1}
            value={salaryCap}
            onChange={setSalaryCap}
          />
        </label>

        <div className="aggression">
          <div className="aggression-head">
            <span>Aggression</span>
            <strong>{aggression.toFixed(2)}</strong>
          </div>
          <input
            type="range"
            min={-1}
            max={1}
            step={0.05}
            value={aggression}
            onChange={(e) => setAggression(Number(e.target.value))}
          />
          <div className="presets" role="group" aria-label="Aggression presets">
            <button
              type="button"
              className={aggression === -0.25 ? 'active' : undefined}
              onClick={() => setAggression(-0.25)}
            >
              Cash
            </button>
            <button
              type="button"
              className={aggression === 0 ? 'active' : undefined}
              onClick={() => setAggression(0)}
            >
              Balanced
            </button>
            <button
              type="button"
              className={aggression === 0.75 ? 'active' : undefined}
              onClick={() => setAggression(0.75)}
            >
              GPP
            </button>
          </div>
          <p className="hint">Floor ← Median (DK Proj) → Ceiling</p>
        </div>

        <label>
          Lineups
          <NumberField
            min={1}
            max={20}
            value={numLineups}
            onChange={setNumLineups}
          />
        </label>

        <label>
          Min unique
          <NumberField
            min={1}
            max={3}
            value={minUnique}
            onChange={setMinUnique}
          />
        </label>

        <div className="min-floor">
          <label className="check">
            <input
              type="checkbox"
              checked={minFloorEnabled}
              onChange={(e) => setMinFloorEnabled(e.target.checked)}
            />
            Min lineup floor
          </label>
          <NumberField
            min={0}
            disabled={!minFloorEnabled}
            value={minFloor}
            onChange={setMinFloor}
          />
        </div>

        <button
          type="button"
          className="primary"
          disabled={busy || !players.length}
          onClick={onOptimize}
        >
          {busy ? 'Working…' : 'Optimize'}
        </button>
      </section>

      <section className="pool">
        <div className="pool-head">
          <h2>
            Players{' '}
            <span>
              {players.length ? `${filtered.length} of ${players.length}` : 'No slate loaded'}
            </span>
          </h2>
          <div className="pool-filters">
            <input
              type="search"
              placeholder="Search players"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <select
              value={posFilter}
              onChange={(e) => setPosFilter(e.target.value as Position | 'ALL')}
            >
              {POSITIONS.map((p) => (
                <option key={p} value={p}>
                  {p === 'ALL' ? 'All' : p}
                </option>
              ))}
            </select>
            <span className="meta">
              {locked.size} locked · {excluded.size} out
            </span>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Lock</th>
                <th>Excl</th>
                <th onClick={() => toggleSort('name')}>Player</th>
                <th onClick={() => toggleSort('position')}>Pos</th>
                <th onClick={() => toggleSort('team')}>Team</th>
                <th>Opp</th>
                <th onClick={() => toggleSort('salary')}>Salary</th>
                <th onClick={() => toggleSort('projection')}>Proj</th>
                <th onClick={() => toggleSort('floor')}>Floor</th>
                <th onClick={() => toggleSort('ceiling')}>Ceil</th>
                <th onClick={() => toggleSort('small_field_own')}>Own S</th>
                <th onClick={() => toggleSort('large_field_own')}>Own L</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => {
                const isLocked = locked.has(p.id)
                const isExcluded = excluded.has(p.id)
                return (
                  <tr
                    key={p.id}
                    className={
                      isLocked ? 'locked' : isExcluded ? 'excluded' : undefined
                    }
                  >
                    <td>
                      <input
                        type="checkbox"
                        checked={isLocked}
                        onChange={() => toggleLock(p.id)}
                      />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        checked={isExcluded}
                        onChange={() => toggleExclude(p.id)}
                      />
                    </td>
                    <td className="name">{p.name}</td>
                    <td>{p.position}</td>
                    <td>{p.team}</td>
                    <td>{p.opp}</td>
                    <td>{formatSalary(p.salary)}</td>
                    <td>{p.projection.toFixed(1)}</td>
                    <td>{p.floor.toFixed(1)}</td>
                    <td>{p.ceiling.toFixed(1)}</td>
                    <td>{p.small_field_own.toFixed(1)}%</td>
                    <td>{p.large_field_own.toFixed(1)}%</td>
                  </tr>
                )
              })}
              {!filtered.length && (
                <tr>
                  <td colSpan={12} className="empty">
                    Upload an ETR CSV or load the sample slate to begin.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="results">
        <div className="results-head">
          <h2>Lineups</h2>
          {!!lineups.length && (
            <button type="button" className="ghost" onClick={() => exportLineups(lineups)}>
              Export CSV
            </button>
          )}
        </div>

        {!lineups.length && (
          <p className="empty-copy">Your optimized lineups will show up here.</p>
        )}

        <div className="lineup-grid">
          {lineups.map((lu) => (
            <article key={lu.rank} className="lineup">
              <header>
                <h3>#{lu.rank}</h3>
                <div className="totals">
                  <span>Score {lu.total_score.toFixed(1)}</span>
                  <span>Proj {lu.total_projection.toFixed(1)}</span>
                  <span>Floor {lu.total_floor.toFixed(1)}</span>
                  <span>Ceil {lu.total_ceiling.toFixed(1)}</span>
                  <span>
                    {formatSalary(lu.total_salary)} / {formatSalary(salaryCap)}
                  </span>
                  <span>Left {formatSalary(lu.leftover_salary)}</span>
                </div>
              </header>
              <table>
                <thead>
                  <tr>
                    <th>Slot</th>
                    <th>Player</th>
                    <th>Pos</th>
                    <th>Sal</th>
                    <th>Proj</th>
                    <th>Floor</th>
                    <th>Ceil</th>
                  </tr>
                </thead>
                <tbody>
                  {lu.players.map((p) => (
                    <tr key={`${lu.rank}-${p.id}`}>
                      <td>{p.slot}</td>
                      <td>
                        {p.name}{' '}
                        <span className="muted">
                          {p.team} {p.opp}
                        </span>
                      </td>
                      <td>{p.position}</td>
                      <td>{formatSalary(p.salary)}</td>
                      <td>{p.projection.toFixed(1)}</td>
                      <td>{p.floor.toFixed(1)}</td>
                      <td>{p.ceiling.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
