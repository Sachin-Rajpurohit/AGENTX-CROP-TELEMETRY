import React, { useState } from 'react';
import { AgentJudgesResponse } from '../types';
import { X, Copy, Check, Download, Terminal, CheckCircle2, AlertCircle } from 'lucide-react';

interface ContractModalProps {
  isOpen: boolean;
  onClose: () => void;
  lastResponse: AgentJudgesResponse | null;
}

export const ContractModal: React.FC<ContractModalProps> = ({
  isOpen,
  onClose,
  lastResponse
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const jsonString = lastResponse
    ? JSON.stringify(lastResponse, null, 2)
    : JSON.stringify(
        {
          answer: 'No query executed yet. Run a query in the console.',
          trace: []
        },
        null,
        2
      );

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agentx-telemetry-contract-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Automated judging contract checks
  const hasAnswer = !!lastResponse?.answer;
  const hasTrace = Array.isArray(lastResponse?.trace);
  const traceCount = lastResponse?.trace.length ?? 0;
  const adheresStepCap = traceCount <= 6;
  const hasGrounding = traceCount > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Judges Contract JSON Output (<code className="text-xs text-blue-300">--json</code>)
              </h3>
              <p className="text-xs text-slate-400">
                Single stdout JSON line specification: <code className="text-slate-300">{"{ answer, trace }"}</code>
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

        {/* Validation Badges */}
        <div className="px-5 py-3 bg-slate-950/40 border-b border-slate-800/80 flex flex-wrap gap-2 text-xs">
          <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800/80 text-slate-300">
            {hasAnswer ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <AlertCircle className="w-3.5 h-3.5 text-amber-400" />}
            <span>Answer String: {hasAnswer ? 'Valid' : 'Missing'}</span>
          </div>
          <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800/80 text-slate-300">
            {hasGrounding ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <AlertCircle className="w-3.5 h-3.5 text-amber-400" />}
            <span>Tool Trace: {traceCount} steps</span>
          </div>
          <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800/80 text-slate-300">
            {adheresStepCap ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
            <span>Loop Cap Guard: {traceCount} / 6</span>
          </div>
        </div>

        {/* JSON Viewer */}
        <div className="p-5">
          <div className="relative">
            <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-emerald-300 overflow-x-auto max-h-[420px] overflow-y-auto leading-relaxed">
              {jsonString}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between">
          <span className="text-[11px] text-slate-500 font-mono">
            Complies with AgentX Challenge automated evaluation harness
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition cursor-pointer"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 text-xs font-bold rounded-lg transition cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span>Download .json</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
