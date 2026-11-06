import { useEffect, useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { CircleHelp, ClipboardList, HeartPulse, LayoutDashboard, Plus, UserRound } from 'lucide-react'
import { isDemoMode, type AnalysisResult } from './api/analysis'
import type { Account } from './account/demoAccounts'
import { DEMO_RECORDS } from './data/demoRecords'
import type { AnalysisRecord } from './types/records'
import Dashboard from './pages/Dashboard'
import Analyses from './pages/Analyses'
import AnalysisDetail from './pages/AnalysisDetail'
import AccountPage from './pages/Account'
import Help from './pages/Help'
import NewAnalysis from './pages/NewAnalysis'

function Workspace() {
  const [records, setRecords] = useState<AnalysisRecord[]>(isDemoMode ? DEMO_RECORDS : [])
  const [account, setAccount] = useState<Account | null>(null)
  const { pathname } = useLocation()
  const title = pathname === '/' ? 'Dashboard'
    : pathname === '/analyses/new' ? 'New analysis'
    : pathname === '/analyses' ? 'Analyses'
    : pathname === '/help' ? 'Help & workflow'
    : pathname === '/account/create' ? 'Create account'
    : pathname === '/account/sign-in' ? 'Sign in'
    : pathname === '/account' ? 'My account'
    : 'Analysis details'

  useEffect(() => { document.title = `${title} | Ablation Outcome`; window.scrollTo(0, 0) }, [title, pathname])

  function recordCompleted(result: AnalysisResult, inputMode: 'file' | 'manual', sourceName: string) {
    const record: AnalysisRecord = { ...result, analysisId: isDemoMode ? `demo-${crypto.randomUUID()}` : result.analysisId, createdAt: new Date().toISOString(), inputMode, sourceName, isDemo: isDemoMode }
    setRecords(current => [record, ...current.filter(item => item.analysisId !== record.analysisId)])
  }

  const navigation = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/analyses/new', label: 'New analysis', icon: Plus },
    { path: '/analyses', label: 'Analyses', icon: ClipboardList },
    { path: '/help', label: 'Help & workflow', icon: CircleHelp },
    { path: account ? '/account' : '/account/create', label: account ? 'My account' : 'Create account', icon: UserRound },
  ]

  return <div className="app-shell">
    <aside className="sidebar">
      <Link to="/" className="brand"><span className="brand-mark"><HeartPulse size={23}/></span><span>Ablation<span className="brand-light">Outcome</span><small>CLINICAL RESEARCH TOOL</small></span></Link>
      <div className="side-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{navigation.map(item => <NavLink key={item.path} to={item.path} end={item.path !== '/analyses'} className={({isActive}) => `nav-item ${isActive && !(item.path === '/analyses' && pathname === '/analyses/new') ? 'side-active' : ''}`}><item.icon size={18}/>{item.label}</NavLink>)}</nav>
      <div className="sidebar-bottom"><Link to={account ? '/account' : '/account/create'} className="user-card"><span className="avatar">{account ? account.name.charAt(0).toUpperCase() : 'R'}</span><span>{account?.name || 'Research workspace'}<small>{account ? 'Tab session account' : 'Create a preview account'}</small></span></Link></div>
    </aside>
    <div className="main-column">
      <header className="topbar"><span className="breadcrumb">Workspace <span>/</span><strong>{title}</strong></span><span className="top-status"><span className="status-dot"/>{isDemoMode ? 'Demo mode' : 'Live API mode'}</span></header>
      <main id="main-content">
        {/* Retain the active draft when navigating to other workspace pages. */}
        <div hidden={pathname !== '/analyses/new'}><NewAnalysis onComplete={recordCompleted}/></div>
        <Routes>
          <Route path="/" element={<Dashboard records={records} account={account} onSignOut={() => setAccount(null)}/>}/>
          <Route path="/analyses" element={<Analyses records={records}/>}/>
          <Route path="/analyses/new" element={null}/>
          <Route path="/analyses/:analysisId" element={<AnalysisDetail records={records}/>}/>
          <Route path="/account/create" element={<AccountPage key="create" mode="create" account={account} onAuthenticated={setAccount} onSignOut={() => setAccount(null)}/>}/>
          <Route path="/account/sign-in" element={<AccountPage key="sign-in" mode="sign-in" account={account} onAuthenticated={setAccount} onSignOut={() => setAccount(null)}/>}/>
          <Route path="/account" element={<AccountPage key="profile" mode="profile" account={account} onAuthenticated={setAccount} onSignOut={() => setAccount(null)}/>}/>
          <Route path="/help" element={<Help/>}/>
          <Route path="*" element={<div className="empty-state work-card"><h1>Page not found</h1><Link className="text-button" to="/">Return to dashboard →</Link></div>}/>
        </Routes>
      </main>
      <footer>Ablation outcome analysis</footer>
    </div>
  </div>
}

export default function App() { return <BrowserRouter><Workspace/></BrowserRouter> }
