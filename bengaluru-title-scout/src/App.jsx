import { useState, useCallback } from 'react'
import TitleBar from './components/TitleBar'
import Dashboard from './components/Dashboard'
import DocumentUpload from './components/DocumentUpload'
import AnalysisReport from './components/AnalysisReport'
import SettingsPanel from './components/SettingsPanel'
import { Toaster } from './components/ui/toaster'

export default function App() {
  const [activeView, setActiveView] = useState('dashboard')
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [caseHistory, setCaseHistory] = useState([])

  const handleAnalysisComplete = useCallback((result) => {
    setAnalysisResult(result)
    setCaseHistory(prev => [result, ...prev].slice(0, 20))
    setActiveView('report')
    setIsAnalyzing(false)
  }, [])

  const handleNewCase = useCallback(() => {
    setAnalysisResult(null)
    setActiveView('upload')
  }, [])

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      <TitleBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          activeView={activeView}
          setActiveView={setActiveView}
          caseHistory={caseHistory}
          hasResult={!!analysisResult}
        />
        <main className="flex-1 overflow-hidden">
          {activeView === 'dashboard' && (
            <Dashboard
              caseHistory={caseHistory}
              onNewCase={handleNewCase}
              onSelectCase={(r) => { setAnalysisResult(r); setActiveView('report') }}
            />
          )}
          {activeView === 'upload' && (
            <DocumentUpload
              onAnalysisStart={() => setIsAnalyzing(true)}
              onAnalysisComplete={handleAnalysisComplete}
              isAnalyzing={isAnalyzing}
            />
          )}
          {activeView === 'report' && analysisResult && (
            <AnalysisReport result={analysisResult} onNewCase={handleNewCase} />
          )}
          {activeView === 'settings' && <SettingsPanel />}
        </main>
      </div>
      <Toaster />
    </div>
  )
}

function Sidebar({ activeView, setActiveView, caseHistory, hasResult }) {
  const navItems = [
    { id: 'dashboard', icon: '⊞', label: 'Dashboard' },
    { id: 'upload',    icon: '↑', label: 'New Analysis' },
    { id: 'report',    icon: '◈', label: 'Report',   disabled: !hasResult },
    { id: 'settings',  icon: '⚙', label: 'Settings' },
  ]

  return (
    <aside className="w-16 flex flex-col items-center py-4 gap-2 border-r border-border bg-card">
      <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center mb-4">
        <span className="text-primary text-xs font-bold">BTS</span>
      </div>
      {navItems.map(item => (
        <button
          key={item.id}
          disabled={item.disabled}
          onClick={() => !item.disabled && setActiveView(item.id)}
          title={item.label}
          className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg transition-all
            ${activeView === item.id
              ? 'bg-primary/20 text-primary'
              : item.disabled
                ? 'text-muted-foreground/30 cursor-not-allowed'
                : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
            }`}
        >
          {item.icon}
        </button>
      ))}
      <div className="mt-auto text-muted-foreground/50 text-xs">
        {caseHistory.length > 0 && (
          <span className="w-5 h-5 rounded-full bg-primary/20 text-primary text-xs flex items-center justify-center">
            {caseHistory.length}
          </span>
        )}
      </div>
    </aside>
  )
}
