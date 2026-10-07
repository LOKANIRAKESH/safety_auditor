import { useEffect, useRef, useState } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import api from '../api/client'
import { Share2 } from 'lucide-react'

interface GraphNode { id: string; label: string; node_type: string }
interface GraphEdge { from_id: string; to_id: string; label: string; rel_type: string }

const NODE_COLORS: Record<string, string> = {
  Pump: '#3b82f6', Sensor: '#f97316', PressureTransmitter: '#f97316',
  LevelTransmitter: '#eab308', FlowTransmitter: '#22c55e',
  Valve: '#22c55e', Controller: '#a855f7', Interlock: '#ec4899',
}

export default function KnowledgeGraph({ runId }: { runId: string | null }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [loading, setLoading] = useState(false)
  const [nodeCount, setNodeCount] = useState(0)
  const [edgeCount, setEdgeCount] = useState(0)

  useEffect(() => {
    if (!runId || !containerRef.current) return
    setLoading(true)

    api.get<{ nodes: GraphNode[]; edges: GraphEdge[] }>(`/audit/${runId}/graph`)
      .then(({ data }) => {
        setNodeCount(data.nodes.length)
        setEdgeCount(data.edges.length)

        const nodes = new DataSet(
          data.nodes.map(n => ({
            id: n.id,
            label: n.label,
            title: `${n.label} (${n.node_type})`,
            color: {
              background: NODE_COLORS[n.node_type] ?? '#6b7280',
              border: '#374151',
              highlight: { background: '#60a5fa', border: '#93c5fd' },
            },
            font: { color: '#f9fafb', size: 13 },
            shape: n.node_type?.toLowerCase().includes('pump') ? 'ellipse' :
                   n.node_type?.toLowerCase().includes('valve') ? 'diamond' :
                   'dot',
            size: 22,
          }))
        )

        const edges = new DataSet(
          data.edges.map((e, i) => ({
            id: i,
            from: e.from_id,
            to: e.to_id,
            label: e.label,
            arrows: 'to',
            color: { color: '#4b5563', highlight: '#3b82f6' },
            font: { color: '#9ca3af', size: 10, align: 'middle' },
            smooth: { type: 'curvedCW', roundness: 0.15 } as any,
          }))
        )

        const network = new Network(
          containerRef.current!,
          { nodes, edges },
          {
            physics: { stabilization: { iterations: 200 }, barnesHut: { gravitationalConstant: -8000 } },
            interaction: { hover: true, tooltipDelay: 200 },
            layout: { improvedLayout: true },
          }
        )

        network.on('click', (params) => {
          if (params.nodes.length > 0) {
            const id = params.nodes[0]
            const n = data.nodes.find(x => x.id === id) ?? null
            setSelectedNode(n)
          } else {
            setSelectedNode(null)
          }
        })
      })
      .finally(() => setLoading(false))
  }, [runId])

  if (!runId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <Share2 className="w-10 h-10 mb-3" />
        <p>Run an audit first to see the knowledge graph.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Equipment Knowledge Graph</h2>
          <p className="text-gray-400 text-sm">{nodeCount} nodes · {edgeCount} edges</p>
        </div>
        <div className="flex gap-3 text-xs">
          {Object.entries({ Pump: '#3b82f6', Sensor: '#f97316', Valve: '#22c55e', Controller: '#a855f7' }).map(([k, c]) => (
            <span key={k} className="flex items-center gap-1.5 text-gray-400">
              <span className="w-3 h-3 rounded-full inline-block" style={{ background: c }} />
              {k}
            </span>
          ))}
        </div>
      </div>

      <div className="flex gap-4">
        <div
          ref={containerRef}
          className="flex-1 h-[520px] bg-gray-900 border border-gray-800 rounded-xl"
          style={{ minHeight: 400 }}
        >
          {loading && (
            <div className="flex items-center justify-center h-full text-gray-500">
              Loading graph…
            </div>
          )}
        </div>

        {/* Node detail panel */}
        {selectedNode && (
          <div className="w-64 bg-gray-900 border border-gray-800 rounded-xl p-5 shrink-0 self-start">
            <h3 className="font-bold text-white text-base mb-1">{selectedNode.label}</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900 text-blue-300">
              {selectedNode.node_type}
            </span>
            <div className="mt-4 space-y-2 text-sm">
              <div>
                <span className="text-gray-500 text-xs">Tag</span>
                <p className="text-gray-200 font-mono">{selectedNode.id}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="mt-4 text-xs text-gray-500 hover:text-gray-300"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
