import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useMemo } from 'react'

function OwnerNode({ data }) {
  const typeColors = {
    individual:  'border-blue-500/50 bg-blue-500/10',
    company:     'border-amber-500/50 bg-amber-500/10',
    government:  'border-purple-500/50 bg-purple-500/10',
    current:     'border-green-500/60 bg-green-500/15',
    unknown:     'border-red-500/50 bg-red-500/10',
  }
  const color = typeColors[data.ownerType] || typeColors.individual

  return (
    <div className={`px-3 py-2 rounded-xl border text-xs w-44 ${color}`}>
      <div className="font-semibold text-foreground truncate">{data.name}</div>
      {data.period  && <div className="text-muted-foreground mt-0.5">{data.period}</div>}
      {data.docType && <div className="text-muted-foreground/60 font-mono text-[10px]">{data.docType}</div>}
      {data.flag    && (
        <div className="mt-1 text-[10px] text-red-400 bg-red-500/10 rounded px-1 py-0.5">
          ⚠ {data.flag}
        </div>
      )}
    </div>
  )
}

const nodeTypes = { ownerNode: OwnerNode }

export default function ChainOfOwnership({ chain }) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!chain?.length) return { nodes: [], edges: [] }

    const nodes = chain.map((entry, i) => ({
      id:       String(i),
      type:     'ownerNode',
      position: { x: 220 * (i % 4), y: Math.floor(i / 4) * 130 },
      data: {
        name:      entry.owner_name || 'Unknown',
        period:    entry.period || (entry.from_date ? `${entry.from_date} → ${entry.to_date || 'present'}` : null),
        docType:   entry.document_type,
        ownerType: entry.owner_type || (i === chain.length - 1 ? 'current' : 'individual'),
        flag:      entry.flag,
      },
    }))

    const edges = chain.slice(0, -1).map((_, i) => ({
      id:           `e${i}-${i + 1}`,
      source:       String(i),
      target:       String(i + 1),
      animated:     i === chain.length - 2,
      style:        { stroke: '#3b82f6', strokeWidth: 1.5 },
      label:        chain[i + 1]?.transfer_type || '',
      labelStyle:   { fill: '#94a3b8', fontSize: 10 },
      labelBgStyle: { fill: '#0f172a' },
    }))

    return { nodes, edges }
  }, [chain])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  if (!chain?.length) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground gap-3">
        <div className="text-4xl">🔗</div>
        <div className="text-sm">No ownership chain data extracted</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="glass rounded-xl p-3 border border-border">
        <div className="flex gap-4 text-xs text-muted-foreground flex-wrap">
          {[
            { color: 'bg-blue-500/40',   label: 'Individual Owner' },
            { color: 'bg-amber-500/40',  label: 'Company / Trust' },
            { color: 'bg-purple-500/40', label: 'Government / Inam' },
            { color: 'bg-green-500/40',  label: 'Current Owner' },
            { color: 'bg-red-500/40',    label: 'Unknown / Gap' },
          ].map(l => (
            <div key={l.label} className="flex items-center gap-1.5">
              <div className={`w-2.5 h-2.5 rounded-full ${l.color}`} />
              {l.label}
            </div>
          ))}
        </div>
      </div>

      <div className="h-96 rounded-xl border border-border overflow-hidden bg-[#0a1628]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.3}
          maxZoom={2}
        >
          <Background color="#1e293b" gap={20} />
          <Controls className="!bg-card !border-border" />
          <MiniMap
            nodeColor={(n) => {
              const t = n.data?.ownerType
              return t === 'current' ? '#22c55e' : t === 'unknown' ? '#ef4444' : '#3b82f6'
            }}
            className="!bg-card !border-border"
          />
        </ReactFlow>
      </div>

      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Chain Details ({chain.length} entries)
        </h3>
        {chain.map((entry, i) => (
          <div key={i} className="flex gap-3 items-start p-3 rounded-lg bg-secondary border border-border text-sm">
            <div className="w-6 h-6 rounded-full bg-primary/20 text-primary text-xs flex items-center justify-center shrink-0 mt-0.5">
              {i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-foreground">{entry.owner_name || 'Unknown'}</div>
              <div className="text-xs text-muted-foreground">
                {entry.document_type && <span className="mr-2 font-mono">{entry.document_type}</span>}
                {entry.period || (entry.from_date ? `${entry.from_date} → ${entry.to_date || 'present'}` : '')}
                {entry.document_number && <span className="ml-2 text-muted-foreground/60">Doc #{entry.document_number}</span>}
              </div>
              {entry.flag && (
                <div className="text-xs text-red-400 mt-1">⚠ {entry.flag}</div>
              )}
            </div>
            {i < chain.length - 1 && (
              <div className="text-xs text-muted-foreground/40 shrink-0">
                {entry.transfer_type || '→'}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
