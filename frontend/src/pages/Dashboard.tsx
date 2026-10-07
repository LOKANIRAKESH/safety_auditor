import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { ShieldCheck, LogOut, Upload, AlertTriangle, Share2, Clock } from 'lucide-react'
import UploadPanel from '../components/UploadPanel'
import FindingCharts from '../components/FindingCharts'
import KnowledgeGraph from '../components/KnowledgeGraph'
import AuditHistory from '../components/AuditHistory'

const TABS = [
  { id: 'upload', label: 'Upload & Run', icon: Upload },
  { id: 'findings', label: 'Findings', icon: AlertTriangle },
  { id: 'graph', label: 'Knowledge Graph', icon: Share2 },
  { id: 'history', label: 'Audit History', icon: Clock },
] as const

type TabId = typeof TABS[number]['id']

export interface RunResult {
  run_id: string
  input_source: string
  total_findings: number
  high_count: number
  medium_count: number
  low_count: number
  total_rules: number
  total_entities: number
  invariants_checked: number
  status: string
  report_path: string | null
  plc_path: string | null
}

export default function Dashboard() {
  const { username, role, logout } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabId>('upload')
  const [latestRun, setLatestRun] = useState<RunResult | null>(null)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  function onRunComplete(run: RunResult) {
    setLatestRun(run)
    setActiveTab('findings')
  }

  const roleBadge =
    role === 'admin'
      ? 'bg-purple-900 text-purple-200 border-purple-700'
      : 'bg-blue-900 text-blue-200 border-blue-700'

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* ── Navbar ── */}
      <nav className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-bold text-white text-sm">ICS Safety Auditor</span>
            <span className="text-gray-500 text-xs ml-2">Pre-Synthesis Verification</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-gray-400 text-sm">{username}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${roleBadge}`}>
            {role === 'admin' ? 'Admin' : 'Safety Engineer'}
          </span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Logout
          </button>
        </div>
      </nav>

      {/* ── Tab bar ── */}
      <div className="border-b border-gray-800 bg-gray-900 px-6">
        <div className="flex gap-1">
          {TABS.map(({ id, label, icon: Icon }) => {
            const active = activeTab === id
            const disabled = id === 'upload' && role === 'viewer'
            return (
              <button
                key={id}
                onClick={() => !disabled && setActiveTab(id)}
                disabled={disabled}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  active
                    ? 'border-blue-500 text-blue-400'
                    : disabled
                    ? 'border-transparent text-gray-600 cursor-not-allowed'
                    : 'border-transparent text-gray-400 hover:text-white hover:border-gray-600'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Tab content ── */}
      <main className="flex-1 p-6 overflow-auto">
        {activeTab === 'upload' && <UploadPanel onRunComplete={onRunComplete} />}
        {activeTab === 'findings' && <FindingCharts run={latestRun} />}
        {activeTab === 'graph' && <KnowledgeGraph runId={latestRun?.run_id ?? null} />}
        {activeTab === 'history' && <AuditHistory onSelectRun={(r) => { setLatestRun(r); setActiveTab('findings') }} />}
      </main>
    </div>
  )
}
