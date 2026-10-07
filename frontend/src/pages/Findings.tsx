import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertTriangle, Filter, ArrowUpRight } from 'lucide-react'
import api from '../api/client'
import { RunRef } from './AppShell'
import { PageHeader } from './Overview'

interface Finding {
  id: number; finding_type: string; severity: string
  equipment_tag: string; invariant_id: string; iec_clause: string
  description: string; recommendation: string; z3_result: string
}

const SEV: Record<string, string> = { HIGH: '#ef4444', MEDIUM: '#f97316', LOW: '#10b981' }
const TYPE_CLR: Record<string, string> = {
  OMISSION: '#3b82f6', CONTRADICTION: '#ef4444', TAG_MISMATCH: '#f97316',
  UNSAFE_STATE: '#a855f7', INCONSISTENCY: '#eab308',
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[#16162a] border border-[#2a2a45] rounded-lg px-3 py-2 text-xs text-gray-300 shadow-xl">
      <p className="font-semibold">{payload[0].name}</p>
      <p className="text-gray-400">{payload[0].value} findings</p>
    </div>
  )
}

export default function Findings({ run }: { run: RunRef | null }) {
  const [findings, setFindings] = useState<Finding[]>([])
  const [filter, setFilter] = useState<string>('ALL')
  const [expanded, setExpanded] = useState<number | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!run?.run_id) return
    api.get<Finding[]>(`/audit/${run.run_id}/findings`).then(r => setFindings(r.data))
  }, [run?.run_id])

  if (!run) {
    return (
      <EmptyState
        icon={<AlertTriangle className="w-10 h-10" />}
        message="No findings loaded"
        action={<button onClick={() => navigate('/audit')} className="btn-primary mt-4">Run an Audit</button>}
      />
    )
  }

  const sevData = [
    { name: 'HIGH', value: run.high_count },
    { name: 'MEDIUM', value: run.medium_count },
    { name: 'LOW', value: run.low_count },
  ].filter(d => d.value > 0)

  const typeCounts: Record<string, number> = {}
  findings.forEach(f => { typeCounts[f.finding_type] = (typeCounts[f.finding_type] ?? 0) + 1 })
  const typeData = Object.entries(typeCounts).map(([name, count]) => ({ name, count }))

  const filtered = filter === 'ALL' ? findings : findings.filter(f => f.severity === filter)

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <PageHeader
        title="Findings"
        subtitle={`${run.high_count + run.medium_count + run.low_count} findings · ${run.total_rules ?? 0} rules · ${run.total_entities ?? 0} entities`}
        action={
          <button onClick={() => navigate('/graph')} className="btn-ghost border border-[#2a2a45]">
            Knowledge Graph <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        }
      />

      {/* Stat row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Findings', value: run.total_findings ?? 0, cls: 'text-white' },
          { label: 'High Severity', value: run.high_count, cls: 'text-red-400' },
          { label: 'Medium', value: run.medium_count, cls: 'text-orange-400' },
          { label: 'Low', value: run.low_count, cls: 'text-emerald-400' },
        ].map(({ label, value, cls }) => (
          <div key={label} className="stat-card">
            <p className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">{label}</p>
            <p className={`text-3xl font-bold ${cls}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-5">
          <p className="text-sm font-semibold text-gray-400 mb-4">Severity Distribution</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={sevData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                   dataKey="value" paddingAngle={3}
                   label={({ name, value }) => `${name} ${value}`}
                   labelLine={false}>
                {sevData.map(({ name }) => <Cell key={name} fill={SEV[name]} />)}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <p className="text-sm font-semibold text-gray-400 mb-4">Finding Types</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={typeData} layout="vertical" margin={{ left: 10 }}>
              <XAxis type="number" tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} width={115} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={20}>
                {typeData.map(({ name }) => <Cell key={name} fill={TYPE_CLR[name] ?? '#6b7280'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Findings list */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e32]">
          <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" /> All Findings
          </h2>
          <div className="flex gap-1">
            {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(s => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                  filter === s ? 'bg-blue-600/20 text-blue-400' : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-[#1a1a2a]">
          {filtered.map(f => (
            <div
              key={f.id}
              className="hover:bg-white/[0.015] transition-colors cursor-pointer"
              onClick={() => setExpanded(expanded === f.id ? null : f.id)}
            >
              <div className="flex items-start gap-4 px-6 py-4">
                <span className={`badge-base border mt-0.5 shrink-0 ${
                  f.severity === 'HIGH' ? 'badge-high' :
                  f.severity === 'MEDIUM' ? 'badge-med' : 'badge-low'}`}>
                  {f.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-xs font-mono text-blue-400">{f.equipment_tag}</span>
                    <span className="text-[10px] text-gray-600 bg-[#1a1a2a] px-2 py-0.5 rounded-md">{f.finding_type}</span>
                    {f.iec_clause && (
                      <span className="text-[10px] text-gray-600">{f.iec_clause}</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-300 leading-relaxed">{f.description}</p>
                  {expanded === f.id && f.recommendation && (
                    <div className="mt-3 bg-blue-500/5 border border-blue-500/15 rounded-xl p-3">
                      <p className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider mb-1">Recommendation</p>
                      <p className="text-xs text-gray-400 leading-relaxed">{f.recommendation}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="flex items-center justify-center py-12 text-gray-600 text-sm">
              No findings match the current filter.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ icon, message, action }: { icon: React.ReactNode; message: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center h-full py-24 text-gray-600">
      <div className="mb-4">{icon}</div>
      <p className="text-sm">{message}</p>
      {action}
    </div>
  )
}
