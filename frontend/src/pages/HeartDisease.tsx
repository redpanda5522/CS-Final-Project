import { useEffect, useState, type FormEvent } from 'react'
import { HeartPulse, RotateCcw } from 'lucide-react'
import { fetchHeartDiseaseModel, predictHeartDisease, type HeartDiseaseModel, type HeartDiseaseResult } from '../api/heartDisease'

export default function HeartDisease() {
  const [model, setModel] = useState<HeartDiseaseModel | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [result, setResult] = useState<HeartDiseaseResult | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    fetchHeartDiseaseModel().then(data => { if (active) setModel(data) })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Could not load the model configuration.') })
    return () => { active = false }
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!model?.available || loading) return
    const features: Record<string, string | number> = {}
    for (const field of model.fields) {
      const raw = values[field.name]?.trim() ?? ''
      if (!raw) { setError(`Enter ${field.label}.`); return }
      if (field.type === 'number') {
        const number = Number(raw)
        if (!Number.isFinite(number) || field.min !== undefined && number < field.min ||
            field.max !== undefined && number > field.max) { setError(`Enter a valid value for ${field.label}.`); return }
        features[field.name] = number
      } else {
        const choice = field.options?.find(option => String(option.value) === raw)
        if (!choice) { setError(`Choose ${field.label}.`); return }
        features[field.name] = choice.value
      }
    }
    setLoading(true); setError(''); setResult(null)
    try { setResult(await predictHeartDisease(features)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Prediction failed.') }
    finally { setLoading(false) }
  }

  return <>
    <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line"/> MODEL ANALYSIS</div>
      <h1>Heart disease detection</h1><p>Enter the features required by the connected model to run a prediction.</p></div>
    <div className="content-grid"><section className="work-card"><div className="card-body">
      <div className="section-title"><span className="icon-box"><HeartPulse size={20}/></span><div><h2>New prediction</h2><p>{model?.available ? `Model ${model.modelVersion}` : 'Model setup pending'}</p></div></div>
      {!model && !error && <p className="schema-note">Loading model configuration…</p>}
      {model && !model.available && <div className="demo-notice" role="status">{model.reason || 'The model is not available yet.'}</div>}
      {model?.available && <form onSubmit={submit}><div className="heart-fields">{model.fields.map(field => <div className="heart-field" key={field.name}>
        <label className="field-label" htmlFor={`heart-${field.name}`}>{field.label}{field.unit ? ` (${field.unit})` : ''} <span>*</span></label>
        {field.type === 'select' ? <select id={`heart-${field.name}`} required value={values[field.name] ?? ''} onChange={event => { setValues(current => ({ ...current, [field.name]: event.target.value })); setResult(null); setError('') }}><option value="">Select…</option>{field.options?.map(option => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select>
          : <input id={`heart-${field.name}`} type="number" step="any" required min={field.min} max={field.max} value={values[field.name] ?? ''} onChange={event => { setValues(current => ({ ...current, [field.name]: event.target.value })); setResult(null); setError('') }}/>}</div>)}</div>
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="card-actions"><span>All fields are required</span><button className="primary-button" type="submit" disabled={loading}>{loading ? 'Running prediction…' : 'Run prediction'}</button></div></form>}
      {error && !model?.available && <p className="error-message" role="alert">{error}</p>}
      {result && <div className="heart-result" aria-live="polite"><span className="result-label">MODEL PREDICTION</span><div className="result-outcome">{result.predictedClass === 'positive' ? 'Positive' : 'Negative'}</div><p>Estimated probability of the model’s positive class: <strong>{(result.positiveClassProbability * 100).toFixed(1)}%</strong></p><p>Model version: {result.modelVersion}</p><button className="text-button" type="button" onClick={() => { setValues({}); setResult(null); setError('') }}><RotateCcw size={16}/> Clear inputs</button></div>}
    </div></section><aside className="right-rail"><div className="rail-card"><div className="rail-icon"><HeartPulse size={21}/></div><h3>About this model</h3><p className="schema-note">The model supplies its exact input fields and the meaning of its positive class through the backend configuration. Results appear only after a connected model responds.</p></div></aside></div>
  </>
}
