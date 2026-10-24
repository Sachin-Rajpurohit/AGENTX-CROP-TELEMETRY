import React, { useState } from 'react';
import { CropTools, MAX_NUTRIENT_KG_PER_ACRE, MAX_WATER_MM, ROOT_ZONE_MM } from '../lib/cropTools';
import { DosageResult } from '../types';
import { X, Calculator, ShieldAlert, CheckCircle2, Droplets, Sparkles, Scale, Info } from 'lucide-react';

interface DosageCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  cropTools: CropTools;
}

export const DosageCalculatorModal: React.FC<DosageCalculatorModalProps> = ({
  isOpen,
  onClose,
  cropTools
}) => {
  const [crop, setCrop] = useState('tomato');
  const [stage, setStage] = useState('flowering');
  const [acres, setAcres] = useState(1.0);

  if (!isOpen) return null;

  const dosageRaw = cropTools.calculateDosage(crop, acres, stage);
  const dosageData: DosageResult = JSON.parse(dosageRaw);

  const stagesByCrop: Record<string, string[]> = {
    tomato: ['seedling', 'vegetative', 'flowering', 'fruiting'],
    rice: ['seedling', 'tillering', 'flowering', 'ripening'],
    maize: ['seedling', 'vegetative', 'tasseling', 'grain_filling'],
    cotton: ['seedling', 'vegetative', 'flowering', 'boll_development'],
    banana: ['vegetative', 'shooting', 'bunch_development'],
    groundnut: ['vegetative', 'flowering', 'peg_formation', 'pod_filling']
  };

  const availableStages = stagesByCrop[crop] || ['seedling', 'vegetative', 'flowering', 'fruiting'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden my-8">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Agronomic Dosage & Irrigation Calculator
              </h3>
              <p className="text-xs text-slate-400">
                Formula: Deficit / 2.471 * Acres with TNAU/ICAR safety guardrails
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

        {/* Modal Content */}
        <div className="p-5 space-y-6">
          {/* Input Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <div>
              <label htmlFor="modal-crop-select" className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Target Crop
              </label>
              <select
                id="modal-crop-select"
                value={crop}
                onChange={(e) => {
                  setCrop(e.target.value);
                  setStage(stagesByCrop[e.target.value]?.[0] || 'flowering');
                }}
                className="w-full bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2 focus:ring-1 focus:ring-emerald-500 cursor-pointer"
              >
                <option value="tomato">Tomato (Solanum lycopersicum)</option>
                <option value="rice">Rice / Paddy (Oryza sativa)</option>
                <option value="maize">Maize / Corn (Zea mays)</option>
                <option value="cotton">Cotton (Gossypium)</option>
                <option value="banana">Banana (Musa)</option>
                <option value="groundnut">Groundnut (Arachis hypogaea)</option>
              </select>
            </div>

            <div>
              <label htmlFor="modal-stage-select" className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Growth Stage
              </label>
              <select
                id="modal-stage-select"
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2 focus:ring-1 focus:ring-emerald-500 cursor-pointer capitalize"
              >
                {availableStages.map((s) => (
                  <option key={s} value={s}>
                    {s.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="modal-acres-input" className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Field Area (Acres): <span className="text-emerald-400 font-bold">{acres}</span>
              </label>
              <input
                id="modal-acres-input"
                type="number"
                min="0.1"
                max="50"
                step="0.5"
                value={acres}
                onChange={(e) => setAcres(Math.max(0.1, parseFloat(e.target.value) || 1))}
                className="w-full bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2 focus:ring-1 focus:ring-emerald-500"
              />
            </div>
          </div>

          {/* Results Display */}
          {dosageData.error ? (
            <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-center gap-3 text-rose-300 text-sm">
              <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
              <span>{dosageData.error}</span>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Nutrients Table */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                  <Scale className="w-4 h-4 text-emerald-400" />
                  Fertilizer Nutrient Deficit & Capped Dose
                </h4>
                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800">
                      <tr>
                        <th className="p-3">Nutrient</th>
                        <th className="p-3">Current Soil Level</th>
                        <th className="p-3">Ideal Level</th>
                        <th className="p-3">Deficit (kg/ha)</th>
                        <th className="p-3">Calculated Dose ({acres} acre)</th>
                        <th className="p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300">
                      {['N', 'P', 'K'].map((nut) => {
                        const item = (dosageData.dosage as any)?.[nut];
                        if (!item) return null;
                        const isCapped = item.dose_kg === MAX_NUTRIENT_KG_PER_ACRE * acres;
                        return (
                          <tr key={nut} className="hover:bg-slate-800/40">
                            <td className="p-3 font-bold text-white flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                              {nut === 'N' ? 'Nitrogen (N)' : nut === 'P' ? 'Phosphorus (P)' : 'Potassium (K)'}
                            </td>
                            <td className="p-3 font-mono">{item.current} kg/ha</td>
                            <td className="p-3 font-mono text-cyan-300">{item.ideal} kg/ha</td>
                            <td className="p-3 font-mono text-amber-300">
                              {item.deficit > 0 ? `+${item.deficit}` : '0 (Met)'}
                            </td>
                            <td className="p-3 font-mono font-bold text-emerald-400 text-sm">
                              {item.dose_kg} kg
                            </td>
                            <td className="p-3">
                              {isCapped ? (
                                <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded font-semibold">
                                  Safety Capped
                                </span>
                              ) : (
                                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-semibold">
                                  Within Limits
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Water Requirement Card */}
              {dosageData.dosage?.water && (
                <div className="bg-cyan-950/30 border border-cyan-800/40 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="p-2.5 rounded-xl bg-cyan-500/20 text-cyan-400 mt-0.5">
                      <Droplets className="w-5 h-5" />
                    </div>
                    <div>
                      <h5 className="text-sm font-bold text-white">
                        Irrigation Requirement (Root Zone: {ROOT_ZONE_MM} mm)
                      </h5>
                      <p className="text-xs text-slate-300 mt-0.5">
                        Current Moisture: <span className="font-semibold text-cyan-300">{dosageData.dosage.water.current_pct}%</span> | Target: <span className="font-semibold text-cyan-300">{dosageData.dosage.water.ideal_pct}%</span>
                      </p>
                    </div>
                  </div>
                  <div className="text-right sm:border-l sm:border-cyan-800/50 sm:pl-4">
                    <div className="text-lg font-extrabold text-cyan-300">
                      {dosageData.dosage.water.irrigation_mm} mm
                    </div>
                    <div className="text-xs font-mono text-slate-400">
                      {dosageData.dosage.water.litres.toLocaleString()} Litres ({acres} acre)
                    </div>
                  </div>
                </div>
              )}

              {/* Notes & Guardrails */}
              {dosageData.notes.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-xs text-amber-200 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4 text-amber-400" /> Agronomic Safety Guardrail
                  </div>
                  {dosageData.notes.map((note, i) => (
                    <div key={i}>• {note}</div>
                  ))}
                </div>
              )}

              {/* Assumptions */}
              <div className="text-[11px] text-slate-500 bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-start gap-2">
                <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-slate-400">Assumptions: </span>
                  {dosageData.assumptions}
                  <div className="mt-1 text-slate-600">Source: {dosageData.requirements_source}</div>
                </div>
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
            Close Calculator
          </button>
        </div>
      </div>
    </div>
  );
};
