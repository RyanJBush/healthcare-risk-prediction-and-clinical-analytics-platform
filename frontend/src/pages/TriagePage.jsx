import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiRequest } from '../api'

const statuses = ['new', 'reviewed', 'escalated', 'monitored']
const riskFilters = ['', 'medium', 'high']
const targetOptions = ['readmission', 'deterioration', 'adverse_event']

export default function TriagePage({ token }) {
  const [queue, setQueue] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [targetType, setTargetType] = useState('readmission')
  const [mode, setMode] = useState('queue')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)

  const loadQueue = useCallback(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (statusFilter) params.set('status', statusFilter)
    params.set('target_type', targetType)
    const endpoint = mode === 'watchlist' ? '/api/triage/watchlist' : '/api/triage/queue'
    apiRequest(`${endpoint}?${params.toString()}`, {}, token)
      .then((data) => {
        const filtered = riskFilter ? data.filter((item) => item.risk_category === riskFilter) : data
        setQueue(filtered)
        setError('')
      })
      .catch(() => {
        setQueue([])
        setError('Unable to load triage queue right now.')
      })
      .finally(() => setLoading(false))
  }, [mode, riskFilter, statusFilter, targetType, token])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadQueue()
  }, [loadQueue])

  async function updateStatus(patientId, reviewStatus) {
    setBusyId(patientId)
    try {
      await apiRequest(
        `/api/patients/${patientId}/review-status`,
        {
          method: 'PATCH',
          body: JSON.stringify({ review_status: reviewStatus }),
        },
        token,
      )
      loadQueue()
    } catch {
      setError('Unable to update review status right now.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Triage Queue</h1>
      <div className="rounded-xl bg-white p-4 shadow">
        <div className="mb-3 flex gap-2">
          <button
            type="button"
            onClick={() => setMode('queue')}
            className={`rounded px-3 py-1 text-sm ${mode === 'queue' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}
          >
            Alert Queue
          </button>
          <button
            type="button"
            onClick={() => setMode('watchlist')}
            className={`rounded px-3 py-1 text-sm ${mode === 'watchlist' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}
          >
            High-Risk Watchlist
          </button>
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm">
            Review status
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="ml-2 rounded border border-slate-300 px-2 py-1"
            >
              <option value="">All</option>
              {statuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Target
            <select value={targetType} onChange={(event) => setTargetType(event.target.value)} className="ml-2 rounded border border-slate-300 px-2 py-1">
              {targetOptions.map((target) => (
                <option key={target} value={target}>
                  {target}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Risk
            <select value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)} className="ml-2 rounded border border-slate-300 px-2 py-1">
              <option value="">All</option>
              {riskFilters.map((risk) => (
                <option key={risk || 'all'} value={risk}>
                  {risk || 'all'}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <div className="rounded-xl bg-white p-4 shadow">
        {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
        <ul className="space-y-2 text-sm">
          {loading ? <li className="rounded border border-slate-200 p-3 text-slate-500">Loading triage queue…</li> : null}
          {queue.map((item) => (
            <li key={item.patient_id} className="rounded border border-slate-200 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium">
                    <Link to={`/patients/${item.patient_id}`} className="text-blue-700 hover:underline">
                      {item.masked_identifier}
                    </Link>
                  </p>
                  <p className="text-slate-600">
                    {item.target_type} risk {item.risk_score.toFixed(2)} ({item.risk_category}) • confidence {item.confidence_score.toFixed(2)}
                  </p>
                  <p className="text-xs text-slate-500">Updated {new Date(item.updated_at).toLocaleString()}</p>
                </div>
                <select
                  value={item.review_status}
                  onChange={(event) => updateStatus(item.patient_id, event.target.value)}
                  className="rounded border border-slate-300 px-2 py-1"
                  disabled={busyId === item.patient_id}
                >
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>
            </li>
          ))}
          {!loading && queue.length === 0 ? (
            <li className="rounded border border-slate-200 p-3 text-slate-500">No patients match this queue filter.</li>
          ) : null}
        </ul>
      </div>
    </div>
  )
}
