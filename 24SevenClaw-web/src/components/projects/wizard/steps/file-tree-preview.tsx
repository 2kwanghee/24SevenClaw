"use client";

import { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  File,
  Folder,
  FolderOpen,
} from "lucide-react";

import type { FileTreeNode } from "@/lib/api-client";

interface FileTreePreviewProps {
  tree: FileTreeNode[];
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

export function FileTreePreview({
  tree,
  selectedPath,
  onSelectFile,
}: FileTreePreviewProps) {
  return (
    <div className="space-y-0.5">
      {tree.map((node) => (
        <TreeNode
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelectFile={onSelectFile}
        />
      ))}
    </div>
  );
}

interface TreeNodeProps {
  node: FileTreeNode;
  depth: number;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

function TreeNode({ node, depth, selectedPath, onSelectFile }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isDir = node.type === "directory";
  const isSelected = node.path === selectedPath;
  const name = node.path.split("/").pop() ?? node.path;

  const handleClick = () => {
    if (isDir) {
      setExpanded((prev) => !prev);
    } else {
      onSelectFile(node.path);
    }
  };

  return (
    <div>
      <button
        type="button"
        onClick={handleClick}
        className={`flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left text-xs transition-colors ${
          isSelected
            ? "bg-violet-500/15 text-violet-300"
            : "text-slate-400 hover:bg-white/5 hover:text-slate-300"
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {isDir ? (
          <>
            {expanded ? (
              <ChevronDown className="h-3 w-3 shrink-0 text-slate-600" />
            ) : (
              <ChevronRight className="h-3 w-3 shrink-0 text-slate-600" />
            )}
            {expanded ? (
              <FolderOpen className="h-3.5 w-3.5 shrink-0 text-violet-400/70" />
            ) : (
              <Folder className="h-3.5 w-3.5 shrink-0 text-violet-400/70" />
            )}
          </>
        ) : (
          <>
            <span className="h-3 w-3 shrink-0" />
            <File className="h-3.5 w-3.5 shrink-0 text-slate-500" />
          </>
        )}
        <span className="truncate">{name}</span>
      </button>

      {isDir && expanded && node.children.length > 0 && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
            />
          ))}
        </div>
      )}
    </div>
  );
}
