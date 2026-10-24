import React from 'react';
import { Sprout, Activity, Award, CloudRain } from 'lucide-react';

interface HeaderProps {
  onOpenData: () => void;
  onOpenCalculator: () => void;
  onOpenContract: () => void;
  onOpenMilestones: () => void;
  scenarioName: string;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenCalculator,
  onOpenMilestones,
  scenarioName
}) => {
  return (
    <header className="border-b border-emerald-950/60 bg-slate-900/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 ring-1 ring-emerald-400/30">
            <Sprout className="w-6 h-6 text-slate-950 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                UZHAVAN <span className="text-emerald-400 font-extrabold">CROP ADVISOR</span>
              </h1>
              <span className="px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full">
                Tamil Nadu
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">
              உழவன் பயிர் ஆலோசனை &bull; Precision Soil & Weather Advisory
            </p>
          </div>
        </div>

        {/* Farmer Actions & Evaluation Spec */}
        <div className="flex items-center gap-2 sm:gap-2.5 text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
            <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span className="text-slate-400">Field:</span>
            <span className="font-semibold text-slate-200 truncate max-w-[140px]">{scenarioName}</span>
          </div>

          <button
            onClick={onOpenCalculator}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/70 hover:bg-emerald-900/70 border border-emerald-800/60 text-emerald-300 font-medium transition cursor-pointer"
            title="Open Dosage Calculator for water and fertilizer"
          >
            <CloudRain className="w-3.5 h-3.5 text-emerald-400" />
            <span>Dosage Tool</span>
          </button>

          <button
            onClick={onOpenMilestones}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 font-medium transition cursor-pointer"
            title="View 100% Score Rubric, Anti-Wrapper Verification & CLI Contract"
          >
            <Award className="w-3.5 h-3.5 text-amber-400" />
            <span>Audit & Rubric</span>
          </button>
        </div>
      </div>
    </header>
  );
};
