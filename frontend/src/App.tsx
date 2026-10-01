import { useEffect, useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { Activity, CircleHelp, ClipboardList, HeartPulse, LayoutDashboard } from 'lucide-react'
import { isDemoMode, type AnalysisResult } from './api/analysis'
import { DEMO_RECORDS } from './data/demoRecords'
import type { AnalysisRecord } from './types/records'
import Dashboard from './pages/Dashboard'
import Analyses from './pages/Analyses'
import AnalysisDetail from './pages/AnalysisDetail'
import Help from './pages/Help'
import NewAnalysis from './pages/NewAnalysis'

function Workspace() {
  const [records, setRecords] = useState<AnalysisRecord[]>(isDemoMode ? DEMO_RECORDS : [])
  const { pathname } = useLocation()
  const title = pathname === '/' ? 'Dashboard' : pathname === '/analyses/new' ? 'New analysis' : pathname === '/analyses' ? 'Analyses' : pathname === '/help' ? 'Help & workflow' : 'Analysis details'
  useEffect(() => { document.title = `${title} | Ablation Outcome`; window.scrollTo(0, 0) }, [title, pathname])

  function recordCompleted(result: AnalysisResult, inputMode: 'file' | 'manual', sourceName: string) {
    const record: AnalysisRecord = { ...result, analysisId: isDemoMode ? `demo-${crypto.randomUUID()}` : result.analysisId, createdAt: new Date().toISOString(), inputMode, sourceName, isDemo: isDemoMode }
    setRecords(current => [record, ...current.filter(item => item.analysisId !== record.analysisId)])
  }

  const navigation = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/analyses/new', label: 'New analysis', icon: Activity },
    { path: '/analyses', label: 'Analyses', icon: ClipboardList },
    { path: '/help', label: 'Help & workflow', icon: CircleHelp },
  ]
  return <div className="app-shell"><aside className="sidebar"><Link to="/" className="brand"><span className="brand-mark"><HeartPulse size={23}/></span><span>Ablation<span className="brand-light">Outcome</span><small>CLINICAL RESEARCH TOOL</small></span></Link><div className="side-label">WORKSPACE</div><nav aria-label="Main navigation">{navigation.map(item => <NavLink key={item.path} to={item.path} end={item.path !== '/analyses'} className={({isActive}) => `nav-item ${isActive && !(item.path === '/analyses' && pathname === '/analyses/new') ? 'side-active' : ''}`}><item.icon size={18}/>{item.label}</NavLink>)}</nav><div className="sidebar-bottom"><div className="user-card"><span className="avatar">R</span><span>Research workspace<small>{isDemoMode ? 'Demo session' : 'Local session'}</small></span></div></div></aside><div className="main-column"><header className="topbar"><span className="breadcrumb">Workspace <span>/</span><strong>{title}</strong></span><span className="top-status"><span className="status-dot"/>{isDemoMode ? 'Demo mode' : 'Live API mode'}</span></header><main id="main-content">
    {/* Retain the active draft when navigating to other workspace pages. */}
    <div hidden={pathname !== '/analyses/new'}><NewAnalysis onComplete={recordCompleted}/></div>
    <Routes><Route path="/" element={<Dashboard records={records}/>}/><Route path="/analyses" element={<Analyses records={records}/>}/><Route path="/analyses/new" element={null}/><Route path="/analyses/:analysisId" element={<AnalysisDetail records={records}/>}/><Route path="/help" element={<Help/>}/><Route path="*" element={<div className="empty-state work-card"><h1>Page not found</h1><Link className="text-button" to="/">Return to dashboard →</Link></div>}/></Routes>
  </main><footer>Ablation outcome analysis</footer></div></div>
}

export default function App() { return <BrowserRouter><Workspace/></BrowserRouter> }
