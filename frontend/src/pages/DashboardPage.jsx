import { useEffect, useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import { apiRequest } from '../api'

const COLORS = ['#16a34a', '#f59e0b', '#dc2626']

export default function DashboardPage({ token }) {
  const [metrics, setMetrics] = useState(null)
  const [cohorts, setCohorts] = useState(null)

  useEffect(() => {
    apiRequest('/api/metrics/summary', {}, token).then(setMetrics).catch(() => setMetrics(null))
    apiRequest('/api/metrics/cohorts', {}, token).then(setCohorts).catch(() => setCohorts(null))
  }, [token])

  const chartData = metrics
    ? Object.entries(metrics.by_category).map(([name, value]) => ({ name, value }))
    : []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
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
        </div>
      </div>
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
