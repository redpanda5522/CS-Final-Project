import { useState, type Dispatch, type SetStateAction } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { MAX_CATHETERS, newPoint, type CatheterPoint, type ProcedureDraft } from '../types/procedure'
import { REGIONS, sourceGroupsForRegion } from '../config/regions'
import AtriaPlot from './AtriaPlot'

type Props = { values: ProcedureDraft; onChange: Dispatch<SetStateAction<ProcedureDraft>> }
export default function ManualEntry({ values, onChange }: Props) {
  const [selectedId, setSelectedId] = useState(values.points[0]?.id)
  const selected = values.points.find(point => point.id === selectedId) ?? values.points[0]
  const selectedIndex = values.points.findIndex(point => point.id === selected?.id)
  function update(changes: Partial<CatheterPoint>) {
    if (!selected) return
    onChange(current => ({ ...current, points: current.points.map(point => point.id === selected.id ? { ...point, ...changes } : point) }))
  }
  function add() {
    if (values.points.length >= MAX_CATHETERS) return
    const point = newPoint()
    onChange(current => ({ ...current, points: current.points.length < MAX_CATHETERS ? [...current.points, point] : current.points })); setSelectedId(point.id)
  }
  return <div className="entry-area catheter-entry">
    <AtriaPlot points={values.points} selectedId={selected?.id} onRegionSelect={regionId => update({ regionId })}/>
    <div className="position-heading"><h3>Catheters <span>{values.points.length} / {MAX_CATHETERS}</span></h3><button type="button" className="text-button" disabled={values.points.length >= MAX_CATHETERS} onClick={add}><Plus size={16}/> Add catheter</button></div>
    <div className="position-tabs" aria-label="Catheters">{values.points.map((point, index) => <button type="button" key={point.id} className={selected?.id === point.id ? 'selected' : ''} aria-pressed={selected?.id === point.id} onClick={() => setSelectedId(point.id)}>Catheter {index + 1}</button>)}</div>
    {selected && <div className="position-editor"><div className="position-heading"><strong>Catheter {selectedIndex + 1}</strong><button type="button" className="text-button" aria-label={`Remove catheter ${selectedIndex + 1}`} onClick={() => onChange(current => ({ ...current, points: current.points.filter(point => point.id !== selected.id) }))}><Trash2 size={15}/> Remove</button></div>
      <div className="region-field"><label>Heart region *<select aria-label="Heart region" value={selected.regionId} onChange={event => update({ regionId: event.target.value as CatheterPoint['regionId'] })}><option value="">Choose a region</option>{REGIONS.map(region => <option key={region.id} value={region.id}>{region.label} ({region.short})</option>)}</select></label></div>
      {selected.regionId && <details className="source-groups"><summary>{sourceGroupsForRegion(selected.regionId).length} associated named data groups</summary><ul>{sourceGroupsForRegion(selected.regionId).map(key => <li key={key}><code>{key}</code></li>)}</ul></details>}
      <div className="measurement-fields"><label>Temperature<input type="number" step="any" placeholder="Optional" value={selected.temperature} onChange={event => update({ temperature: event.target.value })}/></label><label>Unit<select aria-label="Temperature unit" value={values.temperatureUnit} onChange={event => onChange(current => ({ ...current, temperatureUnit: event.target.value as ProcedureDraft['temperatureUnit'] }))}><option value="unspecified">Unspecified</option><option value="C">°C</option><option value="F">°F</option></select></label><label>Pressure / contact force<input type="number" min="0" step="any" placeholder="Optional" value={selected.pressure} onChange={event => update({ pressure: event.target.value })}/></label><label>Unit<select aria-label="Pressure unit" value={values.pressureUnit} onChange={event => onChange(current => ({ ...current, pressureUnit: event.target.value as ProcedureDraft['pressureUnit'] }))}><option value="unspecified">Unspecified</option><option value="g">g (contact force)</option><option value="mmHg">mmHg</option><option value="kPa">kPa</option></select></label></div>
    </div>}
  </div>
}
