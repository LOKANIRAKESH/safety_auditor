import { useEffect, useState } from 'react'
import api from '../api/client'
import { Clock, ChevronDown, ChevronRight } from 'lucide-react'
import { RunResult } from '../pages/Dashboard'

interface Finding {
  id: number; finding_type: string; severity: string
  equipment_tag: string; iec_clause: string; description: string
}

interface Props {
  onSelectRun: (run: RunResult) => void
}

export default function AuditHistory({ onSelectRun }: Props) {
  const [runs, setRuns] = useState<RunResult[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [findings, setFindings] = useState<Record<string, Finding[]>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<RunResult[]>('/audit/history')
      .then(r => setRuns(r.data))
      .finally(() => setLoading(false))
  }, [])

  async function toggleExpand(runId: string) {
    if (expanded === runId) { setExpanded(null); return }
    setExpanded(runId)
    if (!findings[runId]) {
      const { data } = await api.get<Finding[]>(`/audit/${runId}/findings`)
      setFindings(prev => ({ ...prev, [runId]: data }))
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Loading history…</div>
  }

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <Clock className="w-10 h-10 mb-3" />
        <p>No audit runs yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Audit History</h2>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              {['', 'Run ID', 'Document', 'Date', 'HIGH', 'MED', 'LOW', 'Status', ''].map((h, i) => (
                <th key={i} className="text-left px-4 py-3 text-gray-400 font-medium text-xs">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map(run => (
              <>
                <tr
                  key={run.run_id}
                  className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer"
                  onClick={() => toggleExpand(run.run_id)}
                >
                  <td className="px-4 py-3 text-gray-500">
                    {expanded === run.run_id
                      ? <ChevronDown className="w-4 h-4" />
                      : <ChevronRight className="w-4 h-4" />}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{run.run_id}</td>
                  <td className="px-4 py-3 text-gray-300 text-xs max-w-[160px] truncate">
                    {run.input_source.split(/[/\\]/).pop()}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {run.created_at ? new Date(run.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-red-400 font-bold text-xs">{run.high_count}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-orange-400 font-bold text-xs">{run.medium_count}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-green-400 font-bold text-xs">{run.low_count}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-green-900 text-green-300">
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      className="text-xs text-blue-400 hover:text-blue-300"
                      onClick={e => { e.stopPropagation(); onSelectRun(run) }}
                    >
                      View →
                    </button>
                  </td>
                </tr>

                {/* Expanded findings */}
                {expanded === run.run_id && (
                  <tr key={`${run.run_id}-exp`} className="bg-gray-900/50">
                    <td colSpan={9} className="px-8 py-4">
                      {findings[run.run_id]?.length ? (
                        <div className="space-y-2">
                          {findings[run.run_id].map(f => (
                            <div key={f.id} className="flex items-start gap-3 text-xs">
                              <span className={`shrink-0 px-1.5 py-0.5 rounded font-bold ${
                                f.severity === 'HIGH' ? 'bg-red-900 text-red-300' :
                                f.severity === 'MEDIUM' ? 'bg-orange-900 text-orange-300' :
                                'bg-green-900 text-green-300'}`}>
                                {f.severity}
                              </span>
                              <span className="text-blue-400 font-mono shrink-0 w-16">{f.equipment_tag}</span>
                              <span className="text-gray-300">{f.description}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-500 text-xs">No findings for this run.</p>
                      )}
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
