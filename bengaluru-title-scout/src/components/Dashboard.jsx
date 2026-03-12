import { RISK_COLORS } from '../lib/utils'

export default function Dashboard({ caseHistory, onNewCase, onSelectCase }) {
  const stats = {
    total: caseHistory.length,
    low:      caseHistory.filter(c => c.risk_level === 'LOW').length,
    medium:   caseHistory.filter(c => c.risk_level === 'MEDIUM').length,
    high:     caseHistory.filter(c => c.risk_level === 'HIGH').length,
    critical: caseHistory.filter(c => c.risk_level === 'CRITICAL').length,
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Karnataka Land Title Due Diligence Platform
            </p>
          </div>
          <button
            onClick={onNewCase}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <span>+</span> New Analysis
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Cases', value: stats.total, color: 'text-foreground', sub: 'analysed' },
            { label: 'Low Risk',    value: stats.low,   color: 'text-green-400',  sub: 'clear' },
            { label: 'High Risk',   value: stats.high,  color: 'text-red-400',    sub: 'flagged' },
            { label: 'Critical',    value: stats.critical, color: 'text-purple-400', sub: 'blocked' },
          ].map(s => (
            <div key={s.label} className="glass rounded-xl p-4 border border-border">
              <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-xs text-muted-foreground mt-1 uppercase tracking-wide">{s.label}</div>
              <div className="text-xs text-muted-foreground/50">{s.sub}</div>
            </div>
          ))}
        </div>

        {caseHistory.length === 0 ? (
          <EmptyState onNewCase={onNewCase} />
        ) : (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Recent Cases</h2>
            {caseHistory.map((c, i) => (
              <CaseCard key={i} case_={c} onClick={() => onSelectCase(c)} />
            ))}
          </div>
        )}

        <LawReference />
      </div>
    </div>
  )
}

function EmptyState({ onNewCase }) {
  return (
    <div className="border border-dashed border-border rounded-xl p-12 flex flex-col items-center gap-4 text-center">
      <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-3xl">⚖️</div>
      <div>
        <h3 className="text-lg font-semibold text-foreground">No cases yet</h3>
        <p className="text-muted-foreground text-sm mt-1 max-w-sm">
          Upload land documents to begin AI-powered title due diligence against Karnataka state laws
        </p>
      </div>
      <button
        onClick={onNewCase}
        className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
      >
        Upload First Document
      </button>
    </div>
  )
}

function CaseCard({ case_, onClick }) {
  const colors = RISK_COLORS[case_.risk_level] || RISK_COLORS.MEDIUM
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all hover:scale-[1.01] ${colors.bg} ${colors.border} border`}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${colors.badge}`}>
              {case_.risk_level}
            </span>
            <span className="text-sm font-semibold text-foreground truncate">
              {case_.property_details?.survey_number || case_.document_name || 'Unknown Property'}
            </span>
          </div>
          <div className="text-xs text-muted-foreground mt-1 truncate">
            {case_.property_details?.location || 'Bengaluru, Karnataka'} •{' '}
            {case_.flags?.length || 0} issues found •{' '}
            {case_.timestamp ? new Date(case_.timestamp).toLocaleDateString('en-IN') : 'Just now'}
          </div>
        </div>
        <span className="text-muted-foreground text-sm ml-2">→</span>
      </div>
    </button>
  )
}

function LawReference() {
  const acts = [
    { name: 'Karnataka Land Revenue Act, 1964', sections: 'Sec 45, 79, 95, 128', color: 'text-blue-400' },
    { name: 'Karnataka Land Reforms Act, 1961', sections: 'Sec 63, 79A, 79B', color: 'text-amber-400' },
    { name: 'PTCL Act (SC/ST Protection)', sections: 'Sec 4, 5, 7, 8', color: 'text-purple-400' },
    { name: 'RERA Karnataka', sections: 'Reg 3, 4, 11, 14', color: 'text-green-400' },
  ]
  return (
    <div className="glass rounded-xl p-4 border border-border">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
        Active Knowledge Base — Karnataka Laws
      </h3>
      <div className="grid grid-cols-2 gap-2">
        {acts.map(a => (
          <div key={a.name} className="flex items-start gap-2 p-2 rounded-lg bg-secondary/50">
            <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
            <div>
              <div className={`text-xs font-medium ${a.color}`}>{a.name}</div>
              <div className="text-xs text-muted-foreground/60">{a.sections}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
