import React from 'react';
import { Sparkles, Shield, Coffee, FolderPlus } from 'lucide-react';

export default function Header({ title, subtitle, onQuickSample, isScanning }) {
  return (
    <header className="bg-[#FAF8F2] border-b border-[#E8E2D5] px-8 py-5 flex items-center justify-between sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <div>
        <div className="flex items-center space-x-2">
          <h1 className="text-2xl font-bold text-[#14261C] tracking-tight">{title}</h1>
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-[#EBF1ED] text-[#254633] border border-[#CCD8D0] flex items-center gap-1">
            <Coffee className="w-3 h-3 text-[#3E7354]" />
            Take it slow
          </span>
        </div>
        <p className="text-xs text-[#5C6E63] mt-0.5">{subtitle}</p>
      </div>

      <div className="flex items-center space-x-3">
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#EBF1ED] text-xs text-[#2A4B38] font-medium border border-[#CCD8D0]">
          <Shield className="w-3.5 h-3.5 text-[#3A6B4E]" />
          <span>Zero Cloud Telemetry</span>
        </div>

        <button
          onClick={onQuickSample}
          disabled={isScanning}
          className="inline-flex items-center space-x-2 bg-[#2D5A40] hover:bg-[#234732] text-white text-xs font-semibold px-3.5 py-2 rounded-lg shadow-sm hover:shadow transition-all duration-150 disabled:opacity-50 cursor-pointer"
          title="Instantly generate and scan a messy folder playground with PDFs, scripts, and notes"
        >
          <FolderPlus className="w-3.5 h-3.5 text-[#84E1A9]" />
          <span>{isScanning ? 'Loading Sample...' : 'Try Sample Playground'}</span>
        </button>
      </div>
    </header>
  );
}
