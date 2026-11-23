import { useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { ArrowLeft, ArrowRight, Check, CloudUpload, FileSpreadsheet, RotateCcw, ShieldCheck, X } from 'lucide-react'
import { analyzeAblationSites, type AblationSiteAnalysisResult } from '../api/analysis'

const MAX_SIZE = 10 * 1024 * 1024

export default function AblationSiteAnalysis() {
  const [stage, setStage] = useState<'input' | 'review' | 'result'>('input')
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<AblationSiteAnalysisResult | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  function selectFile(candidate?: File) {
    setError('')
    if (!candidate) return
    if (!candidate.name.toLowerCase().endsWith('.txt')) {
      setError('Choose a whitespace-delimited .txt file.')
      return
    }
    if (candidate.size > MAX_SIZE) {
      setError('Choose a file smaller than 10 MB.')
      return
    }
    if (candidate.size === 0) {
      setError('The selected file is empty.')
      return
    }
    setFile(candidate)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    selectFile(event.dataTransfer.files[0])
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0])
    event.target.value = ''
  }

  async function submit() {
    if (!file) {
      setError('Choose an ablation-site data file to continue.')
      setStage('input')
      return
    }
    setLoading(true)
    setError('')
    try {
      setResult(await analyzeAblationSites(file))
      setStage('result')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The clustering analysis could not be completed.')
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setStage('input')
    setFile(null)
    setResult(null)
    setError('')
  }

  return <div className="content-grid">
    <section className="work-card">
      <div className="stepper">
        <div className={`step ${stage === 'input' ? 'current' : 'done'}`}><span>{stage === 'input' ? '1' : <Check size={15}/>}</span> Provide data</div>
        <div className="step-line"/>
        <div className={`step ${stage === 'review' ? 'current' : stage === 'result' ? 'done' : ''}`}><span>{stage === 'result' ? <Check size={15}/> : '2'}</span> Review</div>
        <div className="step-line"/>
        <div className={`step ${stage === 'result' ? 'current' : ''}`}><span>3</span> Result</div>
      </div>
      {stage === 'input' && <div className="card-body">
        <div className="section-title"><span className="icon-box"><CloudUpload size={20}/></span><div><h2>Ablation-Site Data</h2><p>Upload one patient’s site records to project them into the saved PCA/KMeans clusters. This feature is compatible with the Sites.txt file from the CARTO VISITAG™ Module</p></div></div>
        <label className="field-label">Patient site data file <span>*</span></label>
        <div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={handleDrop}>
          <input ref={fileInput} className="visually-hidden" type="file" accept=".txt,text/plain" onChange={handleFileChange} aria-label="Upload ablation-site data file"/>
          <div className="upload-icon"><CloudUpload size={28}/></div>
          <strong>Drag and drop your file here</strong>
          <span>or choose a file from your device</span>
          <button type="button" className="secondary-button" onClick={() => fileInput.current?.click()}>Browse Files</button>
          <small>Whitespace-delimited TXT with a header row · Maximum 10 MB</small>
        </div>
        {file && <div className="selected-file"><FileSpreadsheet size={22}/><div><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB · Ready to submit</span></div><button type="button" aria-label="Remove selected file" onClick={() => setFile(null)}><X size={18}/></button></div>}
        <div className="info-box"><span>The file must contain one patient’s site rows and the columns Session, ChannelID, SiteIndex, X, Y, Z, DurationTime, AverageForce, MaxTemperature, MaxPower, BaseImpedance, ImpedanceDrop, FTI, RFIndex, and TagIndexStatus. Missing measurement values and extreme values are handled by the clustering model.</span></div>
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="card-actions"><span>One patient per file</span><button type="button" className="primary-button" onClick={() => file ? (setError(''), setStage('review')) : setError('Choose an ablation-site data file to continue.')}>Continue to review <ArrowRight size={17}/></button></div>
      </div>}
      {stage === 'review' && <div className="card-body">
        <div className="section-title"><span className="icon-box"><ShieldCheck size={20}/></span><div><h2>Review submission</h2><p>The saved preprocessing pipeline will summarize and project the uploaded patient.</p></div></div>
        <div className="review-panel"><span>INPUT DATA</span><strong>{file?.name}</strong><hr/><span>PROCESSING</span><strong>Site Statistics → Input Standardization → KMeans and PCA</strong></div>
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="card-actions"><button type="button" className="text-button" onClick={() => { setStage('input'); setError('') }}><ArrowLeft size={17}/> Edit file</button><button type="button" className="primary-button" disabled={loading} onClick={submit}>{loading ? 'Analyzing…' : 'Run clustering'} {!loading && <ArrowRight size={17}/>}</button></div>
      </div>}
      {stage === 'result' && result && <div className="card-body">
        <div className="section-title"><span className="icon-box"><Check size={20}/></span><div><h2>Ablation Clustering result</h2><p>{result.sourceName}</p></div></div>
        <div className="result-panel cluster-result-panel"><span className="result-label">ASSIGNED GROUP</span><div className="result-outcome">{clusterName(result.cluster)}</div><p>{clusterDescription(result.cluster)}</p></div>
        <AblationClusterCharts result={result}/>
        <p className="result-footnote">Feature contributions use between-cluster sum of squares as in the reference analysis. Model: {result.modelVersion}.</p>
        <div className="card-actions"><button type="button" className="text-button" onClick={reset}><RotateCcw size={17}/> Analyze another patient</button></div>
      </div>}
    </section>
    <aside className="right-rail"><div className="rail-card"><div className="rail-icon"><CloudUpload size={21}/></div><h3>How It Works</h3><div className="rail-step"><span>01</span><div><strong>Input Data</strong><p>Upload the Sites.txt file from the Carto Visitag output folder</p></div></div><div className="rail-step"><span>02</span><div><strong>Load Clustering Model</strong><p>The pipeline computes site statistics and applies the trained model.</p></div></div><div className="rail-step"><span>03</span><div><strong>Cluster Visualization</strong><p>See the patient’s projected position and the features that separate clusters.</p></div></div></div></aside>
  </div>
}

