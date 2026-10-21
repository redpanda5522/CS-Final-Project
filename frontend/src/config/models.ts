export const modelOptions = [
  { id: 'logistic', label: 'Logistic regression' },
  { id: 'random_forest', label: 'Random forest' },
  { id: 'xgboost', label: 'XGBoost' },
] as const

export type ModelName = (typeof modelOptions)[number]['id']
export const defaultModel: ModelName = 'logistic'
