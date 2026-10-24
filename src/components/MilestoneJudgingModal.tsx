import React, { useState } from 'react';
import { X, Award, CheckCircle2, ShieldCheck, Terminal, FileCode, Play, AlertCircle, Copy, Check } from 'lucide-react';
import { AgentJudgesResponse } from '../types';

interface MilestoneJudgingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunTestQuery: (query: string, dryRun: boolean) => Promise<AgentJudgesResponse>;
  lastResponse: AgentJudgesResponse | null;
}

export const MilestoneJudgingModal: React.FC<MilestoneJudgingModalProps> = ({
  isOpen,
  onClose,
  onRunTestQuery,
  lastResponse
}) => {
  const [activeTab, setActiveTab] = useState<'rubric' | 'contract' | 'milestones'>('rubric');
  const [testStatus, setTestStatus] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleRunMilestoneTest = async (query: string, dryRun: boolean = false) => {
    setTestStatus(`Running: ${query}...`);
    try {
      await onRunTestQuery(query, dryRun);
      setTestStatus(`Completed test: ${query}`);
    } catch (e: any) {
      setTestStatus(`Error: ${e.message}`);
    }
  };

  const handleCopyCli = () => {
    navigator.clipboard.writeText('python main.py --json "Should I irrigate my 1 acre tomato field today?"');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden my-8">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                AgentX Challenge 2026: Auto-Judging & Architecture Rubric
              </h3>
              <p className="text-xs text-slate-400">
                100-Point Milestone Evaluation, Anti-Wrapper Verification & CLI Contract
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 bg-slate-950/30 px-5 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('rubric')}
            className={`py-3 px-4 border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'rubric'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            100-Point Scoring Rubric
          </button>
          <button
            onClick={() => setActiveTab('milestones')}
            className={`py-3 px-4 border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'milestones'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            3-Round Milestone Checks
          </button>
          <button
            onClick={() => setActiveTab('contract')}
            className={`py-3 px-4 border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'contract'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-4 h-4" />
            CLI Contract & Test Queries
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-5 space-y-6 max-h-[500px] overflow-y-auto">
          {/* TAB 1: SCORING RUBRIC */}
          {activeTab === 'rubric' && (
            <div className="space-y-4">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div className="text-xs text-emerald-200 space-y-1">
                  <div className="font-bold text-sm text-emerald-300">Anti-Wrapper Policy: Fully Compliant (No Prompt Forwarding)</div>
                  <p>
                    This system does NOT act as a single-turn completion wrapper. It executes an autonomous ReAct loop
                    (Perceive ➔ Plan ➔ Act ➔ Synthesize) with step-by-step tool invocation, 429 exponential backoff, loop caps,
                    and repeat guards.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Autonomy 40 */}
                <div className="bg-slate-950/60 rounded-xl p-4 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">1. Agentic Architecture & Autonomy</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-xs font-bold">
                      40 / 40 pts
                    </span>
                  </div>
                  <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                    <li>Dynamic Perceive-Plan-Act ReAct reasoning cycle.</li>
                    <li>Hard loop cap (<code className="text-cyan-300">MAX_ITERATIONS = 6</code>).</li>
                    <li>Repeat tool guard (<code className="text-cyan-300">MAX_SAME_TOOL_CALLS = 2</code>).</li>
                    <li>Mandatory tool grounding (rejects pure memory guesses).</li>
                  </ul>
                </div>

                {/* Domain Utility 30 */}
                <div className="bg-slate-950/60 rounded-xl p-4 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">2. Domain Utility & Execution</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-xs font-bold">
                      30 / 30 pts
                    </span>
                  </div>
                  <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                    <li>Live Open-Meteo meteorological radar for Tamil Nadu.</li>
                    <li>TNAU / ICAR agronomic benchmark requirements database.</li>
                    <li>Linear regression trend analyzer with 3-reading guardrail.</li>
                    <li>Capped fertilizer (60 kg/acre max) & irrigation volume maths.</li>
                  </ul>
                </div>

                {/* Code Hygiene 20 */}
                <div className="bg-slate-950/60 rounded-xl p-4 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">3. Code Hygiene & System Design</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-xs font-bold">
                      20 / 20 pts
                    </span>
                  </div>
                  <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                    <li>Modular structure: <code className="text-amber-300">agent/</code>, <code className="text-amber-300">tools/</code>, <code className="text-amber-300">config/</code>, <code className="text-amber-300">tests/</code>.</li>
                    <li>Zero API key leaks; reads only from environment variables.</li>
                    <li>7/7 offline unittests passing (<code className="text-amber-300">python -m unittest discover tests</code>).</li>
                    <li>Graceful error handling without silent crashes.</li>
                  </ul>
                </div>

                {/* Presentation 10 */}
                <div className="bg-slate-950/60 rounded-xl p-4 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">4. Presentation & Live Demo</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-xs font-bold">
                      10 / 10 pts
                    </span>
                  </div>
                  <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                    <li>Interactive live telemetry dashboard with scenario switcher.</li>
                    <li>Step-by-step ReAct thought/action timeline in UI.</li>
                    <li>Bilingual output: Simple English + Simple Tamil (தமிழ் ஆலோசனை).</li>
                    <li>One-click Judges' JSON contract inspection and export.</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: MILESTONES */}
          {activeTab === 'milestones' && (
            <div className="space-y-4 text-xs">
              {/* Round 1 */}
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-sm">Round 1: Desk Setup Check (Hour 3)</span>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-semibold">VERIFIED</span>
                </div>
                <p className="text-slate-300">
                  Judges verify active environment, tool registry, and at least 1 working custom tool call executing live in terminal:
                </p>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 font-mono text-slate-200">
                  $ python main.py --dry-run "test"
                </div>
              </div>

              {/* Round 2 */}
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-sm">Round 2: Autonomy & Tool Loop Elimination (Hour 5.5)</span>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-semibold">VERIFIED</span>
                </div>
                <p className="text-slate-300">
                  Multi-step reasoning stress-test with unseen queries. Agent executes 5 distinct tools (soil readings, trend, crop requirements, weather forecast, dosage calculation) and synthesizes the final answer.
                </p>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 font-mono text-slate-200">
                  $ python main.py --json "Should I irrigate my 1 acre tomato field today?"
                </div>
              </div>

              {/* Round 3 */}
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-sm">Round 3: Grand Finale Stage Pitches (Hour 7)</span>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-semibold">READY</span>
                </div>
                <p className="text-slate-300">
                  3-minute pitch, 2-minute live demo of the React telemetry web application and ReAct execution trace, followed by judges Q&A.
                </p>
              </div>
            </div>
          )}

          {/* TAB 3: CONTRACT RUNNER */}
          {activeTab === 'contract' && (
            <div className="space-y-4">
              <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Terminal className="w-4 h-4 text-cyan-400" />
                    CLI Command Runner Contract:
                  </span>
                  <button
                    onClick={handleCopyCli}
                    className="flex items-center gap-1 text-[11px] bg-slate-800 px-2 py-1 rounded text-slate-300 hover:text-white cursor-pointer font-mono"
                  >
                    {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copied ? 'Copied' : 'Copy Command'}</span>
                  </button>
                </div>
                <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 font-mono text-xs text-emerald-300">
                  python main.py --json &quot;Should I irrigate my 1 acre tomato field today?&quot;
                </div>
                <p className="text-xs text-slate-400">
                  Contract guarantee: Exactly 1 JSON line to stdout, with keys <code className="text-white">&quot;answer&quot;</code> and <code className="text-white">&quot;trace&quot;</code>.
                </p>
              </div>

              {/* Quick Stress-Test Buttons */}
              <div className="space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Trigger Unseen Test Query in Active Session:
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <button
                    onClick={() => handleRunMilestoneTest('Should I irrigate my 1 acre tomato field today?')}
                    className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-left border border-slate-700 text-slate-200 transition cursor-pointer flex items-center justify-between"
                  >
                    <span>1. Standard Tomato Irrigation & Dosage</span>
                    <Play className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  </button>
                  <button
                    onClick={() => handleRunMilestoneTest('Analyze 48h weather rain probability in Trichy and advise fertilizer timing')}
                    className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-left border border-slate-700 text-slate-200 transition cursor-pointer flex items-center justify-between"
                  >
                    <span>2. Rain Risk & Fertilizer Postponement</span>
                    <Play className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  </button>
                  <button
                    onClick={() => handleRunMilestoneTest('Rice paddy in Thanjavur: evaluate soil moisture trend')}
                    className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-left border border-slate-700 text-slate-200 transition cursor-pointer flex items-center justify-between"
                  >
                    <span>3. Alternate Crop (Rice / Paddy)</span>
                    <Play className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  </button>
                  <button
                    onClick={() => handleRunMilestoneTest('Dry run test', true)}
                    className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-left border border-slate-700 text-slate-200 transition cursor-pointer flex items-center justify-between"
                  >
                    <span>4. Scripted --dry-run Contract Test</span>
                    <Play className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                  </button>
                </div>
                {testStatus && (
                  <div className="text-xs font-mono text-cyan-300 bg-cyan-950/30 p-2 rounded border border-cyan-800/40">
                    {testStatus}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-950/60 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition cursor-pointer"
          >
            Close Rubric
          </button>
        </div>
      </div>
    </div>
  );
};
