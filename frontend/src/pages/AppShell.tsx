import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import Overview from './Overview'
import NewAudit from './NewAudit'
import Findings from './Findings'
import GraphPage from './GraphPage'
import History from './History'

export interface RunRef {
  run_id: string
  filename: string
  total_findings: number
  high_count: number
  medium_count: number
  low_count: number
  total_rules: number
  total_entities: number
  invariants_checked: number
}

export default function AppShell() {
  const [activeRun, setActiveRun] = useState<RunRef | null>(null)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<Overview onSelectRun={setActiveRun} />} />
          <Route path="/audit" element={<NewAudit onRunComplete={setActiveRun} />} />
          <Route path="/findings" element={<Findings run={activeRun} />} />
          <Route path="/graph" element={<GraphPage runId={activeRun?.run_id ?? null} />} />
          <Route path="/history" element={<History onSelectRun={setActiveRun} />} />
        </Routes>
      </main>
    </div>
  )
}
