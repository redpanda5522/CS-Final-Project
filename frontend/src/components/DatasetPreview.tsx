import { useEffect, useState } from 'react'
import { REGIONS } from '../config/regions'
import { parseRegionCsv, regionalValues } from '../data/regionGrouping'
import AtriaPlot from './AtriaPlot'

type Preview = ReturnType<typeof parseRegionCsv>
export default function DatasetPreview({ file, rowIndex, onRowChange }: { file: File; rowIndex: number; onRowChange: (index: number) => void }) {
  const [preview, setPreview] = useState<Preview | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let cancelled = false
    setPreview(null); setError('')
    if (!file.name.toLowerCase().endsWith('.csv')) return
    void file.text().then(text => { const result = parseRegionCsv(text); if (!cancelled) setPreview(result) }).catch(cause => { if (!cancelled) setError(cause instanceof Error ? cause.message : 'Preview unavailable.') })
    return () => { cancelled = true }
  }, [file])
  if (!file.name.toLowerCase().endsWith('.csv')) return <p className="schema-note">Region preview is available for binary CSV files. Your original file will be submitted.</p>
  if (error) return <p className="schema-note" role="status">{error}</p>
  if (!preview) return <p className="schema-note" role="status">Reading region groups…</p>
  const flags = regionalValues(preview.groups, preview.rows[rowIndex])
  const active = REGIONS.filter(region => flags[region.id] === 1).map(region => region.id)
  const activeNamed = preview.groups.filter(group => preview.rows[rowIndex][group.key] === 1)
  const unmapped = activeNamed.filter(group => !group.regionId)
  return <div className="dataset-region-preview"><div className="position-heading"><h3>Collapsed region preview</h3><span>{preview.groups.length.toLocaleString()} named groups</span></div><p className="schema-note">{preview.variantCount.toLocaleString()} V columns grouped with the nearest named column to their left. Shading indicates a recorded region flag, not a catheter count.</p>
    <label className="preview-row">Preview row<select aria-label="Preview row" value={rowIndex} onChange={event => onRowChange(Number(event.target.value))}>{preview.rows.map((_, index) => <option key={index} value={index}>Row {index + 1}</option>)}</select></label>
    <AtriaPlot points={[]} activeRegions={active}/>
    <div className="region-summary">{REGIONS.map(region => <span key={region.id} className={flags[region.id] === 1 ? 'present' : ''}>{region.short}: {flags[region.id] === 1 ? 'present' : flags[region.id] === 0 ? 'not recorded' : 'unspecified'}</span>)}</div>
    <details className="source-groups"><summary>{activeNamed.length} active named groups · {unmapped.length} without a diagram mapping</summary><ul>{activeNamed.map(group => <li key={group.key}><code>{group.key}</code>{group.columns.length > 1 && <small> + {group.columns.length - 1} V variations</small>}{!group.regionId && <small> · unmapped</small>}</li>)}</ul></details>
  </div>
}
