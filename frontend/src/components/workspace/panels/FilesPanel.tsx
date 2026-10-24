import React, { useState, useEffect } from 'react';
import { FolderGit2, Folder, FileCode, Copy, Check, ChevronRight, ChevronDown } from 'lucide-react';
import { FileNode } from '../../../types';
import { api } from '../../../api';

interface FilesPanelProps {
  sessionId?: string | null;
}

export const FilesPanel: React.FC<FilesPanelProps> = ({ sessionId }) => {
  const [fileTree, setFileTree] = useState<FileNode | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    api
      .getExportTree(sessionId)
      .then((tree) => {
        setFileTree(tree);
        // Auto select first file if available
        if (tree.children && tree.children.length > 0) {
          const findFirst = (n: FileNode): string | null => {
            if (!n.is_dir) return n.path;
            if (n.children) {
              for (const c of n.children) {
                const f = findFirst(c);
                if (f) return f;
              }
            }
            return null;
          };
          const first = findFirst(tree);
          if (first) {
            handleSelectFile(first);
          }
        }
      })
      .catch(() => {
        // App not exported yet
      });
  }, [sessionId]);

  const handleSelectFile = (path: string) => {
    if (!sessionId) return;
    setSelectedPath(path);
    setLoading(true);
    api
      .getExportFile(sessionId, path)
      .then((res) => {
        setFileContent(res.content);
        setLoading(false);
      })
      .catch((err) => {
        setFileContent(`// Error loading file: ${err.message}`);
        setLoading(false);
      });
  };

  const handleCopy = () => {
    if (!fileContent) return;
    navigator.clipboard.writeText(fileContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!sessionId || !fileTree) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted">
        <FolderGit2 className="w-8 h-8 mb-2 text-[var(--muted)]/40" strokeWidth={1.5} />
        <p className="text-sm font-medium text-[var(--muted)]">
          No files generated yet — they appear after Drafting
        </p>
      </div>
    );
  }

  const renderTree = (node: FileNode, depth = 0) => {
    const isSelected = selectedPath === node.path;
    const isFolder = node.is_dir;

    return (
      <div key={node.path} className="flex flex-col">
        <button
          onClick={() => (isFolder ? null : handleSelectFile(node.path))}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
          className={`flex items-center gap-1.5 py-1 pr-2 text-left text-xs truncate transition-colors ${
            isSelected
              ? 'bg-[var(--surface)] text-[var(--text)] font-semibold'
              : 'text-[var(--muted)] hover:text-[var(--text)]'
          }`}
        >
          {isFolder ? (
            <Folder className="w-3.5 h-3.5 text-[var(--muted)] flex-shrink-0" strokeWidth={1.5} />
          ) : (
            <FileCode className="w-3.5 h-3.5 text-[var(--accent)] flex-shrink-0" strokeWidth={1.5} />
          )}
          <span className="truncate">{node.name}</span>
        </button>

        {isFolder && node.children && node.children.map((c) => renderTree(c, depth + 1))}
      </div>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Top File Tree (Compact) */}
      <div className="h-40 border-b border-[var(--border)] overflow-y-auto p-2 bg-[var(--surface)]/30">
        <div className="text-[11px] font-medium text-[var(--muted)] px-2 pb-1">
          Package Layout
        </div>
        {renderTree(fileTree)}
      </div>

      {/* Code Viewer */}
      <div className="flex-1 flex flex-col min-h-0 bg-[var(--bg)] overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border)] bg-[var(--surface)] text-xs text-[var(--muted)]">
          <span className="font-mono truncate">{selectedPath || 'Select file'}</span>
          <button
            onClick={handleCopy}
            disabled={!fileContent}
            className="flex items-center gap-1 text-[var(--muted)] hover:text-[var(--text)] transition-colors py-0.5 px-1.5 rounded-card"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-[var(--ok)]" />
                <span className="text-[var(--ok)]">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>

        <div className="flex-1 p-3 overflow-auto">
          {loading ? (
            <div className="text-xs text-[var(--muted)]">Loading file...</div>
          ) : (
            <pre className="text-xs text-[var(--text)] leading-relaxed font-mono">
              {fileContent}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};
