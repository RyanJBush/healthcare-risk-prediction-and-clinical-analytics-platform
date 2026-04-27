import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { apiRequest } from '../api'

export default function RiskAnalysisPage({ token }) {
  const [patients, setPatients] = useState([])
  const [modelComparison, setModelComparison] = useState(null)
  const [modelCards, setModelCards] = useState([])
  const [disclaimer, setDisclaimer] = useState(null)
  const [evaluationRun, setEvaluationRun] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [restrictedMessage, setRestrictedMessage] = useState('')
  const [targetType, setTargetType] = useState('readmission')
  const [threshold, setThreshold] = useState(0.55)

  const chartData = useMemo(() => patients.slice(0, 30), [patients])

  const loadRiskAnalysis = useCallback(async () => {
    setLoading(true)
    setError('')
    setRestrictedMessage('')
    try {
      const [items, cards, disclaimerPayload] = await Promise.all([
        apiRequest('/api/patients', {}, token),
        apiRequest('/api/model-cards', {}, token),
        apiRequest('/api/disclaimer', {}, token),
      ])
      setModelCards(cards)
      setDisclaimer(disclaimerPayload)

      const withScores = await Promise.all(
        items.map(async (patient) => {
          const predictions = await apiRequest(`/api/predictions/${patient.id}`, {}, token)
          const latestTargetPrediction = Array.isArray(predictions)
            ? predictions.find((prediction) => prediction.target_type === targetType)
            : null
          return {
            patient: patient.masked_identifier,
            risk: latestTargetPrediction ? Number(latestTargetPrediction.risk_score.toFixed(2)) : 0,
          }
        }),
      )
      setPatients(withScores)

      try {
        const comparison = await apiRequest(`/api/evaluation/model-comparison?target_type=${targetType}`, {}, token)
        setModelComparison(comparison)
      } catch (evaluationError) {
        setModelComparison(null)
        setRestrictedMessage(evaluationError.message || 'Evaluation comparison unavailable for this role.')
      }
    } catch (loadError) {
      setError(loadError.message || 'Unable to load risk analysis.')
    } finally {
      setLoading(false)
    }
  }, [targetType, token])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadRiskAnalysis()
  }, [loadRiskAnalysis])

  async function createEvaluationRun() {
    setBusy(true)
    try {
      const run = await apiRequest(
        `/api/evaluation/runs?target_type=${targetType}&threshold=${threshold}`,
        {
          method: 'POST',
        },
        token,
      )
      setEvaluationRun(run)
      setRestrictedMessage('')
      await loadRiskAnalysis()
    } catch (runError) {
      setRestrictedMessage(runError.message || 'Unable to create evaluation run for current role.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Risk Analysis</h1>
      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {disclaimer ? <p className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">{disclaimer.message}</p> : null}
      <div className="flex flex-wrap items-center gap-3 rounded-xl bg-white p-4 shadow">
        <label className="text-sm">
          Target
          <select value={targetType} onChange={(event) => setTargetType(event.target.value)} className="ml-2 rounded border border-slate-300 px-2 py-1">
            <option value="readmission">readmission</option>
            <option value="deterioration">deterioration</option>
            <option value="adverse_event">adverse_event</option>
          </select>
        </label>
        <label className="text-sm">
          Threshold
          <input
            type="number"
            min="0.1"
            max="0.95"
            step="0.01"
            value={threshold}
            onChange={(event) => setThreshold(Number(event.target.value))}
            className="ml-2 w-24 rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <button
          type="button"
          onClick={createEvaluationRun}
          className="rounded bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-60"
          disabled={busy}
        >
          {busy ? 'Running…' : 'Run Evaluation'}
        </button>
        {evaluationRun ? <p className="text-sm text-emerald-700">Evaluation run #{evaluationRun.id} completed.</p> : null}
      </div>
      {restrictedMessage ? <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{restrictedMessage}</p> : null}
      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-4 text-lg font-medium">Patient {targetType} Risk</h2>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="patient" />
              <YAxis domain={[0, 1]} />
              <Tooltip />
              <Bar dataKey="risk" fill="#334155" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        {loading ? <p className="mt-3 text-sm text-slate-500">Loading risk distribution…</p> : null}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-4 text-lg font-medium">Model Comparison</h2>
          {modelComparison?.models?.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-2 py-1">Model</th>
                    <th className="px-2 py-1">ROC AUC</th>
                    <th className="px-2 py-1">PR AUC</th>
                    <th className="px-2 py-1">Precision</th>
                    <th className="px-2 py-1">Recall</th>
                    <th className="px-2 py-1">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {modelComparison.models.map((model) => (
                    <tr key={model.model_name} className="border-t border-slate-100">
                      <td className="px-2 py-1">{model.model_name}</td>
                      <td className="px-2 py-1">{model.roc_auc.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.pr_auc.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.precision.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.recall.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.cost_score.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Model comparison metrics unavailable for this role or dataset size.</p>
          )}
        </section>
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-4 text-lg font-medium">Threshold Simulation</h2>
          {modelComparison?.threshold_sweep?.length ? (
            <ul className="space-y-2 text-sm">
              {modelComparison.threshold_sweep.map((item) => (
                <li key={item.threshold} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2">
                  <span>Threshold {Number(item.threshold).toFixed(2)}</span>
                  <span>{item.alerts} alerts</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">Threshold sweep unavailable.</p>
          )}
        </section>
      </div>
      <section className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-4 text-lg font-medium">Model Cards</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {modelCards.map((card) => (
            <article key={card.id} className="rounded border border-slate-200 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">{card.target_type}</p>
              <h3 className="font-medium">
                {card.model_name} ({card.model_version})
              </h3>
              <p className="mt-1 text-sm text-slate-600">{card.summary}</p>
              <p className="mt-2 text-xs text-slate-500">Intended use: {card.intended_use}</p>
              <p className="mt-1 text-xs text-slate-500">Limitations: {card.limitations}</p>
            </article>
          ))}
          {modelCards.length === 0 ? <p className="text-sm text-slate-500">No model cards available.</p> : null}
        </div>
      </section>
    </div>
  )
}
