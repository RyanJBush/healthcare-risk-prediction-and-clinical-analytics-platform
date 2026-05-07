import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiRequest } from '../api'

const blankPatient = {
  full_name: '',
  age: 50,
  bmi: 27,
  blood_pressure: 120,
  cholesterol: 180,
  glucose: 100,
  smoker: false,
  has_historical_outcome: false,
}

export default function PatientsPage({ token }) {
  const [patients, setPatients] = useState([])
  const [cohortRows, setCohortRows] = useState([])
  const [formData, setFormData] = useState(blankPatient)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [targetType, setTargetType] = useState('readmission')
  const [highRiskOnly, setHighRiskOnly] = useState(false)

  const loadPatients = useCallback(() => {
    setLoading(true)
    Promise.all([
      apiRequest('/api/patients', {}, token),
      apiRequest(`/api/cohorts/filter?target_type=${targetType}`, {}, token),
    ])
      .then(([patientRows, cohortData]) => {
        setPatients(patientRows)
        setCohortRows(cohortData)
        setError('')
      })
      .catch((loadError) => {
        setPatients([])
        setCohortRows([])
        setError(loadError.message || 'Unable to load patients.')
      })
      .finally(() => setLoading(false))
  }, [targetType, token])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadPatients()
  }, [loadPatients])

  const riskByPatientId = new Map(cohortRows.map((row) => [row.patient_id, row]))
  const displayPatients = patients.filter((patient) => {
    if (!highRiskOnly) return true
    return riskByPatientId.get(patient.id)?.risk_category === 'high'
  })
  const avgRisk = cohortRows.length ? cohortRows.reduce((sum, row) => sum + row.risk_score, 0) / cohortRows.length : 0
  const highRiskCount = cohortRows.filter((row) => row.risk_category === 'high').length

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      await apiRequest(
        '/api/patients',
        {
          method: 'POST',
          body: JSON.stringify(formData),
        },
        token,
      )
      setFormData(blankPatient)
      loadPatients()
      setError('')
    } catch (saveError) {
      setError(saveError.message || 'Unable to create patient.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Patients</h1>
      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="text-sm text-slate-500">Average {targetType} risk</p>
          <p className="mt-1 text-2xl font-semibold">{avgRisk.toFixed(2)}</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="text-sm text-slate-500">High-risk patients</p>
          <p className="mt-1 text-2xl font-semibold">{highRiskCount}</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="text-sm text-slate-500">Patients with scores</p>
          <p className="mt-1 text-2xl font-semibold">{cohortRows.length}</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 rounded-xl bg-white p-4 shadow">
        <label className="text-sm">
          Target
          <select value={targetType} onChange={(event) => setTargetType(event.target.value)} className="ml-2 rounded border border-slate-300 px-2 py-1">
            <option value="readmission">readmission</option>
            <option value="deterioration">deterioration</option>
            <option value="adverse_event">adverse_event</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={highRiskOnly} onChange={(event) => setHighRiskOnly(event.target.checked)} />
          Show high-risk only
        </label>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <form onSubmit={handleSubmit} className="space-y-3 rounded-xl bg-white p-4 shadow">
          <h2 className="text-lg font-medium">Add Patient</h2>
          <TextInput label="Full Name" value={formData.full_name} onChange={(full_name) => setFormData({ ...formData, full_name })} />
          <TextInput label="Age" type="number" value={formData.age} onChange={(age) => setFormData({ ...formData, age: Number(age) })} />
          <TextInput label="BMI" type="number" step="0.1" value={formData.bmi} onChange={(bmi) => setFormData({ ...formData, bmi: Number(bmi) })} />
          <TextInput
            label="Blood Pressure"
            type="number"
            value={formData.blood_pressure}
            onChange={(blood_pressure) => setFormData({ ...formData, blood_pressure: Number(blood_pressure) })}
          />
          <TextInput
            label="Cholesterol"
            type="number"
            value={formData.cholesterol}
            onChange={(cholesterol) => setFormData({ ...formData, cholesterol: Number(cholesterol) })}
          />
          <TextInput
            label="Glucose"
            type="number"
            value={formData.glucose}
            onChange={(glucose) => setFormData({ ...formData, glucose: Number(glucose) })}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={formData.smoker}
              onChange={(event) => setFormData({ ...formData, smoker: event.target.checked })}
            />
            Smoker
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={formData.has_historical_outcome}
              onChange={(event) => setFormData({ ...formData, has_historical_outcome: event.target.checked })}
            />
            Historical Outcome Label Present
          </label>
          <button
            type="submit"
            className="rounded bg-slate-900 px-3 py-2 text-white hover:bg-slate-700 disabled:opacity-60"
            disabled={saving}
          >
            {saving ? 'Saving Patient…' : 'Save Patient'}
          </button>
        </form>

        <div className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Patient Profiles</h2>
          <ul className="space-y-2">
            {loading ? <li className="rounded border border-slate-200 p-3 text-slate-500">Loading patients…</li> : null}
            {displayPatients.map((patient) => {
              const riskRow = riskByPatientId.get(patient.id)
              return (
              <li key={patient.id} className="rounded border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{patient.masked_identifier}</p>
                    <p className="text-sm text-slate-500">
                      Age {patient.age}, BMI {patient.bmi}, BP {patient.blood_pressure}
                    </p>
                    <p className="text-sm text-slate-600">
                      Risk: {riskRow ? `${riskRow.risk_score.toFixed(2)} (${riskRow.risk_category})` : 'No score yet'}
                    </p>
                  </div>
                  <Link to={`/patients/${patient.id}`} className="text-sm text-blue-700 hover:underline">
                    View
                  </Link>
                </div>
              </li>
              )
            })}
            {!loading && displayPatients.length === 0 ? (
              <li className="rounded border border-slate-200 p-3 text-slate-500">No patients yet. Add one to begin.</li>
            ) : null}
          </ul>
        </div>
      </div>
    </div>
  )
}

function TextInput({ label, value, onChange, type = 'text', step }) {
  return (
    <label className="block text-sm">
      {label}
      <input
        type={type}
        step={step}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
      />
    </label>
  )
}
