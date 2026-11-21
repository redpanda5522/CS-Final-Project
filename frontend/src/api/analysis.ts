import type { ManualAnalysisRequest } from '../types/procedure'
import type { ModelName } from '../config/models'
import type { AnalysisRecord } from '../types/records'

export type ManualInput = ManualAnalysisRequest

export type PerformanceMetrics = Partial<Record<
  'accuracy' | 'precision' | 'recall' | 'f1' | 'auroc' | 'auprc' |
  'logLoss' | 'brierScore' | 'scaledBrierScore' | 'calibrationIntercept' |
  'calibrationSlope' | 'observedExpectedRatio', number
>>

export type AnalysisResult = {
  analysisId: string
  predictedOutcome: 'success' | 'failure'
  probability: number // P(success), 0..1; not a calibrated clinical confidence score.
  outcomeDefinition: string
  modelVersion?: string
  performanceMetrics?: PerformanceMetrics
}

export type AblationSiteAnalysisResult = {
  sourceName: string
  numSites: number
  numSessions: number
  cluster: number
  modelVersion: string
  pca: {
    point: { x: number; y: number }
    trainingPoints: { cluster: number; x: number; y: number }[]
    explainedVariance: [number, number]
  }
  featureContributions: { feature: string; contributionPercent: number }[]
}

const metricNames: (keyof PerformanceMetrics)[] = [
  'accuracy', 'precision', 'recall', 'f1', 'auroc', 'auprc', 'logLoss',
  'brierScore', 'scaledBrierScore', 'calibrationIntercept',
  'calibrationSlope', 'observedExpectedRatio',
]

function validMetrics(value: unknown): value is PerformanceMetrics {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  return Object.entries(value).every(([key, metric]) =>
    metricNames.includes(key as keyof PerformanceMetrics) &&
    typeof metric === 'number' && Number.isFinite(metric) &&
    (!['accuracy', 'precision', 'recall', 'f1', 'auroc', 'auprc', 'brierScore'].includes(key) || (metric >= 0 && metric <= 1)) &&
    (key !== 'logLoss' || metric >= 0) &&
    (key !== 'observedExpectedRatio' || metric >= 0),
  )
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
  performanceMetrics?: PerformanceMetrics
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
      (data.modelVersion !== undefined && typeof data.modelVersion !== 'string') ||
      (data.performanceMetrics !== undefined && !validMetrics(data.performanceMetrics))) {
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
      data.accuracy < 0 || data.accuracy > 1 ||
      (data.performanceMetrics !== undefined && !validMetrics(data.performanceMetrics))) {
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

export async function analyzeAblationSites(file: File): Promise<AblationSiteAnalysisResult> {
  const form = new FormData()
  form.append('file', file, file.name)
  const result = await readResponse(await fetch('/api/analyses/ablation-sites', { method: 'POST', body: form }))
  if (!isAblationSiteAnalysisResult(result)) {
    throw new Error('The server response does not match the agreed clustering format.')
  }
  return result
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value)
}

function isPcaPoint(value: unknown): value is { x: number; y: number } {
  return isRecord(value) && isFiniteNumber(value.x) && isFiniteNumber(value.y)
}

function isClusterPoint(value: unknown): value is { cluster: number; x: number; y: number } {
  return isRecord(value) && isInteger(value.cluster) && value.cluster >= 0 && isPcaPoint(value)
}

function isFeatureContribution(value: unknown): value is { feature: string; contributionPercent: number } {
  return isRecord(value) && typeof value.feature === 'string' &&
    isFiniteNumber(value.contributionPercent) && value.contributionPercent >= 0
}

function isAblationSiteAnalysisResult(value: unknown): value is AblationSiteAnalysisResult {
  if (!isRecord(value) || !isRecord(value.pca)) return false
  const pca = value.pca
  return typeof value.sourceName === 'string' && value.sourceName.trim().length > 0 &&
    isInteger(value.numSites) && value.numSites > 0 &&
    isInteger(value.numSessions) && value.numSessions > 0 &&
    isInteger(value.cluster) && value.cluster >= 0 &&
    typeof value.modelVersion === 'string' && value.modelVersion.trim().length > 0 &&
    isPcaPoint(pca.point) &&
    Array.isArray(pca.trainingPoints) && pca.trainingPoints.length > 0 && pca.trainingPoints.every(isClusterPoint) &&
    Array.isArray(pca.explainedVariance) && pca.explainedVariance.length === 2 &&
    pca.explainedVariance.every(isFiniteNumber) &&
    Array.isArray(value.featureContributions) && value.featureContributions.length > 0 &&
    value.featureContributions.every(isFeatureContribution)
}

/**
 * Calls the API to train a model on the provided file and target column.
 * @param file: The file to train the model on.
 * @param targetColumn: The column to use as the target variable.
 * @param modelName: The name of the model to train.
 * @returns A promise resolving to the training result.
 */
export async function trainModel(file: File, targetColumn: string, modelName: ModelName): Promise<ModelTrainingResult> {
  if (mockMode) throw new Error('Live API mode is required to train a model and view measured performance metrics.')
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

/** The signed-in account's saved analyses, newest first (live mode only). */
export async function fetchAnalyses(): Promise<AnalysisRecord[]> {
  const value = await readResponse(await fetch('/api/analyses?limit=200'))
  if (!Array.isArray(value)) throw new Error('The server returned an invalid analysis list.')
  return value.filter((item): item is AnalysisRecord => {
    const record = item as Partial<AnalysisRecord> | null
    return !!record && typeof record.analysisId === 'string' &&
      (record.predictedOutcome === 'success' || record.predictedOutcome === 'failure') &&
      typeof record.probability === 'number' && typeof record.outcomeDefinition === 'string' &&
      (record.inputMode === 'file' || record.inputMode === 'manual') &&
      typeof record.sourceName === 'string' && typeof record.createdAt === 'string' &&
      (record.performanceMetrics === undefined || validMetrics(record.performanceMetrics))
  }).map(record => ({ ...record, isDemo: false }))
}
