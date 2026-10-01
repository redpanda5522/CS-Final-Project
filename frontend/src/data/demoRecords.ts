import type { AnalysisRecord } from '../types/records'

export const DEMO_RECORDS: AnalysisRecord[] = [
  { analysisId: 'demo-001', inputMode: 'file', sourceName: 'sample-procedure-a.csv', createdAt: '2026-10-01T13:00:00Z', isDemo: true, predictedOutcome: 'success', probability: 0.72, outcomeDefinition: 'Example only. The dataset outcome and follow-up interval have not been confirmed.', modelVersion: 'Demo fixture' },
  { analysisId: 'demo-002', inputMode: 'manual', sourceName: 'Manual entry', createdAt: '2026-10-01T12:30:00Z', isDemo: true, predictedOutcome: 'failure', probability: 0.34, outcomeDefinition: 'Example only. The dataset outcome and follow-up interval have not been confirmed.', modelVersion: 'Demo fixture' },
  { analysisId: 'demo-003', inputMode: 'file', sourceName: 'sample-procedure-b.csv', createdAt: '2026-09-30T15:20:00Z', isDemo: true, predictedOutcome: 'success', probability: 0.81, outcomeDefinition: 'Example only. The dataset outcome and follow-up interval have not been confirmed.', modelVersion: 'Demo fixture' },
]
