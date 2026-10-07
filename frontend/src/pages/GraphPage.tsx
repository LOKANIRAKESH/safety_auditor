import { useEffect, useRef, useState } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { useNavigate } from 'react-router-dom'
import { Share2, Info, X } from 'lucide-react'
import api from '../api/client'
import { PageHeader } from './Overview'

interface GNode { id: string; label: string; node_type: string }
interface GEdge { from_id: string; to_id: string; label: string; rel_type: string }

const NODE_STYLE: Record<string, { color: string; shape: string }> = {
  Pump:                   { color: '#3b82f6', shape: 'ellipse' },
  Compressor:             { color: '#6366f1', shape: 'ellipse' },
  Valve:                  { color: '#10b981', shape: 'diamond' },
  Sensor:                 { color: '#f97316', shape: 'dot' },
  PressureTransmitter:    { color: '#f97316', shape: 'dot' },
  LevelTransmitter:       { color: '#eab308', shape: 'dot' },
  FlowTransmitter:        { color: '#22d3ee', shape: 'dot' },
  TemperatureTransmitter: { color: '#f43f5e', shape: 'dot' },
  Controller:             { color: '#a855f7', shape: 'hexagon' },
  Interlock:              { color: '#ec4899', shape: 'star' },
}
const DEFAULT_STYLE = { color: '#6b7280', shape: 'dot' }

const LEGEND = [
  { label: 'Pump/Compressor', color: '#3b82f6' },
  { label: 'Valve', color: '#10b981' },
  { label: 'Pressure Sensor', color: '#f97316' },
  { label: 'Level Sensor', color: '#eab308' },
  { label: 'Controller', color: '#a855f7' },
  { label: 'Interlock', color: '#ec4899' },
]

export default function GraphPage({ runId }: { runId: string | null }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [selected, setSelected] = useState<GNode | null>(null)
  const [counts, setCounts] = useState({ nodes: 0, edges: 0 })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!runId || !containerRef.current) return
    setLoading(true)
    setSelected(null)

    api.get<{ nodes: GNode[]; edges: GEdge[] }>(`/audit/${runId}/graph`).then(({ data }) => {
      setCounts({ nodes: data.nodes.length, edges: data.edges.length })

      const nodes = new DataSet(data.nodes.map(n => {
        const style = NODE_STYLE[n.node_type] ?? DEFAULT_STYLE
        return {
          id: n.id,
          label: n.label,
          title: `<div style="font-family:monospace;font-size:12px;color:#e2e2f0;padding:4px">${n.label}<br/><span style="color:#6b7280">${n.node_type}</span></div>`,
          color: {
            background: style.color + '22',
            border: style.color,
            highlight: { background: style.color + '44', border: style.color },
            hover: { background: style.color + '33', border: style.color },
          },
          font: { color: '#d1d5db', size: 12, face: 'monospace' },
          shape: style.shape as any,
          size: 22,
          borderWidth: 1.5,
        }
      }))

      const edges = new DataSet(data.edges.map((e, i) => ({
        id: i,
        from: e.from_id,
        to: e.to_id,
        label: e.label,
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        color: { color: '#2a2a45', highlight: '#4f8ef7', hover: '#3b82f6' },
        font: { color: '#4b5563', size: 10, align: 'middle', background: '#08080f' },
        smooth: { type: 'curvedCW', roundness: 0.1 } as any,
        width: 1.5,
        hoverWidth: 2.5,
      })))

      const network = new Network(containerRef.current!, { nodes, edges }, {
        physics: {
          enabled: true,
          stabilization: { iterations: 300 },
          barnesHut: { gravitationalConstant: -12000, centralGravity: 0.1, springLength: 180 },
        },
        interaction: { hover: true, tooltipDelay: 100, navigationButtons: false, zoomView: true },
        layout: { improvedLayout: true },
      })

      network.on('click', ({ nodes: clicked }) => {
        if (clicked.length > 0) {
          const n = data.nodes.find(x => x.id === clicked[0]) ?? null
          setSelected(n)
        } else setSelected(null)
      })
    }).finally(() => setLoading(false))
  }, [runId])

  if (!runId) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-24 text-gray-600">
        <Share2 className="w-10 h-10 mb-4" />
        <p className="text-sm">Run an audit first to see the knowledge graph</p>
        <button onClick={() => navigate('/audit')} className="btn-primary mt-4">New Audit</button>
      </div>
    )
  }

  return (
    <div className="p-8 h-full flex flex-col gap-6">
      <PageHeader
        title="Knowledge Graph"
        subtitle={loading ? 'Building graph…' : `${counts.nodes} nodes · ${counts.edges} edges · click any node for details`}
      />

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {LEGEND.map(({ label, color }) => (
          <span key={label} className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Graph canvas */}
        <div className="flex-1 card overflow-hidden relative">
          <div ref={containerRef} className="w-full h-full min-h-[500px]" />
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#10101c]/80 rounded-2xl">
              <p className="text-gray-500 text-sm animate-pulse">Rendering graph…</p>
            </div>
          )}
          <div className="absolute bottom-4 left-4 text-[11px] text-gray-700">
            Scroll to zoom · Drag to pan · Click node for details
          </div>
        </div>

        {/* Side panel */}
        {selected && (
          <div className="w-56 card p-4 space-y-4 self-start shrink-0">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-gray-500 shrink-0" />
                <p className="text-xs font-semibold text-gray-300">Node Details</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-600 hover:text-gray-400">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <p className="text-gray-600 mb-0.5">Tag</p>
                <p className="font-mono text-blue-400 font-semibold">{selected.id}</p>
              </div>
              <div>
                <p className="text-gray-600 mb-0.5">Label</p>
                <p className="text-gray-300">{selected.label}</p>
              </div>
              <div>
                <p className="text-gray-600 mb-0.5">Type</p>
                <span className={`badge-base border px-2 py-0.5 rounded-md text-[11px]`}
                  style={{ background: (NODE_STYLE[selected.node_type]?.color ?? '#6b7280') + '22',
                           color: NODE_STYLE[selected.node_type]?.color ?? '#9ca3af',
                           borderColor: (NODE_STYLE[selected.node_type]?.color ?? '#6b7280') + '44' }}>
                  {selected.node_type}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
