import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { apiRequest } from '../api'

export default function PatientDetailPage({ token }) {
  const { id } = useParams()
  const [patient, setPatient] = useState(null)
  const [predictions, setPredictions] = useState([])
  const [explanations, setExplanations] = useState([])

  useEffect(() => {
    apiRequest(`/api/patients/${id}`, {}, token).then(setPatient)
    apiRequest(`/api/predictions/${id}`, {}, token).then(setPredictions)
    apiRequest(`/api/explanations/${id}`, {}, token).then(setExplanations)
  }, [id, token])

  async function runPrediction() {
    await apiRequest(
      '/api/predict',
      {
        method: 'POST',
        body: JSON.stringify({ patient_id: Number(id) }),
      },
      token,
    )
    const [nextPredictions, nextExplanations] = await Promise.all([
      apiRequest(`/api/predictions/${id}`, {}, token),
      apiRequest(`/api/explanations/${id}`, {}, token),
    ])
    setPredictions(nextPredictions)
    setExplanations(nextExplanations)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Patient Detail</h1>
      {patient ? (
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="font-medium">{patient.full_name}</p>
          <p className="text-sm text-slate-600">
            Age {patient.age}, BMI {patient.bmi}, BP {patient.blood_pressure}, Cholesterol {patient.cholesterol}, Glucose {patient.glucose}
          </p>
        </div>
      ) : null}
      <button type="button" onClick={runPrediction} className="rounded bg-slate-900 px-3 py-2 text-white hover:bg-slate-700">
        Run Risk Prediction
      </button>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Predictions</h2>
          <ul className="space-y-2 text-sm">
            {predictions.map((prediction) => (
              <li key={prediction.id} className="rounded border border-slate-200 p-2">
                Risk {prediction.risk_score.toFixed(2)} ({prediction.risk_category})
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Top Explanation Factors</h2>
          <ul className="space-y-2 text-sm">
            {explanations.map((explanation) => {
              const factors = JSON.parse(explanation.top_factors)
              return (
                <li key={explanation.id} className="rounded border border-slate-200 p-2">
                  {factors.map((factor) => `${factor.feature}: ${factor.impact}`).join(', ')}
                </li>
              )
            })}
          </ul>
        </section>
      </div>
    </div>
  )
}
