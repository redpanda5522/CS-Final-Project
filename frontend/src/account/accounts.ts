import { isDemoMode } from '../api/analysis'
import * as demo from './demoAccounts'

export type Account = demo.Account

// Live mode keeps accounts in the backend database; the session is an httpOnly cookie the
// browser sends with every /api request. Demo mode keeps the in-memory tab accounts.
export const accountsAreSaved = !isDemoMode

const INVALID_DETAILS = 'Enter your name, a valid email, and a password of at least 8 characters.'

async function errorMessage(response: Response, invalid = INVALID_DETAILS): Promise<string> {
  try {
    const body = await response.json() as { detail?: string | { msg?: string }[] }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return invalid
  } catch { /* Use the status below. */ }
  return `The server returned ${response.status}. Please try again.`
}

async function readAccount(response: Response): Promise<Account> {
  if (!response.ok) throw new Error(await errorMessage(response))
  const value = await response.json() as Partial<Account>
  if (typeof value.id !== 'string' || typeof value.name !== 'string' || typeof value.email !== 'string' ||
      typeof value.organization !== 'string') throw new Error('The server returned an invalid account.')
  return value as Account
}

const postJson = (url: string, body: unknown) =>
  fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export async function createAccount(input: { name: string; email: string; organization: string; password: string }): Promise<Account> {
  if (isDemoMode) return demo.createAccount(input)
  return readAccount(await postJson('/api/accounts', input))
}

export async function signIn(email: string, password: string): Promise<Account> {
  if (isDemoMode) return demo.signIn(email, password)
  return readAccount(await postJson('/api/accounts/sign-in', { email, password }))
}

/** The signed-in account from an earlier visit, or null. */
export async function fetchCurrentAccount(): Promise<Account | null> {
  if (isDemoMode) return null
  const response = await fetch('/api/accounts/me', { signal: AbortSignal.timeout(5000) })
  if (response.status === 401) return null
  return readAccount(response)
}

export async function signOut(): Promise<void> {
  if (isDemoMode) return
  const response = await fetch('/api/accounts/sign-out', { method: 'POST' })
  if (!response.ok) throw new Error(await errorMessage(response))
}

const DEMO_ONLY = 'Passwords can only be changed in live API mode.'
const NEW_PASSWORD_RULE = 'Use a new password of at least 8 characters.'

/** Changes the password; other browsers signed in to the account are signed out. */
export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  if (isDemoMode) throw new Error(DEMO_ONLY)
  const response = await postJson('/api/accounts/password', { currentPassword, newPassword })
  if (!response.ok) throw new Error(await errorMessage(response, NEW_PASSWORD_RULE))
}

/** Asks for a reset link. Succeeds whether or not the email has an account. */
export async function requestPasswordReset(email: string): Promise<string> {
  if (isDemoMode) throw new Error(DEMO_ONLY)
  const response = await postJson('/api/accounts/password-reset', { email })
  if (!response.ok) throw new Error(await errorMessage(response, 'Enter a valid email address.'))
  const body = await response.json() as { detail?: unknown }
  return typeof body.detail === 'string' ? body.detail : 'If an account exists for that email, a reset link is on its way.'
}

/** Sets a new password from a reset link. Every session is signed out afterwards. */
export async function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  if (isDemoMode) throw new Error(DEMO_ONLY)
  const response = await postJson('/api/accounts/password-reset/confirm', { token, newPassword })
  if (!response.ok) throw new Error(await errorMessage(response, NEW_PASSWORD_RULE))
}
