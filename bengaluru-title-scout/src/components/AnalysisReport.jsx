import { useState } from 'react'
import ChainOfOwnership from './ChainOfOwnership'
import RiskBadge from './RiskBadge'
import { RISK_COLORS, formatDate, API_BASE } from '../lib/utils'
import axios from 'axios'

export default function AnalysisReport({ result, onNewCase }) {
  const [activeTab, setActiveTab] = useState('summary')
  const [downloading, setDownloading] = useState(false)

  const colors = RISK_COLORS[result.risk_level] || RISK_COLORS.MEDIUM

  const handleDownloadPDF = async () => {
    setDownloading(true)
    try {
      const response = await axios.post(
        `${API_BASE}/generate-report`,
        { analysis: result },
        { responseType: 'blob', timeout: 60000 }
      )
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `title-report-${result.property_details?.survey_number || 'property'}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      alert('PDF generation failed. Check backend.')
    } finally {
      setDownloading(false)
    }
  }

  const tabs = [
    { id: 'summary',   label: 'Summary' },
    { id: 'chain',     label: 'Ownership Chain' },
    { id: 'flags',     label: `Flags (${result.flags?.length || 0})` },
    { id: 'legal',     label: 'Legal Analysis' },
    { id: 'raw',       label: 'Extracted Data' },
  ]

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className={`shrink-0 p-5 border-b border-border ${colors.bg}`}>
        <div className="flex items-start justify-between max-w-5xl mx-auto">
          <div className="flex items-start gap-4">
            <RiskBadge level={result.risk_level} size="lg" />
            <div>
              <h1 className="text-xl font-bold text-foreground">
                {result.property_details?.survey_number
                  ? `Survey No. ${result.property_details.survey_number}`
                  : result.document_name || 'Property Analysis'}
              </h1>
              <div className="text-sm text-muted-foreground mt-0.5">
                {result.property_details?.location || 'Bengaluru, Karnataka'} •{' '}
                {result.property_details?.extent || 'N/A'} •{' '}
                {result.document_type_detected || result.doc_type || 'Mixed Documents'}
              </div>
              <div className="text-xs text-muted-foreground/60 mt-0.5">
                Analysed: {result.timestamp ? new Date(result.timestamp).toLocaleString('en-IN') : 'Just now'}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleDownloadPDF}
              disabled={downloading}
              className="px-4 py-2 bg-primary/20 text-primary border border-primary/30 rounded-lg text-sm font-medium hover:bg-primary/30 transition-colors disabled:opacity-50"
            >
              {downloading ? 'Generating...' : '⬇ Download PDF'}
            </button>
            <button
              onClick={onNewCase}
              className="px-4 py-2 bg-secondary text-foreground border border-border rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors"
            >
              + New Case
            </button>
          </div>
        </div>

        <div className="flex gap-1 mt-4 max-w-5xl mx-auto">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                ${activeTab === t.id
                  ? 'bg-primary/20 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary'}`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        <div className="max-w-5xl mx-auto">
          {activeTab === 'summary'  && <SummaryTab result={result} />}
          {activeTab === 'chain'    && <ChainOfOwnership chain={result.ownership_chain} />}
          {activeTab === 'flags'    && <FlagsTab flags={result.flags} />}
          {activeTab === 'legal'    && <LegalTab legal={result.legal_analysis} />}
          {activeTab === 'raw'      && <RawDataTab data={result.extracted_data} />}
        </div>
      </div>
    </div>
  )
}

function SummaryTab({ result }) {
  const colors = RISK_COLORS[result.risk_level] || RISK_COLORS.MEDIUM
  return (
    <div className="space-y-5">
      <div className={`p-5 rounded-xl border ${colors.bg} ${colors.border}`}>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          AI Assessment
        </h2>
        <p className="text-foreground leading-relaxed">{result.summary || 'No summary available.'}</p>
        <div className="mt-4 grid grid-cols-3 gap-3">
          <ScoreCard label="Title Clarity" score={result.scores?.title_clarity} />
          <ScoreCard label="Chain Continuity" score={result.scores?.chain_continuity} />
          <ScoreCard label="Legal Compliance" score={result.scores?.legal_compliance} />
        </div>
      </div>

      {result.property_details && (
        <div className="glass rounded-xl p-4 border border-border">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Property Details
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(result.property_details).map(([k, v]) => v && (
              <div key={k}>
                <div className="text-xs text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</div>
                <div className="text-sm text-foreground font-medium">{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.recommendations?.length > 0 && (
        <div className="glass rounded-xl p-4 border border-border">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Recommendations
          </h2>
          <ul className="space-y-2">
            {result.recommendations.map((rec, i) => (
              <li key={i} className="flex gap-2 text-sm text-foreground">
                <span className="text-primary shrink-0 mt-0.5">→</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function ScoreCard({ label, score }) {
  const pct = score != null ? score : 0
  const color = pct >= 75 ? 'text-green-400' : pct >= 50 ? 'text-amber-400' : 'text-red-400'
  return (
    <div className="bg-secondary/50 rounded-lg p-3">
      <div className={`text-2xl font-bold ${color}`}>{pct}<span className="text-sm">/100</span></div>
      <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
    </div>
  )
}

function FlagsTab({ flags }) {
  if (!flags?.length) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <div className="text-4xl mb-3">✅</div>
        <div className="font-medium text-foreground">No flags raised</div>
        <div className="text-sm">The document passed all Karnataka legal checks</div>
      </div>
    )
  }
  const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }
  const sorted = [...flags].sort((a, b) => (severityOrder[a.severity] ?? 4) - (severityOrder[b.severity] ?? 4))

  return (
    <div className="space-y-3">
      {sorted.map((flag, i) => {
        const colors = RISK_COLORS[flag.severity] || RISK_COLORS.MEDIUM
        return (
          <div key={i} className={`p-4 rounded-xl border ${colors.bg} ${colors.border}`}>
            <div className="flex items-start gap-3">
              <RiskBadge level={flag.severity} size="sm" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-foreground">{flag.title}</div>
                <div className="text-sm text-muted-foreground mt-1">{flag.description}</div>
                {flag.law_reference && (
                  <div className="text-xs text-primary mt-2 font-mono bg-primary/5 px-2 py-1 rounded inline-block">
                    {flag.law_reference}
                  </div>
                )}
                {flag.recommendation && (
                  <div className="text-xs text-muted-foreground mt-2">
                    <span className="text-foreground font-medium">Action: </span>{flag.recommendation}
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function LegalTab({ legal }) {
  if (!legal) return <div className="text-muted-foreground text-sm py-8 text-center">No legal analysis available.</div>

  const sections = [
    { key: 'ptcl_analysis',          label: 'PTCL Act Analysis (SC/ST Grant Land)',      icon: '🛡️' },
    { key: 'land_reforms_analysis',   label: 'Karnataka Land Reforms Act, 1961',           icon: '⚖️' },
    { key: 'land_revenue_analysis',   label: 'Karnataka Land Revenue Act, 1964',           icon: '📋' },
    { key: 'rera_analysis',           label: 'RERA Karnataka Compliance',                  icon: '🏢' },
    { key: 'dc_conversion_analysis',  label: 'DC Conversion & Zoning',                    icon: '🗺️' },
    { key: 'encumbrance_analysis',    label: 'Encumbrance & Liabilities',                  icon: '🔗' },
  ]

  return (
    <div className="space-y-4">
      {sections.map(s => {
        const content = legal[s.key]
        if (!content) return null
        return (
          <div key={s.key} className="glass rounded-xl p-4 border border-border">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-2">
              <span>{s.icon}</span>{s.label}
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{content}</p>
          </div>
        )
      })}
    </div>
  )
}

function RawDataTab({ data }) {
  if (!data) return <div className="text-muted-foreground text-sm py-8 text-center">No extracted data.</div>
  return (
    <pre className="text-xs text-muted-foreground bg-secondary rounded-xl p-4 overflow-auto font-mono leading-relaxed whitespace-pre-wrap">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}
