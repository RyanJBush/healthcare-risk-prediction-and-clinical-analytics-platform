import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { apiRequest } from '../api'

export default function RiskAnalysisPage({ token }) {
  const [patients, setPatients] = useState([])

  useEffect(() => {
    apiRequest('/api/patients', {}, token).then(async (items) => {
      const withScores = await Promise.all(
        items.map(async (patient) => {
          const predictions = await apiRequest(`/api/predictions/${patient.id}`, {}, token)
          const latest = Array.isArray(predictions) && predictions.length > 0 ? predictions[0] : null
          return {
            patient: patient.full_name,
            risk: latest ? Number(latest.risk_score.toFixed(2)) : 0,
          }
        }),
      )
      setPatients(withScores)
    })
  }, [token])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Risk Analysis</h1>
      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-4 text-lg font-medium">Patient Risk Chart</h2>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={patients}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="patient" />
              <YAxis domain={[0, 1]} />
              <Tooltip />
              <Bar dataKey="risk" fill="#334155" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
