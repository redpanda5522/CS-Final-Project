import { Link } from 'react-router-dom'
import { ArrowUpRight, FileSpreadsheet, ClipboardList } from 'lucide-react'
import type { AnalysisRecord } from '../types/records'

export function displayDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

export default function AnalysisTable({ records }: { records: AnalysisRecord[] }) {
  if (records.length === 0) return <div className="empty-state"><FileSpreadsheet size={30}/><h3>No analyses to display</h3><p>Create an analysis or change your search filters.</p><Link className="text-button" to="/analyses/new">Start a new analysis →</Link></div>
  return <div className="table-scroll"><table className="analysis-table"><thead><tr><th>Submission</th><th>Created</th><th>Input</th><th>Status</th><th><span className="visually-hidden">Details</span></th></tr></thead><tbody>{records.map(record => <tr key={record.analysisId}><td><div className="submission-cell"><span className="table-icon">{record.inputMode === 'file' ? <FileSpreadsheet size={18}/> : <ClipboardList size={18}/>}</span><div><strong>{record.sourceName}</strong><small>{record.analysisId} {record.isDemo && '· Demo'}</small></div></div></td><td>{displayDate(record.createdAt)}</td><td>{record.inputMode === 'file' ? 'File upload' : 'Manual entry'}</td><td><span className="complete-badge">Completed</span></td><td><Link className="row-link" aria-label={`View ${record.sourceName} ${record.analysisId}`} to={`/analyses/${encodeURIComponent(record.analysisId)}`}><ArrowUpRight size={18}/></Link></td></tr>)}</tbody></table></div>
}
