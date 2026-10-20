import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import OverviewView from './components/OverviewView';
import OrganizerView from './components/OrganizerView';
import ApprovalQueueView from './components/ApprovalQueueView';
import HistoryView from './components/HistoryView';
import SettingsView from './components/SettingsView';
import {
  fetchAIStatus,
  fetchSummary,
  fetchHistory,
  fetchSettings,
  scanFolder,
  createSamplePlayground,
  generateSuggestions,
  approveSuggestions,
  executeActions,
  undoOperation
} from './api';

export default function App() {
  const [currentView, setCurrentView] = useState('overview');
  const [aiStatus, setAiStatus] = useState(null);
  const [summary, setSummary] = useState(null);
  const [operations, setOperations] = useState([]);
  const [currentSettings, setCurrentSettings] = useState(null);

  // Active workflow state
  const [currentScan, setCurrentScan] = useState(null);
  const [suggestions, setSuggestions] = useState([]);

  // Loading states
  const [isScanning, setIsScanning] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isUndoing, setIsUndoing] = useState(false);

  // Notification Toast
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const refreshCoreData = async () => {
    try {
      const [ai, sum, hist, sett] = await Promise.all([
        fetchAIStatus().catch(() => null),
        fetchSummary().catch(() => null),
        fetchHistory().catch(() => ({ operations: [] })),
        fetchSettings().catch(() => null)
      ]);
      if (ai) setAiStatus(ai);
      if (sum) setSummary(sum);
      if (hist?.operations) setOperations(hist.operations);
      if (sett) setCurrentSettings(sett);
    } catch (e) {
      console.error('Error refreshing core data:', e);
    }
  };

  useEffect(() => {
    refreshCoreData();
    const interval = setInterval(refreshCoreData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleScan = async (folderPath, recursive, maxFiles) => {
    setIsScanning(true);
    try {
      const scanData = await scanFolder(folderPath, recursive, maxFiles);
      setCurrentScan(scanData);
      showToast(`Scanned ${scanData.files_scanned} files successfully!`, 'success');
      refreshCoreData();
    } catch (err) {
      showToast(`Scan error: ${err.message}`, 'error');
    } finally {
      setIsScanning(false);
    }
  };

  const handleQuickSample = async () => {
    setIsScanning(true);
    try {
      const sample = await createSamplePlayground();
      const scanData = await scanFolder(sample.sample_dir, true, 100);
      setCurrentScan(scanData);
      showToast(`Loaded sample messy folder with ${scanData.files_scanned} files!`, 'success');
      setCurrentView('organizer');
      refreshCoreData();
    } catch (err) {
      showToast(`Sample creation failed: ${err.message}`, 'error');
    } finally {
      setIsScanning(false);
    }
  };

  const handleGenerateSuggestions = async (sessionId, rootPath, files) => {
    setIsGenerating(true);
    try {
      const res = await generateSuggestions(sessionId, rootPath, files);
      setSuggestions(res.suggestions);
      showToast(`Generated ${res.suggestions.length} organization suggestions!`, 'success');
      setCurrentView('queue');
      refreshCoreData();
    } catch (err) {
      showToast(`Suggestion generation failed: ${err.message}`, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExecute = async (rootPath, actions) => {
    setIsExecuting(true);
    try {
      const approvedIds = actions.filter(a => a.approved).map(a => a.id);
      if (approvedIds.length > 0) {
        await approveSuggestions(approvedIds);
      }
      const res = await executeActions(rootPath, actions);
      showToast(`Executed ${res.total_succeeded} action(s) safely!`, 'success');
      // Remove executed suggestions from pending queue
      const executedIds = new Set(res.results.filter(r => r.success).map(r => r.action_id));
      setSuggestions(prev => prev.filter(s => !executedIds.has(s.id)));
      await refreshCoreData();
      return res;
    } catch (err) {
      showToast(`Execution failed: ${err.message}`, 'error');
      return null;
    } finally {
      setIsExecuting(false);
    }
  };

  const handleUndo = async (operationId) => {
    setIsUndoing(true);
    try {
      const res = await undoOperation(operationId);
      if (res.success) {
        showToast(res.message, 'success');
      } else {
        showToast(`Undo blocked: ${res.message}`, 'error');
      }
      refreshCoreData();
    } catch (err) {
      showToast(`Undo request failed: ${err.message}`, 'error');
    } finally {
      setIsUndoing(false);
    }
  };

  const handleUpdateSuggestion = (id, updates) => {
    setSuggestions(prev => prev.map(s => s.id === id ? { ...s, ...updates } : s));
  };

  const getPageInfo = () => {
    switch (currentView) {
      case 'overview':
        return { title: 'Dashboard', subtitle: 'Overview of files, pending reviews, and local AI activity' };
      case 'organizer':
        return { title: 'File Organizer', subtitle: 'Scan messy folders and prepare an intelligent action plan' };
      case 'queue':
        return { title: 'Review & Approval Queue', subtitle: 'Review proposed moves and renames before execution' };
      case 'history':
        return { title: 'Activity History & Undo', subtitle: 'Persistent SQLite audit trail with one-click reversal' };
      case 'settings':
        return { title: 'Settings & AI Diagnostics', subtitle: 'Configure Ollama Gemma model, offline settings, and benchmarks' };
      default:
        return { title: 'SlothDesk AI', subtitle: 'Slow and Steady AI Productivity' };
    }
  };

  const pageInfo = getPageInfo();

  return (
    <div className="flex min-h-screen bg-[#FAF8F2] text-[#14261C] font-sans antialiased selection:bg-[#2D5A40] selection:text-white">
      {/* Fixed Sidebar */}
      <Sidebar
        currentView={currentView}
        setCurrentView={setCurrentView}
        aiStatus={aiStatus}
        pendingCount={suggestions.length}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          title={pageInfo.title}
          subtitle={pageInfo.subtitle}
          onQuickSample={handleQuickSample}
          isScanning={isScanning}
        />

        {/* Global Floating Toast */}
        {toast && (
          <div className="fixed bottom-6 right-6 z-50 animate-bounce">
            <div className={`px-4 py-3 rounded-xl shadow-lg border text-xs font-semibold flex items-center space-x-2 ${
              toast.type === 'success'
                ? 'bg-[#1B3B2B] text-[#84E1A9] border-[#2D5A40]'
                : toast.type === 'error'
                ? 'bg-[#4A1515] text-[#FCA5A5] border-[#7F1D1D]'
                : 'bg-[#1E293B] text-white border-slate-700'
            }`}>
              <span>{toast.message}</span>
            </div>
          </div>
        )}

        {/* View Switcher */}
        <main className="flex-1 pb-16">
          {currentView === 'overview' && (
            <OverviewView
              summary={summary}
              aiStatus={aiStatus}
              recentOperations={operations}
              onNavigate={setCurrentView}
              onQuickSample={handleQuickSample}
              onUndo={handleUndo}
              isUndoing={isUndoing}
            />
          )}

          {currentView === 'organizer' && (
            <OrganizerView
              currentScan={currentScan}
              isScanning={isScanning}
              onScan={handleScan}
              onQuickSample={handleQuickSample}
              onGenerateSuggestions={handleGenerateSuggestions}
              isGenerating={isGenerating}
              defaultPath={currentSettings?.sample_dir}
            />
          )}

          {currentView === 'queue' && (
            <ApprovalQueueView
              suggestions={suggestions}
              rootPath={currentScan?.root_path || ''}
              onExecute={handleExecute}
              isExecuting={isExecuting}
              onUpdateSuggestion={handleUpdateSuggestion}
              onNavigate={setCurrentView}
            />
          )}

          {currentView === 'history' && (
            <HistoryView
              operations={operations}
              onUndo={handleUndo}
              isUndoing={isUndoing}
            />
          )}

          {currentView === 'settings' && (
            <SettingsView
              aiStatus={aiStatus}
              currentSettings={currentSettings}
              onSettingsUpdated={refreshCoreData}
            />
          )}
        </main>
      </div>
    </div>
  );
}
