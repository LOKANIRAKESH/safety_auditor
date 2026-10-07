import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { UploadCloud, FileText, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import api from '../api/client'
import { RunRef } from './AppShell'
import { PageHeader } from './Overview'

const PHASES = [
  'PDF Extraction',
  'LLM Entity Extraction',
  'Cross-Modal Linking',
  'Knowledge Graph',
  'Rule IR',
  'Invariant Coverage',
  'Z3 Verification',
  'Audit Report',
  'PLC Sketch',
]

interface JobStatus {
  status: 'queued' | 'running' | 'completed' | 'failed'
  phase: string
  progress: number
  run_id: string | null
  error: string | null
  filename: string
  total_findings: number
  high_count: number
  medium_count: number
  low_count: number
}

export default function NewAudit({ onRunComplete }: { onRunComplete: (r: RunRef) => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<JobStatus | null>(null)
  const [uploadError, setUploadError] = useState('')
  const navigate = useNavigate()

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) { setFile(accepted[0]); setUploadError(''); setJobId(null); setJob(null) }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
  })

  // Poll job status every 2s
  useEffect(() => {
    if (!jobId) return
    const id = setInterval(async () => {
      try {
        const { data } = await api.get<JobStatus>(`/audit/job/${jobId}`)
        setJob(data)
        if (data.status === 'completed' && data.run_id) {
          clearInterval(id)
          const run = await api.get(`/audit/${data.run_id}`)
          onRunComplete(run.data)
        } else if (data.status === 'failed') {
          clearInterval(id)
        }
      } catch { clearInterval(id) }
    }, 2000)
    return () => clearInterval(id)
  }, [jobId, onRunComplete])

  async function startAudit() {
    if (!file) return
    setUploadError('')
    const form = new FormData()
    form.append('file', file)
    try {
      const { data } = await api.post<{ job_id: string }>('/audit/run', form)
      setJobId(data.job_id)
      setJob({ status: 'queued', phase: 'Queued', progress: 0, run_id: null, error: null,
               filename: file.name, total_findings: 0, high_count: 0, medium_count: 0, low_count: 0 })
    } catch (e: any) {
      setUploadError(e.response?.data?.detail ?? 'Upload failed. Is the backend running?')
    }
  }

  const isRunning = job?.status === 'running' || job?.status === 'queued'
  const isDone = job?.status === 'completed'
  const isFailed = job?.status === 'failed'

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <PageHeader
        title="New Audit"
        subtitle="Upload a control narrative PDF to run the full 9-phase safety audit"
      />

      {/* Upload zone */}
      {!isRunning && !isDone && (
        <>
          <div
            {...getRootProps()}
            className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200
              ${isDragActive ? 'border-blue-500 bg-blue-500/5' : 'border-[#2a2a45] bg-[#10101c] hover:border-[#3a3a5f] hover:bg-[#12122a]'}`}
          >
            <input {...getInputProps()} />
            <UploadCloud className={`w-10 h-10 mx-auto mb-4 transition-colors ${isDragActive ? 'text-blue-400' : 'text-gray-600'}`} />
            {isDragActive ? (
              <p className="text-blue-400 font-medium">Drop it here</p>
            ) : (
              <>
                <p className="text-gray-300 font-semibold">Drag & drop your PDF here</p>
                <p className="text-gray-600 text-sm mt-1">or click to browse files</p>
                <p className="text-gray-700 text-xs mt-3">Accepts: control narrative, cause-effect tables, combined specs</p>
              </>
            )}
          </div>

          {file && (
            <div className="flex items-center gap-3 card-sm px-4 py-3">
              <FileText className="w-5 h-5 text-blue-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-200 truncate">{file.name}</p>
                <p className="text-xs text-gray-600">{(file.size / 1024).toFixed(1)} KB · PDF</p>
              </div>
              <button onClick={() => setFile(null)} className="text-gray-600 hover:text-gray-400">
                <XCircle className="w-4 h-4" />
              </button>
            </div>
          )}

          {uploadError && (
            <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-red-400 text-sm">
              <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
              {uploadError}
            </div>
          )}

          <button onClick={startAudit} disabled={!file} className="btn-primary w-full justify-center py-3 text-base">
            Run Safety Audit
          </button>
        </>
      )}

      {/* Progress */}
      {(isRunning || isDone || isFailed) && job && (
        <div className="card p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-gray-200">{job.filename}</p>
              <p className="text-xs text-gray-500 mt-0.5">{
                isDone ? 'Audit complete' :
                isFailed ? 'Audit failed' :
                job.phase
              }</p>
            </div>
            <StatusBadge status={job.status} />
          </div>

          {/* Progress bar */}
          {!isFailed && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-gray-600">
                <span>Progress</span>
                <span>{job.progress}%</span>
              </div>
              <div className="w-full bg-[#1e1e32] rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all duration-500 ${isDone ? 'bg-emerald-500' : 'bg-blue-500'}`}
                  style={{ width: `${job.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Phase steps */}
          <div className="grid grid-cols-3 gap-2">
            {PHASES.map((phase, i) => {
              const currentIdx = PHASES.indexOf(job.phase)
              const done = isDone || i < currentIdx
              const active = !isDone && i === currentIdx
              return (
                <div key={phase} className={`flex items-center gap-2 text-xs rounded-lg px-3 py-2 transition-colors
                  ${done ? 'bg-emerald-500/10 text-emerald-400' :
                    active ? 'bg-blue-500/10 text-blue-400' :
                    'bg-[#16162a] text-gray-600'}`}>
                  <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0
                    ${done ? 'bg-emerald-500 text-white' :
                      active ? 'bg-blue-500 text-white' :
                      'bg-[#2a2a45] text-gray-600'}`}>
                    {done ? '✓' : i + 1}
                  </span>
                  <span className="truncate">{phase}</span>
                  {active && <Loader2 className="w-3 h-3 animate-spin ml-auto shrink-0" />}
                </div>
              )
            })}
          </div>

          {isFailed && (
            <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-red-400 text-sm">
              <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{job.error ?? 'Unknown error. Is Ollama running?'}</span>
            </div>
          )}

          {isDone && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Findings', value: job.total_findings, color: 'text-white' },
                  { label: 'HIGH', value: job.high_count, color: 'text-red-400' },
                  { label: 'MED', value: job.medium_count, color: 'text-orange-400' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="card-sm p-3 text-center">
                    <p className={`text-2xl font-bold ${color}`}>{value}</p>
                    <p className="text-xs text-gray-500 mt-1">{label}</p>
                  </div>
                ))}
              </div>
              <div className="flex gap-3">
                <button onClick={() => navigate('/findings')} className="btn-primary flex-1 justify-center">
                  View Findings
                </button>
                <button onClick={() => navigate('/graph')} className="btn-ghost flex-1 justify-center border border-[#2a2a45]">
                  Knowledge Graph
                </button>
              </div>
            </div>
          )}

          {(isRunning || isDone) && (
            <button
              onClick={() => { setFile(null); setJob(null); setJobId(null) }}
              className="text-xs text-gray-600 hover:text-gray-400 w-full text-center"
            >
              Start another audit
            </button>
          )}
        </div>
      )}

      {/* Info cards */}
      {!isRunning && !isDone && (
        <div className="grid grid-cols-2 gap-4 text-xs text-gray-500">
          <div className="card-sm p-4">
            <p className="font-semibold text-gray-300 mb-2">What gets checked</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>Missing shutdown rules (IEC 61511-1 Cl. 9.2.2)</li>
              <li>Contradictory control rules (Z3 UNSAT)</li>
              <li>Ambiguous equipment tags</li>
              <li>ESD propagation completeness</li>
            </ul>
          </div>
          <div className="card-sm p-4">
            <p className="font-semibold text-gray-300 mb-2">What you get</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>Severity-ranked safety findings</li>
              <li>IEC 61511 clause references</li>
              <li>Interactive knowledge graph</li>
              <li>IEC 61131-3 PLC code sketch</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    queued: 'bg-gray-500/15 text-gray-400 border-gray-500/25',
    running: 'bg-blue-500/15 text-blue-400 border-blue-500/25 animate-pulse',
    completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
    failed: 'bg-red-500/15 text-red-400 border-red-500/25',
  }
  return (
    <span className={`badge-base border capitalize ${map[status] ?? map.queued}`}>
      {status}
    </span>
  )
}
