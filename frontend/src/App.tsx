import { useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { Activity, ArrowLeft, ArrowRight, Check, ChevronDown, CircleHelp, ClipboardList, CloudUpload, FileSpreadsheet, HeartPulse, Info, RotateCcw, ShieldCheck, X } from 'lucide-react'
import { analyzeFile, analyzeManual, isDemoMode, type AnalysisResult } from './api/analysis'
import { LOCATION_FIELDS, type LocationId } from './config/fields'

type Mode = 'file' | 'manual'
type Stage = 'input' | 'review' | 'result'
const MAX_SIZE = 10 * 1024 * 1024 // Provisional limit; align with backend.
const ALLOWED = ['csv', 'json', 'xlsx']

const emptyLocations = (): Record<LocationId, boolean> => Object.fromEntries(
  LOCATION_FIELDS.map(field => [field.id, false]),
) as Record<LocationId, boolean>

function App() {
  const [mode, setMode] = useState<Mode>('file')
  const [stage, setStage] = useState<Stage>('input')
  const [file, setFile] = useState<File | null>(null)
  const [locations, setLocations] = useState(emptyLocations)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const selectedCount = Object.values(locations).filter(Boolean).length

  function selectFile(candidate?: File) {
    setError('')
    if (!candidate) return
    const extension = candidate.name.split('.').pop()?.toLowerCase()
    if (!extension || !ALLOWED.includes(extension)) { setError('Choose a CSV, JSON, or XLSX file.'); return }
    if (candidate.size > MAX_SIZE) { setError('Choose a file smaller than 10 MB.'); return }
    if (candidate.size === 0) { setError('The selected file is empty.'); return }
    setFile(candidate)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files[0])
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]); event.target.value = ''
  }

  function next() {
    if (mode === 'file' && !file) { setError('Choose a procedure data file to continue.'); return }
    if (mode === 'manual' && selectedCount === 0) { setError('Select at least one location to continue.'); return }
    setError(''); setStage('review')
  }

  async function submit() {
    setLoading(true); setError('')
    try {
      const output = mode === 'file' && file
        ? await analyzeFile(file)
        : await analyzeManual({ locations })
      setResult(output); setStage('result')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The analysis could not be completed.')
    } finally { setLoading(false) }
  }

  function reset() {
    setStage('input'); setMode('file'); setFile(null); setLocations(emptyLocations())
    setResult(null); setError('')
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark"><HeartPulse size={23} strokeWidth={2.1} /></span><span>Ablation<span className="brand-light">Outcome</span><small>CLINICAL RESEARCH TOOL</small></span></div>
      <div className="side-label">WORKSPACE</div>
      <div className="side-active"><Activity size={18} /> New analysis</div>
      <div className="sidebar-bottom"><div className="side-help"><CircleHelp size={18} /> Project prototype</div><div className="user-card"><span className="avatar">R</span><span>Research workspace<small>Capstone prototype</small></span><ChevronDown size={15} /></div></div>
    </aside>

    <div className="main-column">
      <header className="topbar"><span className="breadcrumb">Workspace <span>/</span> <strong>New analysis</strong></span><span className="top-status"><span className="status-dot" /> {isDemoMode ? 'Demo mode' : 'API connected'}</span></header>
      <main>
        <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line" /> PROCEDURE ANALYSIS</div><h1>{stage === 'result' ? 'Analysis result' : 'New analysis'}</h1><p>Submit catheter location data from a completed ablation procedure for outcome prediction.</p></div>
        <div className="content-grid"><section className="work-card">
          <div className="stepper"><div className={`step ${stage === 'input' ? 'current' : 'done'}`}><span>{stage === 'input' ? '1' : <Check size={15}/>}</span> Provide data</div><div className="step-line"/><div className={`step ${stage === 'review' ? 'current' : stage === 'result' ? 'done' : ''}`}><span>{stage === 'result' ? <Check size={15}/> : '2'}</span> Review</div><div className="step-line"/><div className={`step ${stage === 'result' ? 'current' : ''}`}><span>3</span> Result</div></div>
          {stage === 'input' && <div className="card-body"><div className="section-title"><span className="icon-box"><ClipboardList size={20}/></span><div><h2>Procedure data</h2><p>Choose how you would like to provide catheter location information.</p></div></div>
            <div className="tabs" role="tablist" aria-label="Input method"><button type="button" role="tab" aria-selected={mode === 'file'} className={mode === 'file' ? 'active' : ''} onClick={() => { setMode('file'); setError('') }}><CloudUpload size={17}/> Upload file</button><button type="button" role="tab" aria-selected={mode === 'manual'} className={mode === 'manual' ? 'active' : ''} onClick={() => { setMode('manual'); setError('') }}><ClipboardList size={17}/> Enter manually</button></div>
            {mode === 'file' ? <div className="entry-area"><label className="field-label">Procedure data file <span>*</span></label><div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={handleDrop}><input ref={fileInput} className="visually-hidden" type="file" accept=".csv,.json,.xlsx" onChange={handleFileChange} aria-label="Upload procedure data file"/><div className="upload-icon"><CloudUpload size={28}/></div><strong>Drag and drop your file here</strong><span>or choose a file from your device</span><button type="button" className="secondary-button" onClick={() => fileInput.current?.click()}>Browse files</button><small>CSV, JSON, or XLSX · Maximum 10 MB</small></div>
              {file && <div className="selected-file"><FileSpreadsheet size={22}/><div><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB · Ready to submit</span></div><button type="button" aria-label="Remove selected file" onClick={() => setFile(null)}><X size={18}/></button></div>}</div>
            : <div className="entry-area"><div className="manual-heading"><div><label className="field-label">Catheter locations <span>*</span></label><p>Select each location recorded in the procedure.</p></div><span>{selectedCount} selected</span></div><div className="locations-grid">{LOCATION_FIELDS.map(field => <label key={field.id} className={`location-option ${locations[field.id] ? 'selected' : ''}`}><input type="checkbox" checked={locations[field.id]} onChange={() => setLocations(current => ({ ...current, [field.id]: !current[field.id] }))}/><span className="checkbox-visual"><Check size={13}/></span><span>{field.label}</span></label>)}</div><div className="info-box"><Info size={18}/><span>These are example location fields. Replace them with the dataset’s exact location names and add any required procedure settings before connecting a real model.</span></div></div>}
            {error && <p className="error-message" role="alert">{error}</p>}
            <div className="card-actions"><span>Fields marked * are required</span><button type="button" className="primary-button" onClick={next}>Continue to review <ArrowRight size={17}/></button></div>
          </div>}
          {stage === 'review' && <div className="card-body"><div className="section-title"><span className="icon-box"><ShieldCheck size={20}/></span><div><h2>Review submission</h2><p>Check the information before starting the analysis.</p></div></div><div className="review-panel"><span>INPUT METHOD</span><strong>{mode === 'file' ? 'Uploaded file' : 'Manual entry'}</strong><hr/><span>{mode === 'file' ? 'SELECTED FILE' : 'SELECTED LOCATIONS'}</span><strong>{mode === 'file' ? file?.name : LOCATION_FIELDS.filter(field => locations[field.id]).map(field => field.label).join(', ')}</strong></div><div className="info-box"><Info size={18}/><span>{isDemoMode ? 'This will show a sample result. The prototype does not upload or analyze your data.' : 'The backend will process your submission and return a prediction.'}</span></div>{error && <p className="error-message" role="alert">{error}</p>}<div className="card-actions"><button type="button" className="text-button" onClick={() => { setStage('input'); setError('') }}><ArrowLeft size={17}/> Edit information</button><button type="button" className="primary-button" disabled={loading} onClick={submit}>{loading ? 'Analyzing…' : 'Run analysis'} {!loading && <ArrowRight size={17}/>}</button></div></div>}
          {stage === 'result' && result && <div className="card-body"><div className="section-title"><span className="icon-box"><Activity size={20}/></span><div><h2>{isDemoMode ? 'Sample prediction' : 'Model prediction'}</h2><p>Outcome estimate based on the submitted procedure data.</p></div></div><div className="result-panel"><span className="result-label">PREDICTED OUTCOME</span><div className="result-outcome">{result.predictedOutcome === 'success' ? 'Successful outcome' : 'Unsuccessful outcome'}</div><p>Model estimate based on this procedure’s inputs.</p><div className="probability-row"><span>Estimated probability of success</span><strong>{Math.round(result.probability * 100)}%</strong></div><div className="meter"><div style={{ width: `${result.probability * 100}%` }}/></div></div><div className="definition"><strong>What does “success” mean?</strong><p>{result.outcomeDefinition}</p></div><p className="result-footnote">{isDemoMode ? 'Illustrative result only. Do not use for clinical decisions.' : 'Prediction is model generated and requires clinical interpretation.'} {result.modelVersion && `Model: ${result.modelVersion}.`}</p><div className="card-actions"><button type="button" className="text-button" onClick={reset}><RotateCcw size={17}/> Start another analysis</button></div></div>}
        </section><aside className="right-rail"><div className="rail-card"><div className="rail-icon"><HeartPulse size={21}/></div><h3>How it works</h3><div className="rail-step"><span>01</span><div><strong>Provide procedure data</strong><p>Upload a file or enter location flags manually.</p></div></div><div className="rail-step"><span>02</span><div><strong>Backend processing</strong><p>The service validates and formats data for the model.</p></div></div><div className="rail-step"><span>03</span><div><strong>Review prediction</strong><p>See the model’s estimated procedure outcome.</p></div></div></div><div className="rail-note"><ShieldCheck size={18}/><p><strong>Research prototype</strong><br/>Use de-identified sample data while access, privacy, and clinical review requirements are being defined.</p></div></aside></div>
      </main><footer>Capstone project prototype <span>·</span> Ablation outcome analysis</footer>
    </div>
  </div>
}

export default App
