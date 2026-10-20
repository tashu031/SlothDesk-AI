import React, { useState } from 'react';
import { 
  Cpu, 
  Settings as SettingsIcon, 
  ShieldCheck, 
  Terminal, 
  Copy, 
  Check, 
  Activity, 
  Play, 
  CheckCircle2, 
  XCircle,
  Clock,
  Sparkles,
  Save,
  BookOpen
} from 'lucide-react';
import { updateSettings, runEvaluation } from '../api';

export default function SettingsView({ aiStatus, currentSettings, onSettingsUpdated }) {
  const [modelName, setModelName] = useState(currentSettings?.model_name || 'gemma2:2b');
  const [ollamaUrl, setOllamaUrl] = useState(currentSettings?.ollama_base_url || 'http://localhost:11434');
  const [secondsSaved, setSecondsSaved] = useState(currentSettings?.seconds_saved_per_file || 45);
  const [copiedCmd, setCopiedCmd] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Benchmark evaluation state
  const [isRunningEval, setIsRunningEval] = useState(false);
  const [evalResult, setEvalResult] = useState(null);

  const handleCopy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(key);
    setTimeout(() => setCopiedCmd(''), 2000);
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      const res = await updateSettings({
        model_name: modelName,
        ollama_base_url: ollamaUrl,
        seconds_saved_per_file: Number(secondsSaved)
      });
      if (res?.status === 'updated') {
        setSaveSuccess(true);
        if (onSettingsUpdated) onSettingsUpdated();
        setTimeout(() => setSaveSuccess(false), 3000);
      }
    } catch (err) {
      alert('Failed to save settings: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRunEvaluation = async (forceDeterministic = false) => {
    setIsRunningEval(true);
    try {
      const res = await runEvaluation(forceDeterministic);
      setEvalResult(res);
    } catch (err) {
      alert('Evaluation failed: ' + err.message);
    } finally {
      setIsRunningEval(false);
    }
  };

  const isAiOnline = aiStatus?.ollama_available && aiStatus?.model_available;

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Page Title */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-[#EBF5EE] text-[#1B3B2B]">
            <SettingsIcon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[#14261C] tracking-tight">Settings & AI Diagnostics</h2>
            <p className="text-xs text-[#5C6E63]">
              Configure local inference, model weights, time-saving heuristics, and run real classification benchmarks.
            </p>
          </div>
        </div>
      </div>

      {/* AI Health & Model Configuration */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Form settings */}
        <div className="md:col-span-2 bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm space-y-5">
          <h3 className="text-base font-bold text-[#14261C] flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#2D5A40]" />
            Local AI Engine Preferences
          </h3>

          <form onSubmit={handleSaveSettings} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-[#4A5D52] uppercase mb-1">
                Ollama Model Tag
              </label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="e.g. gemma2:2b or gemma:2b"
                className="w-full px-3.5 py-2 bg-[#FAF8F2] border border-[#DDD5C5] rounded-xl text-xs font-mono text-[#14261C] focus:outline-none focus:ring-2 focus:ring-[#2D5A40]"
                required
              />
              <p className="text-[11px] text-[#7B8F83] mt-1">
                Recommended: <code className="text-[#2D5A40] font-semibold">gemma2:2b</code> (Google open weights, 1.6 GB, fast inference on laptops).
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#4A5D52] uppercase mb-1">
                Ollama HTTP Base URL
              </label>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder="http://localhost:11434"
                className="w-full px-3.5 py-2 bg-[#FAF8F2] border border-[#DDD5C5] rounded-xl text-xs font-mono text-[#14261C] focus:outline-none focus:ring-2 focus:ring-[#2D5A40]"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#4A5D52] uppercase mb-1">
                Estimated Time Saved per File (Seconds)
              </label>
              <input
                type="number"
                min="5"
                max="3600"
                value={secondsSaved}
                onChange={(e) => setSecondsSaved(e.target.value)}
                className="w-full px-3.5 py-2 bg-[#FAF8F2] border border-[#DDD5C5] rounded-xl text-xs font-mono text-[#14261C] focus:outline-none focus:ring-2 focus:ring-[#2D5A40]"
                required
              />
              <p className="text-[11px] text-[#7B8F83] mt-1">
                Used in the Lazy Morning Brief to estimate manual time saved (reviewing, creating subdirectories, moving).
              </p>
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-[#2D5A40] font-semibold">
                {saveSuccess ? '✓ Settings updated successfully' : ''}
              </span>
              <button
                type="submit"
                disabled={isSaving}
                className="px-5 py-2 bg-[#2D5A40] hover:bg-[#234732] text-white text-xs font-bold rounded-xl shadow cursor-pointer transition-all flex items-center gap-1.5"
              >
                <Save className="w-3.5 h-3.5" />
                {isSaving ? 'Saving...' : 'Save Preferences'}
              </button>
            </div>
          </form>
        </div>

        {/* Live Diagnostics Pill */}
        <div className="bg-[#FAF8F2] rounded-2xl p-6 border border-[#E6E0D4] shadow-sm flex flex-col justify-between space-y-4">
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#5C6E63]">Live Status</h4>
            <div className="mt-3 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#5C6E63]">Ollama Service:</span>
                <span className={`font-semibold ${aiStatus?.ollama_available ? 'text-green-700' : 'text-amber-700'}`}>
                  {aiStatus?.ollama_available ? 'Running' : 'Offline / Unreachable'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-[#5C6E63]">Target Model:</span>
                <span className={`font-semibold ${aiStatus?.model_available ? 'text-green-700' : 'text-amber-700'}`}>
                  {aiStatus?.model_available ? 'Ready' : 'Not Pulled'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-[#5C6E63]">Inference Mode:</span>
                <span className="font-mono text-[#14261C] font-semibold">
                  {aiStatus?.inference_mode}
                </span>
              </div>

              <div className="pt-2 border-t border-[#DDD5C5]">
                <span className="text-[#5C6E63] block mb-1">Installed Models:</span>
                <div className="bg-white p-2 rounded-lg border border-[#DDD5C5] text-[11px] font-mono text-[#14261C] max-h-24 overflow-y-auto">
                  {aiStatus?.available_models && aiStatus.available_models.length > 0 ? (
                    aiStatus.available_models.map((m, i) => <div key={i}>• {m}</div>)
                  ) : (
                    <span className="text-[#8FA094]">None detected yet</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-[#DDD5C5] text-[11px] text-[#5C6E63]">
            Offline Ready: <span className="font-semibold text-[#14261C]">100% Guaranteed</span>
          </div>
        </div>
      </div>

      {/* Step-by-Step Setup Guide */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm space-y-4">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-[#2D5A40]" />
          <h3 className="text-base font-bold text-[#14261C]">Quick Setup: Activate Local Gemma in 2 Minutes</h3>
        </div>
        <p className="text-xs text-[#5C6E63]">
          If you want to run open-weight Gemma locally on Windows without sending any file names to third parties:
        </p>

        <div className="space-y-3 text-xs">
          {/* Step 1 */}
          <div className="bg-[#FAF8F2] p-3.5 rounded-xl border border-[#E8E2D5] flex items-center justify-between">
            <div>
              <span className="font-bold text-[#14261C]">Step 1: Download Ollama for Windows</span>
              <p className="text-[#5C6E63] text-[11px] mt-0.5">Free, open-source local inference engine</p>
            </div>
            <a
              href="https://ollama.com/download"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1 bg-white hover:bg-[#F0ECE1] text-[#2D5A40] text-xs font-semibold rounded-lg border border-[#DDD5C5]"
            >
              ollama.com/download ↗
            </a>
          </div>

          {/* Step 2 */}
          <div className="bg-[#FAF8F2] p-3.5 rounded-xl border border-[#E8E2D5] flex items-center justify-between">
            <div className="flex-1 mr-3">
              <span className="font-bold text-[#14261C]">Step 2: Pull the Gemma 2B model</span>
              <p className="font-mono text-[11px] text-[#2D5A40] bg-white px-2 py-1 rounded border border-[#E0D8C8] mt-1 inline-block">
                ollama pull gemma2:2b
              </p>
            </div>
            <button
              onClick={() => handleCopy('ollama pull gemma2:2b', 'pull')}
              className="px-3 py-1.5 bg-white hover:bg-[#F0ECE1] text-[#14261C] text-xs font-semibold rounded-lg border border-[#DDD5C5] flex items-center gap-1 cursor-pointer"
            >
              {copiedCmd === 'pull' ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
              {copiedCmd === 'pull' ? 'Copied' : 'Copy'}
            </button>
          </div>

          {/* Step 3 */}
          <div className="bg-[#FAF8F2] p-3.5 rounded-xl border border-[#E8E2D5]">
            <span className="font-bold text-[#14261C]">Step 3: Refresh SlothDesk AI</span>
            <p className="text-[#5C6E63] text-[11px] mt-0.5">
              The status indicator will automatically switch to <span className="font-semibold text-[#2D5A40]">Ollama Active (Gemma)</span>.
            </p>
          </div>
        </div>
      </div>

      {/* Benchmark Evaluation Section */}
      <div className="bg-white rounded-2xl p-6 border border-[#E6E0D4] shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#F0ECE1] gap-2">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#2D5A40]" />
              <h3 className="text-base font-bold text-[#14261C]">Real Evaluation Benchmark</h3>
            </div>
            <p className="text-xs text-[#5C6E63] mt-0.5">
              Runs a labeled test dataset against the active classifier to measure genuine accuracy and latency.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleRunEvaluation(true)}
              disabled={isRunningEval}
              className="px-3 py-1.5 rounded-xl bg-[#FAF8F2] hover:bg-[#F0ECE1] text-[#5C6E63] text-xs font-semibold border border-[#DDD5C5] cursor-pointer"
            >
              Benchmark Rules
            </button>
            <button
              onClick={() => handleRunEvaluation(false)}
              disabled={isRunningEval}
              className="px-4 py-1.5 rounded-xl bg-[#2D5A40] hover:bg-[#234732] text-white text-xs font-bold shadow flex items-center gap-1.5 cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 text-[#84E1A9]" />
              {isRunningEval ? 'Evaluating...' : 'Run Benchmark'}
            </button>
          </div>
        </div>

        {evalResult ? (
          <div className="space-y-4">
            {/* Metric Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-[#FAF8F2] p-4 rounded-xl border border-[#E8E2D5]">
                <div className="text-[11px] text-[#5C6E63] font-semibold uppercase">Accuracy</div>
                <div className="text-2xl font-bold text-[#2D5A40] mt-1">
                  {evalResult.accuracy_percentage}%
                </div>
                <div className="text-[11px] text-[#7B8F83] mt-0.5">
                  {evalResult.correct_classifications} of {evalResult.total_samples} correct
                </div>
              </div>

              <div className="bg-[#FAF8F2] p-4 rounded-xl border border-[#E8E2D5]">
                <div className="text-[11px] text-[#5C6E63] font-semibold uppercase">Avg Latency</div>
                <div className="text-2xl font-bold text-[#14261C] mt-1 font-mono">
                  {evalResult.average_latency_ms} ms
                </div>
                <div className="text-[11px] text-[#7B8F83] mt-0.5">
                  Real measured execution time
                </div>
              </div>

              <div className="bg-[#FAF8F2] p-4 rounded-xl border border-[#E8E2D5]">
                <div className="text-[11px] text-[#5C6E63] font-semibold uppercase">Model Evaluated</div>
                <div className="text-lg font-bold text-[#14261C] mt-1 font-mono truncate">
                  {evalResult.model_tested}
                </div>
                <div className="text-[11px] text-[#7B8F83] mt-0.5">
                  {evalResult.is_fallback ? 'Rule Classifier' : 'Local Gemma LLM'}
                </div>
              </div>
            </div>

            {/* Benchmark details table */}
            <div className="overflow-x-auto border border-[#EAE3D5] rounded-xl max-h-64 overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#FAF8F2] text-[#5C6E63] font-semibold border-b border-[#EAE3D5] sticky top-0">
                  <tr>
                    <th className="py-2 px-3">Test File</th>
                    <th className="py-2 px-3">Expected</th>
                    <th className="py-2 px-3">Predicted</th>
                    <th className="py-2 px-3">Latency</th>
                    <th className="py-2 px-3 text-right">Result</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0ECE1]">
                  {evalResult.details.map((d, i) => (
                    <tr key={i} className="hover:bg-[#FAF8F2]">
                      <td className="py-2 px-3 font-mono text-[#14261C]">{d.filename}</td>
                      <td className="py-2 px-3 text-[#5C6E63]">{d.expected_category}</td>
                      <td className="py-2 px-3 font-semibold text-[#14261C]">{d.predicted_category}</td>
                      <td className="py-2 px-3 font-mono text-[#7B8F83]">{d.latency_ms} ms</td>
                      <td className="py-2 px-3 text-right">
                        {d.correct ? (
                          <span className="text-green-700 font-bold">✓ Pass</span>
                        ) : (
                          <span className="text-red-600 font-bold">✗ Fail</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-[#FAF8F2] rounded-xl border border-[#E8E2D5] text-xs text-[#5C6E63] text-center">
            Click "Run Benchmark" to execute the 10-item labeled test suite and view measured accuracy and latency.
          </div>
        )}
      </div>

      {/* Open Source Manifesto Card */}
      <div className="bg-[#14261C] text-[#E8EFE9] rounded-2xl p-6 border border-[#223B2D] space-y-3">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-[#84E1A9]" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Why Open Weights & Local Inference Matter
          </h3>
        </div>
        <p className="text-xs text-[#A8C7B6] leading-relaxed">
          SlothDesk AI was built for Hacktoberfest 2026 Week 3: "Slow and Steady." Rather than rushing to funnel your personal desktop data into centralized cloud APIs with unpredictable subscription pricing and surveillance risks, SlothDesk AI proves that local open-weight models like Gemma offer complete privacy, predictable performance, offline resilience, and total model ownership.
        </p>
      </div>
    </div>
  );
}
