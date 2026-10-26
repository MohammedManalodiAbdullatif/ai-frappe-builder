import React, { useState, useMemo, useCallback, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  Node,
  Edge,
  Connection,
  MarkerType,
  NodeProps,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
  addEdge,
  reconnectEdge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import {
  Layers,
  Link as LinkIcon,
  Table as TableIcon,
  Plus,
  RefreshCw,
  Trash2,
  X,
  Info,
} from 'lucide-react';
import { AppMetadata, DocTypeSpec, FieldSpec } from '../../../types';

interface ErdPanelProps {
  app: AppMetadata | null;
  onUpdateApp?: (app: AppMetadata) => void;
}

interface DocTypeNodeData {
  doctype: DocTypeSpec;
  fieldCount: number;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Custom DocType Node Component with Multi-direction Drag Handles
// ---------------------------------------------------------------------------
const DocTypeNode: React.FC<NodeProps<Node<DocTypeNodeData>>> = ({ data }) => {
  const dt = data.doctype;

  return (
    <div className="w-[240px] bg-[var(--surface)] border border-[var(--border)] rounded-card shadow-sm text-left overflow-hidden select-none hover:border-[var(--accent)] transition-colors">
      {/* Handles on 4 sides for seamless multi-directional connecting */}
      <Handle
        type="target"
        id="t-target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !bg-[var(--accent)] !border-2 !border-[var(--surface)] hover:!scale-125 transition-transform"
      />
      <Handle
        type="source"
        id="b-source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !bg-[var(--accent)] !border-2 !border-[var(--surface)] hover:!scale-125 transition-transform"
      />
      <Handle
        type="target"
        id="l-target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-[var(--accent)] !border-2 !border-[var(--surface)] hover:!scale-125 transition-transform"
      />
      <Handle
        type="source"
        id="r-source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-[var(--accent)] !border-2 !border-[var(--surface)] hover:!scale-125 transition-transform"
      />

      {/* Card Header */}
      <div className="p-2.5 bg-[var(--bg)] border-b border-[var(--border)] flex items-center justify-between gap-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <Layers className="w-3.5 h-3.5 text-[var(--accent)] flex-shrink-0" />
          <span className="font-semibold text-xs text-[var(--text)] truncate" title={dt.name}>
            {dt.name}
          </span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {dt.istable && (
            <span className="px-1.5 py-0.2 rounded-pill bg-[var(--warn)]/15 text-[var(--warn)] text-[9px] font-medium">
              Child
            </span>
          )}
          {dt.is_submittable && (
            <span className="px-1.5 py-0.2 rounded-pill bg-[var(--accent)]/15 text-[var(--accent)] text-[9px] font-medium">
              Submittable
            </span>
          )}
        </div>
      </div>

      {/* Fields List */}
      <div className="p-2 flex flex-col gap-1 max-h-[140px] overflow-y-auto">
        {dt.fields.slice(0, 5).map((f) => (
          <div
            key={f.fieldname}
            className="flex items-center justify-between gap-1 text-[11px] text-[var(--text)] py-0.5 border-b border-[var(--border)]/40 last:border-0"
          >
            <div className="flex items-center gap-1 min-w-0 truncate">
              {f.fieldtype === 'Link' ? (
                <LinkIcon className="w-3 h-3 text-[var(--accent)] flex-shrink-0" />
              ) : f.fieldtype === 'Table' ? (
                <TableIcon className="w-3 h-3 text-[var(--warn)] flex-shrink-0" />
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--muted)] flex-shrink-0" />
              )}
              <span className="truncate font-medium">{f.label || f.fieldname}</span>
            </div>
            <span className="text-[9px] text-[var(--muted)] font-mono flex-shrink-0">
              {f.fieldtype === 'Link' && f.options ? `-> ${f.options}` : f.fieldtype}
            </span>
          </div>
        ))}
        {dt.fields.length > 5 && (
          <div className="text-[10px] text-[var(--muted)] pt-0.5 text-center">
            +{dt.fields.length - 5} more fields
          </div>
        )}
      </div>
    </div>
  );
};

const nodeTypes = {
  doctypeNode: DocTypeNode,
};

// ---------------------------------------------------------------------------
// Dagre Graph Layout Helper for ERD
// ---------------------------------------------------------------------------
const getLayoutedElements = (nodes: Node<DocTypeNodeData>[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'LR', nodesep: 60, ranksep: 90 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 240, height: 160 });
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
        x: nodeWithPosition.x - 120,
        y: nodeWithPosition.y - 80,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

