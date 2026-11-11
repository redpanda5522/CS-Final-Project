// Model IDs come from GET /api/models; the backend validates the one submitted.
export type ModelName = string
export type ModelOption = { id: ModelName; label: string; available: boolean; inputFormats: Array<'raw' | 'combined'> }
export type ModelCatalog = { defaultModel: ModelName; models: ModelOption[] }

// Used in demo mode, and when the backend's list cannot be loaded. Mirrors the backend.
export const FALLBACK_CATALOG: ModelCatalog = {
  defaultModel: 'logistic',
  models: [
    { id: 'logistic', label: 'Logistic regression', available: true, inputFormats: ['raw', 'combined'] },
    { id: 'random_forest', label: 'Random forest', available: true, inputFormats: ['raw', 'combined'] },
    { id: 'xgboost', label: 'XGBoost', available: true, inputFormats: ['raw', 'combined'] },
    { id: 'k_nearest', label: 'Nearest centroid', available: true, inputFormats: ['raw'] },
  ],
}
