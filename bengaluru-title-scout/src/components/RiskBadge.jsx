import { RISK_COLORS } from '../lib/utils'

const RISK_LABELS = {
  LOW:      'Low Risk',
  MEDIUM:   'Medium Risk',
  HIGH:     'High Risk',
  CRITICAL: 'Critical',
}

const RISK_ICONS = {
  LOW:      '✅',
  MEDIUM:   '⚠️',
  HIGH:     '🚨',
  CRITICAL: '🔴',
}

export default function RiskBadge({ level, size = 'md' }) {
  const colors = RISK_COLORS[level] || RISK_COLORS.MEDIUM
  const label  = RISK_LABELS[level] || level
  const icon   = RISK_ICONS[level]  || '❓'

  if (size === 'lg') {
    return (
      <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border font-bold ${colors.bg} ${colors.border} ${colors.text}`}>
        <span className="text-xl">{icon}</span>
        <div>
          <div className="text-xs font-medium uppercase tracking-widest opacity-70">Risk Level</div>
          <div className="text-lg leading-tight">{label}</div>
        </div>
      </div>
    )
  }

  if (size === 'sm') {
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${colors.badge}`}>
        {icon} {level}
      </span>
    )
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold border ${colors.badge} ${colors.border}`}>
      {icon} {label}
    </span>
  )
}
