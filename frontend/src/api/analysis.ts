import type { ManualAnalysisRequest } from '../types/procedure'
import type { ModelName } from '../config/models'

export type ManualInput = ManualAnalysisRequest

export type AnalysisResult = {
  analysisId: string
  predictedOutcome: 'success' | 'failure'
  probability: number // P(success), 0..1; not a calibrated clinical confidence score.
  outcomeDefinition: string
  modelVersion?: string
}

export type ModelTrainingResult = {
  modelName: string
  modelVersion: string
  targetColumn: string
  classificationType: 'binary' | 'multiclass'
  classLabels: string[]
  compatibleWithOutcomeAnalysis: boolean
  rowsTrained: number
  featureCount: number
  validationRows: number
  accuracy: number
}

async function readResponse(response: Response): Promise<unknown> {
  if (!response.ok) {
    let message = `The server returned ${response.status}. Please try again.`
    try {
      const body = await response.json() as { detail?: unknown }
      if (typeof body.detail === 'string' && body.detail.trim()) message = body.detail
      else if (Array.isArray(body.detail)) {
        const first = body.detail.find(item => item && typeof item.msg === 'string') as { msg: string } | undefined
        if (first) message = first.msg
      }
    } catch { /* Use the HTTP status message. */ }
    throw new Error(message)
  }
  return response.json()
}

async function readResult(response: Response): Promise<AnalysisResult> {
  const result = await readResponse(response)
  if (!result || typeof result !== 'object') throw new Error('The server returned an invalid result.')
  const data = result as Partial<AnalysisResult>
  if (typeof data.analysisId !== 'string' || !data.analysisId.trim() ||
      (data.predictedOutcome !== 'success' && data.predictedOutcome !== 'failure') ||
      typeof data.probability !== 'number' || !Number.isFinite(data.probability) ||
      data.probability < 0 || data.probability > 1 ||
      typeof data.outcomeDefinition !== 'string' || !data.outcomeDefinition.trim() ||
      (data.modelVersion !== undefined && typeof data.modelVersion !== 'string')) {
    throw new Error('The server response does not match the agreed analysis format.')
  }
  return data as AnalysisResult
}

/**
 * Reads the training result from the API response.
 * @param response: The API response object.
 * @returns A promise resolving to the training result.
 */
async function readTrainingResult(response: Response): Promise<ModelTrainingResult> {
  const result = await readResponse(response)
  if (!result || typeof result !== 'object') throw new Error('The server returned an invalid training result.')
  const data = result as Partial<ModelTrainingResult>
  if (typeof data.modelName !== 'string' ||
      typeof data.modelVersion !== 'string' || !data.modelVersion.trim() ||
      typeof data.targetColumn !== 'string' || !data.targetColumn.trim() ||
      (data.classificationType !== 'binary' && data.classificationType !== 'multiclass') ||
      !Array.isArray(data.classLabels) || data.classLabels.length < 2 ||
      !data.classLabels.every(label => typeof label === 'string') ||
      typeof data.compatibleWithOutcomeAnalysis !== 'boolean' ||
      typeof data.rowsTrained !== 'number' || !Number.isInteger(data.rowsTrained) || data.rowsTrained < 1 ||
      typeof data.featureCount !== 'number' || !Number.isInteger(data.featureCount) || data.featureCount < 1 ||
      typeof data.validationRows !== 'number' || !Number.isInteger(data.validationRows) || data.validationRows < 1 ||
      typeof data.accuracy !== 'number' || !Number.isFinite(data.accuracy) ||
      data.accuracy < 0 || data.accuracy > 1) {
    throw new Error('The server response does not match the agreed training format.')
  }
  return data as ModelTrainingResult
}

const mockMode = import.meta.env.VITE_USE_MOCK_API !== 'false'
export const isDemoMode = mockMode

async function demoResult(modelName: ModelName): Promise<AnalysisResult> {
  await new Promise(resolve => setTimeout(resolve, 800))
  return {
    analysisId: 'demo-analysis', predictedOutcome: 'success', probability: 0.72,
    outcomeDefinition: 'Outcome definition pending confirmation from the dataset team.',
    modelVersion: `Demo only (${modelName})`,
  }
}

// rowIndex is the 0-based CSV row chosen in the preview; the backend requires it for multi-row files.
export async function analyzeFile(file: File, modelName: ModelName, rowIndex?: number): Promise<AnalysisResult> {
  if (mockMode) return demoResult(modelName)
  const form = new FormData()
  form.append('file', file, file.name)
  form.append('model_name', modelName)
  if (rowIndex !== undefined) form.append('row_index', String(rowIndex))
  // Do not set Content-Type: the browser adds the multipart boundary.
  return readResult(await fetch('/api/analyses/file', { method: 'POST', body: form }))
}

/**
 * Calls the API to train a model on the provided file and target column.
 * @param file: The file to train the model on.
 * @param targetColumn: The column to use as the target variable.
 * @param modelName: The name of the model to train.
 * @returns A promise resolving to the training result. 
 */
export async function trainModel(file: File, targetColumn: string, modelName: ModelName): Promise<ModelTrainingResult> {
  const form = new FormData()
  form.append('file', file, file.name)
  form.append('target_column', targetColumn)
  form.append('model_name', modelName)
  // Do not set Content-Type: the browser adds the multipart boundary.
  return readTrainingResult(await fetch('/api/analyses/train', { method: 'POST', body: form }))
}

export async function analyzeManual(input: ManualInput, modelName: ModelName): Promise<AnalysisResult> {
  if (mockMode) return demoResult(modelName)
  return readResult(await fetch('/api/analyses/manual', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...input, model_name: modelName }),
  }))
}
