import { useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { ArrowLeft, ArrowRight, Check, ClipboardList, CloudUpload, FileSpreadsheet, HeartPulse, RotateCcw, ShieldCheck, X } from 'lucide-react'
import { trainModel, isDemoMode, type ModelTrainingResult } from '../api/analysis'
import { FALLBACK_CATALOG, type ModelName } from '../config/models'

type Stage = 'input' | 'review' | 'result'
const MAX_SIZE = 10 * 1024 * 1024 // Provisional limit; align with backend.
const ALLOWED = ['csv', 'json', 'xlsx']

function NewModel() {
  const [stage, setStage] = useState<Stage>('input')
  const [file, setFile] = useState<File | null>(null)
  const [targetColumn, setTargetColumn] = useState('')
  const [modelName, setModelName] = useState<ModelName>('')
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ModelTrainingResult | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const selectedModel = FALLBACK_CATALOG.models.find(model => model.id === modelName)

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
    if (!file) { setError('Choose a data file to continue.'); return }
    if (!targetColumn.trim()) { setError('Enter the target column name to continue.'); return }
    if (!modelName) { setError('Select a model to continue.'); return }
    setError(''); setStage('review')
  }

  async function submit() {
    if (!file) { setError('Choose a data file to continue.'); return }
    if (!modelName) { setError('Select a model to continue.'); return }
    setLoading(true); setError('')
    try {
      const output = await trainModel(file, targetColumn.trim(), modelName)
      setResult(output); setStage('result')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Model training could not be completed.')
    } finally { setLoading(false) }
  }

  function reset() {
    setStage('input'); setFile(null); setTargetColumn(''); setModelName('')
    setResult(null); setError('')
  }

  return <>
        <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line" /> MODEL MANAGEMENT</div><h1>Model Training</h1><p>Train binary or multiclass XGBoost classifiers using an uploaded dataset.</p></div>
        <div className="content-grid"><section className="work-card">
          <div className="stepper"><div className={`step ${stage === 'input' ? 'current' : 'done'}`}><span>{stage === 'input' ? '1' : <Check size={15}/>}</span> Provide data</div><div className="step-line"/><div className={`step ${stage === 'review' ? 'current' : stage === 'result' ? 'done' : ''}`}><span>{stage === 'result' ? <Check size={15}/> : '2'}</span> Review</div><div className="step-line"/><div className={`step ${stage === 'result' ? 'current' : ''}`}><span>3</span> Result</div></div>
          {stage === 'input' && <div className="card-body"><div className="section-title"><span className="icon-box"><ClipboardList size={20}/></span><div><h2>Model Training</h2><p>Upload a dataset and choose its target column.</p></div></div>
            <div className="entry-area"><label className="field-label">Dataset File Upload <span>*</span></label><div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={handleDrop}><input ref={fileInput} className="visually-hidden" type="file" accept=".csv,.json,.xlsx" onChange={handleFileChange} aria-label="Upload Dataset File"/><div className="upload-icon"><CloudUpload size={28}/></div><strong>Drag and drop your file here</strong><span>or choose a file from your device</span><button type="button" className="secondary-button" onClick={() => fileInput.current?.click()}>Browse files</button><small>CSV, JSON, or XLSX · Maximum 10 MB</small></div>
              {file && <div className="selected-file"><FileSpreadsheet size={22}/><div><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB · Ready to submit</span></div><button type="button" aria-label="Remove selected file" onClick={() => setFile(null)}><X size={18}/></button></div>}
            </div>
            <div className="model-choice"><label className="field-label" htmlFor="target-column">Target column <span>*</span></label><input id="target-column" type="text" value={targetColumn} onChange={event => { setTargetColumn(event.target.value); setError('') }} aria-describedby="target-column-help"/><p id="target-column-help">Name of the column with at least two class labels. Numeric and categorical labels are supported.</p></div>
            <div className="model-choice">
              <label className="field-label" htmlFor="training-model">Model</label>
              <select id="training-model" value={modelName} required onChange={event => { setModelName(event.target.value); setError('') }}>
                <option value="" disabled>Select a model</option>
                {FALLBACK_CATALOG.models.map(model => (
                  <option key={model.id} value={model.id} disabled={model.id !== 'xgboost'}>
                    {model.label}
                  </option>
                ))}
              </select>
              <p>Only XGBoost training is currently supported.</p>
            </div>
            {error && <p className="error-message" role="alert">{error}</p>}
            <div className="card-actions"><span>Fields marked * are required</span><button type="button" className="primary-button" onClick={next}>Continue to review <ArrowRight size={17}/></button></div>
          </div>}
          {stage === 'review' && <div className="card-body"><div className="section-title"><span className="icon-box"><ShieldCheck size={20}/></span><div><h2>Review training</h2><p>Confirm the dataset and target column before training.</p></div></div><div className="review-panel"><span>DATASET</span><strong>{file?.name}</strong><hr/><span>TARGET COLUMN</span><strong>{targetColumn.trim()}</strong><hr/><span>MODEL</span><strong>{selectedModel?.label ?? modelName}</strong></div>{error && <p className="error-message" role="alert">{error}</p>}<div className="card-actions"><button type="button" className="text-button" onClick={() => { setStage('input'); setError('') }}><ArrowLeft size={17}/> Edit inputs</button><button type="button" className="primary-button" disabled={loading} onClick={submit}>{loading ? 'Training…' : 'Train model'} {!loading && <ArrowRight size={17}/>}</button></div></div>}
          {stage === 'result' && result && <div className="card-body"><div className="section-title"><span className="icon-box"><ClipboardList size={20}/></span><div><h2>{isDemoMode ? 'Demo training complete' : 'Training complete'}</h2><p>{isDemoMode ? 'Demo mode simulates the request; no model was trained.' : result.compatibleWithOutcomeAnalysis ? 'The binary XGBoost model was trained and activated for outcome analysis.' : 'The model was trained and saved. The existing outcome-analysis workflow accepts only binary labels 0 and 1.'}</p></div></div><div className="result-panel"><span className="result-label">VALIDATION ACCURACY</span><div className="result-outcome">{Math.round(result.accuracy * 100)}%</div><p>Correct predictions on the held-out validation rows for “{result.targetColumn}”.</p><div className="probability-row"><span>Validation rows</span><strong>{result.validationRows}</strong></div><div className="meter"><div style={{ width: `${result.accuracy * 100}%` }}/></div></div><p className="result-footnote">Accuracy is the share of held-out rows whose predicted class matched the target label. It is not a probability estimate or a measure of clinical confidence.</p><div className="review-panel"><span>MODEL</span><strong>XGBoost</strong><hr/><span>CLASSIFICATION TYPE</span><strong>{result.classificationType}</strong><hr/><span>CLASS LABELS</span><strong>{result.classLabels.join(', ')}</strong><hr/><span>TARGET COLUMN</span><strong>{result.targetColumn}</strong><hr/><span>ROWS TRAINED</span><strong>{result.rowsTrained}</strong><hr/><span>VALIDATION ROWS</span><strong>{result.validationRows}</strong><hr/><span>FEATURES</span><strong>{result.featureCount}</strong><hr/><span>MODEL VERSION</span><strong>{result.modelVersion}</strong></div><div className="card-actions"><button type="button" className="text-button" onClick={reset}><RotateCcw size={17}/> Train another model</button></div></div>}
        </section><aside className="right-rail"><div className="rail-card"><div className="rail-icon"><HeartPulse size={21}/></div><h3>How it works</h3><div className="rail-step"><span>01</span><div><strong>Upload the training dataset</strong><p>Provide a CSV, JSON, or XLSX file with labeled rows.</p></div></div><div className="rail-step"><span>02</span><div><strong>Select the target column</strong><p>Choose a column with two or more class labels.</p></div></div><div className="rail-step"><span>03</span><div><strong>Train the classifier</strong><p>The backend chooses binary or multiclass XGBoost based on the labels.</p></div></div></div></aside></div>
  </>
}

export default NewModel
