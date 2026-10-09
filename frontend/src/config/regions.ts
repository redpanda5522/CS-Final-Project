import columnGroups from './column-groups.json'

// Display anchors are illustration pixels, never submitted as catheter coordinates.
export const REGIONS = [
  { id: 'la', label: 'Left atrium', short: 'LA', color: '#198779', anchor: [623, 350], path: 'M607 315 Q637 310 650 338 L683 384 Q654 389 604 386 L593 361 Z' },
  { id: 'ra', label: 'Right atrium', short: 'RA', color: '#367da8', anchor: [405, 393], path: 'M366 330 Q399 315 415 334 Q465 345 470 382 L438 452 Q405 462 357 430 Q338 374 366 330 Z' },
  { id: 'lspv', label: 'Left superior pulmonary vein', short: 'LSPV', color: '#9958bc', anchor: [658, 302], path: 'M641 304 Q658 291 677 290 L684 301 L651 321 Z' },
  { id: 'lipv', label: 'Left inferior pulmonary vein', short: 'LIPV', color: '#ba668f', anchor: [680, 326], path: 'M657 322 L694 314 Q705 320 695 332 L665 342 Z' },
  { id: 'rspv', label: 'Right superior pulmonary vein', short: 'RSPV', color: '#cb8b35', anchor: [341, 302], path: 'M320 286 Q333 280 340 297 L356 321 L340 330 Z' },
  { id: 'ripv', label: 'Right inferior pulmonary vein', short: 'RIPV', color: '#bd6552', anchor: [327, 335], path: 'M314 327 L349 318 L359 333 L321 350 Q305 350 308 337 Z' },
  { id: 'svc', label: 'Superior vena cava', short: 'SVC', color: '#6071b9', anchor: [392, 254], path: 'M362 205 Q395 218 420 201 L424 244 L411 325 L365 327 Z' },
  { id: 'ivc', label: 'Inferior vena cava', short: 'IVC', color: '#56866a', anchor: [411, 641], path: 'M391 603 L428 613 L432 656 Q409 672 393 660 Z' },
] as const
export type RegionId = typeof REGIONS[number]['id']
export const regionById = (id: string) => REGIONS.find(region => region.id === id)
export const COLUMN_GROUPS = columnGroups
export const GROUPING_VERSION = 'left-named-column-v1'
export const sourceGroupsForRegion = (id: string) => COLUMN_GROUPS.filter(group => group.regionId === id).map(group => group.key)
