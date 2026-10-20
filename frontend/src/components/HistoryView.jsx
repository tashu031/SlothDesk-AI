import React, { useState } from 'react';
import { 
  History, 
  RotateCcw, 
  CheckCircle, 
  AlertCircle, 
  Search, 
  ShieldCheck, 
  FileText,
  Clock
} from 'lucide-react';

export default function HistoryView({ operations, onUndo, isUndoing }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const filteredOps = (operations || []).filter((op) => {
    const matchesSearch = 
      op.original_path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      op.destination_path.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (filterStatus === 'all') return matchesSearch;
    return matchesSearch && op.status === filterStatus;
  });

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Header and Filter Card */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#F0ECE1] gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-[#14261C] tracking-tight">Activity History & Undo</h2>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-[#FAF8F2] border border-[#DDD5C5] text-[#2D5A40]">
                {operations.length} operations
              </span>
            </div>
            <p className="text-xs text-[#5C6E63] mt-0.5">
              Every file moved or renamed by SlothDesk AI is logged in SQLite with one-click safe reversal.
            </p>
          </div>

          {/* Search Box */}
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 text-[#7B8F83] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search past files..."
              className="w-full pl-9 pr-3 py-1.5 bg-[#FAF8F2] border border-[#DDD5C5] rounded-xl text-xs text-[#14261C] focus:outline-none focus:ring-1 focus:ring-[#2D5A40]"
            />
          </div>
        </div>

        {/* Filters and Undo Assurance */}
        <div className="mt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-[#7B8F83] font-medium">Status:</span>
            {['all', 'executed', 'undone', 'failed'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-2.5 py-1 rounded-lg font-medium capitalize transition-colors cursor-pointer ${
                  filterStatus === st
                    ? 'bg-[#2D5A40] text-white'
                    : 'bg-[#FAF8F2] text-[#5C6E63] hover:bg-[#F0ECE1]'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <div className="text-[11px] text-[#5C6E63] flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-[#2D5A40]" />
            <span>Filesystem verification guaranteed before reversing any move.</span>
          </div>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm">
        {filteredOps.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#FAF8F2] text-[#5C6E63] uppercase tracking-wider font-semibold border-b border-[#EAE3D5]">
                <tr>
                  <th className="py-3 px-3">Original Location</th>
                  <th className="py-3 px-3">Organized Location</th>
                  <th className="py-3 px-3">Size</th>
                  <th className="py-3 px-3">Executed At</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F0ECE1]">
                {filteredOps.map((op) => (
                  <tr key={op.id} className="hover:bg-[#FAF8F2] transition-colors">
                    <td className="py-3 px-3 font-mono text-[#14261C] max-w-xs truncate" title={op.original_path}>
                      {op.original_path}
                    </td>
                    <td className="py-3 px-3 font-mono font-medium text-[#2D5A40] max-w-xs truncate" title={op.destination_path}>
                      {op.destination_path || '—'}
                    </td>
                    <td className="py-3 px-3 text-[#5C6E63] font-mono">
                      {formatBytes(op.file_size)}
                    </td>
                    <td className="py-3 px-3 text-[#7B8F83]">
                      {new Date(op.executed_at).toLocaleString([], { 
                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
                      })}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        op.status === 'executed'
                          ? 'bg-[#EBF5EE] text-[#1B3B2B]'
                          : op.status === 'undone'
                          ? 'bg-[#EAEAEA] text-[#6E6E6E]'
                          : 'bg-[#FCECEE] text-[#B91C1C]'
                      }`}>
                        {op.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      {op.status === 'executed' ? (
                        <button
                          onClick={() => onUndo(op.id)}
                          disabled={isUndoing}
                          className="px-3 py-1 rounded-lg bg-[#FAF8F2] hover:bg-[#F0ECE1] text-[#2D5A40] text-xs font-semibold border border-[#DDD5C5] inline-flex items-center gap-1 cursor-pointer transition-all disabled:opacity-50"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Undo Move
                        </button>
                      ) : op.status === 'undone' ? (
                        <span className="text-[11px] text-[#8BA094] flex items-center justify-end gap-1">
                          <CheckCircle className="w-3 h-3 text-[#3A6B4E]" />
                          Restored
                        </span>
                      ) : (
                        <span className="text-[11px] text-red-600 font-mono">
                          {op.error_message ? op.error_message.slice(0, 20) + '...' : 'Failed'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 bg-[#FAF8F2] rounded-xl border border-dashed border-[#DDD5C5]">
            <Clock className="w-8 h-8 text-[#A0B0A7] mx-auto mb-2" />
            <h4 className="text-xs font-bold text-[#14261C]">No matching operations found</h4>
            <p className="text-[11px] text-[#7B8F83] mt-0.5">
              {searchQuery ? 'Try adjusting your search query.' : 'Executed file operations will appear here.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
