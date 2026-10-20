import React from 'react';
import { 
  FileSearch, 
  CheckCircle, 
  Clock, 
  ListFilter, 
  ArrowRight, 
  FolderPlus, 
  Sparkles, 
  Info, 
  ShieldCheck, 
  AlertTriangle,
  RotateCcw,
  Bot
} from 'lucide-react';

export default function OverviewView({ 
  summary, 
  aiStatus, 
  recentOperations, 
  onNavigate, 
  onQuickSample, 
  onUndo, 
  isUndoing 
}) {
  const isAiOnline = aiStatus?.ollama_available && aiStatus?.model_available;

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-[#1B3B2B] to-[#2B543D] text-[#F3F8F5] rounded-2xl p-6 shadow-md border border-[#2D503B] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="w-14 h-14 rounded-2xl bg-[#2C5B41] flex items-center justify-center text-3xl shadow-inner border border-[#3E7554] shrink-0">
            🦥
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              "Let your AI do the boring stuff. You take it slow."
            </h2>
            <p className="text-xs text-[#A8C7B6] mt-1">
              Organize downloads, coursework, research PDFs, and code projects without cloud subscriptions or telemetry.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onNavigate('organizer')}
            className="bg-[#FAF8F2] hover:bg-white text-[#1B3B2B] text-xs font-bold px-4 py-2.5 rounded-xl shadow transition-all cursor-pointer flex items-center gap-1.5"
          >
            <FileSearch className="w-4 h-4 text-[#2D5A40]" />
            Scan New Folder
          </button>
          <button
            onClick={onQuickSample}
            className="bg-[#2D5A40] hover:bg-[#386B4E] text-[#E8F3ED] text-xs font-semibold px-4 py-2.5 rounded-xl border border-[#437A5A] transition-all cursor-pointer flex items-center gap-1.5"
          >
            <FolderPlus className="w-4 h-4 text-[#84E1A9]" />
            Try Sample Playground
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Scanned Files */}
        <div className="bg-white rounded-2xl p-5 border border-[#E6E0D4] shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-[#5C6E63]">
            <span className="text-xs font-semibold uppercase tracking-wider">Files Scanned</span>
            <div className="p-2 rounded-xl bg-[#F0F5F2] text-[#2D5A40]">
              <FileSearch className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-[#14261C]">{summary?.total_files_scanned ?? 0}</span>
            <span className="text-xs text-[#7B8F83]">across all scans</span>
          </div>
          <p className="text-[11px] text-[#7B8F83] mt-2">
            Total scan sessions: <span className="font-semibold text-[#14261C]">{summary?.total_scans ?? 0}</span>
          </p>
        </div>

        {/* Pending Suggestions */}
        <div className="bg-white rounded-2xl p-5 border border-[#E6E0D4] shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-[#5C6E63]">
            <span className="text-xs font-semibold uppercase tracking-wider">Pending Review</span>
            <div className="p-2 rounded-xl bg-[#FEF4E8] text-[#D97706]">
              <ListFilter className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-[#D97706]">{summary?.pending_suggestions ?? 0}</span>
            <span className="text-xs text-[#7B8F83]">files waiting</span>
          </div>
          <div className="mt-2">
            {summary?.pending_suggestions > 0 ? (
              <button 
                onClick={() => onNavigate('queue')} 
                className="text-xs font-bold text-[#D97706] hover:underline flex items-center gap-1 cursor-pointer"
              >
                Go to Review Queue <ArrowRight className="w-3 h-3" />
              </button>
            ) : (
              <span className="text-[11px] text-[#7B8F83]">Queue is clear</span>
            )}
          </div>
        </div>

        {/* Actions Completed */}
        <div className="bg-white rounded-2xl p-5 border border-[#E6E0D4] shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-[#5C6E63]">
            <span className="text-xs font-semibold uppercase tracking-wider">Actions Completed</span>
            <div className="p-2 rounded-xl bg-[#EBF5EE] text-[#1B3B2B]">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-[#1B3B2B]">{summary?.executed_operations ?? 0}</span>
            <span className="text-xs text-[#7B8F83]">files organized</span>
          </div>
          <p className="text-[11px] text-[#7B8F83] mt-2">
            Undone actions: <span className="font-semibold text-[#14261C]">{summary?.undone_operations ?? 0}</span>
          </p>
        </div>

        {/* Estimated Time Saved */}
        <div className="bg-white rounded-2xl p-5 border border-[#E6E0D4] shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-[#5C6E63]">
            <span className="text-xs font-semibold uppercase tracking-wider">Est. Time Saved</span>
            <div className="p-2 rounded-xl bg-[#F0EFEB] text-[#4A6E59]">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-[#2D5A40]">{summary?.estimated_minutes_saved ?? 0}</span>
            <span className="text-xs text-[#7B8F83]">minutes</span>
          </div>
          <p className="text-[10px] text-[#7B8F83] mt-2 flex items-center gap-1" title={summary?.time_saved_formula_explanation}>
            <Info className="w-3 h-3 text-[#4A6E59] shrink-0" />
            <span className="truncate">~45s per organized file</span>
          </p>
        </div>
      </div>

      {/* Lazy Morning Brief Card */}
      <div className="bg-[#FAF6ED] rounded-2xl p-6 border border-[#E2D9C8] shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <span className="text-lg">☕</span>
            <h3 className="text-base font-bold text-[#14261C] tracking-tight">The Lazy Morning Brief</h3>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-[#E5DCC9] text-[#463B26]">
              Real Activity Report
            </span>
          </div>
          <span className="text-xs text-[#6F7A72]">
            Formula: {summary?.time_saved_formula_explanation ? 'Documented & Configurable' : 'Default 45s/file'}
          </span>
        </div>
        <p className="text-sm text-[#2D3F34] leading-relaxed font-medium">
          {summary?.lazy_morning_brief || "Good morning! No files have been scanned yet. Select a folder to begin."}
        </p>
        <div className="mt-3 pt-3 border-t border-[#EAE3D5] flex items-center justify-between text-xs text-[#6F7A72]">
          <span>Safety guarantee: Files are never automatically deleted or overwritten.</span>
          <button 
            onClick={() => onNavigate('history')} 
            className="text-xs font-semibold text-[#2D5A40] hover:underline flex items-center gap-1 cursor-pointer"
          >
            View full audit log <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* AI Connection & Privacy Card */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-2">
          <div className="flex items-center space-x-2">
            <Bot className="w-5 h-5 text-[#2D5A40]" />
            <h3 className="text-base font-bold text-[#14261C]">Local Open-Weight Intelligence</h3>
          </div>
          <p className="text-xs text-[#5C6E63] leading-relaxed">
            SlothDesk AI is designed to run completely on your local machine using Gemma open weights through Ollama. 
            Your file contents, names, coursework, and personal financial sheets never leave your disk.
          </p>
          <div className="pt-2 flex flex-wrap gap-2 text-xs">
            <span className="px-2.5 py-1 rounded-lg bg-[#EBF1ED] text-[#254633] font-medium flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#3A6B4E]" />
              Zero External API Keys
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-[#EBF1ED] text-[#254633] font-medium flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-[#3A6B4E]" />
              Offline Capable Once Downloaded
            </span>
          </div>
        </div>

        <div className="bg-[#FAF8F2] rounded-xl p-4 border border-[#E8E2D5] flex flex-col justify-between">
          <div>
            <div className="text-xs text-[#5C6E63] font-medium">Engine Status</div>
            <div className="mt-1 flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full ${isAiOnline ? 'bg-green-500 animate-pulse' : 'bg-amber-500'}`} />
              <span className="text-sm font-bold text-[#14261C]">
                {isAiOnline ? 'Ollama Active (Gemma)' : 'Deterministic Fallback'}
              </span>
            </div>
            <p className="text-[11px] text-[#7B8F83] mt-1 font-mono">
              {aiStatus?.current_model}
            </p>
          </div>
          <button
            onClick={() => onNavigate('settings')}
            className="mt-3 w-full py-1.5 px-3 rounded-lg bg-white hover:bg-[#F3EFE6] text-xs font-semibold text-[#14261C] border border-[#DDD5C5] transition-all cursor-pointer text-center"
          >
            Configure AI / Setup Guide →
          </button>
        </div>
      </div>

      {/* Recent Operations Audit Table */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-[#14261C]">Recent File Actions</h3>
            <p className="text-xs text-[#5C6E63]">Persistent SQLite audit log of executed file moves and renames</p>
          </div>
          <button
            onClick={() => onNavigate('history')}
            className="text-xs font-bold text-[#2D5A40] hover:underline"
          >
            View All ({recentOperations?.length || 0})
          </button>
        </div>

        {recentOperations && recentOperations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#FAF8F2] text-[#5C6E63] uppercase tracking-wider font-semibold border-b border-[#EAE3D5]">
                <tr>
                  <th className="py-2.5 px-3">Original File</th>
                  <th className="py-2.5 px-3">Destination Path</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F0ECE1]">
                {recentOperations.slice(0, 5).map((op) => (
                  <tr key={op.id} className="hover:bg-[#FAF8F2] transition-colors">
                    <td className="py-2.5 px-3 font-mono font-medium text-[#14261C] max-w-xs truncate" title={op.original_path}>
                      {op.original_path.split(/[\\/]/).pop()}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[#5C6E63] max-w-xs truncate" title={op.destination_path}>
                      {op.destination_path ? op.destination_path.split(/[\\/]/).slice(-2).join('/') : '—'}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        op.status === 'executed' 
                          ? 'bg-[#EBF5EE] text-[#1B3B2B]' 
                          : op.status === 'undone' 
                          ? 'bg-[#EAEAEA] text-[#6E6E6E]'
                          : 'bg-[#FCECEE] text-[#B91C1C]'
                      }`}>
                        {op.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[#7B8F83]">
                      {new Date(op.executed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {op.status === 'executed' && (
                        <button
                          onClick={() => onUndo(op.id)}
                          disabled={isUndoing}
                          className="text-xs font-semibold text-[#2D5A40] hover:text-[#14261C] flex items-center gap-1 justify-end ml-auto cursor-pointer"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Undo
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 bg-[#FAF8F2] rounded-xl border border-dashed border-[#DDD5C5]">
            <p className="text-xs text-[#7B8F83]">No file operations recorded yet.</p>
            <p className="text-[11px] text-[#A0AFA6] mt-1">Files you organize will appear here with one-click undo support.</p>
          </div>
        )}
      </div>
    </div>
  );
}