function AblationClusterCharts({ result }: { result: AblationSiteAnalysisResult }) {
  const width = 620
  const height = 360
  const left = 58
  const right = 22
  const top = 24
  const bottom = 48
  const points = [
    ...result.pca.trainingPoints.map(point => ({ ...point, patient: false })),
    { cluster: result.cluster, x: result.pca.point.x, y: result.pca.point.y, patient: true },
  ]
  const xValues = points.map(point => point.x)
  const yValues = points.map(point => point.y)
  const xSpan = Math.max(...xValues) - Math.min(...xValues) || 1
  const ySpan = Math.max(...yValues) - Math.min(...yValues) || 1
  const xMin = Math.min(...xValues) - xSpan * 0.12
  const xMax = Math.max(...xValues) + xSpan * 0.12
  const yMin = Math.min(...yValues) - ySpan * 0.12
  const yMax = Math.max(...yValues) + ySpan * 0.12
  const px = (value: number) => left + (value - xMin) / (xMax - xMin) * (width - left - right)
  const py = (value: number) => height - bottom - (value - yMin) / (yMax - yMin) * (height - top - bottom)
  const maxContribution = Math.max(...result.featureContributions.map(item => item.contributionPercent), 1)

  return <div className="cluster-charts">
    <section className="cluster-chart-card" aria-labelledby="pca-chart-title">
      <h3 id="pca-chart-title">PCA-Based Visualization of Patient Clusters</h3>
      <p>This graph shows the similarity between the uploaded patient and other patients, clustered into 2 groups and projected into a 2D space using PCA.</p>
      <div className="cluster-chart-scroll"><svg className="pca-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`PCA scatter plot. Patient assigned to ${clusterName(result.cluster)}.`}>
        {[0, 1, 2, 3, 4].map(tick => {
          const y = top + tick * (height - top - bottom) / 4
          const value = yMax - tick * (yMax - yMin) / 4
          return <g key={tick}><line x1={left} x2={width - right} y1={y} y2={y} className="chart-gridline"/><text x={left - 8} y={y + 4} textAnchor="end" className="chart-tick">{value.toFixed(2)}</text></g>
        })}
        <line x1={left} x2={left} y1={top} y2={height - bottom} className="chart-axis"/>
        <line x1={left} x2={width - right} y1={height - bottom} y2={height - bottom} className="chart-axis"/>
        <text x={(left + width - right) / 2} y={height - 10} textAnchor="middle" className="chart-axis-label">PC1</text>
        <text transform={`translate(16 ${(top + height - bottom) / 2}) rotate(-90)`} textAnchor="middle" className="chart-axis-label">PC2</text>
        {points.map((point, index) => <g key={`${point.patient ? 'patient' : 'training'}-${index}`}>
          <circle cx={px(point.x)} cy={py(point.y)} r={point.patient ? 9 : 3.5} className={point.patient ? 'pca-patient-point' : 'pca-training-point'} style={!point.patient ? { fill: clusterColor(point.cluster) } : undefined}/>
          {point.patient && <text x={px(point.x) + 10} y={py(point.y) - 9} className="pca-point-label">{result.sourceName} · patient</text>}
          <title>{point.patient ? `${result.sourceName}, assigned to ${clusterName(point.cluster)}` : `Training sample ${index + 1}, ${clusterName(point.cluster)}`}</title>
        </g>)}
      </svg></div>
      <div className="chart-legend"><span><i className="legend-patient"/> Uploaded patient</span>{Array.from(new Set(result.pca.trainingPoints.map(point => point.cluster))).sort((a, b) => a - b).map(cluster => <span key={cluster}><i style={{ backgroundColor: clusterColor(cluster) }}/> {clusterName(cluster)}</span>)}</div>
    </section>
    <section className="cluster-chart-card" aria-labelledby="feature-chart-title">
      <h3 id="feature-chart-title">Feature Contributions to Clustering</h3>
      <p>Top features ranked by between-cluster sum of squares.</p>
      <ol className="contribution-list">{result.featureContributions.map(item => <li key={item.feature}>
        <span className="contribution-name">{item.feature}</span>
        <span className="contribution-track"><i style={{ width: `${item.contributionPercent / maxContribution * 100}%` }}/></span>
        <strong>{item.contributionPercent.toFixed(1)}%</strong>
      </li>)}</ol>
    </section>
  </div>
}

function clusterColor(cluster: number): string {
  const colors = ['#168f86', '#5577c8']
  return colors[cluster % colors.length]
}

function clusterName(cluster: number): string {
  if (cluster === 0) return 'Abnormal'
  return `Normal`
}

function clusterDescription(cluster: number): string {
  if (cluster === 0) {
    return 'The model found a significant difference between the uploaded patient and normal ablation site characteristics. This patient may have atypical ablation-site features, but there isn’t enough data to determine an ablation outcome yet.'
  }
  return 'The model found that the uploaded patient has ablation site characteristics similar to patients in the training data that recovered from atrial fibrillation after ablation. This is a clustering result, not a clinical outcome prediction.'
}
