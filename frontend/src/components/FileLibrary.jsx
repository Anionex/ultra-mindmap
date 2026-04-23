import { useState, useRef, useCallback } from 'react';
import { Upload, FileText, Trash2, Check } from 'lucide-react';
import gsap from 'gsap';

const TYPE_LABELS = { '.txt': 'TXT', '.md': 'MD', '.pdf': 'PDF', '.docx': 'DOCX' };

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileLibrary({ files, selectedIds, onSelectChange, onUpload, onDelete }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const handleFiles = useCallback((fileList) => {
    const arr = Array.from(fileList);
    if (arr.length > 0) onUpload(arr);
  }, [onUpload]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const toggleSelect = (id) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectChange(next);
  };

  const handleDelete = (id, e) => {
    e.stopPropagation();
    const el = e.currentTarget.closest('[data-file-item]');
    if (el) {
      gsap.to(el, {
        opacity: 0, x: -20, height: 0, padding: 0, margin: 0,
        duration: 0.25, ease: 'power2.in',
        onComplete: () => onDelete(id),
      });
    } else {
      onDelete(id);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">文件库</h3>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200
          ${dragOver ? 'border-gray-900 bg-gray-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'}
        `}
      >
        <Upload size={24} className="mx-auto text-gray-400 mb-2" />
        <p className="text-sm text-gray-500">拖放文件到此处，或点击上传</p>
        <p className="text-xs text-gray-400 mt-1">支持 TXT、MD、PDF、DOCX</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".txt,.md,.pdf,.docx"
          className="hidden"
          onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
        />
      </div>

      <div ref={listRef} className="flex flex-col gap-1 max-h-[40vh] overflow-y-auto">
        {files.map((f) => (
          <div
            key={f.id}
            data-file-item
            onClick={() => toggleSelect(f.id)}
            className={`
              flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150 group
              ${selectedIds.has(f.id) ? 'bg-gray-100 ring-1 ring-gray-300' : 'hover:bg-gray-50'}
            `}
          >
            <div className={`
              w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors
              ${selectedIds.has(f.id) ? 'bg-gray-900 border-gray-900' : 'border-gray-300'}
            `}>
              {selectedIds.has(f.id) && <Check size={12} className="text-white" />}
            </div>
            <FileText size={16} className="text-gray-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-800 truncate">{f.filename}</p>
              <p className="text-xs text-gray-400">
                {TYPE_LABELS[f.file_type] || f.file_type} &middot; {formatSize(f.file_size)}
              </p>
            </div>
            <button
              onClick={(e) => handleDelete(f.id, e)}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all p-1"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
        {files.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-4">暂无文件</p>
        )}
      </div>
    </div>
  );
}
