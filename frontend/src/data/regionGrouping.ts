import Papa from 'papaparse'
import { COLUMN_GROUPS, REGIONS } from '../config/regions'
export type BinaryFlag = 0 | 1 | null
export type NamedGroup = { key: string; columns: string[]; regionId: string | null }
const known = new Map(COLUMN_GROUPS.map(group => [group.key, group.regionId]))
export function groupHeaders(headers: string[]): NamedGroup[] {
  const groups: NamedGroup[] = []
  if (new Set(headers).size !== headers.length) throw new Error('Duplicate column names cannot be grouped reliably.')
  for (const key of headers) {
    if (/^v\d+$/i.test(key)) {
      if (!groups.length) throw new Error('A V column appears before any named column.')
      groups[groups.length - 1].columns.push(key)
    } else groups.push({ key, columns: [key], regionId: known.get(key) ?? null })
  }
  return groups.filter(group => !['id', 'recur', 'redo'].includes(group.key.toLowerCase()))
}
// Presence rule: any 1 => 1; all known 0 => 0; otherwise unspecified.
// This is a lossy display aggregation, not a replacement ML feature array.
export function collapseValues(values: BinaryFlag[]): BinaryFlag {
  return values.some(value => value === 1) ? 1 : values.length && values.every(value => value === 0) ? 0 : null
}
export function collapseRow(headers: string[], row: string[], groups: NamedGroup[]): Record<string, BinaryFlag> {
  const indexes = new Map(headers.map((key, index) => [key, index]))
  return Object.fromEntries(groups.map(group => [group.key, collapseValues(group.columns.map(key => {
    const raw = (row[indexes.get(key)!] ?? '').trim()
    if (raw === '') return null
    if (raw !== '0' && raw !== '1') throw new Error('Region preview requires binary 0/1 flags. The original file can still be submitted.')
    return raw === '1' ? 1 : 0
  }))]))
}
export function regionalValues(groups: NamedGroup[], collapsed: Record<string, BinaryFlag>) {
  return Object.fromEntries(REGIONS.map(region => [region.id, collapseValues(groups.filter(group => group.regionId === region.id).map(group => collapsed[group.key]))]))
}
export function parseRegionCsv(text: string) {
  const parsed = Papa.parse<string[]>(text, { skipEmptyLines: 'greedy' })
  if (parsed.errors.length) throw new Error('CSV preview could not be read. Check quoting and delimiters.')
  const [rawHeaders, ...rows] = parsed.data
  if (!rawHeaders?.length || !rows.length) throw new Error('CSV preview needs a header and at least one data row.')
  const headers = rawHeaders.map(value => value.trim())
  if (rows.some(row => row.length !== headers.length)) throw new Error('CSV rows do not match the header length.')
  const groups = groupHeaders(headers)
  if (!groups.length) throw new Error('No input columns are available for region preview.')
  return { groups, rows: rows.map(row => collapseRow(headers, row, groups)), variantCount: groups.reduce((count, group) => count + group.columns.length - 1, 0) }
}
