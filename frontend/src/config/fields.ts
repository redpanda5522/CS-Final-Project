import datasetFields from './dataset-fields.json'

// Header-derived candidates, not a verified model feature selection.
export const MANUAL_FIELDS = datasetFields
export const FIELD_GROUPS = [...new Set(MANUAL_FIELDS.map(field => field.group))]
export const EXCLUDED_FIELDS = ['id', 'recur', 'redo'] as const
export const SCHEMA_VERSION = 'data-csv-header-v1'
export type BinaryValue = 0 | 1 | null
export type FeatureValues = Record<string, BinaryValue>
export const emptyFeatures = (): FeatureValues => Object.fromEntries(MANUAL_FIELDS.map(field => [field.id, null]))
