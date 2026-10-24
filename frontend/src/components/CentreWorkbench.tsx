import React, { useState, useEffect } from 'react';
import {
  Layers,
  FileCode2,
  Workflow,
  Eye,
  Braces,
  Copy,
  Check,
  Folder,
  FileText,
  Table as TableIcon,
  Link as LinkIcon,
  Hash,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';
import { AppMetadata, DocTypeSpec, FieldSpec, FileNode } from '../types';
import { api } from '../api';

interface CentreWorkbenchProps {
  app?: AppMetadata | null;
  specRaw?: any;
  sessionId?: string;
}

type TabType = 'erd' | 'form' | 'workflow' | 'code' | 'json';

export const CentreWorkbench: React.FC<CentreWorkbenchProps> = ({
  app,
  specRaw,
  sessionId,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('erd');
  const [selectedDocType, setSelectedDocType] = useState<DocTypeSpec | null>(null);
  const [copiedJson, setCopiedJson] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  const handleCopyCode = () => {
    if (!fileContent) return;
    navigator.clipboard.writeText(fileContent);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleCopyJson = () => {
    const jsonStr = JSON.stringify(specRaw || app, null, 2);
    navigator.clipboard.writeText(jsonStr);
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  // File tree state
  const [fileTree, setFileTree] = useState<FileNode | null>(null);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [loadingFile, setLoadingFile] = useState(false);

  // Set default selected doctype
  useEffect(() => {
    if (app && app.doctypes && app.doctypes.length > 0) {
      if (!selectedDocType || !app.doctypes.find((d) => d.name === selectedDocType.name)) {
        setSelectedDocType(app.doctypes[0]);
      }
    }
  }, [app]);

  // Load export file tree when code tab is opened
  useEffect(() => {
    if (activeTab === 'code' && sessionId && app) {
      api
        .getExportTree(sessionId)
        .then((tree) => {
          setFileTree(tree);
          // Auto select first file if available
          const firstFile = findFirstFile(tree);
          if (firstFile) {
            handleSelectFile(firstFile.path);
          }
        })
        .catch((err) => console.log('Could not load tree', err));
    }
  }, [activeTab, sessionId, app]);

  const findFirstFile = (node: FileNode): FileNode | null => {
    if (!node.is_dir) return node;
    for (const child of node.children || []) {
      const found = findFirstFile(child);
      if (found) return found;
    }
    return null;
  };

  const handleSelectFile = (path: string) => {
    if (!sessionId) return;
    setSelectedFilePath(path);
    setLoadingFile(true);
    api
      .getExportFile(sessionId, path)
      .then((res) => {
        setFileContent(res.content);
        setLoadingFile(false);
      })
      .catch((err) => {
        setFileContent(`// Error reading file: ${err.message}`);
        setLoadingFile(false);
      });
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* 1. Workbench Tab Bar */}
      <div className="h-11 border-b border-slate-800 bg-slate-900/60 px-4 flex items-center justify-between flex-shrink-0 select-none">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('erd')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'erd'
                ? 'bg-slate-800 text-sky-400 shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Data Model (ERD)</span>
          </button>

          <button
            onClick={() => setActiveTab('form')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'form'
                ? 'bg-slate-800 text-sky-400 shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Form Simulator</span>
          </button>

          <button
            onClick={() => setActiveTab('workflow')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'workflow'
                ? 'bg-slate-800 text-sky-400 shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <Workflow className="w-3.5 h-3.5" />
            <span>Workflows</span>
          </button>

          <button
            onClick={() => setActiveTab('code')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'code'
                ? 'bg-slate-800 text-sky-400 shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <FileCode2 className="w-3.5 h-3.5" />
            <span>Files & Code</span>
          </button>

          <button
            onClick={() => setActiveTab('json')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'json'
                ? 'bg-slate-800 text-sky-400 shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <Braces className="w-3.5 h-3.5" />
            <span>Spec JSON</span>
          </button>
        </div>

        {activeTab === 'json' && (
          <button
            onClick={handleCopyJson}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700"
          >
            {copiedJson ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>{copiedJson ? 'Copied' : 'Copy'}</span>
          </button>
        )}
      </div>

      {/* 2. Active Tab Content Area */}
      <div className="flex-1 overflow-auto relative">
        {!app ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Layers className="w-10 h-10 mb-3 opacity-40 animate-pulse text-sky-400" />
            <p className="text-sm font-medium">Awaiting Discovery Requirements...</p>
            <p className="text-xs text-slate-600 mt-1">Answer questions in the chat to generate the data model.</p>
          </div>
        ) : (
          <>
            {/* TAB 1: ERD GRAPH */}
            {activeTab === 'erd' && (
              <div className="p-6 min-h-full">
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {app.doctypes.map((dt) => (
                    <div
                      key={dt.name}
                      onClick={() => setSelectedDocType(dt)}
                      className={`cursor-pointer rounded-xl border bg-slate-900 transition-all shadow-md overflow-hidden ${
                        selectedDocType?.name === dt.name
                          ? 'border-sky-500 ring-1 ring-sky-500/40 shadow-sky-950/40'
                          : 'border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {/* DocType Card Header */}
                      <div className="px-4 py-3 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <TableIcon className="w-4 h-4 text-sky-400" />
                          <span className="font-semibold text-sm text-slate-100">{dt.name}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {dt.istable && (
                            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-950/80 text-amber-300 border border-amber-800/50">
                              Child Table
                            </span>
                          )}
                          {dt.is_submittable && (
                            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/50">
                              Submittable
                            </span>
                          )}
                        </div>
                      </div>

                      {/* DocType Fields List */}
                      <div className="p-3 divide-y divide-slate-850 text-xs">
                        {dt.fields.map((f) => (
                          <div key={f.fieldname} className="py-1.5 flex items-center justify-between group">
                            <div className="flex items-center gap-2">
                              {f.fieldtype === 'Link' ? (
                                <LinkIcon className="w-3 h-3 text-sky-400" />
                              ) : f.fieldtype === 'Table' ? (
                                <TableIcon className="w-3 h-3 text-amber-400" />
                              ) : (
                                <Hash className="w-3 h-3 text-slate-500" />
                              )}
                              <span className="font-mono text-slate-300 group-hover:text-white">
                                {f.fieldname}
                              </span>
                              {f.reqd && <span className="text-rose-400 text-[10px]">*</span>}
                            </div>
                            <div className="flex items-center gap-1.5 text-slate-500 text-[11px]">
                              <span className="font-mono">{f.fieldtype}</span>
                              {f.options && (
                                <span className="text-sky-400 max-w-[100px] truncate">
                                  → {f.options}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 2: FORM SIMULATOR */}
            {activeTab === 'form' && (
              <div className="p-6 max-w-4xl mx-auto">
                {/* DocType Selector */}
                <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Simulate Form:
                    </span>
                    <select
                      value={selectedDocType?.name || ''}
                      onChange={(e) => {
                        const found = app.doctypes.find((d) => d.name === e.target.value);
                        if (found) setSelectedDocType(found);
                      }}
                      className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs font-semibold text-sky-400 outline-none"
                    >
                      {app.doctypes.map((d) => (
                        <option key={d.name} value={d.name}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <span className="px-2.5 py-1 text-xs rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                    Draft Status (Not Saved)
                  </span>
                </div>

                {/* Desk Form Layout */}
                {selectedDocType && (
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                      <div>
                        <h2 className="text-lg font-bold text-slate-100">{selectedDocType.name}</h2>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Module: {selectedDocType.module} | Autoname: {selectedDocType.autoname}
                        </p>
                      </div>
                      <button className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition">
                        Save
                      </button>
                    </div>

                    {/* Field Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {selectedDocType.fields
                        .filter(
                          (f) =>
                            !['Section Break', 'Column Break', 'Tab Break'].includes(f.fieldtype)
                        )
                        .map((f) => (
                          <div
                            key={f.fieldname}
                            className={`flex flex-col gap-1.5 ${
                              f.fieldtype === 'Table' || f.fieldtype === 'Small Text'
                                ? 'col-span-full'
                                : ''
                            }`}
                          >
                            <label className="text-xs font-medium text-slate-300 flex items-center justify-between">
                              <span>
                                {f.label} {f.reqd && <span className="text-rose-400">*</span>}
                              </span>
                              <span className="text-[10px] text-slate-500 font-mono">
                                {f.fieldtype}
                              </span>
                            </label>

                            {f.fieldtype === 'Select' ? (
                              <select className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 outline-none focus:border-sky-500">
                                {(f.options || '').split('\n').map((opt, oi) => (
                                  <option key={oi} value={opt}>
                                    {opt}
                                  </option>
                                ))}
                              </select>
                            ) : f.fieldtype === 'Check' ? (
                              <input
                                type="checkbox"
                                className="w-4 h-4 rounded bg-slate-950 border-slate-700 text-sky-500"
                              />
                            ) : f.fieldtype === 'Table' ? (
                              <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950 p-3">
                                <div className="text-xs text-slate-400 mb-2 font-mono">
                                  Child Grid ({f.options})
                                </div>
                                <div className="p-3 bg-slate-900 rounded border border-dashed border-slate-800 text-center text-xs text-slate-500">
                                  + Add Row in {f.label}
                                </div>
                              </div>
                            ) : (
                              <input
                                type="text"
                                placeholder={`Enter ${f.label.toLowerCase()}...`}
                                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder:text-slate-600 outline-none focus:border-sky-500"
                              />
                            )}
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: WORKFLOWS */}
            {activeTab === 'workflow' && (
              <div className="p-6 max-w-4xl mx-auto space-y-6">
                {(!app.workflows || app.workflows.length === 0) ? (
                  <div className="text-center py-12 text-slate-500 text-sm">
                    No custom multi-step workflows defined in this application.
                  </div>
                ) : (
                  app.workflows.map((wf) => (
                    <div
                      key={wf.name}
                      className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4"
                    >
                      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                        <div>
                          <h3 className="font-bold text-slate-100">{wf.name}</h3>
                          <p className="text-xs text-slate-400">Target DocType: {wf.document_type}</p>
                        </div>
                        <span className="px-2 py-0.5 text-xs rounded bg-sky-950 text-sky-400 border border-sky-800">
                          Active
                        </span>
                      </div>

                      {/* States Flow */}
                      <div>
                        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                          Workflow States:
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {wf.states.map((st) => (
                            <div
                              key={st.state}
                              className="px-3 py-1.5 bg-slate-800 rounded-lg border border-slate-700 flex items-center gap-2 text-xs"
                            >
                              <span className="font-semibold text-slate-200">{st.state}</span>
                              <span
                                className={`px-1.5 py-0.2 rounded text-[10px] ${
                                  st.doc_status === 1
                                    ? 'bg-emerald-950 text-emerald-300'
                                    : 'bg-slate-700 text-slate-300'
                                }`}
                              >
                                doc_status: {st.doc_status}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Transitions */}
                      <div>
                        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                          Transitions:
                        </div>
                        <div className="space-y-1.5 text-xs">
                          {wf.transitions.map((tr, i) => (
                            <div
                              key={i}
                              className="p-2 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between font-mono"
                            >
                              <div className="flex items-center gap-2 text-slate-300">
                                <span>{tr.state}</span>
                                <span className="text-sky-400 font-bold">--[{tr.action}]--&gt;</span>
                                <span className="text-emerald-400">{tr.next_state}</span>
                              </div>
                              <span className="text-[11px] text-slate-500">
                                Role: {tr.allowed}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* TAB 4: FILES & CODE */}
            {activeTab === 'code' && (
              <div className="flex h-full select-text">
                {/* File Tree Sidebar */}
                <div className="w-64 border-r border-slate-800 bg-slate-900/60 p-3 overflow-y-auto font-mono text-xs select-text">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-3 select-none">
                    Package Hierarchy
                  </div>
                  {fileTree && renderTreeNode(fileTree, selectedFilePath, handleSelectFile)}
                </div>

                {/* Code Viewer */}
                <div className="flex-1 bg-slate-950 p-4 flex flex-col font-mono text-xs overflow-auto select-text">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-slate-400 select-none">
                    <span className="font-semibold text-slate-300">{selectedFilePath || 'Select a file'}</span>
                    <button
                      onClick={handleCopyCode}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 hover:text-white transition"
                    >
                      {copiedCode ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-sky-400" />
                          <span>Copy Code</span>
                        </>
                      )}
                    </button>
                  </div>
                  {loadingFile ? (
                    <div className="text-slate-500 py-8 text-center">Loading file...</div>
                  ) : (
                    <pre className="text-slate-300 leading-relaxed overflow-auto flex-1 select-text">
                      {fileContent}
                    </pre>
                  )}
                </div>
              </div>
            )}

            {/* TAB 5: SPEC JSON */}
            {activeTab === 'json' && (
              <div className="p-6 select-text space-y-3">
                <div className="flex items-center justify-between select-none">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Frappe AppSpec 2.0 Contract
                  </span>
                  <button
                    onClick={handleCopyJson}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-850 text-slate-200 hover:text-white transition text-xs font-medium shadow-sm"
                  >
                    {copiedJson ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied Spec</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-sky-400" />
                        <span>Copy JSON Spec</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-xs font-mono text-slate-300 overflow-auto max-h-[calc(100vh-220px)] select-text">
                  {JSON.stringify(specRaw || app, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

function renderTreeNode(
  node: FileNode,
  selectedPath: string | null,
  onSelect: (path: string) => void,
  depth: number = 0
): JSX.Element {
  const isSelected = selectedPath === node.path;
  return (
    <div key={node.path} style={{ paddingLeft: `${depth * 10}px` }}>
      <div
        onClick={() => !node.is_dir && onSelect(node.path)}
        className={`flex items-center gap-1.5 py-1 px-1.5 rounded cursor-pointer transition ${
          isSelected
            ? 'bg-sky-600 text-white font-semibold'
            : node.is_dir
            ? 'text-slate-400 font-semibold hover:text-slate-200'
            : 'text-slate-300 hover:text-white hover:bg-slate-800'
        }`}
      >
        {node.is_dir ? (
          <Folder className="w-3.5 h-3.5 text-sky-400" />
        ) : (
          <FileText className="w-3.5 h-3.5 text-slate-400" />
        )}
        <span className="truncate">{node.name}</span>
      </div>
      {node.is_dir &&
        node.children?.map((child) => renderTreeNode(child, selectedPath, onSelect, depth + 1))}
    </div>
  );
}
