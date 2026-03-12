import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { API_BASE, formatFileSize } from '../lib/utils'

const STAGE_LABELS = [
  { key: 'ocr',      label: 'OCR Extraction',        sub: 'Azure AI Document Intelligence' },
  { key: 'parse',    label: 'Document Parsing',       sub: 'Identifying document type & fields' },
  { key: 'rag',      label: 'Legal RAG Lookup',       sub: 'Querying Karnataka law knowledge base' },
  { key: 'analyze',  label: 'AI Title Analysis',      sub: 'Claude / GPT-4o deep analysis' },
  { key: 'report',   label: 'Report Generation',      sub: 'Building chain of ownership & risk report' },
]

export default function DocumentUpload({ onAnalysisStart, onAnalysisComplete, isAnalyzing }) {
  const [files, setFiles] = useState([])
  const [stage, setStage]   = useState(null)
  const [stageIdx, setStageIdx] = useState(-1)
  const [error, setError]   = useState(null)
  const [docType, setDocType] = useState('auto')
  const [additionalContext, setAdditionalContext] = useState('')

  const onDrop = useCallback((accepted) => {
    setFiles(prev => [...prev, ...accepted].slice(0, 10))
    setError(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/tiff': ['.tiff', '.tif'],
    },
    maxSize: 50 * 1024 * 1024,
    disabled: isAnalyzing,
  })

  const removeFile = (idx) => setFiles(prev => prev.filter((_, i) => i !== idx))

  const handleAnalyze = async () => {
    if (files.length === 0) return
    setError(null)
    onAnalysisStart()
    setStageIdx(0)

    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    formData.append('doc_type', docType)
    formData.append('additional_context', additionalContext)

    try {
      const stageInterval = setInterval(() => {
        setStageIdx(prev => {
          if (prev < STAGE_LABELS.length - 1) return prev + 1
          clearInterval(stageInterval)
          return prev
        })
      }, 3500)

      const response = await axios.post(`${API_BASE}/analyze`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000,
      })

      clearInterval(stageInterval)
      setStageIdx(STAGE_LABELS.length)
      onAnalysisComplete({ ...response.data, document_name: files[0].name, timestamp: new Date().toISOString() })
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Analysis failed. Is the backend running?')
      setStageIdx(-1)
      onAnalysisStart()
    }
  }

  if (isAnalyzing) {
    return <AnalysisProgress stageIdx={stageIdx} />
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">New Title Analysis</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Upload RTC, EC, Sale Deed, Mutation Register, or any Karnataka land document
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center gap-4 cursor-pointer transition-all
            ${isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-secondary/30'}`}
        >
          <input {...getInputProps()} />
          <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center text-2xl">📄</div>
          <div className="text-center">
            <p className="text-foreground font-medium">
              {isDragActive ? 'Drop files here' : 'Drag & drop or click to upload'}
            </p>
            <p className="text-muted-foreground text-sm mt-1">
              PDF, JPG, PNG, TIFF — up to 50MB each, up to 10 files
            </p>
            <p className="text-muted-foreground/60 text-xs mt-1">
              Supports Kannada + English mixed documents
            </p>
          </div>
        </div>

        {files.length > 0 && (
          <div className="space-y-2">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-secondary border border-border">
                <span className="text-lg">{f.type === 'application/pdf' ? '📑' : '🖼️'}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground truncate">{f.name}</div>
                  <div className="text-xs text-muted-foreground">{formatFileSize(f.size)}</div>
                </div>
                <button
                  onClick={() => removeFile(i)}
                  className="text-muted-foreground hover:text-red-400 transition-colors text-sm"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Document Type
            </label>
            <select
              value={docType}
              onChange={e => setDocType(e.target.value)}
              className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="auto">Auto-detect</option>
              <option value="rtc">RTC / Pahani (Form 11/12)</option>
              <option value="ec">Encumbrance Certificate</option>
              <option value="sale_deed">Sale Deed</option>
              <option value="mutation">Mutation Register</option>
              <option value="khatha">Khatha Certificate / Extract</option>
              <option value="sketch">Village Map / Survey Sketch</option>
              <option value="conversion">DC Conversion Order</option>
              <option value="ptcl">Grant Land / PTCL Document</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Additional Context (optional)
            </label>
            <input
              type="text"
              value={additionalContext}
              onChange={e => setAdditionalContext(e.target.value)}
              placeholder="e.g. SC/ST land, Grant Land, commercial use..."
              className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        <div className="glass rounded-xl p-4 border border-border">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            What the AI will check
          </h3>
          <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
            {[
              '30-year ownership chain continuity',
              'PTCL Act — SC/ST grant land restrictions',
              'Karnataka Land Reforms Act Sec 79A/79B',
              'Encumbrance / mortgage / court orders',
              'DC Conversion status & validity',
              'Survey number discrepancies',
              'Mutation register gaps',
              'RERA compliance for apartments',
            ].map(item => (
              <div key={item} className="flex items-center gap-1.5">
                <span className="text-primary">✓</span>
                {item}
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={files.length === 0}
          className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-semibold text-sm hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {files.length === 0 ? 'Upload documents to continue' : `Analyze ${files.length} document${files.length > 1 ? 's' : ''}`}
        </button>
      </div>
    </div>
  )
}

function AnalysisProgress({ stageIdx }) {
  return (
    <div className="h-full flex flex-col items-center justify-center p-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-primary/10 border-2 border-primary/30 flex items-center justify-center text-2xl mx-auto mb-4 animate-pulse-slow">
            ⚖️
          </div>
          <h2 className="text-xl font-bold text-foreground">Analysing Document</h2>
          <p className="text-muted-foreground text-sm mt-1">
            Running Karnataka legal due diligence checks...
          </p>
        </div>

        <div className="space-y-3">
          {STAGE_LABELS.map((s, i) => {
            const done    = i < stageIdx
            const active  = i === stageIdx
            const pending = i > stageIdx
            return (
              <div
                key={s.key}
                className={`flex items-center gap-3 p-3 rounded-lg transition-all border
                  ${done    ? 'bg-green-500/5 border-green-500/20' :
                    active  ? 'bg-primary/10 border-primary/30' :
                              'bg-secondary/30 border-border/50 opacity-40'}`}
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0
                  ${done   ? 'bg-green-500/20 text-green-400' :
                    active ? 'bg-primary/20 text-primary animate-pulse' :
                             'bg-muted text-muted-foreground'}`}
                >
                  {done ? '✓' : active ? '◎' : String(i + 1)}
                </div>
                <div>
                  <div className={`text-sm font-medium ${done ? 'text-green-400' : active ? 'text-primary' : 'text-muted-foreground'}`}>
                    {s.label}
                  </div>
                  {active && <div className="text-xs text-muted-foreground">{s.sub}</div>}
                </div>
              </div>
            )
          })}
        </div>

        <div className="w-full bg-secondary rounded-full h-1.5">
          <div
            className="bg-primary h-1.5 rounded-full transition-all duration-700"
            style={{ width: `${Math.max(5, (stageIdx / STAGE_LABELS.length) * 100)}%` }}
          />
        </div>
      </div>
    </div>
  )
}
