import React, { useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  Node,
  Edge,
  MarkerType,
  NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { GitBranch, Code } from 'lucide-react';
import { AppMetadata, WorkflowSpec } from '../../../types';

interface WorkflowsPanelProps {
  app: AppMetadata | null;
}

interface StateNodeData {
  state: string;
  doc_status: number;
  style: string;
  allow_edit: string;
  isInitial: boolean;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Custom State Node Component
// ---------------------------------------------------------------------------
const StateNode: React.FC<NodeProps<Node<StateNodeData>>> = ({ data }) => {
  const { state, doc_status, style, allow_edit, isInitial } = data;

  let borderLeftColor = 'border-l-[var(--accent)]';
  if (style === 'Success') borderLeftColor = 'border-l-[var(--ok)]';
  else if (style === 'Warning') borderLeftColor = 'border-l-[var(--warn)]';
  else if (style === 'Danger') borderLeftColor = 'border-l-[var(--err)]';

  const docStatusLabel = doc_status === 0 ? 'Draft' : doc_status === 1 ? 'Submitted' : 'Cancelled';
  let docStatusBadge = 'bg-[var(--muted)]/15 text-[var(--muted)]';
  if (doc_status === 1) docStatusBadge = 'bg-[var(--ok)]/15 text-[var(--ok)]';
  else if (doc_status === 2) docStatusBadge = 'bg-[var(--err)]/15 text-[var(--err)]';

  return (
    <div
      className={`w-[180px] p-2.5 bg-[var(--surface)] border border-[var(--border)] border-l-4 ${borderLeftColor} rounded-card flex flex-col gap-1.5 shadow-sm text-left`}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-[var(--border)]" />

      {/* Header: State Name + Initial Badge + doc_status Badge */}
      <div className="flex items-center justify-between gap-1">
        <span className="font-semibold text-xs text-[var(--text)] truncate" title={state}>
          {state}
        </span>
        <div className="flex items-center gap-1 flex-shrink-0">
          {isInitial && (
            <span className="px-1 py-0.2 bg-[var(--accent)]/15 text-[var(--accent)] text-[9px] font-medium rounded-pill">
              Initial
            </span>
          )}
          <span className={`px-1 py-0.2 rounded-pill text-[9px] font-medium ${docStatusBadge}`}>
            {docStatusLabel}
          </span>
        </div>
      </div>

      {/* Subtitle: allow_edit role */}
      <div className="text-[11px] text-[var(--muted)] truncate" title={`Edit: ${allow_edit || 'None'}`}>
        edit: {allow_edit || 'None'}
      </div>

      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-[var(--border)]" />
    </div>
  );
};

const nodeTypes = {
  stateNode: StateNode,
};

// ---------------------------------------------------------------------------
// Dagre Graph Layout Helper
// ---------------------------------------------------------------------------
const getLayoutedElements = (nodes: Node<StateNodeData>[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 70 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 180, height: 75 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 90,
        y: nodeWithPosition.y - 37.5,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

// ---------------------------------------------------------------------------
// Workflows Panel Component
// ---------------------------------------------------------------------------
export const WorkflowsPanel: React.FC<WorkflowsPanelProps> = ({ app }) => {
  const workflows = app?.workflows ?? [];
  const [selectedWfIdx, setSelectedWfIdx] = useState(0);

  const currentWf: WorkflowSpec | undefined = workflows[selectedWfIdx];

  const { nodes, edges } = useMemo(() => {
    if (!currentWf || !currentWf.states) return { nodes: [], edges: [] };

    // Find initial state (state with 0 incoming transitions)
    const incomingCounts: Record<string, number> = {};
    currentWf.states.forEach((s) => {
      incomingCounts[s.state] = 0;
    });
    (currentWf.transitions || []).forEach((t) => {
      if (incomingCounts[t.next_state] !== undefined) {
        incomingCounts[t.next_state] += 1;
      }
    });

    const initialStates = Object.keys(incomingCounts).filter((s) => incomingCounts[s] === 0);
    const initialName = initialStates.length > 0 ? initialStates[0] : currentWf.states[0]?.state;

    // Generate Nodes
    const rawNodes: Node<StateNodeData>[] = currentWf.states.map((st) => ({
      id: st.state,
      type: 'stateNode',
      data: {
        state: st.state,
        doc_status: st.doc_status,
        style: st.style || '',
        allow_edit: st.allow_edit,
        isInitial: st.state === initialName,
      },
      position: { x: 0, y: 0 },
    }));

    // Generate Edges
    const rawEdges: Edge[] = (currentWf.transitions || []).map((t, idx) => ({
      id: `e-${t.state}-${t.action}-${t.next_state}-${idx}`,
      source: t.state,
      target: t.next_state,
      type: 'smoothstep',
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: 'var(--border)',
        width: 14,
        height: 14,
      },
      style: { stroke: 'var(--border)', strokeWidth: 1.5 },
      label: (
        <div className="flex flex-col items-center bg-[var(--surface)] border border-[var(--border)] px-2 py-0.5 rounded-card text-center shadow-sm select-none">
          <div className="flex items-center gap-1">
            <span className="text-[11px] font-medium text-[var(--text)]">{t.action}</span>
            {t.condition && (
              <span
                className="px-1 py-0.2 bg-[var(--accent)]/15 text-[var(--accent)] text-[9px] font-mono rounded"
                title={`Condition: ${t.condition}`}
              >
                fx
              </span>
            )}
          </div>
          <span className="text-[9px] text-[var(--muted)]">{t.allowed}</span>
        </div>
      ),
    }));

    return getLayoutedElements(rawNodes, rawEdges);
  }, [currentWf]);

  if (workflows.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted">
        <GitBranch className="w-8 h-8 mb-2 text-[var(--muted)]/40" strokeWidth={1.5} />
        <p className="text-sm font-medium text-[var(--muted)]">
          No workflows defined yet. Workflows appear when a DocType has a lifecycle or approval process.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[var(--bg)] overflow-hidden">
      {/* Workflow Header & Selector Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[var(--surface)] border-b border-[var(--border)] overflow-x-auto">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-[var(--text)]">{currentWf.name}</span>
          <span className="text-[11px] text-[var(--muted)]">({currentWf.document_type})</span>
        </div>
        {workflows.length > 1 && (
          <div className="flex items-center gap-1">
            {workflows.map((wf, idx) => (
              <button
                key={wf.name}
                onClick={() => setSelectedWfIdx(idx)}
                className={`px-2.5 py-1 rounded-card text-xs font-medium transition-colors whitespace-nowrap ${
                  selectedWfIdx === idx
                    ? 'bg-[var(--accent)] text-white'
                    : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)]'
                }`}
              >
                {wf.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* DAG Graph Canvas */}
      <div className="flex-1 w-full h-full relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.2}
          maxZoom={1.5}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="var(--border)" gap={16} size={1} />
          <Controls showInteractive={false} className="!bg-[var(--surface)] !border-[var(--border)] !fill-[var(--text)]" />
        </ReactFlow>
      </div>
    </div>
  );
};
