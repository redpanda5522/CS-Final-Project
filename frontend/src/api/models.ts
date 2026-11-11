import { isDemoMode } from './analysis'
import { FALLBACK_CATALOG, type ModelCatalog, type ModelOption } from '../config/models'

const FORMATS = ['raw', 'combined']

function isModelOption(value: unknown): value is ModelOption {
  const option = value as Partial<ModelOption> | null
  return !!option && typeof option.id === 'string' && !!option.id.trim() &&
    typeof option.label === 'string' && !!option.label.trim() && typeof option.available === 'boolean' &&
    Array.isArray(option.inputFormats) && option.inputFormats.every(format => FORMATS.includes(format))
}

export async function fetchModelCatalog(): Promise<ModelCatalog> {
  if (isDemoMode) return FALLBACK_CATALOG
  // Fall back to the built-in list quickly if the backend is unreachable.
  const response = await fetch('/api/models', { signal: AbortSignal.timeout(5000) })
  if (!response.ok) throw new Error(`The server returned ${response.status}.`)
  const data = await response.json() as Partial<ModelCatalog>
  if (!Array.isArray(data.models) || !data.models.length || !data.models.every(isModelOption) ||
      typeof data.defaultModel !== 'string' || !data.models.some(model => model.id === data.defaultModel)) {
    throw new Error('The server returned an invalid model list.')
  }
  return { defaultModel: data.defaultModel, models: data.models }
}
