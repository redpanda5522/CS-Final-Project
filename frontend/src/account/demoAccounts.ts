export type Account = {
  id: string
  name: string
  email: string
  organization: string
}

type StoredAccount = { profile: Account; salt: string; passwordHash: string }
const accounts = new Map<string, StoredAccount>()

const normalizeEmail = (email: string) => email.trim().toLowerCase()

async function hashPassword(password: string, salt: string): Promise<string> {
  const bytes = new TextEncoder().encode(`${salt}:${password}`)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
}

export async function createAccount(input: { name: string; email: string; organization: string; password: string }): Promise<Account> {
  const email = normalizeEmail(input.email)
  const name = input.name.trim()
  if (!name || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || input.password.length < 8) throw new Error('Enter your name, a valid email, and a password of at least 8 characters.')
  if (accounts.has(email)) throw new Error('An account with this email already exists in this tab. Sign in instead.')
  const profile: Account = { id: crypto.randomUUID(), name, email, organization: input.organization.trim() }
  const salt = crypto.randomUUID()
  accounts.set(email, { profile, salt, passwordHash: await hashPassword(input.password, salt) })
  return profile
}

export async function signIn(emailInput: string, password: string): Promise<Account> {
  const account = accounts.get(normalizeEmail(emailInput))
  if (!account || account.passwordHash !== await hashPassword(password, account.salt)) {
    throw new Error('Email or password not recognized in this tab session.')
  }
  return account.profile
}
