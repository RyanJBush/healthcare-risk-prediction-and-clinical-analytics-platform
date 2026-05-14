import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { apiRequest } from '../api'
import SurvivalCurveChart from '../components/SurvivalCurveChart'

export default function RiskAnalysisPage({ token }) {
  const [patients, setPatients] = useState([])
  const [modelComparison, setModelComparison] = useState(null)
  const [modelCards, setModelCards] = useState([])
  const [disclaimer, setDisclaimer] = useState(null)
  const [evaluationRun, setEvaluationRun] = useState(null)
  const [driftSignal, setDriftSignal] = useState(null)
  const [predictionLog, setPredictionLog] = useState([])
  const [calibrationCurve, setCalibrationCurve] = useState(null)
  const [survivalCurves, setSurvivalCurves] = useState(null)
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
      const [cards, disclaimerPayload] = await Promise.all([
        apiRequest('/api/model-cards', {}, token),
        apiRequest('/api/disclaimer', {}, token),
      ])
      setModelCards(cards)
      setDisclaimer(disclaimerPayload)

      const cohortRows = await apiRequest(`/api/cohorts/filter?target_type=${targetType}`, {}, token)
      const withScores = Array.isArray(cohortRows)
        ? cohortRows.map((row) => ({
            patient: row.masked_identifier,
            risk: Number(row.risk_score.toFixed(2)),
          }))
        : []
      setPatients(withScores)

      try {
        const [comparison, drift, logs, calibration, survival] = await Promise.all([
          apiRequest(`/api/evaluation/model-comparison?target_type=${targetType}`, {}, token),
          apiRequest(`/api/monitoring/drift?target_type=${targetType}`, {}, token),
          apiRequest(`/api/monitoring/predictions?target_type=${targetType}&limit=30`, {}, token),
          apiRequest('/analytics/calibration-curve', {}, token),
          apiRequest(`/analytics/survival-curves?target_type=${targetType}`, {}, token),
        ])
        setModelComparison(comparison)
        setDriftSignal(drift)
        setPredictionLog(logs)
        setCalibrationCurve(calibration)
        setSurvivalCurves(survival)
      } catch (evaluationError) {
        setModelComparison(null)
        setDriftSignal(null)
        setPredictionLog([])
        setCalibrationCurve(null)
        setSurvivalCurves(null)
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
                    <th className="px-2 py-1">Accuracy</th>
                    <th className="px-2 py-1">Precision</th>
                    <th className="px-2 py-1">Recall</th>
                    <th className="px-2 py-1">F1</th>
                    <th className="px-2 py-1">Confusion Matrix</th>
                    <th className="px-2 py-1">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {modelComparison.models.map((model) => (
                    <tr key={model.model_name} className="border-t border-slate-100">
                      <td className="px-2 py-1">{model.model_name}</td>
                      <td className="px-2 py-1">{model.roc_auc.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.pr_auc.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.accuracy.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.precision.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.recall.toFixed(2)}</td>
                      <td className="px-2 py-1">{model.f1.toFixed(2)}</td>
                      <td className="px-2 py-1 text-xs text-slate-600">
                        TN {model.confusion_matrix?.tn ?? 0} / FP {model.confusion_matrix?.fp ?? 0}
                        <br />
                        FN {model.confusion_matrix?.fn ?? 0} / TP {model.confusion_matrix?.tp ?? 0}
                      </td>
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
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-4 text-lg font-medium">Feature Importance (Top Model)</h2>
          {modelComparison?.models?.[0]?.feature_importance?.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modelComparison.models[0].feature_importance}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="feature" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="importance" fill="#0f766e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Feature importance is unavailable for this evaluation run.</p>
          )}
        </section>
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-4 text-lg font-medium">Model Drift Signal</h2>
          {driftSignal ? (
            <div className="space-y-3 text-sm">
              <p className={`rounded border px-3 py-2 ${driftSignal.drift_flag ? 'border-amber-300 bg-amber-50 text-amber-800' : 'border-emerald-200 bg-emerald-50 text-emerald-700'}`}>
                {driftSignal.drift_flag ? 'Potential drift detected' : 'No meaningful drift detected'}
              </p>
              <p>Baseline avg risk: {driftSignal.baseline_avg_risk.toFixed(2)}</p>
              <p>Recent avg risk: {driftSignal.recent_avg_risk.toFixed(2)}</p>
              <p>Absolute delta: {driftSignal.absolute_delta.toFixed(3)}</p>
              <p>High-risk rate delta: {driftSignal.high_risk_rate_delta.toFixed(3)}</p>
              <p className="text-xs text-slate-500">
                Samples — baseline: {driftSignal.sample_sizes?.baseline ?? 0}, recent: {driftSignal.sample_sizes?.recent ?? 0}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Drift monitoring unavailable for this role.</p>
          )}
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-4 text-lg font-medium">Calibration Curve</h2>
          {calibrationCurve?.mean_predicted_value?.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={calibrationCurve.mean_predicted_value.map((v, i) => ({ x: v, y: calibrationCurve.fraction_of_positives[i] }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="x" domain={[0,1]} type="number" />
                  <YAxis dataKey="y" domain={[0,1]} type="number" />
                  <Tooltip />
                  <Line dataKey="y" stroke="#2563eb" dot />
                  <Line data={[{x:0,y:0},{x:1,y:1}]} dataKey="y" stroke="#94a3b8" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="text-sm text-slate-500">Calibration data unavailable.</p>}
          <p className="mt-2 text-xs text-slate-500">Brier score: {calibrationCurve?.brier_score ?? 'n/a'}</p>
        </section>
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="mb-4 text-lg font-medium">Kaplan-Meier Survival Curves</h2>
          {survivalCurves?.curves ? <SurvivalCurveChart curves={survivalCurves.curves} /> : <p className="text-sm text-slate-500">Survival curves unavailable.</p>}
        </section>
      </div>

      <section className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-4 text-lg font-medium">Recent Prediction Log</h2>
        <ul className="space-y-2 text-sm">
          {predictionLog.slice(0, 10).map((entry) => (
            <li key={entry.prediction_id} className="rounded border border-slate-200 p-3">
              <p className="font-medium">
                Patient #{entry.patient_id} — {entry.target_type}
              </p>
              <p>
                Risk {entry.risk_score.toFixed(2)} ({entry.risk_category}) • {entry.model_version}
              </p>
              <p className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString()}</p>
            </li>
          ))}
          {predictionLog.length === 0 ? <li className="text-slate-500">No prediction logs available.</li> : null}
        </ul>
      </section>
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