// ---------------------------------------------------------------------------
// ERD Interactive Canvas Panel
// ---------------------------------------------------------------------------
export const ErdPanel: React.FC<ErdPanelProps> = ({ app, onUpdateApp }) => {
  const doctypes = app?.doctypes ?? [];

  const [nodes, setNodes] = useState<Node<DocTypeNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newDocTypeName, setNewDocTypeName] = useState('');
  const [newIsTable, setNewIsTable] = useState(false);

  // Build initial graph from DocTypes
  useEffect(() => {
    if (!doctypes || doctypes.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const rawNodes: Node<DocTypeNodeData>[] = doctypes.map((dt) => ({
      id: dt.name,
      type: 'doctypeNode',
      data: { doctype: dt, fieldCount: dt.fields.length },
      position: { x: 0, y: 0 },
    }));

    const rawEdges: Edge[] = [];
    doctypes.forEach((sourceDt) => {
      sourceDt.fields.forEach((field) => {
        if ((field.fieldtype === 'Link' || field.fieldtype === 'Table') && field.options) {
          const targetExists = doctypes.some((d) => d.name === field.options);
          if (targetExists) {
            const isChild = field.fieldtype === 'Table';
            rawEdges.push({
              id: `edge-${sourceDt.name}-${field.options}-${field.fieldname}`,
              source: sourceDt.name,
              target: field.options,
              sourceHandle: 'r-source',
              targetHandle: 'l-target',
              label: `${isChild ? '📋 Table' : '🔗 Link'}: ${field.fieldname}`,
              reconnectable: true,
              deletable: true,
              data: {
                fieldname: field.fieldname,
                fieldtype: field.fieldtype,
                label: field.label,
              },
              style: {
                stroke: isChild ? 'var(--warn, #f59e0b)' : 'var(--accent, #2490ef)',
                strokeWidth: 2,
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: isChild ? 'var(--warn, #f59e0b)' : 'var(--accent, #2490ef)',
              },
            });
          }
        }
      });
    });

    const layouted = getLayoutedElements(rawNodes, rawEdges);
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
  }, [app]);

  // Handle node dragging & position changes
  const onNodesChange = useCallback(
    (changes: NodeChange[]) =>
      setNodes((nds) => applyNodeChanges(changes, nds) as Node<DocTypeNodeData>[]),
    []
  );

  // Handle edge selection & deletion changes
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  // Apply auto-layout
  const handleAutoLayout = useCallback(() => {
    const layouted = getLayoutedElements(nodes, edges);
    setNodes([...layouted.nodes]);
    setEdges([...layouted.edges]);
  }, [nodes, edges]);

  // Drag-and-connect: create a new relationship between DocTypes
  const onConnect = useCallback(
    (params: Connection) => {
      if (!app || !onUpdateApp || !params.source || !params.target) return;
      if (params.source === params.target) return;

      const sourceDt = app.doctypes.find((d) => d.name === params.source);
      const targetDt = app.doctypes.find((d) => d.name === params.target);
      if (!sourceDt || !targetDt) return;

      const isChild = Boolean(targetDt.istable);
      const slugBase = targetDt.name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
      const fieldname = isChild ? `${slugBase}_items` : slugBase;

      // Check if source already has this field
      if (sourceDt.fields.some((f) => f.fieldname === fieldname)) {
        return;
      }

      const newField: FieldSpec = {
        fieldname,
        label: targetDt.name,
        fieldtype: isChild ? 'Table' : 'Link',
        options: targetDt.name,
        reqd: false,
        in_list_view: !isChild,
      };

      const updatedDoctypes = app.doctypes.map((d) => {
        if (d.name === sourceDt.name) {
          return {
            ...d,
            fields: [...d.fields, newField],
          };
        }
        return d;
      });

      const updatedApp: AppMetadata = {
        ...app,
        doctypes: updatedDoctypes,
      };

      onUpdateApp(updatedApp);
    },
    [app, onUpdateApp]
  );

  // Drag-to-reconnect: re-target an existing relationship to a different DocType
  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      if (!app || !onUpdateApp || !newConnection.target || !newConnection.source) return;

      const fieldname = (oldEdge.data as any)?.fieldname;
      const sourceName = newConnection.source;
      const targetName = newConnection.target;

      const targetDt = app.doctypes.find((d) => d.name === targetName);
      if (!targetDt) return;

      const updatedDoctypes = app.doctypes.map((d) => {
        if (d.name === sourceName) {
          const updatedFields = d.fields.map((f) => {
            if (f.fieldname === fieldname || f.options === oldEdge.target) {
              const isChild = Boolean(targetDt.istable);
              return {
                ...f,
                options: targetName,
                fieldtype: isChild ? 'Table' : 'Link',
                label: targetDt.name,
              };
            }
            return f;
          });
          return { ...d, fields: updatedFields };
        }
        return d;
      });

      const updatedApp: AppMetadata = {
        ...app,
        doctypes: updatedDoctypes,
      };

      setEdges((eds) => reconnectEdge(oldEdge, newConnection, eds));
      onUpdateApp(updatedApp);
    },
    [app, onUpdateApp]
  );

  // Delete relationship when edge is removed
  const onEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      if (!app || !onUpdateApp) return;

      let updatedDoctypes = [...app.doctypes];

      deletedEdges.forEach((edge) => {
        const fieldname = (edge.data as any)?.fieldname;
        updatedDoctypes = updatedDoctypes.map((d) => {
          if (d.name === edge.source) {
            return {
              ...d,
              fields: d.fields.filter(
                (f) => !(f.fieldname === fieldname || (f.options === edge.target && (f.fieldtype === 'Link' || f.fieldtype === 'Table')))
              ),
            };
          }
          return d;
        });
      });

      const updatedApp: AppMetadata = {
        ...app,
        doctypes: updatedDoctypes,
      };

      onUpdateApp(updatedApp);
    },
    [app, onUpdateApp]
  );

  // Add DocType handler
  const handleAddDocType = useCallback(() => {
    if (!onUpdateApp || !newDocTypeName.trim()) return;

    const currentApp: AppMetadata = app || {
      app_name: 'custom_app',
      title: 'Custom App',
      description: 'Custom Frappe application',
      publisher: 'Frappe Builder',
      email: 'developer@example.com',
      version: '0.0.1',
      requires_erpnext: false,
      modules: ['General'],
      roles: ['System Manager'],
      doctypes: [],
      workflows: [],
      reports: [],
    };

    const trimmed = newDocTypeName.trim();
    if (currentApp.doctypes.some((d) => d.name.toLowerCase() === trimmed.toLowerCase())) {
      return;
    }

    const defaultModule = currentApp.modules && currentApp.modules.length > 0 ? currentApp.modules[0] : 'General';
    const primaryRole = currentApp.roles && currentApp.roles.length > 0 ? currentApp.roles[0] : 'System Manager';

    const newDt: DocTypeSpec = {
      name: trimmed,
      module: defaultModule,
      istable: newIsTable,
      is_submittable: false,
      fields: [
        {
          fieldname: 'title',
          label: 'Title',
          fieldtype: 'Data',
          reqd: true,
          in_list_view: true,
        },
      ],
      permissions: newIsTable
        ? []
        : [
            {
              role: 'System Manager',
              read: true,
              write: true,
              create: true,
              delete: true,
            },
            ...(primaryRole !== 'System Manager'
              ? [{ role: primaryRole, read: true, write: true, create: true, delete: false }]
              : []),
          ],
    };

    const updatedApp: AppMetadata = {
      ...currentApp,
      doctypes: [...currentApp.doctypes, newDt],
    };

    onUpdateApp(updatedApp);
    setNewDocTypeName('');
    setNewIsTable(false);
    setIsAddModalOpen(false);
  }, [app, onUpdateApp, newDocTypeName, newIsTable]);

  if (!app || !app.doctypes || app.doctypes.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[var(--bg)] relative overflow-hidden select-none">
        <div className="max-w-md p-6 bg-[var(--surface)] border border-[var(--border)] rounded-card shadow-sm flex flex-col items-center">
          <Layers className="w-10 h-10 mb-3 text-[var(--accent)]" strokeWidth={1.5} />
          <h3 className="text-sm font-semibold text-[var(--text)] mb-1">Interactive Data Model (ERD)</h3>
          <p className="text-xs text-[var(--muted)] mb-4">
            No data model yet — it appears after Discovery or click <strong>Add DocType</strong> below to build your flowchart manually (n8n mode)!
          </p>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-card bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add DocType</span>
          </button>
        </div>

        {/* Add DocType Modal */}
        {isAddModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="w-full max-w-sm bg-[var(--surface)] border border-[var(--border)] rounded-card p-4 flex flex-col gap-3 shadow-xl">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
                <span className="font-semibold text-sm text-[var(--text)]">Add New DocType</span>
                <button
                  onClick={() => setIsAddModalOpen(false)}
                  className="p-1 rounded text-[var(--muted)] hover:text-[var(--text)]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex flex-col gap-1.5 text-xs text-left">
                <label className="font-medium text-[var(--text)]">DocType Name</label>
                <input
                  type="text"
                  placeholder="e.g. Maintenance Log"
                  value={newDocTypeName}
                  onChange={(e) => setNewDocTypeName(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-card border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] focus:border-[var(--accent)] outline-none"
                />
              </div>

              <label className="flex items-center gap-2 text-xs text-[var(--text)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={newIsTable}
                  onChange={(e) => setNewIsTable(e.target.checked)}
                  className="rounded border-[var(--border)] text-[var(--accent)] focus:ring-0"
                />
                <span>Is Child Table (Table field on parent)</span>
              </label>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
                <button
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-3 py-1 text-xs rounded font-medium text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)]"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddDocType}
                  disabled={!newDocTypeName.trim()}
                  className="px-3 py-1 text-xs rounded font-medium bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-40"
                >
                  Create DocType
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[var(--bg)] relative overflow-hidden">
      {/* Top Controls Toolbar */}
      <div className="h-10 px-3 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between z-10">
        <div className="flex items-center gap-2 text-xs">
          <span className="font-semibold text-[var(--text)]">Data Model (ERD)</span>
          <span className="px-1.5 py-0.2 rounded-pill bg-[var(--border)] text-[var(--muted)] text-[10px]">
            {doctypes.length} DocTypes • {edges.length} Connections
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleAutoLayout}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)] transition-colors"
            title="Auto-organize nodes with Dagre layout"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Auto Layout</span>
          </button>

          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
          >
            <Plus className="w-3 h-3" />
            <span>Add DocType</span>
          </button>
        </div>
      </div>

      {/* Interactive Helper Banner */}
      <div className="px-3 py-1 bg-[var(--bg)] border-b border-[var(--border)] text-[11px] text-[var(--muted)] flex items-center gap-1.5">
        <Info className="w-3 h-3 text-[var(--accent)] flex-shrink-0" />
        <span>Drag handles to connect DocTypes. Drag edge endpoints to reconnect. Backspace to delete link.</span>
      </div>

      {/* ReactFlow Canvas */}
      <div className="flex-1 w-full h-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onReconnect={onReconnect}
          onEdgesDelete={onEdgesDelete}
          fitView
          attributionPosition="bottom-right"
        >
          <Background gap={16} size={1} />
          <Controls />
          <MiniMap
            nodeStrokeWidth={2}
            zoomable
            pannable
            className="!bg-[var(--surface)] !border-[var(--border)] !rounded-card shadow-sm hidden md:block"
          />
        </ReactFlow>
      </div>

      {/* Add DocType Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-[var(--surface)] border border-[var(--border)] rounded-card p-4 flex flex-col gap-3 shadow-xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
              <span className="font-semibold text-sm text-[var(--text)]">Add New DocType</span>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="p-1 rounded text-[var(--muted)] hover:text-[var(--text)]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col gap-1.5 text-xs text-left">
              <label className="font-medium text-[var(--text)]">DocType Name</label>
              <input
                type="text"
                placeholder="e.g. Maintenance Log"
                value={newDocTypeName}
                onChange={(e) => setNewDocTypeName(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-card border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] focus:border-[var(--accent)] outline-none"
              />
            </div>

            <label className="flex items-center gap-2 text-xs text-[var(--text)] cursor-pointer">
              <input
                type="checkbox"
                checked={newIsTable}
                onChange={(e) => setNewIsTable(e.target.checked)}
                className="rounded border-[var(--border)] text-[var(--accent)] focus:ring-0"
              />
              <span>Is Child Table (Table field on parent)</span>
            </label>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="px-3 py-1 text-xs rounded font-medium text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)]"
              >
                Cancel
              </button>
              <button
                onClick={handleAddDocType}
                disabled={!newDocTypeName.trim()}
                className="px-3 py-1 text-xs rounded font-medium bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-40"
              >
                Create DocType
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
