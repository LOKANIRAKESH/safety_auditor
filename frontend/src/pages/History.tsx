import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock, ChevronDown, ChevronRight, ArrowRight, Search } from 'lucide-react'
import api from '../api/client'
import { RunRef } from './AppShell'
import { PageHeader } from './Overview'

interface HistoryRun {
  run_id: string; input_source: string; created_at: string | null
  total_findings: number; high_count: number; medium_count: number; low_count: number
  total_rules: number; total_entities: number; invariants_checked: number; status: string
}

interface Finding {
  id: number; finding_type: string; severity: string
  equipment_tag: string; iec_clause: string; description: string
}

export default function History({ onSelectRun }: { onSelectRun: (r: RunRef) => void }) {
  const [runs, setRuns] = useState<HistoryRun[]>([])
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [findingsCache, setFindingsCache] = useState<Record<string, Finding[]>>({})
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.get<HistoryRun[]>('/audit/history').then(r => setRuns(r.data)).finally(() => setLoading(false))
  }, [])

  async function toggle(runId: string) {
    if (expanded === runId) { setExpanded(null); return }
    setExpanded(runId)
    if (!findingsCache[runId]) {
      const { data } = await api.get<Finding[]>(`/audit/${runId}/findings`)
      setFindingsCache(p => ({ ...p, [runId]: data }))
    }
  }

  function selectRun(run: HistoryRun) {
    onSelectRun({
      run_id: run.run_id,
      filename: run.input_source?.split(/[/\\]/).pop() ?? run.run_id,
      total_findings: run.total_findings,
      high_count: run.high_count,
      medium_count: run.medium_count,
      low_count: run.low_count,
      total_rules: run.total_rules,
      total_entities: run.total_entities,
      invariants_checked: run.invariants_checked,
    })
    navigate('/findings')
  }

  const filtered = runs.filter(r =>
    !search || r.input_source?.toLowerCase().includes(search.toLowerCase()) ||
    r.run_id.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return <div className="flex items-center justify-center h-full text-gray-600 text-sm">Loading…</div>
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <PageHeader
        title="Audit History"
        subtitle={`${runs.length} runs recorded in the audit store`}
        action={
          <button onClick={() => navigate('/audit')} className="btn-primary">
            New Audit
          </button>
        }
      />

      {runs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-gray-600">
          <Clock className="w-10 h-10 mb-4" />
          <p className="text-sm">No audits have been run yet.</p>
          <button onClick={() => navigate('/audit')} className="btn-primary mt-4">Run First Audit</button>
        </div>
      ) : (
        <div className="card overflow-hidden">
          {/* Search */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[#1e1e32]">
            <Search className="w-4 h-4 text-gray-600 shrink-0" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by filename or run ID…"
              className="bg-transparent text-sm text-gray-300 placeholder-gray-600 outline-none flex-1"
            />
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1e1e32]">
                {['', 'Document', 'Date', 'Findings', 'HIGH', 'MED', 'LOW', 'Status', ''].map((h, i) => (
                  <th key={i} className="text-left px-4 py-3 text-[11px] font-semibold text-gray-600 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(run => (
                <>
                  <tr
                    key={run.run_id}
                    className="border-b border-[#1a1a2a] hover:bg-white/[0.02] cursor-pointer transition-colors"
                    onClick={() => toggle(run.run_id)}
                  >
                    <td className="px-4 py-3 text-gray-600 w-8">
                      {expanded === run.run_id
                        ? <ChevronDown className="w-4 h-4" />
                        : <ChevronRight className="w-4 h-4" />}
                    </td>
                    <td className="px-4 py-3 max-w-[200px]">
                      <p className="text-gray-200 text-xs font-medium truncate">
                        {run.input_source?.split(/[/\\]/).pop() ?? '—'}
                      </p>
                      <p className="text-gray-600 text-[10px] font-mono mt-0.5 truncate">{run.run_id}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {run.created_at ? new Date(run.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-white font-bold text-sm">{run.total_findings}</td>
                    <td className="px-4 py-3"><span className="text-red-400 font-semibold text-xs">{run.high_count}</span></td>
                    <td className="px-4 py-3"><span className="text-orange-400 font-semibold text-xs">{run.medium_count}</span></td>
                    <td className="px-4 py-3"><span className="text-emerald-400 font-semibold text-xs">{run.low_count}</span></td>
                    <td className="px-4 py-3">
                      <span className={`badge-base border text-[10px] ${
                        run.status === 'completed' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25' :
                        'bg-gray-500/15 text-gray-400 border-gray-500/25'}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={e => { e.stopPropagation(); selectRun(run) }}
                        className="btn-ghost text-xs py-1"
                      >
                        View <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>

                  {expanded === run.run_id && (
                    <tr key={`${run.run_id}-exp`} className="bg-[#0c0c18]">
                      <td colSpan={9} className="px-8 py-4">
                        <p className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider mb-3">
                          Findings · {run.total_rules} rules · {run.total_entities} entities · {run.invariants_checked} invariants checked
                        </p>
                        {findingsCache[run.run_id]?.length ? (
                          <div className="space-y-2">
                            {findingsCache[run.run_id].map(f => (
                              <div key={f.id} className="flex items-start gap-3 text-xs">
                                <span className={`badge-base border shrink-0 mt-0.5 ${
                                  f.severity === 'HIGH' ? 'badge-high' :
                                  f.severity === 'MEDIUM' ? 'badge-med' : 'badge-low'}`}>
                                  {f.severity}
                                </span>
                                <span className="font-mono text-blue-400 shrink-0 w-14">{f.equipment_tag}</span>
                                <span className="text-gray-400 leading-relaxed">{f.description}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-gray-600 text-xs">No findings.</p>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>

          {filtered.length === 0 && search && (
            <div className="flex items-center justify-center py-8 text-gray-600 text-sm">
              No runs match "{search}"
            </div>
          )}
        </div>
      )}
    </div>
  )
}
