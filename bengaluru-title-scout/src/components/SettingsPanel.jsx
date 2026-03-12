import { useState } from 'react'
import axios from 'axios'
import { API_BASE } from '../lib/utils'

export default function SettingsPanel() {
  const [config, setConfig] = useState({
    azure_endpoint:     localStorage.getItem('azure_endpoint')     || '',
    azure_key:          localStorage.getItem('azure_key')          || '',
    openai_api_key:     localStorage.getItem('openai_api_key')     || '',
    anthropic_api_key:  localStorage.getItem('anthropic_api_key')  || '',
    preferred_llm:      localStorage.getItem('preferred_llm')      || 'claude',
    rebuild_kb:         false,
  })
  const [saving, setSaving]     = useState(false)
  const [kbStatus, setKbStatus] = useState(null)
  const [testResult, setTestResult] = useState(null)

  const save = async () => {
    setSaving(true)
    Object.entries(config).forEach(([k, v]) => {
      if (typeof v === 'string') localStorage.setItem(k, v)
    })
    try {
      await axios.post(`${API_BASE}/config`, config)
      setTestResult({ ok: true, msg: 'Configuration saved successfully.' })
    } catch {
      setTestResult({ ok: false, msg: 'Backend not reachable. Config saved locally only.' })
    }
    setSaving(false)
  }

  const rebuildKB = async () => {
    setKbStatus('building')
    try {
      await axios.post(`${API_BASE}/rebuild-knowledge-base`)
      setKbStatus('done')
    } catch {
      setKbStatus('error')
    }
  }

  const testBackend = async () => {
    try {
      const r = await axios.get(`${API_BASE}/health`, { timeout: 3000 })
      setTestResult({ ok: true, msg: `Backend online — ${r.data.message || 'All systems operational'}` })
    } catch {
      setTestResult({ ok: false, msg: 'Backend offline. Run: python backend/main.py' })
    }
  }

  const Field = ({ label, id, type = 'text', placeholder }) => (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</label>
      <input
        type={type}
        value={config[id]}
        onChange={e => setConfig(c => ({ ...c, [id]: e.target.value }))}
        placeholder={placeholder}
        className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary font-mono"
      />
    </div>
  )

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground text-sm mt-1">Configure API keys and knowledge base</p>
        </div>

        {testResult && (
          <div className={`p-3 rounded-lg text-sm border ${testResult.ok ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
            {testResult.msg}
          </div>
        )}

        <section className="glass rounded-xl p-5 border border-border space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Azure AI Document Intelligence (OCR)</h2>
          <Field id="azure_endpoint" label="Endpoint URL" placeholder="https://your-resource.cognitiveservices.azure.com/" />
          <Field id="azure_key"      label="API Key"      type="password" placeholder="••••••••••••••••" />
        </section>

        <section className="glass rounded-xl p-5 border border-border space-y-4">
          <h2 className="text-sm font-semibold text-foreground">LLM Gateway</h2>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Preferred LLM</label>
            <select
              value={config.preferred_llm}
              onChange={e => setConfig(c => ({ ...c, preferred_llm: e.target.value }))}
              className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="claude">Claude 3.7 Sonnet (Anthropic)</option>
              <option value="gpt4o">GPT-4o (OpenAI)</option>
              <option value="auto">Auto (RouteLLM — cost-optimized)</option>
            </select>
          </div>
          <Field id="anthropic_api_key" label="Anthropic API Key" type="password" placeholder="sk-ant-••••••••" />
          <Field id="openai_api_key"    label="OpenAI API Key"    type="password" placeholder="sk-••••••••" />
        </section>

        <section className="glass rounded-xl p-5 border border-border space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Knowledge Base (ChromaDB)</h2>
          <p className="text-xs text-muted-foreground">
            The local vector database contains Karnataka laws: Land Revenue Act 1964, Land Reforms Act 1961,
            PTCL Act, and RERA Karnataka regulations. Rebuild if you add new law documents.
          </p>
          <div className="flex gap-2">
            <button
              onClick={rebuildKB}
              disabled={kbStatus === 'building'}
              className="px-4 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50"
            >
              {kbStatus === 'building' ? '⟳ Building...' : kbStatus === 'done' ? '✓ Rebuilt' : '⟳ Rebuild Knowledge Base'}
            </button>
            {kbStatus === 'error' && <span className="text-red-400 text-xs self-center">Build failed</span>}
          </div>
        </section>

        <div className="flex gap-2">
          <button
            onClick={save}
            disabled={saving}
            className="flex-1 py-2.5 bg-primary text-primary-foreground rounded-xl font-medium text-sm hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
          <button
            onClick={testBackend}
            className="px-4 py-2.5 bg-secondary border border-border rounded-xl text-sm text-foreground hover:bg-secondary/80 transition-colors"
          >
            Test Connection
          </button>
        </div>
      </div>
    </div>
  )
}
