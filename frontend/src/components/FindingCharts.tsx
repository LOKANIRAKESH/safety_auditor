import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { AlertTriangle, CheckCircle, Activity, BookOpen } from 'lucide-react'
import api from '../api/client'
import { RunResult } from '../pages/Dashboard'

interface Finding {
  id: number
  finding_type: string
  severity: string
  equipment_tag: string
  invariant_id: string
  iec_clause: string
  description: string
  recommendation: string
  z3_result: string
}

interface Props {
  run: RunResult | null
}

const SEV_COLORS: Record<string, string> = { HIGH: '#ef4444', MEDIUM: '#f97316', LOW: '#22c55e' }
const TYPE_COLORS: Record<string, string> = {
  OMISSION: '#3b82f6', CONTRADICTION: '#ef4444', TAG_MISMATCH: '#f97316', UNSAFE_STATE: '#a855f7',
}

export default function FindingCharts({ run }: Props) {
  const [findings, setFindings] = useState<Finding[]>([])

  useEffect(() => {
    if (!run) return
    api.get<Finding[]>(`/audit/${run.run_id}/findings`).then(r => setFindings(r.data))
  }, [run])

  if (!run) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <AlertTriangle className="w-10 h-10 mb-3" />
        <p>No audit results yet. Upload a document and run the audit first.</p>
      </div>
    )
  }

  const severityData = [
    { name: 'HIGH', value: run.high_count },
    { name: 'MEDIUM', value: run.medium_count },
    { name: 'LOW', value: run.low_count },
  ].filter(d => d.value > 0)

  const typeCounts: Record<string, number> = {}
  findings.forEach(f => { typeCounts[f.finding_type] = (typeCounts[f.finding_type] ?? 0) + 1 })
  const typeData = Object.entries(typeCounts).map(([name, count]) => ({ name, count }))

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Findings', value: run.total_findings, icon: AlertTriangle, color: 'text-red-400' },
          { label: 'Rules Extracted', value: run.total_rules, icon: Activity, color: 'text-blue-400' },
          { label: 'Entities Found', value: run.total_entities, icon: CheckCircle, color: 'text-green-400' },
          { label: 'Invariants Checked', value: run.invariants_checked, icon: BookOpen, color: 'text-purple-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Icon className={`w-4 h-4 ${color}`} />
              <span className="text-gray-400 text-xs">{label}</span>
            </div>
            <p className="text-3xl font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Severity donut */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Findings by Severity</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={severityData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                {severityData.map(({ name }) => <Cell key={name} fill={SEV_COLORS[name] ?? '#6b7280'} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Finding type bar */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Findings by Type</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={typeData} layout="vertical" margin={{ left: 20 }}>
              <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} width={110} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {typeData.map(({ name }) => <Cell key={name} fill={TYPE_COLORS[name] ?? '#6b7280'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Findings table */}
      {findings.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h3 className="text-sm font-semibold text-gray-300">All Findings — {run.input_source.split(/[/\\]/).pop()}</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  {['Severity', 'Type', 'Equipment', 'IEC Clause', 'Description'].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 text-gray-400 font-medium text-xs">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {findings.map(f => (
                  <tr key={f.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-4 py-2.5">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        f.severity === 'HIGH' ? 'bg-red-900 text-red-300' :
                        f.severity === 'MEDIUM' ? 'bg-orange-900 text-orange-300' :
                        'bg-green-900 text-green-300'}`}>
                        {f.severity}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-300 text-xs">{f.finding_type}</td>
                    <td className="px-4 py-2.5 text-blue-400 font-mono text-xs">{f.equipment_tag}</td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{f.iec_clause}</td>
                    <td className="px-4 py-2.5 text-gray-300 text-xs max-w-xs truncate" title={f.description}>{f.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
