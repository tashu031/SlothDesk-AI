import React from 'react';
import { 
  LayoutDashboard, 
  FolderTree, 
  CheckSquare, 
  History, 
  Settings as SettingsIcon, 
  Cpu, 
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function Sidebar({ currentView, setCurrentView, aiStatus, pendingCount }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'organizer', label: 'File Organizer', icon: FolderTree },
    { 
      id: 'queue', 
      label: 'Review Queue', 
      icon: CheckSquare,
      badge: pendingCount > 0 ? pendingCount : null 
    },
    { id: 'history', label: 'Activity & Undo', icon: History },
    { id: 'settings', label: 'Settings & AI', icon: SettingsIcon }
  ];

  const isAiOnline = aiStatus?.ollama_available && aiStatus?.model_available;

  return (
    <aside className="w-64 bg-[#14261C] text-[#E8EFE9] flex flex-col justify-between shrink-0 h-screen sticky top-0 border-r border-[#223B2D] select-none">
      {/* Brand Header */}
      <div>
        <div className="p-6 border-b border-[#223B2D] flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[#2D5A40] flex items-center justify-center text-2xl shadow-inner border border-[#3E7354]">
            🦥
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="font-bold text-lg text-[#F4F9F5] tracking-tight">SlothDesk</span>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded bg-[#2D5A40] text-[#A7D1B7]">AI</span>
            </div>
            <p className="text-xs text-[#8BA897]">Slow and Steady Productivity</p>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="p-4 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-[#254633] text-white shadow-sm font-semibold'
                    : 'text-[#B0C7B9] hover:bg-[#1B3526] hover:text-[#E8EFE9]'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#84E1A9]' : 'text-[#7D9E8A]'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-[#E58325] text-white animate-pulse">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* AI Engine Status Card in Sidebar */}
      <div className="p-4 border-t border-[#223B2D] space-y-3">
        <div className="bg-[#1C3627] rounded-xl p-3 border border-[#2D503B]">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-[#B0C7B9] flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-[#84E1A9]" />
              Inference Mode
            </span>
            <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full ${
              isAiOnline 
                ? 'bg-[#1C4E2D] text-[#84E1A9]' 
                : 'bg-[#4A3B18] text-[#F3C465]'
            }`}>
              {isAiOnline ? (
                <>
                  <CheckCircle2 className="w-3 h-3" />
                  Gemma AI
                </>
              ) : (
                <>
                  <AlertCircle className="w-3 h-3" />
                  Deterministic
                </>
              )}
            </span>
          </div>

          <p className="text-[11px] text-[#8FAFA0] truncate">
            Model: <span className="font-mono text-[#D4E8DC]">{aiStatus?.current_model || 'gemma2:2b'}</span>
          </p>

          <div className="mt-2 pt-2 border-t border-[#274533] flex items-center justify-between text-[11px] text-[#7A9E8A]">
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-[#84E1A9]" />
              100% Local & Private
            </span>
            <span className="text-[10px] bg-[#162B1F] px-1.5 py-0.5 rounded text-[#96B8A5]">v1.0</span>
          </div>
        </div>

        <p className="text-[10px] text-center text-[#6A8875]">
          Hacktoberfest 2026 • Week 3 "Slow & Steady"
        </p>
      </div>
    </aside>
  );
}
