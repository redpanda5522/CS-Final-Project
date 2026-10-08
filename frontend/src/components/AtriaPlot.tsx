import { useId, useState, type MouseEvent } from 'react'
import { REGIONS, regionById, type RegionId } from '../config/regions'
import type { CatheterPoint } from '../types/procedure'

type Props = { points: CatheterPoint[]; selectedId?: string; onRegionSelect?: (id: RegionId) => void; activeRegions?: string[] }
export default function AtriaPlot({ points, selectedId, onRegionSelect, activeRegions = [] }: Props) {
  const titleId = useId()
  const [hovered, setHovered] = useState<{ id: RegionId; x: number; y: number } | null>(null)
  const occupied = new Set([...activeRegions, ...points.map(point => point.regionId)])
  const selected = points.find(point => point.id === selectedId)
  const hoverRegion = (event: MouseEvent<SVGPathElement>, id: RegionId) => {
    const rect = event.currentTarget.ownerSVGElement?.getBoundingClientRect()
    if (!rect) return
    setHovered({ id, x: (event.clientX - rect.left) * 960 / rect.width, y: (event.clientY - rect.top) * 756 / rect.height })
  }
  const hoveredRegion = hovered && regionById(hovered.id)
  const tooltipWidth = hoveredRegion ? Math.max(96, hoveredRegion.label.length * 9 + 24) : 0
  return <div className="atria-preview region-preview">
    <div className="plot-heading"><strong>Heart regions</strong><span>{onRegionSelect ? 'Select a region' : 'Region overview'}</span></div>
    <svg viewBox="0 0 960 756" className="heart-region-map" role="group" aria-labelledby={titleId}>
      <title id={titleId}>Human heart diagram with selectable atria, pulmonary veins, and venae cavae</title>
      <image href="/images/heart-diagram.svg" width="960" height="756" aria-hidden="true"/>
      {REGIONS.map(region => <path key={region.id} data-region={region.id} d={region.path} fill={region.color} fillOpacity={occupied.has(region.id) ? .55 : .13} stroke={selected?.regionId === region.id ? '#183f48' : region.color} strokeWidth={selected?.regionId === region.id ? 5 : 2} strokeDasharray={occupied.has(region.id) ? undefined : '5 4'} className={onRegionSelect ? 'region-hotspot' : ''} role={onRegionSelect ? 'button' : undefined} tabIndex={onRegionSelect ? 0 : undefined} aria-label={onRegionSelect ? `Select ${region.label}` : region.label} aria-pressed={onRegionSelect ? selected?.regionId === region.id : undefined} onMouseMove={event => hoverRegion(event, region.id)} onMouseLeave={() => setHovered(null)} onFocus={() => setHovered({ id: region.id, x: region.anchor[0], y: region.anchor[1] })} onBlur={() => setHovered(null)} onClick={() => onRegionSelect?.(region.id)} onKeyDown={event => { if (onRegionSelect && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onRegionSelect(region.id) } }}/>) }
      {points.map((point, index) => {
        const region = regionById(point.regionId)
        if (!region) return null
        const siblings = points.filter(item => item.regionId === point.regionId)
        const offset = (siblings.findIndex(item => item.id === point.id) - (siblings.length - 1) / 2) * 30
        const [x, y] = region.anchor
        return <g key={point.id} className="catheter-marker" aria-label={`Catheter ${index + 1} attached to ${region.label}`}>
          <path d={`M${x + offset - 28} ${y + 53} Q${x + offset - 18} ${y + 17} ${x} ${y}`} fill="none" stroke="white" strokeWidth="8"/>
          <path d={`M${x + offset - 28} ${y + 53} Q${x + offset - 18} ${y + 17} ${x} ${y}`} fill="none" stroke={selectedId === point.id ? '#e3822d' : '#203f4e'} strokeWidth="4"/>
          <circle cx={x} cy={y} r="4" fill="#203f4e" stroke="white" strokeWidth="2"/><circle cx={x + offset - 28} cy={y + 53} r="12" fill={selectedId === point.id ? '#e3822d' : '#203f4e'} stroke="white" strokeWidth="3"/>
          <text x={x + offset - 28} y={y + 57.5} textAnchor="middle" fill="white" fontSize="14" fontWeight="700">{index + 1}</text>
        </g>
      })}
      {hoveredRegion && <g className="region-tooltip" transform={`translate(${Math.max(tooltipWidth / 2 + 8, Math.min(960 - tooltipWidth / 2 - 8, hovered!.x))} ${Math.max(52, hovered!.y)})`} aria-hidden="true"><rect x={-tooltipWidth / 2} y="-46" width={tooltipWidth} height="34" rx="7"/><text textAnchor="middle" y="-24">{hoveredRegion.label}</text></g>}
    </svg>
    <div className="region-legend">{REGIONS.map(region => <button type="button" key={region.id} disabled={!onRegionSelect} className={`${occupied.has(region.id) ? 'occupied' : ''} ${selected?.regionId === region.id ? 'selected' : ''}`} aria-label={`Choose ${region.label}`} aria-pressed={selected?.regionId === region.id} onClick={() => onRegionSelect?.(region.id)}><i style={{ background: region.color }}/>{region.short}</button>)}</div>
    <p>{onRegionSelect ? 'Click a shaded region or choose its name below. The selected catheter attaches to that region.' : 'Shading shows recorded regions; numbered catheter labels appear when catheters are entered.'}</p>
    <p className="image-credit">Diagram: <a href="https://commons.wikimedia.org/wiki/File:Heart_diagram-en.svg" target="_blank" rel="noreferrer">ZooFari / Wikimedia Commons</a> · <a href="https://creativecommons.org/licenses/by-sa/3.0/" target="_blank" rel="noreferrer">CC BY-SA 3.0</a>. Interactive overlays added; approximate region boundaries.</p>
  </div>
}
