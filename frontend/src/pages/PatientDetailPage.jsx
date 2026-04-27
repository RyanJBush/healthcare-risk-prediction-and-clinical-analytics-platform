import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'

import { apiRequest } from '../api'

const reviewStatuses = ['new', 'reviewed', 'escalated', 'monitored']

const blankObservation = {
  heart_rate: '',
  systolic_bp: '',
  diastolic_bp: '',
  oxygen_saturation: '',
  creatinine: '',
  glucose: '',
  source: 'ehr',
}

const blankNote = {
  note_text: '',
  recommendation: '',
}

export default function PatientDetailPage({ token }) {
  const { id } = useParams()
  const [patient, setPatient] = useState(null)
  const [predictions, setPredictions] = useState([])
  const [explanations, setExplanations] = useState([])
  const [observations, setObservations] = useState([])
  const [notes, setNotes] = useState([])
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [observationForm, setObservationForm] = useState(blankObservation)
  const [noteForm, setNoteForm] = useState(blankNote)
  const [inlineMessage, setInlineMessage] = useState('')
  const [timelineFilter, setTimelineFilter] = useState('all')

  const sortedPredictions = useMemo(
    () => [...predictions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [predictions],
  )
  const latestByTarget = useMemo(() => {
    const seen = new Set()
    return sortedPredictions.filter((prediction) => {
      if (seen.has(prediction.target_type)) return false
      seen.add(prediction.target_type)
      return true
    })
  }, [sortedPredictions])
  const explanationByPrediction = useMemo(
    () => new Map(explanations.map((explanation) => [explanation.prediction_id, explanation])),
    [explanations],
  )
  const filteredTimeline = useMemo(
    () => timeline.filter((event) => timelineFilter === 'all' || event.event_type === timelineFilter),
    [timeline, timelineFilter],
  )

  const loadPatientContext = useCallback(async () => {
    setLoading(true)
    setError('')
    setInlineMessage('')
    try {
      const [nextPatient, nextPredictions, nextExplanations, nextObservations, nextNotes, nextTimeline] = await Promise.all([
        apiRequest(`/api/patients/${id}`, {}, token),
        apiRequest(`/api/predictions/${id}`, {}, token),
        apiRequest(`/api/explanations/${id}`, {}, token),
        apiRequest(`/api/patients/${id}/observations`, {}, token),
        apiRequest(`/api/patients/${id}/notes`, {}, token),
        apiRequest(`/api/patients/${id}/timeline`, {}, token),
      ])
      setPatient(nextPatient)
      setPredictions(nextPredictions)
      setExplanations(nextExplanations)
      setObservations(nextObservations)
      setNotes(nextNotes)
      setTimeline(nextTimeline)
    } catch (loadError) {
      setError(loadError.message || 'Unable to load patient context.')
    } finally {
      setLoading(false)
    }
  }, [id, token])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadPatientContext()
  }, [loadPatientContext])

  async function runPrediction() {
    setBusyAction('predict')
    setInlineMessage('')
    try {
      await apiRequest(
        '/api/predict/tiered',
        {
          method: 'POST',
          body: JSON.stringify({ patient_id: Number(id) }),
        },
        token,
      )
      await loadPatientContext()
      setInlineMessage('Tiered prediction completed and refreshed.')
    } catch (predictError) {
      setError(predictError.message || 'Unable to run prediction.')
    } finally {
      setBusyAction('')
    }
  }

  async function updateReviewStatus(nextStatus) {
    setBusyAction('status')
    setInlineMessage('')
    try {
      await apiRequest(
        `/api/patients/${id}/review-status`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            review_status: nextStatus,
            assigned_reviewer: patient?.assigned_reviewer || null,
          }),
        },
        token,
      )
      await loadPatientContext()
      setInlineMessage(`Review status updated to ${nextStatus}.`)
    } catch (statusError) {
      setError(statusError.message || 'Unable to update review status.')
    } finally {
      setBusyAction('')
    }
  }

  async function submitObservation(event) {
    event.preventDefault()
    setBusyAction('observation')
    setInlineMessage('')
    try {
      const payload = Object.fromEntries(
        Object.entries(observationForm).filter(([, value]) => value !== '' && value !== null && value !== undefined),
      )
      await apiRequest(
        `/api/patients/${id}/observations?recalculate_risk=true`,
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
        token,
      )
      setObservationForm(blankObservation)
      await loadPatientContext()
      setInlineMessage('Observation added and risk recalculated.')
    } catch (observationError) {
      setError(observationError.message || 'Unable to save observation.')
    } finally {
      setBusyAction('')
    }
  }

  async function submitNote(event) {
    event.preventDefault()
    setBusyAction('note')
    setInlineMessage('')
    try {
      await apiRequest(
        `/api/patients/${id}/notes`,
        {
          method: 'POST',
          body: JSON.stringify({
            ...noteForm,
            recommendation: noteForm.recommendation || null,
            state_from: patient?.review_status ?? null,
            state_to: patient?.review_status ?? null,
          }),
        },
        token,
      )
      setNoteForm(blankNote)
      await loadPatientContext()
      setInlineMessage('Review note saved.')
    } catch (noteError) {
      setError(noteError.message || 'Unable to save review note.')
    } finally {
      setBusyAction('')
    }
  }

  function parseFactors(raw) {
    try {
      const parsed = JSON.parse(raw || '[]')
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Patient Detail</h1>
        <p className="rounded-xl bg-white p-4 text-sm text-slate-600 shadow">Loading patient profile and AI context…</p>
      </div>
    )
  }

  if (error && !patient) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Patient Detail</h1>
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
          <button type="button" onClick={loadPatientContext} className="ml-3 rounded bg-red-700 px-2 py-1 text-white">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Patient Detail</h1>
      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {inlineMessage ? <p className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{inlineMessage}</p> : null}
      {patient ? (
        <div className="rounded-xl bg-white p-4 shadow">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-medium">{patient.masked_identifier}</p>
              <p className="text-sm text-slate-600">
                Age {patient.age}, BMI {patient.bmi}, BP {patient.blood_pressure}, Cholesterol {patient.cholesterol}, Glucose {patient.glucose}
              </p>
              <p className="text-sm text-slate-600">Assigned reviewer: {patient.assigned_reviewer || 'Unassigned'}</p>
            </div>
            <label className="text-sm text-slate-700">
              Review status
              <select
                value={patient.review_status}
                onChange={(event) => updateReviewStatus(event.target.value)}
                className="ml-2 rounded border border-slate-300 px-2 py-1"
                disabled={busyAction === 'status'}
              >
                {reviewStatuses.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      ) : null}
      <button
        type="button"
        onClick={runPrediction}
        className="rounded bg-slate-900 px-3 py-2 text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={busyAction === 'predict'}
      >
        {busyAction === 'predict' ? 'Running Tiered Risk Prediction…' : 'Run Tiered Risk Prediction'}
      </button>
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Latest Predictions by Target</h2>
          <ul className="space-y-2 text-sm">
            {latestByTarget.map((prediction) => (
              <li key={prediction.id} className="rounded border border-slate-200 p-3">
                <p className="font-medium">{prediction.target_type}</p>
                <p>
                  Risk {prediction.risk_score.toFixed(2)} ({prediction.risk_category}) • confidence{' '}
                  {prediction.confidence_score.toFixed(2)}
                </p>
                <p className="text-xs text-slate-500">
                  Model {prediction.model_version} • {new Date(prediction.created_at).toLocaleString()}
                </p>
              </li>
            ))}
            {latestByTarget.length === 0 ? <li className="text-slate-500">No predictions yet. Run scoring to begin.</li> : null}
          </ul>
        </section>
        <section className="rounded-xl bg-white p-4 shadow lg:col-span-2">
          <h2 className="mb-3 text-lg font-medium">Explanation Snapshot</h2>
          <ul className="space-y-2 text-sm">
            {latestByTarget.map((prediction) => {
              const explanation = explanationByPrediction.get(prediction.id)
              if (!explanation) {
                return (
                  <li key={`missing-${prediction.id}`} className="rounded border border-slate-200 p-3 text-slate-500">
                    No explanation available yet for {prediction.target_type}.
                  </li>
                )
              }
              const riskFactors = parseFactors(explanation.risk_factors)
              const protectiveFactors = parseFactors(explanation.protective_factors)
              return (
                <li key={explanation.id} className="space-y-2 rounded border border-slate-200 p-3">
                  <p className="font-medium">{explanation.target_type}</p>
                  <p>{explanation.plain_summary}</p>
                  <p className="text-slate-600">{explanation.rationale_summary}</p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-red-700">Top Risk Drivers</p>
                      <ul className="mt-1 space-y-1">
                        {riskFactors.map((factor) => (
                          <li key={`${explanation.id}-${factor.feature}-risk`} className="text-slate-700">
                            {factor.feature?.replaceAll('_', ' ')} ({Number(factor.impact || 0).toFixed(2)})
                          </li>
                        ))}
                        {riskFactors.length === 0 ? <li className="text-slate-500">None identified.</li> : null}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Protective Factors</p>
                      <ul className="mt-1 space-y-1">
                        {protectiveFactors.map((factor) => (
                          <li key={`${explanation.id}-${factor.feature}-protective`} className="text-slate-700">
                            {factor.feature?.replaceAll('_', ' ')} ({Number(factor.impact || 0).toFixed(2)})
                          </li>
                        ))}
                        {protectiveFactors.length === 0 ? <li className="text-slate-500">None identified.</li> : null}
                      </ul>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500">
                    Provenance: {explanation.provenance} • {new Date(explanation.created_at).toLocaleString()}
                  </p>
                </li>
              )
            })}
            {latestByTarget.length === 0 ? <li className="text-slate-500">No explanations available yet.</li> : null}
          </ul>
        </section>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Add Observation</h2>
          <form onSubmit={submitObservation} className="grid gap-2 sm:grid-cols-2">
            <MetricInput
              label="Heart Rate"
              value={observationForm.heart_rate}
              onChange={(value) => setObservationForm((current) => ({ ...current, heart_rate: value }))}
            />
            <MetricInput
              label="Systolic BP"
              value={observationForm.systolic_bp}
              onChange={(value) => setObservationForm((current) => ({ ...current, systolic_bp: value }))}
            />
            <MetricInput
              label="Diastolic BP"
              value={observationForm.diastolic_bp}
              onChange={(value) => setObservationForm((current) => ({ ...current, diastolic_bp: value }))}
            />
            <MetricInput
              label="SpO₂"
              value={observationForm.oxygen_saturation}
              onChange={(value) => setObservationForm((current) => ({ ...current, oxygen_saturation: value }))}
            />
            <MetricInput
              label="Creatinine"
              value={observationForm.creatinine}
              onChange={(value) => setObservationForm((current) => ({ ...current, creatinine: value }))}
            />
            <MetricInput
              label="Glucose"
              value={observationForm.glucose}
              onChange={(value) => setObservationForm((current) => ({ ...current, glucose: value }))}
            />
            <label className="sm:col-span-2">
              <span className="text-sm text-slate-700">Source</span>
              <input
                value={observationForm.source}
                onChange={(event) => setObservationForm((current) => ({ ...current, source: event.target.value }))}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <button
              type="submit"
              className="sm:col-span-2 rounded bg-slate-900 px-3 py-2 text-white hover:bg-slate-700 disabled:opacity-60"
              disabled={busyAction === 'observation'}
            >
              {busyAction === 'observation' ? 'Saving Observation…' : 'Save Observation + Recalculate Risk'}
            </button>
          </form>
        </section>
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Add Review Note</h2>
          <form onSubmit={submitNote} className="space-y-3">
            <label className="block">
              <span className="text-sm text-slate-700">Clinical Note</span>
              <textarea
                value={noteForm.note_text}
                onChange={(event) => setNoteForm((current) => ({ ...current, note_text: event.target.value }))}
                rows={4}
                required
                minLength={5}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                placeholder="Summarize patient review, concerns, and next actions."
              />
            </label>
            <label className="block">
              <span className="text-sm text-slate-700">Recommendation (optional)</span>
              <textarea
                value={noteForm.recommendation}
                onChange={(event) => setNoteForm((current) => ({ ...current, recommendation: event.target.value }))}
                rows={2}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                placeholder="e.g. repeat glucose in 4h, reassess discharge plan."
              />
            </label>
            <button
              type="submit"
              className="rounded bg-slate-900 px-3 py-2 text-white hover:bg-slate-700 disabled:opacity-60"
              disabled={busyAction === 'note'}
            >
              {busyAction === 'note' ? 'Saving Note…' : 'Save Review Note'}
            </button>
          </form>
        </section>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl bg-white p-4 shadow lg:col-span-2">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-medium">Unified Patient Timeline</h2>
            <label className="text-sm">
              Filter
              <select
                value={timelineFilter}
                onChange={(event) => setTimelineFilter(event.target.value)}
                className="ml-2 rounded border border-slate-300 px-2 py-1"
              >
                <option value="all">all</option>
                <option value="prediction">prediction</option>
                <option value="observation">observation</option>
                <option value="review_note">review_note</option>
              </select>
            </label>
          </div>
          <ul className="space-y-2 text-sm">
            {filteredTimeline.map((event) => (
              <li key={`${event.event_type}-${event.event_id}`} className="rounded border border-slate-200 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">{event.event_type}</p>
                  <p className="text-xs text-slate-500">{new Date(event.event_time).toLocaleString()}</p>
                </div>
                <p className="mt-1 text-slate-700">{event.summary}</p>
              </li>
            ))}
            {filteredTimeline.length === 0 ? <li className="text-slate-500">No timeline events for this filter.</li> : null}
          </ul>
        </section>
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Recent Observations</h2>
          <ul className="space-y-2 text-sm">
            {observations.slice(0, 8).map((obs) => (
              <li key={obs.id} className="rounded border border-slate-200 p-3">
                <p className="font-medium">{new Date(obs.observed_at).toLocaleString()}</p>
                <p className="text-slate-600">
                  HR {obs.heart_rate ?? '—'} • SBP {obs.systolic_bp ?? '—'} • DBP {obs.diastolic_bp ?? '—'} • SpO₂ {obs.oxygen_saturation ?? '—'} •
                  Glucose {obs.glucose ?? '—'}
                </p>
              </li>
            ))}
            {observations.length === 0 ? <li className="text-slate-500">No observations recorded yet.</li> : null}
          </ul>
        </section>
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-medium">Recent Review Notes</h2>
          <ul className="space-y-2 text-sm">
            {notes.map((note) => (
              <li key={note.id} className="rounded border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{new Date(note.created_at).toLocaleString()}</p>
                <p className="mt-1">{note.note_text}</p>
                {note.recommendation ? <p className="mt-1 text-slate-600">Recommendation: {note.recommendation}</p> : null}
              </li>
            ))}
            {notes.length === 0 ? <li className="text-slate-500">No review notes yet.</li> : null}
          </ul>
        </section>
      </div>
    </div>
  )
}

function MetricInput({ label, value, onChange }) {
  return (
    <label>
      <span className="text-sm text-slate-700">{label}</span>
      <input
        type="number"
        step="0.1"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
      />
    </label>
  )
}
