import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { apiRequest } from '../api'

export default function PatientDetailPage({ token }) {
  const { id } = useParams()
  const [patient, setPatient] = useState(null)
  const [predictions, setPredictions] = useState([])
  const [explanations, setExplanations] = useState([])
  const [observations, setObservations] = useState([])

  useEffect(() => {
    apiRequest(`/api/patients/${id}`, {}, token).then(setPatient)
    apiRequest(`/api/predictions/${id}`, {}, token).then(setPredictions)
    apiRequest(`/api/explanations/${id}`, {}, token).then(setExplanations)
    apiRequest(`/api/patients/${id}/observations`, {}, token).then(setObservations)
  }, [id, token])

  async function runPrediction() {
    await apiRequest(
      '/api/predict/tiered',
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
          <p className="font-medium">{patient.masked_identifier}</p>
          <p className="text-sm text-slate-600">
            Age {patient.age}, BMI {patient.bmi}, BP {patient.blood_pressure}, Cholesterol {patient.cholesterol}, Glucose {patient.glucose}
          </p>
          <p className="text-sm text-slate-600">Review status: {patient.review_status}</p>
        </div>
      ) : null}
      <button type="button" onClick={runPrediction} className="rounded bg-slate-900 px-3 py-2 text-white hover:bg-slate-700">
        Run Tiered Risk Prediction
      </button>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Predictions</h2>
          <ul className="space-y-2 text-sm">
            {predictions.map((prediction) => (
              <li key={prediction.id} className="rounded border border-slate-200 p-2">
                <p className="font-medium">{prediction.target_type}</p>
                Risk {prediction.risk_score.toFixed(2)} ({prediction.risk_category}) • confidence {prediction.confidence_score.toFixed(2)}
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Clinician Explanations</h2>
          <ul className="space-y-2 text-sm">
            {explanations.map((explanation) => (
              <li key={explanation.id} className="rounded border border-slate-200 p-2">
                <p className="font-medium">{explanation.target_type}</p>
                <p>{explanation.plain_summary}</p>
                <p className="text-slate-600">{explanation.rationale_summary}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <section className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-3 text-lg font-medium">Observation Timeline</h2>
        <ul className="space-y-2 text-sm">
          {observations.map((obs) => (
            <li key={obs.id} className="rounded border border-slate-200 p-2">
              {new Date(obs.observed_at).toLocaleString()} • HR {obs.heart_rate ?? '—'} • SBP {obs.systolic_bp ?? '—'} • SpO2{' '}
              {obs.oxygen_saturation ?? '—'}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
