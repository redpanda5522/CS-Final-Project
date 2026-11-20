import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { isDemoMode } from '../api/analysis'
import AnalysisTable from '../components/AnalysisTable'
import type { AnalysisRecord } from '../types/records'

export default function Analyses({ records, signedIn }: { records: AnalysisRecord[]; signedIn: boolean }) {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('all')
  const filtered = records.filter(record => (mode === 'all' || record.inputMode === mode) && `${record.analysisId} ${record.sourceName}`.toLowerCase().includes(query.toLowerCase()))
  return <><div className="heading-row"><div className="page-heading"><div className="eyebrow"><span className="eyebrow-line"/> SUBMISSION HISTORY</div><h1>Analyses</h1><p>{isDemoMode ? 'Find completed submissions and open their results.' : signedIn ? 'Your saved analyses. Open one to see its result.' : <>Analyses from this visit only. <Link to="/account/sign-in">Sign in</Link> to save them to your account.</>}</p></div><Link className="primary-button" to="/analyses/new"><Plus size={17}/> New analysis</Link></div><section className="work-card"><div className="list-toolbar"><label>Search submissions<input type="search" placeholder="Search filename or analysis ID" value={query} onChange={e => setQuery(e.target.value)}/></label><label>Input method<select value={mode} onChange={e => setMode(e.target.value)}><option value="all">All methods</option><option value="file">File upload</option><option value="manual">Manual entry</option></select></label></div><div className="list-count">{filtered.length} of {records.length} records</div><AnalysisTable records={filtered}/></section></>
}
