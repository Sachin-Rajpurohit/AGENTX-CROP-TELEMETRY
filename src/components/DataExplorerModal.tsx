import React, { useState } from 'react';
import { CropTools } from '../lib/cropTools';
import { X, Database, Search, FileSpreadsheet, Code2 } from 'lucide-react';
import { CROP_REQUIREMENTS_DB } from '../lib/datasets';

interface DataExplorerModalProps {
  isOpen: boolean;
  onClose: () => void;
  cropTools: CropTools;
}

export const DataExplorerModal: React.FC<DataExplorerModalProps> = ({
  isOpen,
  onClose,
  cropTools
}) => {
  const [selectedFile, setSelectedFile] = useState<string>('soil_telemetry.csv');
  const [sqlQuery, setSqlQuery] = useState<string>('SELECT moisture, N, P, K FROM data WHERE moisture < 30');
  const [sqlResult, setSqlResult] = useState<string | null>(null);

  if (!isOpen) return null;

  const files = [
    { name: 'soil_telemetry.csv', desc: 'Active 300mm Root-Zone Sensor Telemetry' },
    { name: 'crop_requirements.json', desc: 'TNAU & ICAR Agronomic Benchmark Standards' },
    { name: 'tomato irrigation dataset.csv', desc: '3,000 Readings Tomato Evapotranspiration Dataset' },
    { name: 'Crop_recommendation.csv', desc: '2,200 Rows Kaggle Multi-Crop Requirements' }
  ];

  const handleRunSql = () => {
    const res = cropTools.sqlQuery(selectedFile, sqlQuery);
    setSqlResult(res);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Data Files & SQL Query Explorer
              </h3>
              <p className="text-xs text-slate-400">
                Inspect local agricultural datasets and execute SQL tool queries
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

        {/* Content */}
        <div className="p-5 space-y-5">
          {/* File Tabs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {files.map((f) => (
              <button
                key={f.name}
                onClick={() => {
                  setSelectedFile(f.name);
                  setSqlResult(null);
                }}
                className={`p-2.5 rounded-xl border text-left transition cursor-pointer ${
                  selectedFile === f.name
                    ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <div className="text-xs font-bold truncate flex items-center gap-1.5">
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  {f.name}
                </div>
                <div className="text-[10px] text-slate-500 truncate mt-0.5">
                  {f.desc}
                </div>
              </button>
            ))}
          </div>

          {/* SQL Query Bar (matching sql_query tool) */}
          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold flex items-center gap-1">
                <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                SQL Query Tool (Table: `data`)
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                tools/data_query.py: sql_query
              </span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={sqlQuery}
                onChange={(e) => setSqlQuery(e.target.value)}
                placeholder="SELECT column FROM data WHERE ..."
                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
              <button
                onClick={handleRunSql}
                className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs rounded-lg transition cursor-pointer"
              >
                Execute
              </button>
            </div>
          </div>

          {/* Display Output */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-400">
              {sqlResult ? 'Query Result (JSON):' : `Preview of ${selectedFile}:`}
            </div>
            <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-72 overflow-y-auto">
              {sqlResult
                ? sqlResult
                : selectedFile === 'crop_requirements.json'
                ? JSON.stringify(CROP_REQUIREMENTS_DB, null, 2)
                : cropTools.readFile(selectedFile, 3000)}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-950/60 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition cursor-pointer"
          >
            Close Explorer
          </button>
        </div>
      </div>
    </div>
  );
};
