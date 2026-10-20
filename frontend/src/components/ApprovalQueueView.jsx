import React, { useState } from 'react';
import { 
  CheckSquare, 
  Square, 
  Sparkles, 
  Edit3, 
  ShieldCheck, 
  ArrowRight, 
  RotateCcw, 
  AlertTriangle,
  CheckCircle2,
  Cpu,
  FolderOpen,
  Info
} from 'lucide-react';

const CATEGORIES = ["Documents", "Study", "Code", "Images", "Data", "Archives", "Miscellaneous"];

export default function ApprovalQueueView({ 
  suggestions, 
  rootPath, 
  onExecute, 
  isExecuting, 
  onUpdateSuggestion,
  onNavigate 
}) {
  const [selectedIds, setSelectedIds] = useState(
    new Set(suggestions.map((s) => s.id))
  );
  const [editingId, setEditingId] = useState(null);
  const [editFilename, setEditFilename] = useState('');
  const [editCategory, setEditCategory] = useState('');
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(suggestions.map((s) => s.id)));
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
  };

  const startEdit = (sug) => {
    setEditingId(sug.id);
    setEditFilename(sug.proposed_filename);
    setEditCategory(sug.category);
  };

  const saveEdit = (id) => {
    onUpdateSuggestion(id, {
      proposed_filename: editFilename.trim() || 'file',
      category: editCategory,
      proposed_rel_path: `${editCategory}/${editFilename.trim() || 'file'}`
    });
    setEditingId(null);
  };

  const handleConfirmExecution = async () => {
    setShowConfirmModal(false);
    const approvedActions = suggestions
      .filter((s) => selectedIds.has(s.id))
      .map((s) => ({
        id: s.id,
        original_path: s.original_path,
        proposed_filename: s.proposed_filename,
        category: s.category,
        proposed_rel_path: s.proposed_rel_path,
        approved: true
      }));

    if (approvedActions.length === 0) return;

    const res = await onExecute(rootPath, approvedActions);
    if (res) {
      setExecutionResult(res);
    }
  };

  const selectedCount = selectedIds.size;

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Header and Controls */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#F0ECE1] gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-[#14261C] tracking-tight">Review & Approval Queue</h2>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-[#FAF8F2] border border-[#DDD5C5] text-[#2D5A40]">
                {suggestions.length} items
              </span>
            </div>
            <p className="text-xs text-[#5C6E63] mt-0.5">
              Carefully review each AI suggestion before approving. You retain full control over your files.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={selectAll}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-[#FAF8F2] hover:bg-[#F0ECE1] text-[#2D5A40] border border-[#DDD5C5] cursor-pointer"
            >
              Select All
            </button>
            <button
              onClick={deselectAll}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-[#FAF8F2] hover:bg-[#F0ECE1] text-[#5C6E63] border border-[#DDD5C5] cursor-pointer"
            >
              Deselect All
            </button>

            <button
              onClick={() => setShowConfirmModal(true)}
              disabled={isExecuting || selectedCount === 0}
              className="bg-[#2D5A40] hover:bg-[#234732] text-white text-xs font-bold px-5 py-2 rounded-xl shadow transition-all disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
            >
              <CheckSquare className="w-4 h-4 text-[#84E1A9]" />
              {isExecuting ? 'Executing Moves...' : `Execute ${selectedCount} Approved Actions`}
            </button>
          </div>
        </div>

        {/* Safety Pipeline Banner */}
        <div className="mt-4 p-3 rounded-xl bg-[#FAF8F2] border border-[#E8E2D5] flex items-center justify-between text-xs text-[#4A5D52]">
          <span className="flex items-center gap-2 font-medium">
            <ShieldCheck className="w-4 h-4 text-[#2D5A40]" />
            Validated Action Pipeline: Root isolation checked • Zero automatic overwrites • Full Undo capability
          </span>
          <span className="text-[11px] text-[#7B8F83] hidden sm:inline">
            Root: <span className="font-mono text-[#14261C]">{rootPath || 'Not set'}</span>
          </span>
        </div>
      </div>

      {/* Execution Results Feedback Banner */}
      {executionResult && (
        <div className="bg-[#EBF5EE] border border-[#B3D6BF] rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-[#1B3B2B]" />
              <h3 className="text-sm font-bold text-[#14261C]">Batch Execution Completed Successfully</h3>
            </div>
            <button 
              onClick={() => onNavigate('history')}
              className="text-xs font-bold text-[#1B3B2B] hover:underline cursor-pointer"
            >
              View in Activity History →
            </button>
          </div>
          <p className="text-xs text-[#2A4B38]">
            Moved {executionResult.total_succeeded} file(s) safely to their organized destinations. 
            Failed / blocked: {executionResult.total_failed}. All changes are logged in SQLite for persistent undo.
          </p>
        </div>
      )}

      {/* Queue Items List */}
      {suggestions.length > 0 ? (
        <div className="space-y-3">
          {suggestions.map((sug) => {
            const isSelected = selectedIds.has(sug.id);
            const isEditing = editingId === sug.id;

            return (
              <div 
                key={sug.id} 
                className={`bg-white rounded-2xl p-5 border transition-all ${
                  isSelected ? 'border-[#2D5A40] shadow-sm' : 'border-[#E6E0D4] opacity-80'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Checkbox and File info */}
                  <div className="flex items-start space-x-3 flex-1 min-w-0">
                    <button
                      onClick={() => toggleSelect(sug.id)}
                      className="mt-1 text-[#2D5A40] cursor-pointer"
                    >
                      {isSelected ? (
                        <CheckSquare className="w-5 h-5 text-[#2D5A40]" />
                      ) : (
                        <Square className="w-5 h-5 text-[#A0B0A7]" />
                      )}
                    </button>

                    <div className="flex-1 min-w-0">
                      {/* Original to Proposed Path Flow */}
                      <div className="flex flex-col sm:flex-row sm:items-center gap-2 text-xs">
                        <span className="font-mono text-[#7B8F83] truncate max-w-xs" title={sug.original_filename}>
                          {sug.original_filename}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-[#2D5A40] shrink-0 hidden sm:inline" />
                        <span className="font-mono font-bold text-[#14261C] bg-[#FAF8F2] px-2 py-0.5 rounded border border-[#EAE3D5] truncate max-w-sm" title={sug.proposed_rel_path}>
                          {sug.proposed_rel_path}
                        </span>
                      </div>

                      {/* Explanation and Intelligence Source */}
                      <p className="text-xs text-[#5C6E63] mt-2 leading-relaxed">
                        <span className="font-semibold text-[#14261C]">Why: </span>
                        {sug.explanation}
                      </p>

                      {/* Tags & Model Attribution */}
                      <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[11px]">
                        <span className="px-2 py-0.5 rounded-md font-semibold bg-[#EBF1ED] text-[#254633] border border-[#CCD8D0]">
                          📂 {sug.category}
                        </span>

                        <span className={`px-2 py-0.5 rounded-md font-medium flex items-center gap-1 ${
                          sug.is_fallback 
                            ? 'bg-[#FEF4E8] text-[#9A5B13]' 
                            : 'bg-[#EBF5EE] text-[#1B3B2B]'
                        }`}>
                          <Cpu className="w-3 h-3" />
                          {sug.is_fallback ? 'Rule Fallback' : `Gemma AI (${sug.model_used})`}
                        </span>

                        <span className="text-[#8BA094] font-mono text-[10px]">
                          {sug.latency_ms} ms
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Edit Action Button */}
                  <div className="shrink-0">
                    <button
                      onClick={() => isEditing ? saveEdit(sug.id) : startEdit(sug)}
                      className="px-3 py-1.5 rounded-lg bg-[#FAF8F2] hover:bg-[#F0ECE1] text-[#2D5A40] text-xs font-semibold border border-[#DDD5C5] flex items-center gap-1 cursor-pointer"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      {isEditing ? 'Save' : 'Customize'}
                    </button>
                  </div>
                </div>

                {/* Inline Edit Panel */}
                {isEditing && (
                  <div className="mt-4 pt-4 border-t border-[#F0ECE1] bg-[#FAF8F2] p-4 rounded-xl space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-bold text-[#4A5D52] uppercase mb-1">
                          Custom Filename
                        </label>
                        <input
                          type="text"
                          value={editFilename}
                          onChange={(e) => setEditFilename(e.target.value)}
                          className="w-full px-3 py-1.5 bg-white border border-[#DDD5C5] rounded-lg text-xs font-mono text-[#14261C] focus:outline-none focus:ring-1 focus:ring-[#2D5A40]"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-bold text-[#4A5D52] uppercase mb-1">
                          Target Category / Folder
                        </label>
                        <select
                          value={editCategory}
                          onChange={(e) => setEditCategory(e.target.value)}
                          className="w-full px-3 py-1.5 bg-white border border-[#DDD5C5] rounded-lg text-xs text-[#14261C] focus:outline-none focus:ring-1 focus:ring-[#2D5A40]"
                        >
                          {CATEGORIES.map((cat) => (
                            <option key={cat} value={cat}>{cat}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1 text-xs text-[#5C6E63] hover:text-[#14261C] cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => saveEdit(sug.id)}
                        className="px-3.5 py-1 bg-[#2D5A40] text-white text-xs font-bold rounded-lg cursor-pointer"
                      >
                        Apply Changes
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-12 border border-[#E6E0D4] shadow-sm text-center space-y-3">
          <div className="w-16 h-16 rounded-full bg-[#FAF8F2] border border-[#E0D8C8] flex items-center justify-center mx-auto text-2xl">
            ✨
          </div>
          <h3 className="text-base font-bold text-[#14261C]">Approval Queue is Clean</h3>
          <p className="text-xs text-[#5C6E63] max-w-md mx-auto">
            Scan a folder in the File Organizer and click "Generate AI Action Plan" to review proposed file moves here.
          </p>
          <div className="pt-2">
            <button
              onClick={() => onNavigate('organizer')}
              className="bg-[#2D5A40] hover:bg-[#234732] text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow transition-all cursor-pointer inline-flex items-center gap-1.5"
            >
              <FolderOpen className="w-4 h-4 text-[#84E1A9]" />
              Go to File Organizer
            </button>
          </div>
        </div>
      )}

      {/* Safety Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-[#DDD5C5] space-y-4">
            <div className="flex items-center space-x-3 text-[#1B3B2B]">
              <div className="p-2 rounded-xl bg-[#EBF5EE]">
                <ShieldCheck className="w-6 h-6 text-[#1B3B2B]" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#14261C]">Confirm Safe File Organization</h3>
                <p className="text-xs text-[#5C6E63]">Safety verification before filesystem execution</p>
              </div>
            </div>

            <div className="bg-[#FAF8F2] p-4 rounded-xl border border-[#E8E2D5] space-y-2 text-xs text-[#4A5D52]">
              <div className="font-bold text-[#14261C]">
                Ready to execute {selectedCount} approved move(s):
              </div>
              <ul className="list-disc pl-5 space-y-1 text-[#5C6E63]">
                <li>Only accesses files strictly inside: <span className="font-mono text-[#14261C]">{rootPath}</span></li>
                <li>Files are never overwritten (duplicate names get unique suffixes).</li>
                <li>No files are ever deleted.</li>
                <li>All moves are recorded in SQLite and can be undone with one click.</li>
              </ul>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 rounded-xl bg-[#FAF8F2] hover:bg-[#F0ECE1] text-[#5C6E63] text-xs font-semibold border border-[#DDD5C5] cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmExecution}
                className="px-5 py-2 rounded-xl bg-[#2D5A40] hover:bg-[#234732] text-white text-xs font-bold shadow cursor-pointer"
              >
                Confirm & Organize Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
