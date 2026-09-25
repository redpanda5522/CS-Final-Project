// Replace these example IDs and labels with the dataset's actual binary location columns.
// Keep IDs identical to the keys expected by FastAPI.
export const LOCATION_FIELDS = [
  { id: 'location_1', label: 'Location 1' },
  { id: 'location_2', label: 'Location 2' },
  { id: 'location_3', label: 'Location 3' },
  { id: 'location_4', label: 'Location 4' },
  { id: 'location_5', label: 'Location 5' },
  { id: 'location_6', label: 'Location 6' },
] as const

export type LocationId = typeof LOCATION_FIELDS[number]['id']
