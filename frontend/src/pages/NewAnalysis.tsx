import { Link } from 'react-router-dom'
import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { Activity, ArrowLeft, ArrowRight, Check, ClipboardList, CloudUpload, FileSpreadsheet, HeartPulse, RotateCcw, ShieldCheck, X } from 'lucide-react'
import { analyzeFile, analyzeManual, isDemoMode, type AnalysisResult } from '../api/analysis'
import { emptyProcedure, procedurePayload, validateProcedure } from '../types/procedure'
import AtriaPlot from '../components/AtriaPlot'
import { regionById } from '../config/regions'
import DatasetPreview from '../components/DatasetPreview'
import ManualEntry from '../components/ManualEntry'
import { FALLBACK_CATALOG, type ModelCatalog, type ModelName } from '../config/models'
import { fetchModelCatalog } from '../api/models'

type Mode = 'file' | 'manual'
type Stage = 'input' | 'review' | 'result'
const MAX_SIZE = 10 * 1024 * 1024 // Provisional limit; align with backend.
const ALLOWED = ['csv', 'json', 'xlsx']

type Props = { onComplete: (result: AnalysisResult, mode: Mode, sourceName: string) => void }

function NewAnalysis({ onComplete }: Props) {
  const [mode, setMode] = useState<Mode>('file')
  const [catalog, setCatalog] = useState<ModelCatalog>(FALLBACK_CATALOG)
  const [catalogStatus, setCatalogStatus] = useState<'loading' | 'ready' | 'fallback'>('loading')
  const [modelName, setModelName] = useState<ModelName>(FALLBACK_CATALOG.defaultModel)
  const [stage, setStage] = useState<Stage>('input')
  const [file, setFile] = useState<File | null>(null)
  const [procedure, setProcedure] = useState(emptyProcedure)
  const [previewRow, setPreviewRow] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const modelChosen = useRef(false)
  const selectedModel = catalog.models.find(model => model.id === modelName)
  const needsRawFile = mode === 'file' && selectedModel?.inputFormats.length === 1 && selectedModel.inputFormats[0] === 'raw'

  useEffect(() => {
    let active = true
    fetchModelCatalog().then(loaded => {
      if (!active) return
      setCatalog(loaded); setCatalogStatus('ready')
      // Keep the user's choice if they picked one while the list was loading.
      setModelName(current => modelChosen.current && loaded.models.some(model => model.id === current && model.available) ? current : loaded.defaultModel)
    }).catch(() => { if (active) setCatalogStatus('fallback') })
    return () => { active = false }
  }, [])

  function selectFile(candidate?: File) {
    setError('')
    if (!candidate) return
    const extension = candidate.name.split('.').pop()?.toLowerCase()
    if (!extension || !ALLOWED.includes(extension)) { setError('Choose a CSV, JSON, or XLSX file.'); return }
    if (candidate.size > MAX_SIZE) { setError('Choose a file smaller than 10 MB.'); return }
    if (candidate.size === 0) { setError('The selected file is empty.'); return }
    setFile(candidate); setPreviewRow(0)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files[0])
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]); event.target.value = ''
  }

  function next() {
    if (mode === 'file' && !file) { setError('Choose a procedure data file to continue.'); return }
    if (mode === 'manual') { const issue = validateProcedure(procedure); if (issue) { setError(issue); return } }
    if (selectedModel && !selectedModel.available) { setError(`The ${selectedModel.label} model is not available right now. Choose another model.`); return }
    setError(''); setStage('review')
  }

  async function submit() {
    if (mode === 'manual') { const issue = validateProcedure(procedure); if (issue) { setError(issue); return } }
    setLoading(true); setError('')
    try {
      const output = mode === 'file' && file
        ? await analyzeFile(file, modelName)
        : await analyzeManual(procedurePayload(procedure), modelName)
      setResult(output); setStage('result')
      onComplete(output, mode, mode === 'file' ? file!.name : 'Manual entry')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The analysis could not be completed.')
    } finally { setLoading(false) }
  }

  function reset() {
    setStage('input'); setMode('file'); setModelName(catalog.defaultModel); modelChosen.current = false; setFile(null); setPreviewRow(0); setProcedure(emptyProcedure())
    setResult(null); setError('')
  }

  return <>
        <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line" /> PROCEDURE ANALYSIS</div><h1>{stage === 'result' ? 'Analysis result' : 'New analysis'}</h1><p>Submit a completed procedure’s data for backend processing and outcome prediction.</p></div>
        <div className="content-grid"><section className="work-card">
          <div className="stepper"><div className={`step ${stage === 'input' ? 'current' : 'done'}`}><span>{stage === 'input' ? '1' : <Check size={15}/>}</span> Provide data</div><div className="step-line"/><div className={`step ${stage === 'review' ? 'current' : stage === 'result' ? 'done' : ''}`}><span>{stage === 'result' ? <Check size={15}/> : '2'}</span> Review</div><div className="step-line"/><div className={`step ${stage === 'result' ? 'current' : ''}`}><span>3</span> Result</div></div>
          {stage === 'input' && <div className="card-body"><div className="section-title"><span className="icon-box"><ClipboardList size={20}/></span><div><h2>Procedure data</h2><p>Choose how you would like to provide procedure data.</p></div></div>
            <div className="tabs" role="tablist" aria-label="Input method"><button type="button" role="tab" aria-selected={mode === 'file'} className={mode === 'file' ? 'active' : ''} onClick={() => { setMode('file'); setError('') }}><CloudUpload size={17}/> Upload file</button><button type="button" role="tab" aria-selected={mode === 'manual'} className={mode === 'manual' ? 'active' : ''} onClick={() => { setMode('manual'); setError('') }}><ClipboardList size={17}/> Enter manually</button></div>
            {mode === 'file' ? <div className="entry-area"><label className="field-label">Procedure data file <span>*</span></label><div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={handleDrop}><input ref={fileInput} className="visually-hidden" type="file" accept=".csv,.json,.xlsx" onChange={handleFileChange} aria-label="Upload procedure data file"/><div className="upload-icon"><CloudUpload size={28}/></div><strong>Drag and drop your file here</strong><span>or choose a file from your device</span><button type="button" className="secondary-button" onClick={() => fileInput.current?.click()}>Browse files</button><small>CSV, JSON, or XLSX · Maximum 10 MB</small></div>
              {file && <div className="selected-file"><FileSpreadsheet size={22}/><div><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB · Ready to submit</span></div><button type="button" aria-label="Remove selected file" onClick={() => setFile(null)}><X size={18}/></button></div>}
              {file && <DatasetPreview file={file} rowIndex={previewRow} onRowChange={setPreviewRow}/>}</div>
            : <ManualEntry values={procedure} onChange={action => { setProcedure(action); setError('') }} />}
            <div className="model-choice"><label className="field-label" htmlFor="model-name">Model variant</label><select id="model-name" value={modelName} disabled={catalogStatus === 'loading'} onChange={event => { modelChosen.current = true; setModelName(event.target.value); setError('') }}>{catalog.models.map(option => <option key={option.id} value={option.id} disabled={!option.available}>{option.label}{option.available ? '' : ' (unavailable)'}</option>)}</select><p>{catalogStatus === 'loading' ? 'Loading available models…' : catalogStatus === 'fallback' ? 'Could not load the model list from the server, so the default list is shown.' : needsRawFile ? 'This model needs the raw data.csv columns, including the V columns. Combined-column files are rejected.' : 'Models are listed by the backend.'}</p></div>
            {error && <p className="error-message" role="alert">{error}</p>}
            <div className="card-actions"><span>Fields marked * are required</span><button type="button" className="primary-button" onClick={next}>Continue to review <ArrowRight size={17}/></button></div>
          </div>}
          {stage === 'review' && <div className="card-body"><div className="section-title"><span className="icon-box"><ShieldCheck size={20}/></span><div><h2>Review submission</h2><p>Check the information before starting the analysis.</p></div></div><div className="review-panel"><span>INPUT METHOD</span><strong>{mode === 'file' ? 'Uploaded file' : 'Manual entry'}</strong><hr/><span>{mode === 'file' ? 'SELECTED FILE' : 'CATHETERS'}</span><strong>{mode === 'file' ? file?.name : `${procedure.points.length} catheters`}</strong><hr/><span>MODEL VARIANT</span><strong>{selectedModel?.label ?? modelName}</strong></div>{mode === 'file' && file && <DatasetPreview file={file} rowIndex={previewRow} onRowChange={setPreviewRow}/>}{mode === 'manual' && <><AtriaPlot points={procedure.points}/><div className="table-scroll"><table className="position-review"><thead><tr><th>Catheter</th><th>Region</th><th>Temperature</th><th>Pressure / force</th></tr></thead><tbody>{procedure.points.map((point, index) => <tr key={point.id}><td>{index + 1}</td><td>{regionById(point.regionId)?.label}</td><td>{point.temperature === '' ? '—' : `${point.temperature} ${procedure.temperatureUnit === 'unspecified' ? '(unit unspecified)' : procedure.temperatureUnit}`}</td><td>{point.pressure === '' ? '—' : `${point.pressure} ${procedure.pressureUnit === 'unspecified' ? '(unit unspecified)' : procedure.pressureUnit}`}</td></tr>)}</tbody></table></div></>}{error && <p className="error-message" role="alert">{error}</p>}<div className="card-actions"><button type="button" className="text-button" onClick={() => { setStage('input'); setError('') }}><ArrowLeft size={17}/> Edit information</button><button type="button" className="primary-button" disabled={loading} onClick={submit}>{loading ? 'Analyzing…' : 'Run analysis'} {!loading && <ArrowRight size={17}/>}</button></div></div>}
          {stage === 'result' && result && <div className="card-body"><div className="section-title"><span className="icon-box"><Activity size={20}/></span><div><h2>{isDemoMode ? 'Sample prediction' : 'Model prediction'}</h2><p>Outcome estimate based on the submitted procedure data.</p></div></div><div className="result-panel"><span className="result-label">PREDICTED OUTCOME</span><div className="result-outcome">{result.predictedOutcome === 'success' ? 'Successful outcome' : 'Unsuccessful outcome'}</div><p>Model estimate based on this procedure’s inputs.</p><div className="probability-row"><span>Estimated probability of success</span><strong>{Math.round(result.probability * 100)}%</strong></div><div className="meter"><div style={{ width: `${result.probability * 100}%` }}/></div></div>{!isDemoMode && <div className="definition"><strong>Outcome definition</strong><p>{result.outcomeDefinition}</p></div>}<p className="result-footnote">{isDemoMode ? 'Illustrative result only. Do not use for clinical decisions.' : 'Prediction is model generated and requires clinical interpretation.'} {result.modelVersion && `Model: ${result.modelVersion}.`}</p><div className="card-actions"><Link className="text-button" to="/analyses">View analyses →</Link><button type="button" className="text-button" onClick={reset}><RotateCcw size={17}/> Start another analysis</button></div></div>}
        </section><aside className="right-rail"><div className="rail-card"><div className="rail-icon"><HeartPulse size={21}/></div><h3>How it works</h3><div className="rail-step"><span>01</span><div><strong>Provide procedure data</strong><p>Upload a file or choose catheter regions and measurements.</p></div></div><div className="rail-step"><span>02</span><div><strong>Backend processing</strong><p>The service validates and formats data for the model.</p></div></div><div className="rail-step"><span>03</span><div><strong>Review prediction</strong><p>See the model’s estimated procedure outcome.</p></div></div></div></aside></div>
  </>
}

export default NewAnalysis
