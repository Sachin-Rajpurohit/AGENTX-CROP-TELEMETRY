import React from 'react';
import { SoilReading } from '../types';
import { Droplets, Activity, Gauge, Thermometer, Wind, AlertTriangle, CheckCircle2, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

interface TelemetryDashboardProps {
  telemetry: SoilReading[];
  scenarios: Record<string, { name: string; description: string; data: SoilReading[] }>;
  activeScenarioKey: string;
  onSelectScenario: (key: string) => void;
  crop: string;
}

export const TelemetryDashboard: React.FC<TelemetryDashboardProps> = ({
  telemetry,
  scenarios,
  activeScenarioKey,
  onSelectScenario,
  crop
}) => {
  const latest = telemetry[telemetry.length - 1] || { moisture: 0, N: 0, P: 0, K: 0, pH: 7 };
  const count = telemetry.length;

  // Calculate simple trend for moisture
  const moistureValues = telemetry.map(t => Number(t.moisture)).filter(v => !isNaN(v));
  let slope = 0;
  let trendStatus: 'falling' | 'rising' | 'stable' = 'stable';

  if (moistureValues.length >= 3) {
    const n = moistureValues.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    for (let i = 0; i < n; i++) {
      sumX += i;
      sumY += moistureValues[i];
      sumXY += i * moistureValues[i];
      sumXX += i * i;
    }
    const denom = n * sumXX - sumX * sumX;
    slope = denom === 0 ? 0 : (n * sumXY - sumX * sumY) / denom;
    trendStatus = slope < -0.05 ? 'falling' : slope > 0.05 ? 'rising' : 'stable';
  }

  // Format data for chart
  const chartData = telemetry.map((r, i) => ({
    name: r.timestamp ? r.timestamp.split(' ')[0].slice(5) : `R${i + 1}`,
    moisture: Number(r.moisture) || 0,
    nitrogen: Number(r.N) || 0,
    phosphorus: Number(r.P) || 0,
    potassium: Number(r.K) || 0,
    idealMoisture: 65
  }));

  const moistureColor =
    latest.moisture < 35 ? 'text-rose-400' : latest.moisture < 55 ? 'text-amber-400' : 'text-emerald-400';

  return (
    <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-5">
      {/* Scenario header and selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 -ml-4.5"></span>
            <h2 className="text-base font-bold text-white tracking-wide">
              LIVE SOIL SENSOR TELEMETRY
            </h2>
            <span className="text-xs text-slate-400 font-mono">
              ({count} readings)
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time root-zone sensor node array at 300 mm depth
          </p>
        </div>

        {/* Dataset Scenario Switcher */}
        <div className="flex items-center gap-2">
          <label htmlFor="scenario-select" className="text-xs text-slate-400 font-medium whitespace-nowrap">
            Telemetry Scenario:
          </label>
          <select
            id="scenario-select"
            value={activeScenarioKey}
            onChange={(e) => onSelectScenario(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
          >
            {Object.entries(scenarios).map(([key, item]) => (
              <option key={key} value={key}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {count < 3 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-200">
            <span className="font-semibold">Guardrail Warning:</span> Sensor has only {count} readings. The ReAct agent requires at least 3 historical readings to verify trends before calculating fertilizer or irrigation dosage.
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Moisture */}
        <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800/90 relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 flex items-center gap-1">
              <Droplets className="w-3.5 h-3.5 text-cyan-400" /> Moisture
            </span>
            {trendStatus === 'falling' && (
              <span className="inline-flex items-center gap-0.5 text-[10px] text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded">
                <TrendingDown className="w-3 h-3" /> Falling
              </span>
            )}
            {trendStatus === 'rising' && (
              <span className="inline-flex items-center gap-0.5 text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                <TrendingUp className="w-3 h-3" /> Rising
              </span>
            )}
            {trendStatus === 'stable' && (
              <span className="inline-flex items-center gap-0.5 text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                <Minus className="w-3 h-3" /> Stable
              </span>
            )}
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className={`text-2xl font-extrabold ${moistureColor}`}>
              {latest.moisture ?? '--'}
            </span>
            <span className="text-xs text-slate-400">%</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500 flex justify-between">
            <span>Ideal: 65%</span>
            <span>Slope: {slope.toFixed(2)}</span>
          </div>
        </div>

        {/* Nitrogen */}
        <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800/90 hover:border-slate-700 transition">
          <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-emerald-400" /> Nitrogen (N)
          </span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-white">
              {latest.N ?? '--'}
            </span>
            <span className="text-xs text-slate-400">kg/ha</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500 flex justify-between">
            <span>Ideal: 100</span>
            <span className={latest.N < 70 ? 'text-amber-400' : 'text-emerald-400'}>
              {latest.N < 100 ? `Deficit: ${100 - latest.N}` : 'Optimal'}
            </span>
          </div>
        </div>

        {/* Phosphorus */}
        <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800/90 hover:border-slate-700 transition">
          <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-blue-400" /> Phosphorus (P)
          </span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-white">
              {latest.P ?? '--'}
            </span>
            <span className="text-xs text-slate-400">kg/ha</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500 flex justify-between">
            <span>Ideal: 50</span>
            <span className={latest.P < 30 ? 'text-amber-400' : 'text-emerald-400'}>
              {latest.P < 50 ? `Deficit: ${50 - latest.P}` : 'Optimal'}
            </span>
          </div>
        </div>

        {/* Potassium */}
        <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800/90 hover:border-slate-700 transition">
          <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-purple-400" /> Potassium (K)
          </span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-white">
              {latest.K ?? '--'}
            </span>
            <span className="text-xs text-slate-400">kg/ha</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500 flex justify-between">
            <span>Ideal: 60</span>
            <span className={latest.K < 40 ? 'text-amber-400' : 'text-emerald-400'}>
              {latest.K < 60 ? `Deficit: ${60 - latest.K}` : 'Optimal'}
            </span>
          </div>
        </div>

        {/* Soil pH */}
        <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800/90 hover:border-slate-700 transition">
          <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Gauge className="w-3.5 h-3.5 text-amber-400" /> Soil pH
          </span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-amber-300">
              {latest.pH ?? 6.4}
            </span>
            <span className="text-xs text-slate-400">pH</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500 flex justify-between">
            <span>Range: 6.0-7.0</span>
            <span className="text-emerald-400">Slightly Acidic</span>
          </div>
        </div>

        {/* Ambient Climate */}
        <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800/90 hover:border-slate-700 transition">
          <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Thermometer className="w-3.5 h-3.5 text-rose-400" /> Climate
          </span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-xl font-extrabold text-white">
              {latest.temperature ?? 30}°C
            </span>
            <span className="text-xs text-slate-400 font-mono">/ {latest.humidity ?? 70}% RH</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500 flex justify-between">
            <span>Crop: {latest.crop || crop}</span>
            <span>Trichy</span>
          </div>
        </div>
      </div>

      {/* Telemetry Trend Chart */}
      <div className="bg-slate-950/50 rounded-xl p-4 border border-slate-800/80">
        <div className="flex items-center justify-between mb-3 text-xs">
          <div className="flex items-center gap-4">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-cyan-500 inline-block"></span>
              Soil Moisture (%)
            </span>
            <span className="text-slate-400 flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-emerald-400 inline-block"></span>
              Ideal Threshold (65%)
            </span>
            <span className="text-slate-400 hidden sm:flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-emerald-600/40 inline-block"></span>
              Nitrogen (N)
            </span>
          </div>
          <span className="text-slate-500 font-mono text-[11px]">
            Timeline: Recent readings
          </span>
        </div>

        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="moistureGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="nitrogenGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} domain={[0, 100]} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                  color: '#e2e8f0'
                }}
              />
              <Area
                type="monotone"
                dataKey="moisture"
                stroke="#06b6d4"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#moistureGradient)"
                name="Soil Moisture %"
              />
              <Area
                type="monotone"
                dataKey="nitrogen"
                stroke="#10b981"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                fillOpacity={1}
                fill="url(#nitrogenGradient)"
                name="Nitrogen kg/ha"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
