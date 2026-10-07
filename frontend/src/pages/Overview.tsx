import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, AlertTriangle, TrendingUp, CheckSquare, Clock, ArrowRight } from 'lucide-react'
import api from '../api/client'
import { RunRef } from './AppShell'

interface Stats {
  total_runs: number
  total_findings: number
  total_high: number
  finding_summary: { type: string; severity: string; count: number }[]
  recent_runs: RunRef[]
}

function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color: string }) {
  return (
    <div className="stat-card">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{label}</p>
      <p className={`text-4xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-600">{sub}</p>}
    </div>
  )
}

export default function Overview({ onSelectRun }: { onSelectRun: (r: RunRef) => void }) {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.get<Stats>('/audit/stats').then(r => setStats(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <PageLoading />

  const s = stats!
  const omissions = s.finding_summary.filter(f => f.type === 'OMISSION').reduce((a, b) => a + b.count, 0)

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <PageHeader
        title="Overview"
        subtitle="System-wide audit statistics and recent activity"
        action={<button onClick={() => navigate('/audit')} className="btn-primary">
          <Activity className="w-4 h-4" /> New Audit
        </button>}
      />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Audits" value={s.total_runs} color="text-white" sub="All time" />
        <StatCard label="Total Findings" value={s.total_findings} color="text-blue-400" sub="Across all runs" />
        <StatCard label="High Severity" value={s.total_high} color="text-red-400" sub="Requires action" />
        <StatCard label="Omissions" value={omissions} color="text-orange-400" sub="Missing safety rules" />
      </div>

      {/* Recent runs */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e32]">
          <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-500" /> Recent Audits
          </h2>
          <button onClick={() => navigate('/history')} className="btn-ghost text-xs">
            View all <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {s.recent_runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-600">
            <CheckSquare className="w-8 h-8 mb-3" />
            <p className="text-sm">No audits yet. Upload a control narrative to get started.</p>
            <button onClick={() => navigate('/audit')} className="btn-primary mt-4">
              Run First Audit
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1e1e32]">
                {['Document', 'Date', 'Findings', 'HIGH', 'MED', 'LOW', ''].map(h => (
                  <th key={h} className="text-left px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {s.recent_runs.map((run: any) => (
                <tr
                  key={run.run_id}
                  className="border-b border-[#1a1a2a] hover:bg-white/[0.02] cursor-pointer transition-colors"
                  onClick={() => { onSelectRun(run); navigate('/findings') }}
                >
                  <td className="px-5 py-3 text-gray-200 text-xs font-medium max-w-[200px] truncate">
                    {run.input_source?.split(/[/\\]/).pop() ?? '—'}
                  </td>
                  <td className="px-5 py-3 text-gray-500 text-xs">
                    {run.created_at ? new Date(run.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-5 py-3">
                    <span className="text-white font-semibold text-sm">{run.total_findings}</span>
                  </td>
                  <td className="px-5 py-3"><span className="text-red-400 font-bold text-xs">{run.high_count}</span></td>
                  <td className="px-5 py-3"><span className="text-orange-400 font-bold text-xs">{run.medium_count}</span></td>
                  <td className="px-5 py-3"><span className="text-emerald-400 font-bold text-xs">{run.low_count}</span></td>
                  <td className="px-5 py-3">
                    <button className="btn-ghost text-xs py-1" onClick={e => { e.stopPropagation(); onSelectRun(run); navigate('/findings') }}>
                      View <ArrowRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Standards reference */}
      <div className="card p-5">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Standards Coverage</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { std: 'IEC 61511', desc: 'Safety Instrumented Systems', clauses: 'Cl. 9–10' },
            { std: 'ISA-84', desc: 'Functional Safety Standard', clauses: 'Part 1' },
            { std: 'IEC 61131-3', desc: 'PLC Programming Languages', clauses: 'ST Output' },
            { std: 'ISA 5.1', desc: 'P&ID Tag Conventions', clauses: 'Tag Linking' },
          ].map(({ std, desc, clauses }) => (
            <div key={std} className="bg-[#16162a] rounded-xl p-3">
              <p className="text-[11px] font-bold text-blue-400">{std}</p>
              <p className="text-[11px] text-gray-400 mt-0.5">{desc}</p>
              <p className="text-[10px] text-gray-600 mt-1">{clauses}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function PageLoading() {
  return (
    <div className="flex items-center justify-center h-full text-gray-600">
      <div className="animate-pulse text-sm">Loading…</div>
    </div>
  )
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}
