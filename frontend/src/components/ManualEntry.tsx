import { useState, type Dispatch, type SetStateAction } from 'react'
import { FIELD_GROUPS, MANUAL_FIELDS, type BinaryValue, type FeatureValues } from '../config/fields'

type Props = { values: FeatureValues; onChange: Dispatch<SetStateAction<FeatureValues>> }
const PAGE_SIZE = 24

export default function ManualEntry({ values, onChange }: Props) {
  const [query, setQuery] = useState('')
  const [group, setGroup] = useState('All fields')
  const [page, setPage] = useState(0)
  const [enteredOnly, setEnteredOnly] = useState(false)
  const entered = Object.values(values).filter(value => value !== null).length
  const filtered = MANUAL_FIELDS.filter(field =>
    field.id.toLowerCase().includes(query.toLowerCase()) &&
    (group === 'All fields' || field.group === group) &&
    (!enteredOnly || values[field.id] !== null),
  )
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pages - 1)

  return <div className="entry-area">
    <div className="manual-heading"><div><h3>Dataset binary fields</h3><p>{MANUAL_FIELDS.length.toLocaleString()} dataset fields.</p></div><span>{entered} entered</span></div>
    <p className="schema-note">Choose 0 or 1 for each known value. Leave unknown values unspecified.</p>
    <div className="field-filters">
      <label>Search column name<input type="search" value={query} placeholder="e.g. la_ecg_export, contactforce, v3" onChange={event => { setQuery(event.target.value); setPage(0) }}/></label>
      <label>Column group<select value={group} onChange={event => { setGroup(event.target.value); setPage(0) }}><option>All fields</option>{FIELD_GROUPS.map(item => <option key={item}>{item}</option>)}</select></label>
    </div>
    <label className="entered-filter"><input type="checkbox" checked={enteredOnly} onChange={event => { setEnteredOnly(event.target.checked); setPage(0) }}/> Show entered fields only</label>
    <div className="dataset-fields">{filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE).map(field => <label className="dataset-field" key={field.id}>
      <span><code>{field.id}</code><small>{field.group}</small></span>
      <select aria-label={`${field.id} binary value`} value={values[field.id] ?? ''} onChange={event => {
        const value: BinaryValue = event.target.value === '' ? null : event.target.value === '1' ? 1 : 0
        onChange(current => ({ ...current, [field.id]: value }))
      }}><option value="">Unspecified</option><option value="0">0</option><option value="1">1</option></select>
    </label>)}</div>
    {filtered.length === 0 && <p className="schema-note">No fields match your filters.</p>}
    <div className="field-pagination"><button type="button" className="text-button" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous</button><span>Page {currentPage + 1} of {pages} · {filtered.length.toLocaleString()} fields</span><button type="button" className="text-button" disabled={currentPage + 1 >= pages} onClick={() => setPage(currentPage + 1)}>Next</button></div>
  </div>
}
