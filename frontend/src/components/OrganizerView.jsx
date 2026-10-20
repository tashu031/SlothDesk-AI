import React, { useState } from 'react';
import { 
  Folder, 
  FileText, 
  FileCode, 
  FileSpreadsheet, 
  Image as ImageIcon, 
  FileArchive, 
  File, 
  FolderSearch, 
  Sparkles, 
  Eye, 
  CheckCircle, 
  AlertCircle,
  HelpCircle,
  FolderPlus,
  Play
} from 'lucide-react';

export default function OrganizerView({ 
  currentScan, 
  isScanning, 
  onScan, 
  onQuickSample, 
  onGenerateSuggestions, 
  isGenerating,
  defaultPath 
}) {
  const [folderPath, setFolderPath] = useState(defaultPath || '');
  const [recursive, setRecursive] = useState(true);
  const [maxFiles, setMaxFiles] = useState(200);
  const [selectedPreview, setSelectedPreview] = useState(null);
  const [filterType, setFilterType] = useState('all');

  const handleScanSubmit = (e) => {
    e.preventDefault();
    if (!folderPath.trim()) return;
    onScan(folderPath.trim(), recursive, maxFiles);
  };

  const getFileIcon = (ext) => {
    switch (ext.toLowerCase()) {
      case '.pdf':
      case '.docx':
      case '.doc':
      case '.txt':
      case '.md':
        return <FileText className="w-4 h-4 text-[#3A6B4E]" />;
      case '.py':
      case '.js':
      case '.ts':
      case '.html':
      case '.css':
        return <FileCode className="w-4 h-4 text-[#2563EB]" />;
      case '.csv':
      case '.xlsx':
      case '.json':
        return <FileSpreadsheet className="w-4 h-4 text-[#D97706]" />;
      case '.png':
      case '.jpg':
      case '.jpeg':
      case '.webp':
        return <ImageIcon className="w-4 h-4 text-[#7C3AED]" />;
      case '.zip':
      case '.tar':
      case '.gz':
        return <FileArchive className="w-4 h-4 text-[#DC2626]" />;
      default:
        return <File className="w-4 h-4 text-[#6B7280]" />;
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const filteredFiles = (currentScan?.files || []).filter((f) => {
    if (filterType === 'all') return true;
    if (filterType === 'docs') return ['.pdf', '.txt', '.md', '.docx'].includes(f.extension);
    if (filterType === 'code') return ['.py', '.js', '.ts', '.html', '.css'].includes(f.extension);
    if (filterType === 'images') return ['.png', '.jpg', '.jpeg', '.webp'].includes(f.extension);
    if (filterType === 'data') return ['.csv', '.json', '.xlsx'].includes(f.extension);
    return true;
  });

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Folder Picker Configuration Card */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#F0ECE1] gap-2">
          <div>
            <h2 className="text-lg font-bold text-[#14261C] tracking-tight">Select Target Folder</h2>
            <p className="text-xs text-[#5C6E63]">
              Choose a messy directory on your local machine to scan and organize.
            </p>
          </div>
          <button
            type="button"
            onClick={onQuickSample}
            disabled={isScanning}
            className="self-start md:self-auto px-3.5 py-1.5 rounded-xl bg-[#EBF1ED] hover:bg-[#DCE7E0] text-[#254633] text-xs font-semibold border border-[#CCD8D0] flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <FolderPlus className="w-4 h-4 text-[#3E7354]" />
            Generate Sample Messy Playground
          </button>
        </div>

        <form onSubmit={handleScanSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-[#4A5D52] mb-1.5">
              Folder Absolute Path
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Folder className="w-4 h-4 text-[#7A8F82] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  placeholder="e.g. D:\Hactober\DEV3\sample_playground or C:\Users\name\Downloads"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#FAF8F2] border border-[#DDD5C5] rounded-xl text-sm font-mono text-[#14261C] focus:outline-none focus:ring-2 focus:ring-[#2D5A40] transition-all"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={isScanning || !folderPath.trim()}
                className="bg-[#2D5A40] hover:bg-[#234732] text-white text-xs font-bold px-6 py-2.5 rounded-xl shadow transition-all disabled:opacity-50 flex items-center gap-2 cursor-pointer shrink-0"
              >
                <FolderSearch className="w-4 h-4 text-[#84E1A9]" />
                {isScanning ? 'Scanning...' : 'Scan Directory'}
              </button>
            </div>
            <p className="text-[11px] text-[#7B8F83] mt-1.5 flex items-center gap-1">
              <HelpCircle className="w-3 h-3 text-[#5C6E63]" />
              Tip: In local-first desktop apps, type or paste any valid folder path on your drive.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-6 pt-2 text-xs text-[#4A5D52]">
            <label className="flex items-center gap-2 cursor-pointer font-medium select-none">
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                className="w-4 h-4 accent-[#2D5A40] rounded"
              />
              Scan recursively (includes subfolders)
            </label>

            <div className="flex items-center gap-2 font-medium">
              <span>Max Files Limit:</span>
              <select
                value={maxFiles}
                onChange={(e) => setMaxFiles(Number(e.target.value))}
                className="bg-[#FAF8F2] border border-[#DDD5C5] rounded-lg px-2.5 py-1 text-xs text-[#14261C] focus:outline-none focus:ring-1 focus:ring-[#2D5A40]"
              >
                <option value={50}>50 files</option>
                <option value={100}>100 files</option>
                <option value={200}>200 files</option>
                <option value={500}>500 files</option>
              </select>
            </div>

            <div className="text-[11px] text-[#7B8F83]">
              Excludes: <span className="font-mono text-[#5C6E63]">.git, node_modules, venv, hidden files</span>
            </div>
          </div>
        </form>
      </div>

      {/* Discovered Files Table & AI Suggestion Action Bar */}
      {currentScan ? (
        <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#F0ECE1] gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-[#14261C]">Discovered Files ({currentScan.files_scanned})</h3>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#FAF8F2] border border-[#E0D8C8] text-[#5C6E63]">
                  {currentScan.scan_duration_ms} ms
                </span>
              </div>
              <p className="text-xs text-[#5C6E63] font-mono mt-0.5 truncate max-w-lg" title={currentScan.root_path}>
                Root: {currentScan.root_path}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => onGenerateSuggestions(currentScan.session_id, currentScan.root_path, currentScan.files)}
                disabled={isGenerating || currentScan.files.length === 0}
                className="bg-gradient-to-r from-[#2D5A40] to-[#1E432F] hover:from-[#234732] hover:to-[#173625] text-white text-xs font-bold px-4 py-2 rounded-xl shadow transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4 text-[#84E1A9]" />
                {isGenerating ? 'Thinking & Analyzing...' : 'Generate AI Action Plan'}
              </button>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-[#7B8F83] font-medium mr-1">Filter:</span>
            {['all', 'docs', 'code', 'data', 'images'].map((tab) => (
              <button
                key={tab}
                onClick={() => setFilterType(tab)}
                className={`px-3 py-1 rounded-lg font-medium capitalize transition-colors cursor-pointer ${
                  filterType === tab
                    ? 'bg-[#2D5A40] text-white'
                    : 'bg-[#FAF8F2] text-[#5C6E63] hover:bg-[#F0ECE1]'
                }`}
              >
                {tab}
              </button>
            ))}
            <span className="text-[11px] text-[#7B8F83] ml-auto">
              Showing {filteredFiles.length} of {currentScan.files.length}
            </span>
          </div>

          {/* Files List */}
          <div className="overflow-x-auto border border-[#EAE3D5] rounded-xl max-h-96 overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#FAF8F2] text-[#5C6E63] uppercase tracking-wider font-semibold border-b border-[#EAE3D5] sticky top-0">
                <tr>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Filename</th>
                  <th className="py-2.5 px-3">Relative Path</th>
                  <th className="py-2.5 px-3">Size</th>
                  <th className="py-2.5 px-3">Last Modified</th>
                  <th className="py-2.5 px-3 text-right">Preview</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F0ECE1]">
                {filteredFiles.map((file, idx) => (
                  <tr key={idx} className="hover:bg-[#FAF8F2] transition-colors">
                    <td className="py-2.5 px-3">
                      {getFileIcon(file.extension)}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-[#14261C]">
                      {file.filename}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[#7B8F83] max-w-xs truncate" title={file.relative_path}>
                      {file.relative_path}
                    </td>
                    <td className="py-2.5 px-3 text-[#5C6E63] font-mono">
                      {formatBytes(file.size_bytes)}
                    </td>
                    <td className="py-2.5 px-3 text-[#7B8F83]">
                      {new Date(file.modified_at).toLocaleDateString()}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {file.preview_snippet ? (
                        <button
                          onClick={() => setSelectedPreview(file)}
                          className="text-xs font-semibold text-[#2D5A40] hover:underline flex items-center gap-1 justify-end ml-auto cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          View
                        </button>
                      ) : (
                        <span className="text-[11px] text-[#A6B4AB]">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-12 border border-[#E6E0D4] shadow-sm text-center space-y-3">
          <div className="w-16 h-16 rounded-full bg-[#FAF8F2] border border-[#E0D8C8] flex items-center justify-center mx-auto text-2xl">
            📁
          </div>
          <h3 className="text-base font-bold text-[#14261C]">No Folder Scanned Yet</h3>
          <p className="text-xs text-[#5C6E63] max-w-md mx-auto">
            Provide a folder path above, or click "Generate Sample Messy Playground" to immediately test SlothDesk AI with realistic messy documents, scripts, and notes.
          </p>
          <div className="pt-2">
            <button
              onClick={onQuickSample}
              disabled={isScanning}
              className="bg-[#2D5A40] hover:bg-[#234732] text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow transition-all cursor-pointer inline-flex items-center gap-1.5"
            >
              <FolderPlus className="w-4 h-4 text-[#84E1A9]" />
              Load Sample Playground
            </button>
          </div>
        </div>
      )}

      {/* Snippet Preview Modal */}
      {selectedPreview && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-[#DDD5C5] space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#F0ECE1]">
              <div className="flex items-center gap-2">
                {getFileIcon(selectedPreview.extension)}
                <span className="text-sm font-bold text-[#14261C]">{selectedPreview.filename}</span>
              </div>
              <button
                onClick={() => setSelectedPreview(null)}
                className="text-xs font-bold text-[#5C6E63] hover:text-[#14261C] p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[#7B8F83] mb-1">
                Bounded Content Extraction (Safety Checked)
              </div>
              <div className="bg-[#FAF8F2] p-3.5 rounded-xl border border-[#E8E2D5] font-mono text-xs text-[#2A3B30] max-h-60 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {selectedPreview.preview_snippet}
              </div>
            </div>
            <div className="flex justify-end">
              <button
                onClick={() => setSelectedPreview(null)}
                className="px-4 py-2 rounded-xl bg-[#2D5A40] text-white text-xs font-bold cursor-pointer"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
