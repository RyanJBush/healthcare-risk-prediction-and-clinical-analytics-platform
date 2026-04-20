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
}

export default function PatientsPage({ token }) {
  const [patients, setPatients] = useState([])
  const [formData, setFormData] = useState(blankPatient)

  const loadPatients = useCallback(() => {
    apiRequest('/api/patients', {}, token).then(setPatients)
  }, [token])

  useEffect(() => {
    loadPatients()
  }, [loadPatients])

  async function handleSubmit(event) {
    event.preventDefault()
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
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Patients</h1>
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
          <button type="submit" className="rounded bg-slate-900 px-3 py-2 text-white hover:bg-slate-700">
            Save Patient
          </button>
        </form>

        <div className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Patient Profiles</h2>
          <ul className="space-y-2">
            {patients.map((patient) => (
              <li key={patient.id} className="rounded border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{patient.full_name}</p>
                    <p className="text-sm text-slate-500">
                      Age {patient.age}, BMI {patient.bmi}, BP {patient.blood_pressure}
                    </p>
                  </div>
                  <Link to={`/patients/${patient.id}`} className="text-sm text-blue-700 hover:underline">
                    View
                  </Link>
                </div>
              </li>
            ))}
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
