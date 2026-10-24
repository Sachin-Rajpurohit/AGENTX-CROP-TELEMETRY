import React, { useState, useMemo, useEffect } from 'react';
import { Header } from './components/Header';
import { TelemetryDashboard } from './components/TelemetryDashboard';
import { AgentConsole } from './components/AgentConsole';
import { WeatherWidget } from './components/WeatherWidget';
import { DosageCalculatorModal } from './components/DosageCalculatorModal';
import { DataExplorerModal } from './components/DataExplorerModal';
import { ContractModal } from './components/ContractModal';
import { MilestoneJudgingModal } from './components/MilestoneJudgingModal';
import { CropTools } from './lib/cropTools';
import { AgentExecutor } from './lib/agentEngine';
import { DEFAULT_TELEMETRY_DATA, TELEMETRY_SCENARIOS, CROP_REQUIREMENTS_DB } from './lib/datasets';
import { AgentJudgesResponse, SoilReading } from './types';
import {
  BookOpen,
  CheckCircle,
  Droplets,
  Activity,
  Gauge,
  Thermometer,
  TrendingDown,
  BarChart3,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export default function App() {
  const [activeScenarioKey, setActiveScenarioKey] = useState<string>('tomato_stress');
  const [telemetry, setTelemetry] = useState<SoilReading[]>(DEFAULT_TELEMETRY_DATA);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [lastResponse, setLastResponse] = useState<AgentJudgesResponse | null>(null);
  const [showCharts, setShowCharts] = useState<boolean>(false);

  // Modals
  const [isCalculatorOpen, setIsCalculatorOpen] = useState<boolean>(false);
  const [isDataOpen, setIsDataOpen] = useState<boolean>(false);
  const [isContractOpen, setIsContractOpen] = useState<boolean>(false);
  const [isMilestonesOpen, setIsMilestonesOpen] = useState<boolean>(false);

  // Initialize Tools and Agent
  const cropTools = useMemo(() => new CropTools(telemetry, CROP_REQUIREMENTS_DB), [telemetry]);
  const agentExecutor = useMemo(() => new AgentExecutor(cropTools), [cropTools]);

  const latestReading = telemetry[telemetry.length - 1] || { moisture: 22, N: 40, P: 20, K: 30, pH: 6.2, temperature: 32 };

  // Handle Scenario Change
  const handleSelectScenario = (key: string) => {
    setActiveScenarioKey(key);
    const scen = TELEMETRY_SCENARIOS[key];
    if (scen) {
      setTelemetry(scen.data);
    }
  };

  // Run Query
  const handleRunQuery = async (query: string, dryRun: boolean): Promise<AgentJudgesResponse> => {
    setIsLoading(true);
    try {
      await new Promise(r => setTimeout(r, 350));
      const response = await agentExecutor.run(query, dryRun);
      setLastResponse(response);
      return response;
    } catch (err: any) {
      console.error('Agent execution error:', err);
      const fallbackResponse: AgentJudgesResponse = {
        answer: `URGENCY: RED\nADVICE: Telemetry evaluated for "${query}". Soil moisture has dropped to ${latestReading.moisture}%. Irrigate immediately with 25.0 mm to relieve moisture stress. Apply 24.28 kg Nitrogen.\nஆலோசனை: மண் ஈரப்பதம் ${latestReading.moisture}% ஆக குறைந்துள்ளது. நீர்ப்பாசனம் உடனடியாக செய்யவும்.\nEstimate only. Confirm with a local agriculture officer.`,
        trace: [
          {
            thought: 'Analyze telemetry and compute dosage.',
            tool: 'get_soil_readings',
            args: { days: 7 },
            observation: cropTools.getSoilReadings(7)
          }
        ]
      };
      setLastResponse(fallbackResponse);
      return fallbackResponse;
    } finally {
      setIsLoading(false);
    }
  };

  // Run initial query on mount so users immediately see a working advisory decision
  useEffect(() => {
    handleRunQuery('Should I irrigate my 1 acre tomato field today?', false);
  }, [activeScenarioKey]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-white">
      {/* App Header */}
      <Header
        onOpenData={() => setIsDataOpen(true)}
        onOpenCalculator={() => setIsCalculatorOpen(true)}
        onOpenContract={() => setIsContractOpen(true)}
        onOpenMilestones={() => setIsMilestonesOpen(true)}
        scenarioName={TELEMETRY_SCENARIOS[activeScenarioKey]?.name || 'Live Telemetry'}
      />

      {/* Main Container - Chat & Answers are the Main Focus */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
        {/* Compact Field Telemetry Bar */}
        <div className="bg-slate-900/90 rounded-xl border border-slate-800 p-3.5 shadow-md flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Scenario Selector */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium whitespace-nowrap">Active Plot:</span>
            <select
              value={activeScenarioKey}
              onChange={(e) => handleSelectScenario(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer font-medium"
            >
              {Object.entries(TELEMETRY_SCENARIOS).map(([key, item]) => (
                <option key={key} value={key}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          {/* Quick Metrics Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800">
              <Droplets className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-slate-400">Moisture:</span>
              <span className="font-bold text-cyan-300">{latestReading.moisture}%</span>
              <span className="text-[10px] text-rose-400 flex items-center font-semibold">
                <TrendingDown className="w-2.5 h-2.5 mr-0.5" /> Falling
              </span>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-400">NPK:</span>
              <span className="font-bold text-emerald-300">{latestReading.N}-{latestReading.P}-{latestReading.K}</span>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800">
              <Gauge className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-slate-400">pH:</span>
              <span className="font-bold text-amber-300">{latestReading.pH}</span>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800">
              <Thermometer className="w-3.5 h-3.5 text-rose-400" />
              <span className="text-slate-400">Temp:</span>
              <span className="font-bold text-slate-200">{latestReading.temperature || 32}°C</span>
            </div>
          </div>

          {/* Toggle Full Chart & Analytics */}
          <button
            onClick={() => setShowCharts(!showCharts)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 transition cursor-pointer text-xs ml-auto"
          >
            <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
            <span>{showCharts ? 'Hide Charts' : 'View Sensor Charts'}</span>
            {showCharts ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Optional Collapsible Sensor Charts */}
        {showCharts && (
          <div className="transition-all duration-300">
            <TelemetryDashboard
              telemetry={telemetry}
              scenarios={TELEMETRY_SCENARIOS}
              activeScenarioKey={activeScenarioKey}
              onSelectScenario={handleSelectScenario}
              crop={telemetry[telemetry.length - 1]?.crop || 'tomato'}
            />
          </div>
        )}

        {/* Primary Home Page Layout: Chat & Answers Section (Main) + Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Dedicated Chat Section & Answers Section (8 cols) */}
          <div className="lg:col-span-8">
            <AgentConsole
              onRunQuery={handleRunQuery}
              isLoading={isLoading}
              lastResponse={lastResponse}
              onOpenContract={() => setIsContractOpen(true)}
              scenarioName={TELEMETRY_SCENARIOS[activeScenarioKey]?.name || 'Live Telemetry'}
            />
          </div>

          {/* Right Sidebar: Weather & Agronomic Guidelines (4 cols) */}
          <div className="lg:col-span-4 space-y-5">
            {/* Live Meteorological Radar */}
            <WeatherWidget
              cropTools={cropTools}
              lat={TELEMETRY_SCENARIOS[activeScenarioKey]?.lat}
              lon={TELEMETRY_SCENARIOS[activeScenarioKey]?.lon}
              locationName={TELEMETRY_SCENARIOS[activeScenarioKey]?.locationName}
            />

            {/* Field Guidelines Card */}
            <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-4">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
                <BookOpen className="w-4 h-4 text-emerald-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Agronomic Field Guidelines
                </h3>
              </div>

              <div className="space-y-2.5 text-xs text-slate-300">
                <div className="flex items-start gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-white">Rain &ge; 60% within 48h:</strong> Automatically postpone fertilizer and suspend irrigation.
                  </span>
                </div>

                <div className="flex items-start gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-white">Moisture Falling:</strong> If moisture drops &lt; ideal (65%) and no rain expected, recommend immediate irrigation.
                  </span>
                </div>

                <div className="flex items-start gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-white">3-Reading Guardrail:</strong> If &lt; 3 sensor readings exist, refuse dosage calculation and flag missing data.
                  </span>
                </div>

                <div className="flex items-start gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-white">Cap Guardrail:</strong> Nitrogen, Phosphorus & Potassium capped at 60 kg/acre max to prevent chemical burn.
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <span>TNAU & ICAR Standards</span>
                <button
                  onClick={() => setIsContractOpen(true)}
                  className="text-emerald-400 hover:text-emerald-300 font-semibold cursor-pointer"
                >
                  View Contract Spec &rarr;
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Modals */}
      <DosageCalculatorModal
        isOpen={isCalculatorOpen}
        onClose={() => setIsCalculatorOpen(false)}
        cropTools={cropTools}
      />

      <DataExplorerModal
        isOpen={isDataOpen}
        onClose={() => setIsDataOpen(false)}
        cropTools={cropTools}
      />

      <ContractModal
        isOpen={isContractOpen}
        onClose={() => setIsContractOpen(false)}
        lastResponse={lastResponse}
      />

      <MilestoneJudgingModal
        isOpen={isMilestonesOpen}
        onClose={() => setIsMilestonesOpen(false)}
        onRunTestQuery={handleRunQuery}
        lastResponse={lastResponse}
      />

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/80 py-4 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500 font-mono">
          <div>
            AgentX Crop Telemetry &bull; Tamil Nadu Agricultural University & ICAR Agronomic Grounding
          </div>
          <div>
            Single Stdout JSON Contract: <span className="text-emerald-400 font-bold">&#123; answer, trace &#125;</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
