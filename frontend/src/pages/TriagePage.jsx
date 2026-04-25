import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiRequest } from '../api'

const statuses = ['new', 'reviewed', 'escalated', 'monitored']

export default function TriagePage({ token }) {
  const [queue, setQueue] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)

  const loadQueue = useCallback(() => {
    setLoading(true)
    const query = statusFilter ? `?status=${statusFilter}` : ''
    apiRequest(`/api/triage/queue${query}`, {}, token)
      .then((data) => {
        setQueue(data)
        setError('')
      })
      .catch(() => {
        setQueue([])
        setError('Unable to load triage queue right now.')
      })
      .finally(() => setLoading(false))
  }, [statusFilter, token])

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
        <label className="text-sm">
          Filter by review status
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
