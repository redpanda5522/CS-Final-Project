export type HeartDiseaseField = {
  name: string
  label: string
  type: 'number' | 'select'
  unit?: string
  min?: number
  max?: number
  options?: { value: string | number; label: string }[]
}

export type HeartDiseaseModel = {
  available: boolean
  reason: string | null
  modelVersion: string | null
  fields: HeartDiseaseField[]
}

export type HeartDiseaseResult = {
  predictedClass: 'positive' | 'negative'
  positiveClassProbability: number
  modelVersion: string
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: string | { msg?: string }[] }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return body.detail.find(item => item.msg)?.msg ?? `Server returned ${response.status}.`
  } catch { /* Use the status below. */ }
  return `Server returned ${response.status}.`
}

export async function fetchHeartDiseaseModel(): Promise<HeartDiseaseModel> {
  let response: Response
  try { response = await fetch('/api/heart-disease/model') }
  catch { throw new Error('Could not reach the heart disease model service.') }
  if (response.status === 404) throw new Error('The heart disease model service is not connected yet.')
  if (!response.ok) throw new Error(await errorMessage(response))
  const value: unknown = await response.json()
  if (!value || typeof value !== 'object') throw new Error('Invalid model configuration response.')
  const model = value as Partial<HeartDiseaseModel>
  if (typeof model.available !== 'boolean' || !Array.isArray(model.fields) ||
      (model.available && (!model.fields.length || typeof model.modelVersion !== 'string')) ||
      !model.fields.every(field => field && typeof field.name === 'string' && typeof field.label === 'string' &&
        (field.type === 'number' || field.type === 'select') &&
        (field.type !== 'select' || Array.isArray(field.options)))) {
    throw new Error('Invalid model configuration response.')
  }
  return model as HeartDiseaseModel
}

export async function predictHeartDisease(features: Record<string, string | number>): Promise<HeartDiseaseResult> {
  const response = await fetch('/api/heart-disease/predict', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ features }),
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  const value: unknown = await response.json()
  if (!value || typeof value !== 'object') throw new Error('Invalid prediction response.')
  const result = value as Partial<HeartDiseaseResult>
  if ((result.predictedClass !== 'positive' && result.predictedClass !== 'negative') ||
      typeof result.positiveClassProbability !== 'number' || !Number.isFinite(result.positiveClassProbability) ||
      result.positiveClassProbability < 0 || result.positiveClassProbability > 1 ||
      typeof result.modelVersion !== 'string' || !result.modelVersion.trim()) {
    throw new Error('Invalid prediction response.')
  }
  return result as HeartDiseaseResult
}
