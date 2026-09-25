import type { LocationId } from '../config/fields'

export type ManualInput = {
  locations: Record<LocationId, boolean>
  // Add required dataset features here after the ML team supplies their schema.
}

export type AnalysisResult = {
  analysisId: string
  predictedOutcome: 'success' | 'failure'
  probability: number // P(success), 0..1; not a calibrated clinical confidence score.
  outcomeDefinition: string
  modelVersion?: string
}

async function readResult(response: Response): Promise<AnalysisResult> {
  if (!response.ok) {
    let message = `The server returned ${response.status}. Please try again.`
    try {
      const body = await response.json() as { detail?: unknown }
      if (typeof body.detail === 'string') message = body.detail
    } catch { /* Use the HTTP status message. */ }
    throw new Error(message)
  }
  const result: unknown = await response.json()
  if (!result || typeof result !== 'object') throw new Error('The server returned an invalid result.')
  const data = result as Partial<AnalysisResult>
  if (typeof data.analysisId !== 'string' ||
      (data.predictedOutcome !== 'success' && data.predictedOutcome !== 'failure') ||
      typeof data.probability !== 'number' || !Number.isFinite(data.probability) ||
      data.probability < 0 || data.probability > 1 ||
      typeof data.outcomeDefinition !== 'string') {
    throw new Error('The server response does not match the agreed analysis format.')
  }
  return data as AnalysisResult
}

const mockMode = import.meta.env.VITE_USE_MOCK_API !== 'false'
export const isDemoMode = mockMode

async function demoResult(): Promise<AnalysisResult> {
  await new Promise(resolve => setTimeout(resolve, 800))
  return {
    analysisId: 'demo-analysis', predictedOutcome: 'success', probability: 0.72,
    outcomeDefinition: 'Outcome definition pending confirmation from the dataset team.',
    modelVersion: 'Demo only',
  }
}

export async function analyzeFile(file: File): Promise<AnalysisResult> {
  if (mockMode) return demoResult()
  const form = new FormData()
  form.append('file', file, file.name)
  // Do not set Content-Type: the browser adds the multipart boundary.
  return readResult(await fetch('/api/analyses/file', { method: 'POST', body: form }))
}

export async function analyzeManual(input: ManualInput): Promise<AnalysisResult> {
  if (mockMode) return demoResult()
  return readResult(await fetch('/api/analyses/manual', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }))
}
