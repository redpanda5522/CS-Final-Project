import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ArrowRight, LogOut, UserRound } from 'lucide-react'
import { createAccount, signIn, type Account } from '../account/demoAccounts'

type Props = {
  mode: 'create' | 'sign-in' | 'profile'
  account: Account | null
  onAuthenticated: (account: Account) => void
  onSignOut: () => void
}

export default function AccountPage({ mode, account, onAuthenticated, onSignOut }: Props) {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [organization, setOrganization] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (mode === 'profile' && !account) return <Navigate to="/account/sign-in" replace />
  if (mode !== 'profile' && account) return <Navigate to="/account" replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (mode === 'create' && password !== confirmation) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const profile = mode === 'create'
        ? await createAccount({ name, email, organization, password })
        : await signIn(email, password)
      onAuthenticated(profile)
      navigate('/account', { replace: true })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The account action could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  if (mode === 'profile' && account) return <>
    <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line"/> ACCOUNT</div><h1>My account</h1><p>Your profile for this tab session.</p></div>
    <section className="work-card card-body account-card">
      <div className="account-profile-heading"><span className="account-profile-icon"><UserRound size={25}/></span><div><h2>{account.name}</h2><p>Signed in for this tab session</p></div></div>
      <dl className="detail-list"><dt>Email</dt><dd>{account.email}</dd><dt>Organization</dt><dd>{account.organization || 'Not provided'}</dd></dl>
      <p className="account-note">This prototype account is held in memory and disappears when the page refreshes. Analyses are still shared within this browser session.</p>
      <div className="account-actions"><Link className="primary-button" to="/analyses/new">New analysis <ArrowRight size={16}/></Link><button className="account-outline-button" type="button" onClick={() => { onSignOut(); navigate('/') }}><LogOut size={16}/> Sign out</button></div>
    </section>
  </>

  const creating = mode === 'create'
  return <>
    <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line"/> ACCOUNT PREVIEW</div><h1>{creating ? 'Create account' : 'Sign in'}</h1><p>{creating ? 'Set up a temporary research workspace profile.' : 'Return to an account created in this tab.'}</p></div>
    <div className="account-layout"><section className="work-card card-body account-card">
      <div className="account-form-heading"><span className="icon-box"><UserRound size={20}/></span><div><h2>{creating ? 'Your details' : 'Welcome back'}</h2><p>{creating ? 'Add your contact details to begin.' : 'Enter the email and password you used here.'}</p></div></div>
      <form className="account-form" onSubmit={submit}>
        {creating && <><label htmlFor="account-name">Full name</label><input id="account-name" name="name" autoComplete="name" value={name} onChange={event => setName(event.target.value)} required maxLength={100}/></>}
        <label htmlFor="account-email">Email address</label><input id="account-email" name="email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required maxLength={254}/>
        {creating && <><label htmlFor="account-organization">Organization <span>(optional)</span></label><input id="account-organization" name="organization" autoComplete="organization" value={organization} onChange={event => setOrganization(event.target.value)} maxLength={120}/></>}
        <label htmlFor="account-password">Password</label><input id="account-password" name="password" type="password" autoComplete={creating ? 'new-password' : 'current-password'} value={password} onChange={event => setPassword(event.target.value)} required minLength={creating ? 8 : undefined}/>
        {creating && <><p className="account-field-help">Use at least 8 characters.</p><label htmlFor="account-confirm">Confirm password</label><input id="account-confirm" name="confirm-password" type="password" autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} required/></>}
        {error && <p className="error-message" role="alert">{error}</p>}
        <button className="primary-button account-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : creating ? 'Create account' : 'Sign in'} {!busy && <ArrowRight size={16}/>}</button>
      </form>
      <p className="account-switch">{creating ? 'Already created an account here?' : 'New to this workspace?'} <Link to={creating ? '/account/sign-in' : '/account/create'}>{creating ? 'Sign in' : 'Create account'}</Link></p>
    </section><aside className="account-aside"><h2>Frontend preview</h2><p>Accounts exist only while this browser tab stays open. Refreshing clears them. Authentication, account recovery, and access control will be connected when the backend is ready.</p><p>Use sample details while testing this flow.</p></aside></div>
  </>
}
