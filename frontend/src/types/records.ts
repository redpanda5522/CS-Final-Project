import type { AnalysisResult } from '../api/analysis'

export type AnalysisRecord = AnalysisResult & {
  inputMode: 'file' | 'manual'
  sourceName: string
  createdAt: string
  isDemo: boolean
}
