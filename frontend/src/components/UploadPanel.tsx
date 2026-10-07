import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, FileText, Loader2, CheckCircle } from 'lucide-react'
import api from '../api/client'
import { RunResult } from '../pages/Dashboard'

interface Props {
  onRunComplete: (run: RunResult) => void
}

export default function UploadPanel({ onRunComplete }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) { setFile(accepted[0]); setDone(false); setError('') }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
  })

  async function runAudit() {
    if (!file) return
    setRunning(true)
    setError('')
    try {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post<RunResult>('/audit/run', form)
      setDone(true)
      onRunComplete(data)
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Audit failed. Is Ollama running?')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">Upload Control Narrative</h2>
        <p className="text-gray-400 text-sm mt-1">
          Upload a PDF specification document. The 9-phase pipeline will extract entities,
          build a knowledge graph, and run Z3 formal verification against IEC 61511 invariants.
        </p>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-500/10'
            : 'border-gray-700 bg-gray-900 hover:border-gray-500'
        }`}
      >
        <input {...getInputProps()} />
        <UploadCloud className="w-10 h-10 text-gray-500 mx-auto mb-3" />
        {isDragActive ? (
          <p className="text-blue-400">Drop the PDF here…</p>
        ) : (
          <>
            <p className="text-gray-300 font-medium">Drag & drop a PDF here</p>
            <p className="text-gray-500 text-sm mt-1">or click to browse</p>
          </>
        )}
      </div>

      {/* Selected file */}
      {file && (
        <div className="flex items-center gap-3 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3">
          <FileText className="w-5 h-5 text-blue-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate">{file.name}</p>
            <p className="text-gray-500 text-xs">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
          {done && <CheckCircle className="w-5 h-5 text-green-400 shrink-0" />}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Run button */}
      <button
        onClick={runAudit}
        disabled={!file || running}
        className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold flex items-center justify-center gap-2 transition-colors"
      >
        {running ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Running 9-phase pipeline… (may take 1–3 min)
          </>
        ) : (
          'Run Audit'
        )}
      </button>

      {/* Pipeline phases info */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <p className="text-gray-400 text-xs font-medium mb-3">PIPELINE PHASES</p>
        <div className="grid grid-cols-3 gap-2">
          {[
            'PDF Extraction', 'LLM Extraction', 'Entity Linking',
            'Knowledge Graph', 'Rule IR', 'Invariant Coverage',
            'Z3 Verification', 'Audit Report', 'PLC Sketch',
          ].map((phase, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-900 text-blue-300 text-xs flex items-center justify-center font-bold shrink-0">
                {i + 1}
              </span>
              <span className="text-gray-400 text-xs">{phase}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
