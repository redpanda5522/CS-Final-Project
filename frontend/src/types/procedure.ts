import { GROUPING_VERSION, regionById, type RegionId } from '../config/regions'
export const MAX_CATHETERS = 4
export type CatheterPoint = { id: string; regionId: RegionId | ''; temperature: string; pressure: string }
export type ProcedureDraft = {
  points: CatheterPoint[]
  temperatureUnit: 'unspecified' | 'C' | 'F'
  pressureUnit: 'unspecified' | 'g' | 'mmHg' | 'kPa'
}
export type ManualAnalysisRequest = {
  schemaVersion: 'catheter-regions-v2'
  groupingVersion: typeof GROUPING_VERSION
  units: { temperature: ProcedureDraft['temperatureUnit']; pressure: ProcedureDraft['pressureUnit'] }
  catheters: Array<{ id: string; regionId: RegionId; temperature: number | null; pressure: number | null }>
}
export const newPoint = (): CatheterPoint => ({ id: crypto.randomUUID(), regionId: '', temperature: '', pressure: '' })
export const emptyProcedure = (): ProcedureDraft => ({ points: [newPoint()], temperatureUnit: 'unspecified', pressureUnit: 'unspecified' })
export function validateProcedure(draft: ProcedureDraft): string {
  if (!draft.points.length) return 'Add at least one catheter.'
  if (draft.points.length > MAX_CATHETERS) return 'A maximum of four catheters is allowed.'
  for (const [index, point] of draft.points.entries()) {
    if (!regionById(point.regionId)) return `Choose a region for catheter ${index + 1}.`
    if ([point.temperature, point.pressure].some(value => value.trim() !== '' && !Number.isFinite(Number(value)))) return `Catheter ${index + 1}: measurements must be numbers.`
    if (point.pressure.trim() !== '' && Number(point.pressure) < 0) return `Catheter ${index + 1}: pressure cannot be negative.`
  }
  return ''
}
export function procedurePayload(draft: ProcedureDraft): ManualAnalysisRequest {
  const issue = validateProcedure(draft)
  if (issue) throw new Error(issue)
  const optionalNumber = (value: string) => value.trim() === '' ? null : Number(value)
  return {
    schemaVersion: 'catheter-regions-v2', groupingVersion: GROUPING_VERSION,
    units: { temperature: draft.temperatureUnit, pressure: draft.pressureUnit },
    catheters: draft.points.map(point => ({ id: point.id, regionId: point.regionId as RegionId, temperature: optionalNumber(point.temperature), pressure: optionalNumber(point.pressure) })),
  }
}
