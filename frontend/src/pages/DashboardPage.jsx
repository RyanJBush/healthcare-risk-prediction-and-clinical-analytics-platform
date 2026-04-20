import { useEffect, useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import { apiRequest } from '../api'

const COLORS = ['#16a34a', '#f59e0b', '#dc2626']

export default function DashboardPage({ token }) {
  const [metrics, setMetrics] = useState(null)

  useEffect(() => {
    apiRequest('/api/metrics/summary', {}, token).then(setMetrics).catch(() => setMetrics(null))
  }, [token])

  const chartData = metrics
    ? Object.entries(metrics.by_category).map(([name, value]) => ({ name, value }))
    : []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard label="Total Patients" value={metrics?.total_patients ?? 0} />
        <KpiCard label="Predictions" value={metrics?.total_predictions ?? 0} />
        <KpiCard label="Average Risk" value={metrics ? metrics.average_risk_score.toFixed(2) : '0.00'} />
      </div>
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
