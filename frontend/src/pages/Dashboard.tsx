import { Link } from 'react-router-dom'
import { ArrowRight, ClipboardList, FileSpreadsheet, Activity, Plus } from 'lucide-react'
import AnalysisTable from '../components/AnalysisTable'
import type { AnalysisRecord } from '../types/records'

export default function Dashboard({ records }: { records: AnalysisRecord[] }) {
  const metrics = [
    { title: 'Completed analyses', value: records.length, icon: Activity },
    { title: 'File submissions', value: records.filter(r => r.inputMode === 'file').length, icon: FileSpreadsheet },
    { title: 'Manual submissions', value: records.filter(r => r.inputMode === 'manual').length, icon: ClipboardList },
  ]
  return <><div className="heading-row"><div className="page-heading"><div className="eyebrow"><span className="eyebrow-line"/> WORKSPACE OVERVIEW</div><h1>Dashboard</h1><p>A workspace for reviewing postprocedure analysis submissions.</p></div><Link className="primary-button" to="/analyses/new"><Plus size={17}/> New analysis</Link></div>
    <div className="welcome-card"><div><span className="eyebrow">START WITH PROCEDURE DATA</span><h2>From submission to a reviewable result.</h2><p>Upload a procedure file or enter dataset flags, check your inputs, and request an outcome estimate.</p><Link className="welcome-link" to="/analyses/new">Start a new analysis <ArrowRight size={17}/></Link></div><div className="welcome-art" aria-hidden="true"><Activity size={75} strokeWidth={1}/></div></div>
    <div className="metric-grid">{metrics.map(metric => <div className="metric-card" key={metric.title}><span className="icon-box"><metric.icon size={20}/></span><strong>{metric.value}</strong><span>{metric.title}</span></div>)}</div>
    <section className="work-card"><div className="panel-heading"><div><h2>Recent analyses</h2><p>Completed records in this workspace session.</p></div><Link className="text-button" to="/analyses">View all <ArrowRight size={15}/></Link></div><AnalysisTable records={records.slice(0, 5)}/></section>
    
  </>
}
