import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { ArrowRight, KeyRound } from 'lucide-react'
import { accountsAreSaved, changePassword, confirmPasswordReset, requestPasswordReset, type Account } from '../account/accounts'

const message = (cause: unknown, fallback: string) => cause instanceof Error ? cause.message : fallback

function Heading({ eyebrow, title, intro }: { eyebrow: string; title: string; intro: string }) {
  return <div className="page-heading"><div className="eyebrow"><span className="eyebrow-line"/> {eyebrow}</div><h1>{title}</h1><p>{intro}</p></div>
}

function DemoNotice() {
  return <section className="work-card card-body account-card"><p className="account-note">Password changes and resets need live API mode. Demo mode accounts last only while this tab stays open.</p><Link className="text-button" to="/account/sign-in">Back to sign in →</Link></section>
}

/** "Forgot password?": asks the backend to email a reset link. */
export function ForgotPassword({ account }: { account: Account | null }) {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (account) return <Navigate to="/account" replace/>

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true); setError('')
    try { setSent(await requestPasswordReset(email)) }
    catch (cause) { setError(message(cause, 'The reset link could not be requested.')) }
    finally { setBusy(false) }
  }

  return <>
    <Heading eyebrow="ACCOUNT" title="Reset password" intro="We will email you a link to choose a new password."/>
    {!accountsAreSaved ? <DemoNotice/> : <section className="work-card card-body account-card">
      <div className="account-form-heading"><span className="icon-box"><KeyRound size={20}/></span><div><h2>Forgot your password?</h2><p>Enter the email you signed up with.</p></div></div>
      {sent ? <p className="account-note" role="status">{sent} The link works once and expires in 30 minutes.</p>
        : <form className="account-form" onSubmit={submit}>
          <label htmlFor="reset-email">Email address</label><input id="reset-email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required maxLength={254}/>
          {error && <p className="error-message" role="alert">{error}</p>}
          <button className="primary-button account-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : 'Send reset link'} {!busy && <ArrowRight size={16}/>}</button>
        </form>}
      <p className="account-switch">Remembered it? <Link to="/account/sign-in">Sign in</Link></p>
    </section>}
  </>
}

/** The page a reset link opens: /account/reset?token=… */
export function ResetPassword({ account, onSignedOut }: { account: Account | null; onSignedOut: () => void }) {
  // Read the token once, then remove it from the address bar and browser history.
  const [token] = useState(() => new URLSearchParams(window.location.search).get('token') ?? '')
  useEffect(() => { if (window.location.search) window.history.replaceState(null, '', window.location.pathname) }, [])
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password !== confirmation) { setError('Passwords do not match.'); return }
    setBusy(true); setError('')
    try {
      await confirmPasswordReset(token, password)
      // The backend signed out every session, including this browser's.
      if (account) onSignedOut()
      setDone(true)
    } catch (cause) { setError(message(cause, 'The password could not be reset.')) }
    finally { setBusy(false) }
  }

  return <>
    <Heading eyebrow="ACCOUNT" title="Choose a new password" intro="Set a new password for your account."/>
    {!accountsAreSaved ? <DemoNotice/> : <section className="work-card card-body account-card">
      <div className="account-form-heading"><span className="icon-box"><KeyRound size={20}/></span><div><h2>New password</h2><p>Every browser signed in to this account will be signed out.</p></div></div>
      {done ? <><p className="account-note" role="status">Your password was changed. Sign in with your new password.</p><Link className="primary-button" to="/account/sign-in">Sign in <ArrowRight size={16}/></Link></>
        : !token ? <><p className="error-message" role="alert">This reset link is incomplete. Request a new one.</p><Link className="text-button" to="/account/forgot">Request a reset link →</Link></>
        : <form className="account-form" onSubmit={submit}>
          <label htmlFor="reset-password">New password</label><input id="reset-password" type="password" autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} required minLength={8} maxLength={256}/>
          <p className="account-field-help">Use at least 8 characters.</p>
          <label htmlFor="reset-confirm">Confirm new password</label><input id="reset-confirm" type="password" autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} required/>
          {error && <><p className="error-message" role="alert">{error}</p>{error.includes('Request a new one') && <p className="account-field-help"><Link to="/account/forgot">Request a new reset link</Link></p>}</>}
          <button className="primary-button account-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : 'Set new password'} {!busy && <ArrowRight size={16}/>}</button>
        </form>}
    </section>}
  </>
}

/** Shown on the My account page. */
export function ChangePassword() {
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (!accountsAreSaved) return null

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus('')
    if (password !== confirmation) { setError('New passwords do not match.'); return }
    setBusy(true); setError('')
    try {
      await changePassword(current, password)
      setCurrent(''); setPassword(''); setConfirmation('')
      setStatus('Password changed. Other browsers signed in to this account were signed out.')
    } catch (cause) { setError(message(cause, 'The password could not be changed.')) }
    finally { setBusy(false) }
  }

  return <section className="work-card card-body account-card">
    <div className="account-form-heading"><span className="icon-box"><KeyRound size={20}/></span><div><h2>Change password</h2><p>Other browsers signed in to this account will be signed out.</p></div></div>
    <form className="account-form" onSubmit={submit}>
      <label htmlFor="current-password">Current password</label><input id="current-password" type="password" autoComplete="current-password" value={current} onChange={event => setCurrent(event.target.value)} required/>
      <label htmlFor="new-password">New password</label><input id="new-password" type="password" autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} required minLength={8} maxLength={256}/>
      <p className="account-field-help">Use at least 8 characters.</p>
      <label htmlFor="confirm-new-password">Confirm new password</label><input id="confirm-new-password" type="password" autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} required/>
      {error && <p className="error-message" role="alert">{error}</p>}
      {status && <p className="account-note" role="status">{status}</p>}
      <button className="primary-button account-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : 'Change password'}</button>
    </form>
  </section>
}
