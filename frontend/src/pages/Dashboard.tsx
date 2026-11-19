import { Link } from 'react-router-dom'
import { ArrowRight, Activity, LogIn, LogOut, UserRound } from 'lucide-react'
import type { Account } from '../account/demoAccounts'
import AnalysisTable from '../components/AnalysisTable'
import type { AnalysisRecord } from '../types/records'

type Props = { records: AnalysisRecord[]; account: Account | null; onSignOut: () => void }

export default function Dashboard({ records, account, onSignOut }: Props) {
  return <>
    <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line"/> WORKSPACE OVERVIEW</div><h1>Dashboard</h1><p>A workspace for reviewing postprocedure analysis submissions.</p></div>
    <section className="work-card home-account-card" aria-labelledby="home-account-title"><div className="home-account-icon"><UserRound size={21}/></div><div className="home-account-copy"><h2 id="home-account-title">{account ? `Welcome, ${account.name}` : 'Set up your account'}</h2><p>{account ? 'Your preview profile is active in this tab.' : 'Create a temporary profile to try the account flow. Accounts will be saved when backend support is added.'}</p></div><div className="home-account-actions">{account ? <><Link className="primary-button" to="/account"><UserRound size={16}/> My account</Link><button className="account-outline-button" type="button" onClick={onSignOut}><LogOut size={16}/> Sign out</button></> : <><Link className="primary-button" to="/account/create"><UserRound size={16}/> Create account</Link><Link className="account-outline-button" to="/account/sign-in"><LogIn size={16}/> Sign in</Link></>}</div></section>
    <div className="welcome-card"><div><span className="eyebrow">START WITH PROCEDURE DATA</span><h2>From submission to a reviewable result.</h2><p>Upload a procedure file or enter dataset flags, check your inputs, and request an outcome estimate.</p><Link className="welcome-link" to="/analyses/new">Start a new analysis <ArrowRight size={17}/></Link></div><div className="welcome-art" aria-hidden="true"><Activity size={75} strokeWidth={1}/></div></div>
    <section className="work-card"><div className="panel-heading"><div><h2>Recent analyses</h2><p>Completed records in this workspace session.</p></div><Link className="text-button" to="/analyses">View all <ArrowRight size={15}/></Link></div><AnalysisTable records={records.slice(0, 5)}/></section>
  </>
}
