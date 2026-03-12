export default function TitleBar() {
  const isElectron = !!window.electronAPI

  return (
    <div className="h-9 flex items-center justify-between px-4 bg-card border-b border-border title-bar-drag select-none shrink-0">
      <div className="flex items-center gap-2 title-bar-no-drag">
        <div className="w-3 h-3 rounded-full bg-primary/60" />
        <span className="text-xs font-semibold text-muted-foreground tracking-widest uppercase">
          Bengaluru Title Scout
        </span>
        <span className="text-xs text-muted-foreground/40 ml-1">v1.0</span>
      </div>
      <div className="text-xs text-muted-foreground/40 hidden md:block">
        Karnataka Land Due Diligence Platform
      </div>
      {isElectron && (
        <div className="flex items-center gap-1 title-bar-no-drag">
          <button
            onClick={() => window.electronAPI.minimizeWindow()}
            className="w-6 h-6 rounded flex items-center justify-center text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors text-xs"
          >
            −
          </button>
          <button
            onClick={() => window.electronAPI.maximizeWindow()}
            className="w-6 h-6 rounded flex items-center justify-center text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors text-xs"
          >
            □
          </button>
          <button
            onClick={() => window.electronAPI.closeWindow()}
            className="w-6 h-6 rounded flex items-center justify-center text-muted-foreground hover:bg-red-500/20 hover:text-red-400 transition-colors text-xs"
          >
            ×
          </button>
        </div>
      )}
    </div>
  )
}
