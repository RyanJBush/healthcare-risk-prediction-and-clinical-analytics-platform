import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import { apiRequest } from '../api'

const COLORS = ['#16a34a', '#f59e0b', '#dc2626']
const reviewStatusOptions = ['', 'new', 'reviewed', 'escalated', 'monitored']
const riskCategoryOptions = ['', 'low', 'medium', 'high']
const targetOptions = ['readmission', 'deterioration', 'adverse_event']

export default function DashboardPage({ token }) {
  const [metrics, setMetrics] = useState(null)
  const [cohorts, setCohorts] = useState(null)
  const [cohortRows, setCohortRows] = useState([])
  const [cohortLoading, setCohortLoading] = useState(true)
  const [error, setError] = useState('')
  const [cohortError, setCohortError] = useState('')
  const [filters, setFilters] = useState({
    review_status: '',
    risk_category: '',
    target_type: 'readmission',
  })

  useEffect(() => {
    Promise.all([apiRequest('/api/metrics/summary', {}, token), apiRequest('/api/metrics/cohorts', {}, token)])
      .then(([nextMetrics, nextCohorts]) => {
        setMetrics(nextMetrics)
        setCohorts(nextCohorts)
        setError('')
      })
      .catch((loadError) => {
        setMetrics(null)
        setCohorts(null)
        setError(loadError.message || 'Unable to load dashboard metrics.')
      })
  }, [token])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCohortLoading(true)
    const params = new URLSearchParams()
    if (filters.review_status) params.set('review_status', filters.review_status)
    if (filters.risk_category) params.set('risk_category', filters.risk_category)
    params.set('target_type', filters.target_type)

    apiRequest(`/api/cohorts/filter?${params.toString()}`, {}, token)
      .then((rows) => {
        setCohortRows(rows)
        setCohortError('')
      })
      .catch((loadError) => {
        setCohortRows([])
        setCohortError(loadError.message || 'Unable to load cohort drill-down.')
      })
      .finally(() => setCohortLoading(false))
  }, [filters, token])

  const chartData = metrics
    ? Object.entries(metrics.by_category).map(([name, value]) => ({ name, value }))
    : []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <div className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
        Clinical decision support only. Use with full chart review and clinician judgment.
      </div>
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
        <KpiCard label="High-Risk Patients" value={metrics?.high_risk_patients ?? 0} />
        <KpiCard label="Average Risk" value={metrics ? metrics.average_risk_score.toFixed(2) : '0.00'} />
        <KpiCard label="Alerts Triggered" value={metrics?.alerts_triggered ?? 0} />
        <KpiCard label="Recall @ Threshold" value={metrics ? metrics.recall_at_threshold.toFixed(2) : '0.00'} />
        <KpiCard label="Monitored Cohort" value={metrics?.monitored_cohort_size ?? 0} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-4 text-lg font-medium">Risk Distribution</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={chartData} dataKey="value" nameKey="name" outerRadius={90}>
                  {chartData.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-4 text-lg font-medium">Cohort Summary</h2>
          <ul className="space-y-2 text-sm">
            {cohorts
              ? Object.entries(cohorts.by_review_status).map(([status, count]) => (
                  <li key={status} className="flex justify-between rounded border border-slate-200 px-3 py-2">
                    <span className="capitalize">{status}</span>
                    <span>{count}</span>
                  </li>
                ))
              : null}
          </ul>
          <p className="mt-4 text-xs text-slate-500">High-risk watchlist size: {cohorts?.high_risk_watchlist_size ?? 0}</p>
        </div>
      </div>
      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-4 text-lg font-medium">Average Risk by Target</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {targetOptions.map((target) => (
            <div key={target} className="rounded border border-slate-200 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">{target}</p>
              <p className="mt-1 text-xl font-semibold">{(cohorts?.average_risk_by_target?.[target] ?? 0).toFixed(2)}</p>
            </div>
          ))}
        </div>
      </div>
      <section className="rounded-xl bg-white p-4 shadow">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-medium">Cohort Drill-Down</h2>
          <div className="flex flex-wrap gap-2 text-sm">
            <FilterSelect
              label="Target"
              value={filters.target_type}
              options={targetOptions}
              onChange={(value) => setFilters((current) => ({ ...current, target_type: value }))}
            />
            <FilterSelect
              label="Review"
              value={filters.review_status}
              options={reviewStatusOptions}
              onChange={(value) => setFilters((current) => ({ ...current, review_status: value }))}
            />
            <FilterSelect
              label="Risk"
              value={filters.risk_category}
              options={riskCategoryOptions}
              onChange={(value) => setFilters((current) => ({ ...current, risk_category: value }))}
            />
          </div>
        </div>
        {cohortError ? <p className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">{cohortError}</p> : null}
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Patient</th>
                <th className="px-3 py-2">Review</th>
                <th className="px-3 py-2">Risk</th>
                <th className="px-3 py-2">Score</th>
              </tr>
            </thead>
            <tbody>
              {cohortLoading ? (
                <tr>
                  <td className="px-3 py-3 text-slate-500" colSpan={4}>
                    Loading cohort rows…
                  </td>
                </tr>
              ) : null}
              {!cohortLoading &&
                cohortRows.map((row) => (
                  <tr key={row.patient_id} className="border-t border-slate-100">
                    <td className="px-3 py-2">
                      <Link to={`/patients/${row.patient_id}`} className="text-blue-700 hover:underline">
                        {row.masked_identifier}
                      </Link>
                    </td>
                    <td className="px-3 py-2 capitalize">{row.review_status}</td>
                    <td className="px-3 py-2 capitalize">{row.risk_category}</td>
                    <td className="px-3 py-2">{row.risk_score.toFixed(2)}</td>
                  </tr>
                ))}
              {!cohortLoading && cohortRows.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-slate-500" colSpan={4}>
                    No cohort records for the selected filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function KpiCard({ label, value }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  )
}

function FilterSelect({ label, value, options, onChange }) {
  return (
    <label className="flex items-center gap-2 rounded border border-slate-200 px-2 py-1">
      <span className="text-slate-600">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="rounded border border-slate-300 px-2 py-1">
        {options.map((option) => (
          <option key={option || 'all'} value={option}>
            {option || 'all'}
          </option>
        ))}
      </select>
    </label>
  )
}
