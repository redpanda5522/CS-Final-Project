import type { PerformanceMetrics as Metrics } from '../api/analysis'

const groups: { title: string; items: { key: keyof Metrics; label: string; hint: string }[] }[] = [
  { title: 'Classification', items: [
    { key: 'accuracy', label: 'Accuracy', hint: 'Share of predictions classified correctly' },
    { key: 'precision', label: 'Precision', hint: 'Share of predicted positives that were positive' },
    { key: 'recall', label: 'Recall', hint: 'Share of actual positives found' },
    { key: 'f1', label: 'F1 score', hint: 'Balance of precision and recall' },
    { key: 'auroc', label: 'AUROC', hint: 'Area under the receiver operating characteristic curve' },
    { key: 'auprc', label: 'AUPRC', hint: 'Area under the precision recall curve' },
  ] },
  { title: 'Probability and calibration', items: [
    { key: 'logLoss', label: 'Log loss', hint: 'Lower is better' },
    { key: 'brierScore', label: 'Brier score', hint: 'Mean squared probability error; lower is better' },
    { key: 'scaledBrierScore', label: 'Scaled Brier score', hint: 'Improvement over a prevalence baseline' },
    { key: 'calibrationIntercept', label: 'Calibration intercept', hint: 'Ideal value is 0' },
    { key: 'calibrationSlope', label: 'Calibration slope', hint: 'Ideal value is 1' },
    { key: 'observedExpectedRatio', label: 'Observed / expected', hint: 'Event count ratio; ideal value is 1' },
  ] },
]

function formatMetric(key: keyof Metrics, value: number | undefined) {
  if (value === undefined) return '—'
  if (['accuracy', 'precision', 'recall', 'f1', 'auroc', 'auprc'].includes(key)) return `${(value * 100).toFixed(1)}%`
  return value.toFixed(3)
}

export default function PerformanceMetrics({ metrics, isDemo }: { metrics?: Metrics; isDemo: boolean }) {
  const available = metrics && Object.keys(metrics).length > 0
  return <section className="work-card card-body performance-section" aria-labelledby="performance-heading">
    <h2 id="performance-heading">Model performance</h2>
    <p className="performance-intro">Evaluation metrics describe how the model performed across a test dataset. They do not measure the certainty of this procedure’s prediction.</p>
    {!available && <p className="performance-notice">{isDemo ? 'Performance metrics are not included in this demo.' : 'Performance metrics have not been provided by the backend for this model.'}</p>}
    {groups.map(group => <div className="performance-group" key={group.title}>
      <h3>{group.title}</h3>
      <dl className="performance-grid">{group.items.map(item => <div className="performance-item" key={item.key}>
        <dt>{item.label}<small>{item.hint}</small></dt>
        <dd aria-label={`${item.label}: ${metrics?.[item.key] === undefined ? 'Not available' : formatMetric(item.key, metrics[item.key])}`}>{formatMetric(item.key, metrics?.[item.key])}</dd>
      </div>)}</dl>
    </div>)}
    {available && <p className="performance-footnote">Metrics require an identified evaluation dataset and positive class for interpretation. A dash means the backend did not supply that metric.</p>}
  </section>
}
